"""
Import TLE data from CelesTrak and merge with existing MongoDB documents.

This script:
1. Fetches TLE data from CelesTrak
2. Extracts orbital parameters from TLE
3. Matches to existing satellites in MongoDB by international designator
4. Updates/creates documents with "celestrak" source
5. Canonical section automatically updates based on source priority (UNOOSA > CelesTrak > Space-Track)
"""

import requests
import math
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional
from db import connect_mongodb, disconnect_mongodb, create_satellite_document, find_satellite
import sys

TLE_SOURCES = [
    ("stations", "https://celestrak.org/NORAD/elements/stations.txt", "Space Stations"),
    ("resource", "https://celestrak.org/NORAD/elements/resource.txt", "Earth Resources"),
    ("sarsat", "https://celestrak.org/NORAD/elements/sarsat.txt", "Search & Rescue"),
    ("dmc", "https://celestrak.org/NORAD/elements/dmc.txt", "Disaster Monitoring"),
    ("weather", "https://celestrak.org/NORAD/elements/weather.txt", "Weather"),
    ("geo", "https://celestrak.org/NORAD/elements/geo.txt", "Geostationary"),
    ("iss", "https://celestrak.org/NORAD/elements/iss.txt", "ISS & Associated"),
    ("high-earth", "https://celestrak.org/NORAD/elements/high-earth.txt", "High Earth Orbit"),
    ("cubesats", "https://celestrak.org/NORAD/elements/cubesats.txt", "CubeSats"),
]


def extract_orbital_parameters(tle_line1: str, tle_line2: str) -> Dict:
    """
    Calculate orbital parameters from TLE lines.
    
    TLE format:
    Line 1: 1 NNNNNC UUUUUUUU NNNNN   NNNNN NNNNNMMMM NNNNNMMMMN NNNNNMMMMN NNNNN
    Line 2: 2 NNNNN  NNN.NNNN NNN.NNNN NNNNNNN NNN.NNNN NNN.NNNN NN.NNNNNNNNNNNNNN
    
    Returns: Dict with orbital parameters
    """
    try:
        inclination = float(tle_line2[8:16])
        eccentricity = float('0.' + tle_line2[26:33])
        mean_motion_rev_day = float(tle_line2[52:63])
        
        period_minutes = 1440.0 / mean_motion_rev_day
        
        GM = 398600.4418
        n_rad_per_sec = (mean_motion_rev_day * 2 * math.pi) / 86400.0
        a = (GM / (n_rad_per_sec * n_rad_per_sec)) ** (1.0/3.0)
        
        earth_radius = 6378.137
        apogee = a * (1 + eccentricity) - earth_radius
        perigee = a * (1 - eccentricity) - earth_radius
        
        return {
            'apogee_km': round(apogee, 2),
            'perigee_km': round(perigee, 2),
            'inclination_degrees': round(inclination, 2),
            'period_minutes': round(period_minutes, 2),
            'semi_major_axis_km': round(a, 2),
            'eccentricity': round(eccentricity, 6),
            'mean_motion_rev_day': round(mean_motion_rev_day, 6),
        }
    except (ValueError, IndexError) as e:
        return {'error': str(e)}


def parse_tle_file(content: str) -> List[Tuple[str, str, str]]:
    """
    Parse TLE file content and return list of (name, line1, line2) tuples.
    """
    tle_data = []
    lines = content.split('\n')
    
    i = 0
    while i < len(lines) - 2:
        sat_name = lines[i].strip()
        tle_line1 = lines[i + 1].strip()
        tle_line2 = lines[i + 2].strip()
        
        if (tle_line1.startswith('1 ') and len(tle_line1) >= 69 and
            tle_line2.startswith('2 ') and len(tle_line2) >= 69):
            try:
                intl_desig = tle_line1[9:17].strip()
                if intl_desig:
                    tle_data.append((sat_name, tle_line1, tle_line2, intl_desig))
            except Exception:
                pass
        i += 3
    
    return tle_data


def fetch_and_parse_tle_source(url: str, category: str, display_name: str) -> Tuple[List, int]:
    """
    Fetch TLE data from a CelesTrak source and parse it.
    
    Returns: (list of TLE tuples, number of TLEs fetched)
    """
    try:
        print(f"\n📡 Fetching {display_name} from {category}...")
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            print(f"  ⚠️  HTTP {response.status_code}")
            return [], 0
        
        tle_data = parse_tle_file(response.text)
        print(f"  ✓ Parsed {len(tle_data)} satellites")
        return tle_data, len(tle_data)
    
    except requests.Timeout:
        print(f"  ❌ Timeout fetching {category}")
        return [], 0
    except Exception as e:
        print(f"  ❌ Error fetching {category}: {e}")
        return [], 0


def match_designator_format(original_designator: str) -> Optional[str]:
    """
    Try to convert designator format between YYNNNSSG and YYYY-NNNX formats.
    
    Examples:
    - "98067A" (YYNNNSSG) -> "1998-067A" (YYYY-NNNX)
    - "1998-067A" (YYYY-NNNX) -> "98067A" (YYNNNSSG)
    """
    try:
        if '-' in original_designator:
            parts = original_designator.split('-')
            if len(parts) == 2:
                year = parts[0]
                rest = parts[1]
                yy = year[-2:]
                seq = rest[:-1] if rest[-1].isalpha() else rest
                piece = rest[-1] if rest[-1].isalpha() else ""
                
                if piece:
                    return f"{yy}{int(seq):0>3}{piece}"
                else:
                    return f"{yy}{int(seq):0>3}"
        else:
            if len(original_designator) >= 5:
                yy = original_designator[:2]
                seq = original_designator[2:5]
                piece = original_designator[5:] if len(original_designator) > 5 else ""
                
                year = int(yy)
                if year > 57:
                    year += 1900
                else:
                    year += 2000
                
                if piece:
                    return f"{year}-{int(seq):03d}{piece}"
                else:
                    return f"{year}-{int(seq):03d}"
    except Exception:
        pass
    
    return None


def import_celestrak_tle():
    """
    Import TLE data from CelesTrak and update MongoDB documents.
    """
    total_fetched = 0
    total_matched = 0
    total_created = 0
    total_updated = 0
    
    for category, url, display_name in TLE_SOURCES:
        tle_data, count = fetch_and_parse_tle_source(url, category, display_name)
        total_fetched += count
        
        if not tle_data:
            continue
        
        matched = 0
        created = 0
        updated = 0
        
        for sat_name, tle_line1, tle_line2, intl_desig in tle_data:
            orbital_params = extract_orbital_parameters(tle_line1, tle_line2)
            
            celestrak_data = {
                "name": sat_name,
                "international_designator": intl_desig,
                "tle_line1": tle_line1,
                "tle_line2": tle_line2,
            }
            
            if 'error' not in orbital_params:
                celestrak_data.update(orbital_params)
            
            existing = find_satellite(international_designator=intl_desig)
            
            if not existing:
                alt_designator = match_designator_format(intl_desig)
                if alt_designator:
                    existing = find_satellite(international_designator=alt_designator)
            
            if existing:
                create_satellite_document(existing['identifier'], 'celestrak', celestrak_data)
                matched += 1
                updated += 1
            else:
                create_satellite_document(intl_desig, 'celestrak', celestrak_data)
                created += 1
            
            if matched % 50 == 0 and matched > 0:
                print(f"  ✓ Processed {matched} satellites...")
        
        print(f"  📊 {category}: {matched} matched, {created} new, {updated} updated")
        total_matched += matched
        total_created += created
        total_updated += updated
    
    print("\n" + "="*60)
    print("🎯 CelesTrak Import Summary")
    print("="*60)
    print(f"Total TLE records fetched:  {total_fetched}")
    print(f"Matched to existing docs:   {total_matched}")
    print(f"New documents created:      {total_created}")
    print(f"Existing docs updated:      {total_updated}")
    print(f"Total documents in MongoDB: {total_matched + total_created}")
    print("="*60)
    print("\n✅ Canonical sections automatically updated based on source priority!")
    print("   Priority: UNOOSA > CelesTrak > Space-Track")
    print("\nUse /v2/satellite/{id} to see all source data\n")


def show_sample_document(designator: str = "1998-067A"):
    """Show a sample document with TLE data added"""
    print(f"\n📋 Sample Document (looking for something like ISS: {designator})...")
    
    sat = find_satellite(international_designator=designator)
    
    if not sat:
        print(f"  (Satellite {designator} not found in this import)")
        return
    
    print(f"\n✓ Found: {sat['canonical'].get('name', 'Unknown')}")
    print(f"  Identifier: {sat['identifier']}")
    print(f"  Sources available: {sat['metadata']['sources_available']}")
    
    if 'tle' in sat['canonical'] and sat['canonical']['tle']:
        print(f"\n  📡 TLE Data (from CelesTrak):")
        tle = sat['canonical']['tle']
        if 'line1' in tle:
            print(f"    Line 1: {tle['line1'][:50]}...")
        if 'line2' in tle:
            print(f"    Line 2: {tle['line2'][:50]}...")
    
    if 'orbit' in sat['canonical'] and sat['canonical']['orbit']:
        print(f"\n  🌍 Orbital Parameters (from CelesTrak):")
        orbit = sat['canonical']['orbit']
        for key, value in orbit.items():
            if key not in ['error']:
                print(f"    {key}: {value}")


if __name__ == "__main__":
    if not connect_mongodb():
        print("❌ Failed to connect to MongoDB")
        print("Make sure MongoDB is running on localhost:27017")
        sys.exit(1)
    
    try:
        print("\n" + "="*60)
        print("🛰️  CelesTrak TLE Data Import")
        print("="*60)
        
        import_celestrak_tle()
        show_sample_document()
    
    except KeyboardInterrupt:
        print("\n⚠️  Import interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        disconnect_mongodb()
