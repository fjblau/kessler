#!/usr/bin/env python3
"""
Import satcat.csv and merge with existing UNOOSA registry.
Adds NORAD_CAT_ID to records and enriches orbital parameters.
"""

import pandas as pd
import sys
from pathlib import Path
from typing import Optional, Dict
from db import create_satellite_document, connect_mongodb, disconnect_mongodb

def normalize_intl_designator(designator: str) -> str:
    """Normalize international designator format (handle both YYYY-NNNA and 1957-001A)"""
    if not designator or pd.isna(designator):
        return ""
    
    designator = str(designator).strip().upper()
    
    # Already in standard format (YYYY-NNNA)
    if designator.count('-') == 1 and len(designator) in [8, 9, 10]:
        return designator
    
    return designator


def match_records(unoosa_df: pd.DataFrame, satcat_df: pd.DataFrame) -> Dict[str, Dict]:
    """
    Match UNOOSA records with satcat records by International Designator.
    Returns dict mapping intl_designator -> matched satcat record
    """
    matches = {}
    
    # Create a lookup dict from satcat using OBJECT_ID as key
    satcat_lookup = {}
    for idx, row in satcat_df.iterrows():
        object_id = str(row['OBJECT_ID']).strip().upper()
        if object_id:
            satcat_lookup[object_id] = row
    
    print(f"Loaded {len(satcat_lookup)} satcat records")
    
    matched_count = 0
    for idx, row in unoosa_df.iterrows():
        intl_desig = normalize_intl_designator(row['International Designator'])
        
        if not intl_desig:
            continue
        
        if intl_desig in satcat_lookup:
            matches[intl_desig] = satcat_lookup[intl_desig]
            matched_count += 1
    
    print(f"Matched {matched_count} records out of {len(unoosa_df)} UNOOSA records")
    return matches


def enrich_unoosa_with_satcat(unoosa_df: pd.DataFrame, satcat_matches: Dict) -> pd.DataFrame:
    """
    Add NORAD_CAT_ID and satcat data to UNOOSA dataframe.
    """
    # Add new columns if they don't exist
    if 'NORAD_CAT_ID' not in unoosa_df.columns:
        unoosa_df['NORAD_CAT_ID'] = None
    
    if 'SATCAT_OBJECT_TYPE' not in unoosa_df.columns:
        unoosa_df['SATCAT_OBJECT_TYPE'] = None
    
    if 'SATCAT_OPS_STATUS' not in unoosa_df.columns:
        unoosa_df['SATCAT_OPS_STATUS'] = None
    
    if 'SATCAT_RCS' not in unoosa_df.columns:
        unoosa_df['SATCAT_RCS'] = None
    
    if 'SATCAT_DECAY_DATE' not in unoosa_df.columns:
        unoosa_df['SATCAT_DECAY_DATE'] = None
    
    enriched_count = 0
    for idx, row in unoosa_df.iterrows():
        intl_desig = normalize_intl_designator(row['International Designator'])
        
        if intl_desig in satcat_matches:
            satcat_row = satcat_matches[intl_desig]
            
            # Add NORAD ID
            if pd.isna(unoosa_df.at[idx, 'NORAD_CAT_ID']):
                unoosa_df.at[idx, 'NORAD_CAT_ID'] = satcat_row['NORAD_CAT_ID']
                enriched_count += 1
            
            # Add satcat metadata
            unoosa_df.at[idx, 'SATCAT_OBJECT_TYPE'] = satcat_row['OBJECT_TYPE']
            unoosa_df.at[idx, 'SATCAT_OPS_STATUS'] = satcat_row['OPS_STATUS_CODE']
            unoosa_df.at[idx, 'SATCAT_RCS'] = satcat_row['RCS']
            unoosa_df.at[idx, 'SATCAT_DECAY_DATE'] = satcat_row['DECAY_DATE']
    
    print(f"Enriched {enriched_count} records with NORAD_CAT_ID")
    return unoosa_df


def enrich_orbital_params(unoosa_df: pd.DataFrame, satcat_matches: Dict) -> pd.DataFrame:
    """
    Fill missing orbital parameters from satcat data.
    """
    params_updated = 0
    
    for idx, row in unoosa_df.iterrows():
        intl_desig = normalize_intl_designator(row['International Designator'])
        
        if intl_desig not in satcat_matches:
            continue
        
        satcat_row = satcat_matches[intl_desig]
        
        # Fill missing apogee
        if pd.isna(row['Apogee (km)']) and pd.notna(satcat_row['APOGEE']):
            try:
                unoosa_df.at[idx, 'Apogee (km)'] = float(satcat_row['APOGEE'])
                params_updated += 1
            except:
                pass
        
        # Fill missing perigee
        if pd.isna(row['Perigee (km)']) and pd.notna(satcat_row['PERIGEE']):
            try:
                unoosa_df.at[idx, 'Perigee (km)'] = float(satcat_row['PERIGEE'])
                params_updated += 1
            except:
                pass
        
        # Fill missing inclination
        if pd.isna(row['Inclination (degrees)']) and pd.notna(satcat_row['INCLINATION']):
            try:
                unoosa_df.at[idx, 'Inclination (degrees)'] = float(satcat_row['INCLINATION'])
                params_updated += 1
            except:
                pass
        
        # Fill missing period
        if pd.isna(row['Period (minutes)']) and pd.notna(satcat_row['PERIOD']):
            try:
                unoosa_df.at[idx, 'Period (minutes)'] = float(satcat_row['PERIOD'])
                params_updated += 1
            except:
                pass
    
    print(f"Updated {params_updated} missing orbital parameters")
    return unoosa_df


def import_to_mongodb(unoosa_df: pd.DataFrame, satcat_matches: Dict, clear_first: bool = False) -> int:
    """
    Import enriched records to MongoDB with satcat as a source.
    """
    if not connect_mongodb():
        print("Failed to connect to MongoDB")
        return 0
    
    try:
        if clear_first:
            from db import clear_collection
            print("Clearing existing MongoDB data...")
            clear_collection()
        
        imported_count = 0
        
        for idx, row in unoosa_df.iterrows():
            intl_desig = normalize_intl_designator(row['International Designator'])
            
            if not intl_desig:
                continue
            
            # Prepare UNOOSA source data
            unoosa_data = {
                'name': row['Object Name'] if pd.notna(row['Object Name']) else None,
                'object_name': row['Object Name'],
                'country_of_origin': row['Country of Origin'],
                'international_designator': intl_desig,
                'registration_number': row['Registration Number'],
                'date_of_launch': row['Date of Launch'],
                'function': row['Function'],
                'status': row['Status'],
                'registration_document': row['Registration Document'],
                'un_registered': row['UN Registered'],
                'gso_location': row['GSO Location'],
                'date_of_decay_or_change': row['Date of Decay or Change'],
                'secretariat_remarks': row['Secretariat Remarks'],
                'external_website': row['External Website'],
                'launch_vehicle': row['Launch Vehicle'],
                'place_of_launch': row['Place of Launch'],
                'apogee_km': row['Apogee (km)'],
                'perigee_km': row['Perigee (km)'],
                'inclination_degrees': row['Inclination (degrees)'],
                'period_minutes': row['Period (minutes)']
            }
            
            # Remove None/NaN values
            unoosa_data = {k: v for k, v in unoosa_data.items() if pd.notna(v)}
            
            # Create initial document with UNOOSA as source
            create_satellite_document(intl_desig, 'unoosa', unoosa_data)
            
            # Add satcat data if matched
            if intl_desig in satcat_matches:
                satcat_row = satcat_matches[intl_desig]
                
                satcat_data = {
                    'name': satcat_row['OBJECT_NAME'],
                    'object_name': satcat_row['OBJECT_NAME'],
                    'country_of_origin': satcat_row['OWNER'],
                    'international_designator': intl_desig,
                    'norad_cat_id': satcat_row['NORAD_CAT_ID'],
                    'object_type': satcat_row['OBJECT_TYPE'],
                    'ops_status_code': satcat_row['OPS_STATUS_CODE'],
                    'date_of_launch': satcat_row['LAUNCH_DATE'],
                    'date_of_decay': satcat_row['DECAY_DATE'],
                    'apogee_km': satcat_row['APOGEE'],
                    'perigee_km': satcat_row['PERIGEE'],
                    'inclination_degrees': satcat_row['INCLINATION'],
                    'period_minutes': satcat_row['PERIOD'],
                    'rcs': satcat_row['RCS'],
                    'launch_site': satcat_row['LAUNCH_SITE'],
                    'orbit_center': satcat_row['ORBIT_CENTER'],
                    'orbit_type': satcat_row['ORBIT_TYPE']
                }
                
                # Remove None/NaN values
                satcat_data = {k: v for k, v in satcat_data.items() if pd.notna(v)}
                
                create_satellite_document(intl_desig, 'spacetrack', satcat_data)
            
            imported_count += 1
        
        print(f"Imported {imported_count} records to MongoDB")
        return imported_count
    
    finally:
        disconnect_mongodb()


def main():
    # Load CSV files
    print("Loading CSV files...")
    try:
        unoosa_df = pd.read_csv("unoosa_registry.csv")
        print(f"Loaded {len(unoosa_df)} UNOOSA records")
    except FileNotFoundError:
        print("Error: unoosa_registry.csv not found")
        sys.exit(1)
    
    try:
        satcat_df = pd.read_csv("/Users/frankblau/Downloads/satcat.csv")
        print(f"Loaded {len(satcat_df)} satcat records")
    except FileNotFoundError:
        print("Error: satcat.csv not found at /Users/frankblau/Downloads/satcat.csv")
        sys.exit(1)
    
    # Match records
    print("\nMatching records...")
    satcat_matches = match_records(unoosa_df, satcat_df)
    
    # Enrich UNOOSA data
    print("\nEnriching UNOOSA data...")
    unoosa_df = enrich_unoosa_with_satcat(unoosa_df, satcat_matches)
    unoosa_df = enrich_orbital_params(unoosa_df, satcat_matches)
    
    # Save enriched CSV
    print("\nSaving enriched CSV...")
    output_file = "unoosa_registry_with_norad.csv"
    unoosa_df.to_csv(output_file, index=False)
    print(f"Saved enriched data to {output_file}")
    
    # Import to MongoDB if available
    print("\nAttempting MongoDB import (clearing existing data)...")
    import_to_mongodb(unoosa_df, satcat_matches, clear_first=True)
    
    print("\n✓ Import complete!")


if __name__ == "__main__":
    main()
