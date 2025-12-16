# CelesTrak TLE Import Guide

Import Two-Line Element (TLE) orbital data from CelesTrak and merge it with existing UNOOSA satellite data in MongoDB using the envelope pattern.

## Overview

The CelesTrak import adds TLE (Two-Line Element) data to satellites in your MongoDB collection. The envelope pattern automatically:

1. **Merges data from multiple sources** - UNOOSA registry + CelesTrak TLE data
2. **Resolves conflicts** - Uses source priority (UNOOSA > CelesTrak > Space-Track)
3. **Preserves all data** - Keeps raw source data in `sources.*` sections
4. **Updates canonical automatically** - Derived from highest-priority sources

## What is TLE Data?

TLE (Two-Line Element) format contains orbital elements for tracking satellites. Example:

```
ISS (ZARYA FGB)
1 25544U 98067A   25349.64833335  .00016717  00000-0  29853-3 0  9998
2 25544  51.6432 247.7832 0002671  86.3996  41.1872 15.54248026435929
```

From TLE, we extract:
- **Name**: ISS (ZARYA FGB)
- **International Designator**: 1998-067A (from line 1, positions 9-17)
- **Orbital Parameters**:
  - Apogee/Perigee (calculated)
  - Inclination: 51.64°
  - Period: 92.65 minutes

## Getting Started

### Prerequisites

- MongoDB running on localhost:27017
- Satellites imported via `import_to_mongodb.py`
- Network access (for live CelesTrak data) or use sample data

### Basic Usage

**Run with sample TLE data** (for testing, no network required):

```bash
python3 import_celestrak_tle_sample.py --test-only
```

**Run with live CelesTrak data** (fetches from CelesTrak URLs):

```bash
python3 import_celestrak_tle_sample.py
```

If CelesTrak is unreachable, it automatically falls back to sample data.

## Document Structure After Import

When TLE data is added to an existing UNOOSA satellite:

```json
{
  "identifier": "2025-206B",
  "canonical": {
    // Merged data from all sources (priority: UNOOSA > CelesTrak > Space-Track)
    "name": "(GLONASS)",
    "country_of_origin": "Russian Federation",
    "international_designator": "2025-206B",
    "registration_number": "3832-2025-014",
    "status": "in orbit",
    "orbit": {
      "apogee_km": 406.15,
      "perigee_km": 402.53,
      "inclination_degrees": 51.64,
      "period_minutes": 92.65
    },
    "tle": {
      "line1": "1 25544U 98067A ...",
      "line2": "2 25544  51.6432 ..."
    }
  },
  "sources": {
    "unoosa": {
      // Original UNOOSA registry data
      "name": "(GLONASS)",
      "country_of_origin": "Russian Federation",
      ...
    },
    "celestrak": {
      // TLE data from CelesTrak
      "name": "ISS (ZARYA FGB)",
      "tle_line1": "1 25544U 98067A ...",
      "tle_line2": "2 25544  51.6432 ...",
      "apogee_km": 406.15,
      "inclination_degrees": 51.64,
      ...
    }
  },
  "metadata": {
    "sources_available": ["unoosa", "celestrak"],
    "source_priority": ["unoosa", "celestrak", "spacetrack"]
  }
}
```

## Understanding the Envelope Pattern

### Canonical Section

The `canonical` section is **automatically derived** from source nodes using **source priority**:

**Priority Order**: UNOOSA > CelesTrak > Space-Track

For each field, the system uses the value from the **highest-priority source** that has it:

| Field | UNOOSA | CelesTrak | Space-Track | Used From |
|-------|--------|-----------|-------------|-----------|
| `name` | "GLONASS" | "ISS (ZARYA FGB)" | - | UNOOSA (higher priority) |
| `tle` | - | Has TLE | - | CelesTrak |
| `apogee_km` | - | 406.15 | 407.0 | CelesTrak (UNOOSA doesn't have it) |
| `status` | "in orbit" | - | - | UNOOSA |

### Source Nodes

Raw data from each source is preserved:

- **unoosa**: Registration info (names, dates, functions, documents)
- **celestrak**: TLE and derived orbital parameters
- **spacetrack**: Alternative tracking data

All source data is kept intact - nothing is lost.

## API Examples

### Get Satellite with All Sources

```bash
curl 'http://localhost:8000/v2/satellite/2025-206B'
```

Response includes:
- `canonical`: Merged data from highest-priority sources
- `sources.unoosa`: Original UNOOSA data
- `sources.celestrak`: CelesTrak TLE data
- `metadata`: Source tracking and priority info

### Search for Satellites with Orbital Data

```bash
# Find satellites in orbit
curl 'http://localhost:8000/v2/search?status=in%20orbit&limit=10'

# Filter by country
curl 'http://localhost:8000/v2/search?country=Russian%20Federation&limit=5'
```

Returns all matching satellites with merged canonical data.

## Running Different Versions

### Version 1: Full Network Import

**File**: `import_celestrak_tle.py`

Fetches from all CelesTrak categories:
- Space Stations
- Earth Resources
- Search & Rescue
- Disaster Monitoring
- Weather
- Geostationary
- ISS & Associated
- High Earth Orbit
- CubeSats

**Use when**: You have network access and want complete TLE data.

```bash
python3 import_celestrak_tle.py
```

### Version 2: Network with Fallback (Recommended)

**File**: `import_celestrak_tle_sample.py`

Attempts to fetch from CelesTrak, falls back to sample data if unreachable.

**Use when**: You want automatic data but can handle network issues gracefully.

```bash
# Try network first
python3 import_celestrak_tle_sample.py

# Force sample data (for testing)
python3 import_celestrak_tle_sample.py --test-only
```

## Periodic Updates

Set up automatic TLE updates via cron (runs daily at 2 AM):

```bash
crontab -e
```

Add this line:

```bash
0 2 * * * cd /path/to/kessler && python3 import_celestrak_tle_sample.py >> /tmp/kessler-tle.log 2>&1
```

Verify it's scheduled:

```bash
crontab -l
```

## Sample Data Included

For testing, the script includes these satellites:

| Name | Designator | Purpose |
|------|-----------|---------|
| ISS (ZARYA FGB) | 1998-067A | Space Station |
| HUBBLE SPACE TELESCOPE | 1990-037B | Space Telescope |
| GLONASS-M (1) | 1997-020A | Navigation |
| ASTRA 2E | 2007-049A | Communications |

## CelesTrak Sources

The import fetches from these CelesTrak categories:

| URL | Category | Purpose |
|-----|----------|---------|
| `stations.txt` | Space Stations | ISS, Mir, etc. |
| `resource.txt` | Earth Resources | Remote sensing satellites |
| `sarsat.txt` | Search & Rescue | SAR satellites |
| `dmc.txt` | Disaster Monitoring | Disaster monitoring missions |
| `weather.txt` | Weather | Meteorological satellites |
| `geo.txt` | Geostationary | GEO communications satellites |
| `iss.txt` | ISS & Associated | ISS and attached payloads |
| `high-earth.txt` | High Earth Orbit | GPS, GLONASS, etc. |
| `cubesats.txt` | CubeSats | Small experimental satellites |

## Troubleshooting

### CelesTrak Unreachable

If the script shows timeouts:

```
📡 Fetching Space Stations from stations...
  ⚠️ Network error: Timeout
```

**Solution**:
1. Check your internet connection
2. Run with sample data: `python3 import_celestrak_tle_sample.py --test-only`
3. Check CelesTrak status: https://celestrak.org/

### MongoDB Connection Failed

```
❌ Failed to connect to MongoDB
Make sure MongoDB is running on localhost:27017
```

**Solution**:
```bash
mongosh localhost:27017
# Should connect successfully
```

### No Documents Matched

If the import shows 0 matched documents, ensure you've imported UNOOSA data first:

```bash
# Step 1: Import UNOOSA
python3 import_to_mongodb.py --clear

# Step 2: Then import TLE
python3 import_celestrak_tle_sample.py --test-only
```

## Advanced: Add Custom TLE Data

To add TLE data from other sources or manually:

```python
from db import connect_mongodb, create_satellite_document

connect_mongodb()

# Add TLE data to existing satellite
create_satellite_document(
    identifier="2025-206B",  # Must match existing document
    source="celestrak",
    data={
        "name": "GLONASS-K1",
        "international_designator": "2025-206B",
        "tle_line1": "1 25544U 98067A ...",
        "tle_line2": "2 25544  51.6432 ...",
        "apogee_km": 406.15,
        "perigee_km": 402.53,
        "inclination_degrees": 51.64,
        "period_minutes": 92.65
    }
)

# Canonical is automatically updated!
```

## Performance Notes

- **Import time**: ~30 seconds for full CelesTrak data (with network)
- **Database size**: ~100 MB with 5000+ satellites and TLE data
- **Query performance**: Fast indexes on `international_designator`, `registration_number`

## Next Steps

1. **Import sample TLE data**: `python3 import_celestrak_tle_sample.py --test-only`
2. **Test API endpoints**: `curl 'http://localhost:8000/v2/satellite/2025-206B'`
3. **Schedule periodic updates**: Add cron job for daily imports
4. **Add Space-Track data**: Create similar import script for Space-Track
5. **Update frontend**: Use `/v2/satellite/{id}` endpoint

## References

- **CelesTrak**: https://celestrak.org/
- **TLE Format**: https://celestrak.org/NORAD/documentation/tle-fmt.php
- **Orbital Mechanics**: https://www.n2yo.com/

See **MONGODB_SETUP.md** for complete MongoDB guide.
