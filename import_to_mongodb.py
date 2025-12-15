"""
Import satellite data from various sources into MongoDB with envelope structure.
"""

import pandas as pd
from db import (
    connect_mongodb, disconnect_mongodb, create_satellite_document,
    clear_collection, get_satellites_collection
)
from datetime import datetime
import sys


def import_unoosa_csv(csv_file: str = "unoosa_registry.csv"):
    """Import UNOOSA registry from CSV file"""
    print(f"📥 Importing UNOOSA data from {csv_file}...")
    
    try:
        df = pd.read_csv(csv_file)
        collection = get_satellites_collection()
        
        count = 0
        for idx, row in df.iterrows():
            intl_desig = row.get("International Designator", "").strip()
            reg_number = row.get("Registration Number", "").strip()
            
            identifier = intl_desig if intl_desig else reg_number
            
            if not identifier:
                continue
            
            data = {
                "object_name": row.get("Object Name", ""),
                "international_designator": intl_desig,
                "registration_number": reg_number,
                "country_of_origin": row.get("Country of Origin", ""),
                "date_of_launch": row.get("Date of Launch", ""),
                "function": row.get("Function", ""),
                "status": row.get("Status", ""),
                "registration_document": row.get("Registration Document", ""),
                "un_registered": row.get("UN Registered", "").lower() == "t",
                "gso_location": row.get("GSO Location", ""),
                "date_of_decay_or_change": row.get("Date of Decay or Change", ""),
                "secretariat_remarks": row.get("Secretariat Remarks", ""),
                "external_website": row.get("External Website", ""),
                "launch_vehicle": row.get("Launch Vehicle", ""),
                "place_of_launch": row.get("Place of Launch", ""),
            }
            
            for field in ["Apogee (km)", "Perigee (km)", "Inclination (degrees)", "Period (minutes)"]:
                if field in df.columns:
                    value = row.get(field)
                    if pd.notna(value) and value != "":
                        try:
                            numeric_value = float(value)
                            data[field.replace(" (km)", "_km").replace(" (degrees)", "_degrees").replace(" (minutes)", "_minutes").lower()] = numeric_value
                        except (ValueError, TypeError):
                            pass
            
            create_satellite_document(identifier, "unoosa", data)
            count += 1
            
            if count % 100 == 0:
                print(f"  ✓ Imported {count} satellites...")
        
        print(f"✅ Successfully imported {count} satellites from UNOOSA")
        return count
    
    except Exception as e:
        print(f"❌ Error importing UNOOSA data: {e}")
        raise


def import_unoosa_csv_with_field_mapping(csv_file: str = "unoosa_registry.csv"):
    """Import UNOOSA registry with proper field name mapping"""
    print(f"📥 Importing UNOOSA data from {csv_file}...")
    
    def safe_str(val):
        """Convert value to string, handling NaN and None"""
        if pd.isna(val):
            return ""
        return str(val).strip()
    
    try:
        df = pd.read_csv(csv_file)
        collection = get_satellites_collection()
        
        count = 0
        for idx, row in df.iterrows():
            intl_desig = safe_str(row["International Designator"])
            reg_number = safe_str(row["Registration Number"])
            
            identifier = intl_desig if intl_desig else reg_number
            
            if not identifier:
                continue
            
            data = {
                "name": safe_str(row["Object Name"]),
                "international_designator": intl_desig,
                "registration_number": reg_number,
                "country_of_origin": safe_str(row["Country of Origin"]),
                "date_of_launch": safe_str(row["Date of Launch"]),
                "function": safe_str(row["Function"]),
                "status": safe_str(row["Status"]),
                "registration_document": safe_str(row["Registration Document"]),
                "un_registered": safe_str(row["UN Registered"]).lower() == "t",
                "gso_location": safe_str(row["GSO Location"]),
                "date_of_decay_or_change": safe_str(row["Date of Decay or Change"]),
                "secretariat_remarks": safe_str(row["Secretariat Remarks"]),
                "external_website": safe_str(row["External Website"]),
                "launch_vehicle": safe_str(row["Launch Vehicle"]),
                "place_of_launch": safe_str(row["Place of Launch"]),
            }
            
            apogee = row["Apogee (km)"]
            if pd.notna(apogee) and apogee != "":
                try:
                    data["apogee_km"] = float(apogee)
                except (ValueError, TypeError):
                    pass
            
            perigee = row["Perigee (km)"]
            if pd.notna(perigee) and perigee != "":
                try:
                    data["perigee_km"] = float(perigee)
                except (ValueError, TypeError):
                    pass
            
            inclination = row["Inclination (degrees)"]
            if pd.notna(inclination) and inclination != "":
                try:
                    data["inclination_degrees"] = float(inclination)
                except (ValueError, TypeError):
                    pass
            
            period = row["Period (minutes)"]
            if pd.notna(period) and period != "":
                try:
                    data["period_minutes"] = float(period)
                except (ValueError, TypeError):
                    pass
            
            create_satellite_document(identifier, "unoosa", data)
            count += 1
            
            if count % 100 == 0:
                print(f"  ✓ Imported {count} satellites...")
        
        print(f"✅ Successfully imported {count} satellites from UNOOSA")
        return count
    
    except Exception as e:
        print(f"❌ Error importing UNOOSA data: {e}")
        raise


if __name__ == "__main__":
    if not connect_mongodb():
        print("❌ Failed to connect to MongoDB")
        sys.exit(1)
    
    clear = "--clear" in sys.argv
    
    if clear:
        print("🗑️  Clearing existing data...")
        clear_collection()
    
    try:
        count = import_unoosa_csv_with_field_mapping()
        print(f"\n📊 MongoDB now contains {count} satellites")
    except Exception as e:
        print(f"Import failed: {e}")
        sys.exit(1)
    finally:
        disconnect_mongodb()
