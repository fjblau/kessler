# MongoDB Integration Setup Guide

This document describes how to set up and use MongoDB with the Kessler satellite tracking application.

## Architecture Overview

The system uses an **envelope pattern** for storing satellite data in MongoDB:

```
Document Structure:
├── identifier: "2025-206B" (unique key)
├── canonical: {...} (merged/canonical data from all sources)
├── sources: {
│   ├── unoosa: {...} (UNOOSA registry data)
│   ├── celestrak: {...} (CelesTrak TLE data)
│   └── spacetrack: {...} (Space-Track data)
└── metadata: {...} (creation/update timestamps, source availability)
```

### Canonical Section

The **canonical** section contains the authoritative satellite data, derived from source nodes using a **priority system**:

**Priority Order**: UNOOSA > CelesTrak > Space-Track

For each field, the system uses the value from the highest-priority source that has it. This allows:
- Multiple sources to contribute data
- Conflict resolution by source priority
- Transparent tracking of which source provided each piece of data
- Easy updates when new sources provide better information

## Installation

### Prerequisites

- MongoDB 4.0+ running on `localhost:27017` (default)
- Python 3.11+

### Setup Steps

1. **Install pymongo**:
   ```bash
   pip install -r requirements-mongodb.txt
   ```

2. **Verify MongoDB is running**:
   ```bash
   # MongoDB should be accessible at localhost:27017
   mongosh localhost:27017
   # Or test from Python:
   python3 -c "from pymongo import MongoClient; MongoClient('localhost', 27017).admin.command('ping'); print('✓ Connected')"
   ```

## Data Import

### Import UNOOSA Registry

Import the UNOOSA satellite registry from CSV into MongoDB:

```bash
python3 import_to_mongodb.py
```

**Options**:
- `--clear`: Clear existing data before importing
  ```bash
  python3 import_to_mongodb.py --clear
  ```

This creates documents in the `kessler.satellites` collection with the UNOOSA data in the `sources.unoosa` section and derives the canonical data.

## API Endpoints

### v2 Endpoints (MongoDB-aware)

All v2 endpoints automatically fall back to CSV if MongoDB is unavailable.

#### Health Check
```
GET /v2/health
```
Returns MongoDB availability status.

#### Search Satellites
```
GET /v2/search?q=ISS&country=Russia&status=in%20orbit&limit=50&skip=0
```

**Parameters**:
- `q`: Search query (name, designator, registration number)
- `country`: Filter by country of origin
- `status`: Filter by status
- `limit`: Results per page (1-1000, default: 100)
- `skip`: Pagination offset (default: 0)

**Response**:
```json
{
  "source": "mongodb",
  "count": 2,
  "skip": 0,
  "limit": 100,
  "data": [
    {
      "identifier": "1998-067A",
      "canonical": {
        "name": "ISS",
        "country_of_origin": "Russian Federation",
        "international_designator": "1998-067A",
        "status": "in orbit",
        ...
      },
      "sources_available": ["unoosa", "celestrak"]
    }
  ]
}
```

#### Get Satellite Details
```
GET /v2/satellite/1998-067A
GET /v2/satellite/3832-2025-014  (by registration number)
```

**Response** (with all sources):
```json
{
  "source": "mongodb",
  "data": {
    "identifier": "1998-067A",
    "canonical": {...},
    "sources": {
      "unoosa": {...},
      "celestrak": {...}
    },
    "metadata": {
      "created_at": "2025-12-15T...",
      "last_updated_at": "2025-12-15T...",
      "sources_available": ["unoosa", "celestrak"],
      "source_priority": ["unoosa", "celestrak", "spacetrack"]
    }
  }
}
```

#### Get Countries
```
GET /v2/countries
```

Returns list of countries with satellite registrations.

#### Get Statuses
```
GET /v2/statuses
```

Returns list of satellite statuses (e.g., "in orbit", "decayed").

#### Get Statistics
```
GET /v2/stats?country=Russia&status=in%20orbit
```

Returns count and filter information.

## Programmatic Usage

### Python Integration

```python
from db import connect_mongodb, search_satellites, find_satellite, create_satellite_document

# Connect to MongoDB
connect_mongodb()

# Search satellites
results = search_satellites(
    query="ISS",
    country="Russian Federation",
    limit=10
)

# Get specific satellite
sat = find_satellite(international_designator="1998-067A")
print(sat["canonical"]["name"])

# Add/update satellite from a new source
data = {
    "name": "My Satellite",
    "international_designator": "2025-999A",
    "country_of_origin": "USA",
    ...
}
create_satellite_document("2025-999A", "spacetrack", data)
```

## Periodic Data Refresh

To automatically import fresh data:

```bash
# Clear and reimport UNOOSA data
python3 import_to_mongodb.py --clear

# Add a cron job (Unix/Linux/macOS)
# Edit crontab: crontab -e
# Add this line to run daily at 2 AM:
0 2 * * * cd /path/to/kessler && python3 import_to_mongodb.py
```

## Database Schema

### Collection: `satellites`

**Document Example**:
```json
{
  "_id": ObjectId("..."),
  "identifier": "1998-067A",
  "canonical": {
    "name": "ISS (ZARYA FGB)",
    "object_name": "ISS",
    "international_designator": "1998-067A",
    "registration_number": "3325-1998-067A",
    "country_of_origin": "Russian Federation",
    "date_of_launch": "1998-11-20",
    "function": "Space Station",
    "status": "in orbit",
    "registration_document": "/path/to/doc",
    "un_registered": true,
    "launch_vehicle": "Proton-K",
    "place_of_launch": "Baikonur Cosmodrome",
    "orbit": {
      "apogee_km": 408.5,
      "perigee_km": 393.2,
      "inclination_degrees": 51.64,
      "period_minutes": 92.68
    },
    "tle": {
      "line1": "1 25544U 98067A   ...",
      "line2": "2 25544  51.6416 139.1728 0006703  130.5360 325.0288 15.54179842435929"
    },
    "updated_at": "2025-12-15T20:22:13Z",
    "source_priority": ["unoosa", "celestrak", "spacetrack"]
  },
  "sources": {
    "unoosa": {
      "name": "ISS",
      "international_designator": "1998-067A",
      "registration_number": "3325-1998-067A",
      "country_of_origin": "Russian Federation",
      "date_of_launch": "1998-11-20",
      "function": "Space Station",
      "status": "in orbit",
      "registration_document": "/path/to/doc",
      "un_registered": true,
      "apogee_km": 408.5,
      "perigee_km": 393.2,
      "inclination_degrees": 51.64,
      "period_minutes": 92.68,
      "updated_at": "2025-12-15T20:22:13Z"
    },
    "celestrak": {
      "name": "ISS (ZARYA FGB)",
      "international_designator": "1998-067A",
      "tle_line1": "1 25544U 98067A   ...",
      "tle_line2": "2 25544  51.6416 139.1728 0006703  130.5360 325.0288 15.54179842435929",
      "apogee_km": 408.5,
      "perigee_km": 393.2,
      "inclination_degrees": 51.64,
      "period_minutes": 92.68,
      "updated_at": "2025-12-15T20:22:13Z"
    }
  },
  "metadata": {
    "created_at": "2025-12-15T15:30:00Z",
    "last_updated_at": "2025-12-15T20:22:13Z",
    "sources_available": ["unoosa", "celestrak"],
    "source_priority": ["unoosa", "celestrak", "spacetrack"]
  }
}
```

### Indexes

The following indexes are automatically created:

- `canonical.international_designator` (for fast lookup by designator)
- `canonical.registration_number` (for fast lookup by registration)
- `identifier` (unique constraint)

## Migrating to MongoDB

### Option 1: Full Migration (Recommended)

1. Import UNOOSA data into MongoDB
2. Update React app to use `/v2/*` endpoints
3. Decommission CSV-based endpoints when ready

### Option 2: Gradual Migration

The API supports both CSV and MongoDB endpoints simultaneously:

- **Legacy endpoints** (`/satellites`, `/get-satellite`) use CSV
- **v2 endpoints** (`/v2/search`, `/v2/satellite/*`) use MongoDB with fallback to CSV

This allows updating the frontend gradually.

## Troubleshooting

### MongoDB Connection Issues

```bash
# Test MongoDB connection
mongosh localhost:27017

# Check if MongoDB is running
ps aux | grep mongod
```

### Import Fails

```bash
# Verify CSV file exists
ls -lh unoosa_registry.csv

# Check Python can read it
python3 -c "import pandas as pd; df = pd.read_csv('unoosa_registry.csv'); print(f'{len(df)} rows')"
```

### API Falls Back to CSV

If MongoDB is unavailable, the API automatically falls back to CSV. Check:
- MongoDB is running: `mongosh localhost:27017`
- API logs show connection status: Check `/v2/health` endpoint

## Next Steps

1. Install pymongo: `pip install -r requirements-mongodb.txt`
2. Ensure MongoDB is running on localhost:27017
3. Import data: `python3 import_to_mongodb.py --clear`
4. Test endpoints: `curl http://localhost:8000/v2/health`
5. Update React app to use `/v2/*` endpoints
