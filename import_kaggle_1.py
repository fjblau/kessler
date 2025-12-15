"""
Kaggle Satellite Catalog Import

Imports satellite data from the Kaggle current_catalog.csv as 'kaggle_1' source.
Matches satellites by NORAD ID and updates existing documents with envelope pattern.
"""

import pandas as pd
import sys
from db import connect_mongodb, disconnect_mongodb, create_satellite_document
from pymongo.errors import ConnectionFailure


def import_kaggle_catalog(csv_file):
    """Import Kaggle catalog data as kaggle_1 source"""
    print(f"📥 Importing Kaggle catalog from {csv_file}...")
    
    try:
        df = pd.read_csv(csv_file)
        collection = get_satellites_collection()
        
        count = 0
        matched = 0
        unmatched = []
        
        for idx, row in df.iterrows():
            norad_id = str(row.get('norad_id', '')).strip()
            
            if not norad_id or norad_id == 'nan':
                continue
            
            data = {
                'norad_id': norad_id,
                'name': str(row.get('name', '')).strip() if pd.notna(row.get('name')) else '',
                'object_type': str(row.get('object_type', '')).strip() if pd.notna(row.get('object_type')) else '',
                'satellite_constellation': str(row.get('satellite_constellation', '')).strip() if pd.notna(row.get('satellite_constellation')) else '',
                'country': str(row.get('country', '')).strip() if pd.notna(row.get('country')) else '',
                'data_source': str(row.get('data_source', '')).strip() if pd.notna(row.get('data_source')) else '',
                'snapshot_date': str(row.get('snapshot_date', '')).strip() if pd.notna(row.get('snapshot_date')) else '',
                'last_seen': str(row.get('last_seen', '')).strip() if pd.notna(row.get('last_seen')) else '',
                'altitude_category': str(row.get('altitude_category', '')).strip() if pd.notna(row.get('altitude_category')) else '',
                'orbital_band': str(row.get('orbital_band', '')).strip() if pd.notna(row.get('orbital_band')) else '',
                'congestion_risk': str(row.get('congestion_risk', '')).strip() if pd.notna(row.get('congestion_risk')) else '',
            }
            
            # Add numeric fields
            numeric_fields = {
                'altitude_km': 'float',
                'inclination': 'float',
                'eccentricity': 'float',
                'mean_motion': 'float',
                'launch_year_estimate': 'int',
                'days_in_orbit_estimate': 'int',
            }
            
            for field, field_type in numeric_fields.items():
                val = row.get(field)
                if pd.notna(val) and val != '':
                    try:
                        if field_type == 'float':
                            data[field] = float(val)
                        elif field_type == 'int':
                            data[field] = int(val)
                    except (ValueError, TypeError):
                        pass
            
            # Add epoch if present
            if pd.notna(row.get('epoch')) and row.get('epoch') != '':
                data['epoch'] = str(row.get('epoch', '')).strip()
            
            # Add orbit_lifetime_category if present
            if pd.notna(row.get('orbit_lifetime_category')) and row.get('orbit_lifetime_category') != '':
                data['orbit_lifetime_category'] = str(row.get('orbit_lifetime_category', '')).strip()
            
            # Try to find existing satellite by NORAD ID
            existing = collection.find_one({'sources.unoosa.norad_id': norad_id}) or \
                      collection.find_one({'sources.celestrak.norad_id': norad_id})
            
            if existing:
                identifier = existing.get('identifier')
                matched += 1
            else:
                # Use NORAD ID as identifier if no existing document found
                identifier = f"norad-{norad_id}"
                unmatched.append((norad_id, data.get('name', 'Unknown')))
            
            create_satellite_document(identifier, 'kaggle_1', data)
            count += 1
            
            if count % 500 == 0:
                print(f"  ✓ Processed {count} satellites ({matched} matched)...")
        
        print(f"\n✅ Successfully imported {count} satellites from Kaggle")
        print(f"   • {matched} matched to existing documents")
        print(f"   • {len(unmatched)} new documents created")
        
        if unmatched and len(unmatched) <= 20:
            print("\n   New satellites created:")
            for norad_id, name in unmatched:
                print(f"     - {norad_id}: {name}")
        elif len(unmatched) > 20:
            print(f"\n   (Showing first 20 of {len(unmatched)} new satellites)")
            for norad_id, name in unmatched[:20]:
                print(f"     - {norad_id}: {name}")
        
        return count, matched
    
    except Exception as e:
        print(f"❌ Error importing Kaggle data: {e}")
        raise


if __name__ == "__main__":
    from db import get_satellites_collection
    
    if not connect_mongodb():
        print("❌ Failed to connect to MongoDB")
        sys.exit(1)
    
    csv_file = "/Users/frankblau/Downloads/archive (2)/current_catalog.csv"
    
    try:
        total, matched = import_kaggle_catalog(csv_file)
        print(f"\n📊 Import Summary:")
        print(f"   Total: {total}")
        print(f"   Matched: {matched}")
        print(f"   New: {total - matched}")
    finally:
        disconnect_mongodb()
