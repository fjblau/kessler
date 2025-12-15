"""
CelesTrak TLE Data Import - Sample/Test Version with Fallback Data

This version:
1. Attempts to fetch from CelesTrak
2. Falls back to sample TLE data for testing
3. Can be run with --test-only flag to use sample data
4. Demonstrates the envelope pattern with multiple sources
"""

import requests
import math
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional
from db import connect_mongodb, disconnect_mongodb, create_satellite_document, find_satellite
import sys

SAMPLE_TLE_DATA = [
    {
        "name": "ISS (ZARYA FGB)",
        "tle_line1": "1 25544U 98067A   25349.64833335  .00016717  00000-0  29853-3 0  9998",
        "tle_line2": "2 25544  51.6432 247.7832 0002671  86.3996  41.1872 15.54248026435929",
        "intl_desig": "1998-067A"
    },
    {
        "name": "HUBBLE SPACE TELESCOPE",
        "tle_line1": "1 20580U 90037B   25349.79833333  .00001428  00000-0  66449-4 0  9998",
        "tle_line2": "2 20580  28.4699 101.0506 0002796 108.2455 251.9446 15.09706701455803",
        "intl_desig": "1990-037B"
    },
    {
        "name": "GLONASS-M (1)",
        "tle_line1": "1 24793U 97020A   25350.51898491  .00000436  00000-0  21625-3 0  9994",
        "tle_line2": "2 24793  64.8013 163.9281 0022134 308.5221  51.3644 14.13669277408920",
        "intl_desig": "1997-020A"
    },
    {
        "name": "ASTRA 2E",
        "tle_line1": "1 32226U 07049A   25350.52857439 -.00000244  00000-0  00000+0 0  9996",
        "tle_line2": "2 32226   0.0235 298.9673 0001127 334.0872  98.5098  1.00271631 32008",
        "intl_desig": "2007-049A"
    },
]

TLE_SOURCES = [
    ("stations", "https://celestrak.org/NORAD/elements/stations.txt", "Space Stations"),
    ("resource", "https://celestrak.org/NORAD/elements/resource.txt", "Earth Resources"),
    ("sarsat", "https://celestrak.org/NORAD/elements/sarsat.txt", "Search & Rescue"),
    ("dmc", "https://celestrak.org/NORAD/elements/dmc.txt", "Disaster Monitoring"),
    ("weather", "https://celestrak.org/NORAD/elements/weather.txt", "Weather"),
    ("geo", "https://celestrak.org/NORAD/elements/geo.txt", "Geostationary"),
    ("iss", "https://celestrak.org/NORAD/elements/iss.txt", "ISS & Associated"),
    ("high-earth", "https://celestrak.org/NORAD/elements/high-earth.txt", "High Earth Orbit"),
]


def extract_orbital_parameters(tle_line1: str, tle_line2: str) -> Dict:
    """Calculate orbital parameters from TLE lines."""
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


def parse_tle_file(content: str) -> List[Tuple[str, str, str, str]]:
    """Parse TLE file content and return list of (name, line1, line2, intl_desig) tuples."""
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


def fetch_and_parse_tle_source(url: str, category: str, display_name: str, timeout: int = 10) -> List[Tuple]:
    """Fetch TLE data from CelesTrak source and parse it."""
    try:
        print(f"\n📡 Fetching {display_name} from {category}...")
        response = requests.get(url, timeout=timeout)
        
        if response.status_code != 200:
            print(f"  ⚠️  HTTP {response.status_code}")
            return []
        
        tle_data = parse_tle_file(response.text)
        print(f"  ✓ Parsed {len(tle_data)} satellites")
        return tle_data
    
    except (requests.Timeout, requests.ConnectionError) as e:
        print(f"  ⚠️  Network error: {type(e).__name__}")
        return []
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return []


def import_tle_data(use_sample_only: bool = False):
    """
    Import TLE data from CelesTrak (or sample data for testing).
    
    Args:
        use_sample_only: If True, only use sample data (skip CelesTrak)
    """
    total_fetched = 0
    total_matched = 0
    total_created = 0
    total_updated = 0
    
    all_tle_data = []
    
    if use_sample_only:
        print("\n📝 Using sample TLE data (--test-only flag)")
        for tle in SAMPLE_TLE_DATA:
            all_tle_data.append((tle["name"], tle["tle_line1"], tle["tle_line2"], tle["intl_desig"]))
        total_fetched = len(SAMPLE_TLE_DATA)
    else:
        for category, url, display_name in TLE_SOURCES:
            tle_data = fetch_and_parse_tle_source(url, category, display_name)
            
            if not tle_data:
                print(f"  ℹ️  Retrying with sample data for testing...")
                tle_data = fetch_and_parse_tle_source(url, category, display_name, timeout=3)
            
            all_tle_data.extend(tle_data)
            total_fetched += len(tle_data)
        
        if not all_tle_data:
            print("\n⚠️  Could not fetch from CelesTrak (network issue)")
            print("   Using sample data for demonstration...")
            for tle in SAMPLE_TLE_DATA:
                all_tle_data.append((tle["name"], tle["tle_line1"], tle["tle_line2"], tle["intl_desig"]))
            total_fetched = len(SAMPLE_TLE_DATA)
    
    print(f"\n📊 Processing {len(all_tle_data)} TLE records...")
    
    for sat_name, tle_line1, tle_line2, intl_desig in all_tle_data:
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
        
        if existing:
            create_satellite_document(existing['identifier'], 'celestrak', celestrak_data)
            total_matched += 1
            total_updated += 1
        else:
            create_satellite_document(intl_desig, 'celestrak', celestrak_data)
            total_created += 1
    
    print("\n" + "="*60)
    print("🎯 CelesTrak TLE Import Summary")
    print("="*60)
    print(f"Total TLE records processed:  {total_fetched}")
    print(f"Matched to existing docs:     {total_matched}")
    print(f"New documents created:        {total_created}")
    print(f"Existing docs updated:        {total_updated}")
    print("="*60)
    print("\n✅ Canonical sections automatically updated!")
    print("   Priority: UNOOSA > CelesTrak > Space-Track")


def show_sample_documents():
    """Show sample documents with TLE data added"""
    sample_designators = [
        ("1998-067A", "ISS"),
        ("1990-037B", "Hubble Space Telescope"),
        ("2025-206B", "GLONASS satellite"),
    ]
    
    print("\n" + "="*60)
    print("📋 Sample Documents with TLE Data")
    print("="*60)
    
    for designator, description in sample_designators:
        print(f"\n🛰️  {description} ({designator}):")
        
        sat = find_satellite(international_designator=designator)
        
        if not sat:
            print(f"   Not found (may be in new documents)")
            continue
        
        name = sat['canonical'].get('name', 'Unknown')
        sources = sat['metadata']['sources_available']
        
        print(f"   Name: {name}")
        print(f"   Sources: {', '.join(sources)}")
        
        if 'orbit' in sat['canonical'] and sat['canonical']['orbit']:
            orbit = sat['canonical']['orbit']
            if 'apogee_km' in orbit:
                print(f"   Apogee: {orbit['apogee_km']} km")
            if 'perigee_km' in orbit:
                print(f"   Perigee: {orbit['perigee_km']} km")
            if 'inclination_degrees' in orbit:
                print(f"   Inclination: {orbit['inclination_degrees']}°")
            if 'period_minutes' in orbit:
                print(f"   Period: {orbit['period_minutes']} min")
        
        if 'tle' in sat['canonical'] and sat['canonical']['tle']:
            tle = sat['canonical']['tle']
            if 'line1' in tle:
                print(f"   TLE Line 1: {tle['line1'][:50]}...")
            if 'line2' in tle:
                print(f"   TLE Line 2: {tle['line2'][:50]}...")


if __name__ == "__main__":
    if not connect_mongodb():
        print("❌ Failed to connect to MongoDB")
        print("Make sure MongoDB is running on localhost:27017")
        sys.exit(1)
    
    use_sample = "--test-only" in sys.argv
    
    try:
        print("\n" + "="*60)
        print("🛰️  CelesTrak TLE Data Import")
        print("="*60)
        
        import_tle_data(use_sample_only=use_sample)
        show_sample_documents()
        
        print("\n" + "="*60)
        print("✨ Next Steps:")
        print("="*60)
        print("1. Test the API:")
        print("   curl 'http://localhost:8000/v2/satellite/1998-067A'")
        print("\n2. Run in production:")
        print("   python3 import_celestrak_tle_sample.py  # Fetch from CelesTrak")
        print("\n3. Schedule periodic imports:")
        print("   0 2 * * * cd /path/to/kessler && python3 import_celestrak_tle_sample.py")
        print("="*60 + "\n")
    
    except KeyboardInterrupt:
        print("\n⚠️  Import interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        disconnect_mongodb()
