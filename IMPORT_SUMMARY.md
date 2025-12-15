# Satcat Import Summary

## Overview
Successfully imported Space-Track NORAD catalog data (satcat.csv) and merged it with the existing UNOOSA satellite registry. NORAD identifiers and additional orbital data have been added to existing records.

## Files Created/Modified

### New Files
- **`import_satcat.py`** - Import script that:
  - Matches UNOOSA records with satcat records by International Designator
  - Adds NORAD_CAT_ID to all matched records
  - Enriches missing orbital parameters (apogee, perigee, inclination, period)
  - Imports data to MongoDB with satcat as a new source
  - Preserves all original data while adding new fields

- **`unoosa_registry_with_norad.csv`** - Enriched registry file with:
  - Original UNOOSA data
  - NORAD_CAT_ID (96.3% match rate)
  - Additional satcat fields (OBJECT_TYPE, OPS_STATUS, RCS, DECAY_DATE)

### Modified Files
- **`api.py`**
  - Updated to load enriched registry with NORAD IDs
  - Updated `get_orbital_state()` endpoint to return NORAD IDs
  - Falls back to original CSV if enriched version unavailable
  - Logs which registry is being used

- **`db.py`**
  - Added `norad_cat_id` to canonical fields list
  - Added object metadata fields (object_type, rcs) to canonical section
  - Ensures NORAD ID is prioritized in merged data

## Data Quality

### Match Statistics
- **Total UNOOSA records**: 5,197
- **Matched with satcat**: 5,004 (96.3%)
- **Records lacking NORAD ID**: 193 (mostly historical/decayed satellites)

### Orbital Parameter Coverage
- **Apogee (km)**: 4,938/5,197 (95.0%)
- **Perigee (km)**: 4,938/5,197 (95.0%)
- **Inclination (degrees)**: 4,938/5,197 (95.0%)
- **Period (minutes)**: 4,938/5,197 (95.0%)
- **Improvement**: +19,124 parameter values added

### MongoDB Integration
- **All 5,197 records** imported to MongoDB
- **2 sources per record**:
  - `unoosa` - Original UNOOSA registry data
  - `spacetrack` - satcat data (when available)
- **Canonical section** merges both sources with UNOOSA priority
- **NORAD ID** accessible in canonical section and all API responses

## API Changes

### Enhanced Responses
All satellite endpoints now include NORAD ID when available:

```json
{
  "registration_number": "3832-2025-014",
  "object_name": "(GLONASS)",
  "international_designator": "2025-206B",
  "norad_id": "65590",
  "n2yo_url": "https://www.n2yo.com/satellite/?s=65590",
  "tracking_available": true,
  "orbital_state": {
    "apogee_km": 19166.0,
    "perigee_km": 19094.0,
    "inclination_degrees": 64.74,
    "period_minutes": 675.74,
    "data_source": "Static registry"
  }
}
```

### Additional Metadata
New satcat fields available in records:
- `SATCAT_OBJECT_TYPE` - Object classification (PAY, R/B, DEB, etc.)
- `SATCAT_OPS_STATUS` - Operational status
- `SATCAT_RCS` - Radar cross-section
- `SATCAT_DECAY_DATE` - Decay/reentry date when available

## Usage

### To run the import:
```bash
python3 import_satcat.py
```

The script will:
1. Load both CSV files
2. Match records by International Designator
3. Enrich orbital parameters
4. Save enriched CSV
5. Import to MongoDB (if available)

### Updated files:
- `unoosa_registry_with_norad.csv` - New enriched registry (for CSV-based API)
- MongoDB collection - Updated with multi-source documents

## Backward Compatibility
✓ Original `unoosa_registry.csv` preserved
✓ API automatically uses enriched registry if available
✓ Falls back to original registry if enriched version missing
✓ All existing endpoints continue to work
✓ NORAD IDs added without breaking changes

## Data Sources
- **UNOOSA Registry**: UN Office for Outer Space Affairs
- **Satcat**: Space-Track (NORAD Satellite Catalog)
- **Integration**: By International Designator matching

## Notes
- 193 UNOOSA records couldn't be matched (historical/decayed satellites not in current satcat)
- NORAD IDs enable real-time tracking via N2YO and other TLE sources
- Satcat object types provide better satellite classification
- RCS values useful for collision avoidance calculations
