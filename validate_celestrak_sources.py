"""
Validate and repair CelesTrak sources in MongoDB.

This script:
1. Checks all satellites for TLE data in canonical section
2. Ensures they have corresponding celestrak source nodes
3. Extracts and repairs any missing source entries
4. Updates canonical sections if needed
"""

from db import connect_mongodb, disconnect_mongodb, create_satellite_document
from pymongo import MongoClient
import sys


def validate_and_repair_celestrak_sources():
    """Check all documents and repair missing celestrak sources."""
    
    client = MongoClient('localhost:27017')
    db = client['kessler']
    collection = db['satellites']
    
    total_docs = collection.count_documents({})
    docs_with_tle = 0
    docs_with_celestrak_source = 0
    docs_needing_repair = 0
    repaired = 0
    
    print(f"📊 Validating {total_docs} documents...\n")
    
    for idx, doc in enumerate(collection.find(), 1):
        identifier = doc.get('identifier', 'unknown')
        canonical = doc.get('canonical', {})
        sources = doc.get('sources', {})
        
        # Check if document has TLE data in canonical
        has_tle_line1 = canonical.get('tle', {}).get('line1')
        has_tle_line2 = canonical.get('tle', {}).get('line2')
        has_orbit = canonical.get('orbit', {})
        
        if has_tle_line1 or has_tle_line2 or (has_orbit and has_orbit != {}):
            docs_with_tle += 1
            
            # Check if celestrak source exists
            if 'celestrak' in sources:
                docs_with_celestrak_source += 1
            else:
                # Need to repair: create celestrak source from canonical TLE data
                docs_needing_repair += 1
                
                celestrak_data = {
                    "name": canonical.get('name', ''),
                    "international_designator": canonical.get('international_designator', ''),
                }
                
                # Extract TLE if present
                if has_tle_line1:
                    celestrak_data['tle_line1'] = canonical['tle']['line1']
                if has_tle_line2:
                    celestrak_data['tle_line2'] = canonical['tle']['line2']
                
                # Extract orbital parameters if present
                if has_orbit:
                    for key in ['apogee_km', 'perigee_km', 'inclination_degrees', 
                               'period_minutes', 'semi_major_axis_km', 'eccentricity', 
                               'mean_motion_rev_day']:
                        if key in has_orbit:
                            celestrak_data[key] = has_orbit[key]
                
                # Create/update document with celestrak source
                try:
                    create_satellite_document(identifier, 'celestrak', celestrak_data)
                    repaired += 1
                    
                    if repaired % 100 == 0 or repaired <= 5:
                        print(f"  ✓ {repaired} repaired: {identifier}")
                except Exception as e:
                    print(f"  ❌ Error repairing {identifier}: {e}")
        
        if idx % 500 == 0:
            print(f"  Scanned {idx}/{total_docs}...")
    
    print("\n" + "="*60)
    print("📊 CelesTrak Source Validation Report")
    print("="*60)
    print(f"Total documents:              {total_docs}")
    print(f"Documents with TLE data:      {docs_with_tle}")
    print(f"With celestrak source:        {docs_with_celestrak_source}")
    print(f"Missing celestrak source:     {docs_needing_repair}")
    print(f"Repaired:                     {repaired}")
    print("="*60)
    
    if repaired > 0:
        print(f"\n✅ Successfully repaired {repaired} documents")
    else:
        print(f"\n✅ All documents valid - no repairs needed")


def show_sample_documents():
    """Show sample documents with celestrak sources."""
    client = MongoClient('localhost:27017')
    db = client['kessler']
    collection = db['satellites']
    
    print("\n" + "="*60)
    print("📋 Sample Documents with CelesTrak Sources")
    print("="*60)
    
    samples = collection.find(
        {'sources.celestrak': {'$exists': True}},
        limit=5
    )
    
    for doc in samples:
        identifier = doc.get('identifier', 'unknown')
        name = doc.get('canonical', {}).get('name', 'Unknown')
        sources_available = doc.get('metadata', {}).get('sources_available', [])
        
        print(f"\n🛰️  {name} ({identifier})")
        print(f"    Sources: {', '.join(sources_available)}")
        
        canonical = doc.get('canonical', {})
        if 'tle' in canonical and canonical['tle']:
            tle = canonical['tle']
            if 'line1' in tle:
                print(f"    TLE Line 1: {tle['line1'][:50]}...")
        
        if 'orbit' in canonical and canonical['orbit']:
            orbit = canonical['orbit']
            if 'apogee_km' in orbit:
                print(f"    Apogee: {orbit['apogee_km']} km")
            if 'inclination_degrees' in orbit:
                print(f"    Inclination: {orbit['inclination_degrees']}°")


if __name__ == "__main__":
    if not connect_mongodb():
        print("❌ Failed to connect to MongoDB")
        sys.exit(1)
    
    try:
        print("\n" + "="*60)
        print("🔍 CelesTrak Source Validation & Repair")
        print("="*60 + "\n")
        
        validate_and_repair_celestrak_sources()
        show_sample_documents()
        
        print("\n" + "="*60)
        print("✨ Validation Complete")
        print("="*60 + "\n")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        disconnect_mongodb()
