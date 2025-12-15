# MongoDB Integration Summary

## What Was Implemented

A complete MongoDB integration for the Kessler satellite tracking application using an **envelope pattern** for multi-source data management.

## Architecture

### Envelope Pattern

Each satellite is stored as a single MongoDB document with:

```
Document = {
  identifier: string (unique key),
  canonical: {...} (merged/authoritative data),
  sources: {
    unoosa: {...},
    celestrak: {...},
    spacetrack: {...}
  },
  metadata: {...}
}
```

**Key Feature**: The `canonical` section is automatically derived from source nodes based on **priority rules**:
- **Priority**: UNOOSA > CelesTrak > Space-Track
- Fields are populated from the highest-priority source that has data for that field
- This enables conflict resolution without data loss

## Files Created

### 1. **db.py** - Database Layer
Core MongoDB operations:
- `connect_mongodb()` - Initialize connection with indexes
- `create_satellite_document()` - Create/update documents with envelope structure
- `update_canonical()` - Derive canonical data from sources (priority-based)
- `find_satellite()` - Look up by designator, registration number, or name
- `search_satellites()` - Full search with filters
- `count_satellites()` - Count with filters
- `get_all_countries()` / `get_all_statuses()` - Aggregate data

### 2. **import_to_mongodb.py** - Data Import
Imports UNOOSA satellite registry from CSV into MongoDB:
```bash
python3 import_to_mongodb.py           # Import
python3 import_to_mongodb.py --clear   # Clear and reimport
```

### 3. **api.py** - API Updates
Added MongoDB-aware v2 endpoints with CSV fallback:

- **GET /v2/health** - Check MongoDB status
- **GET /v2/search** - Search with country/status filters
- **GET /v2/satellite/{identifier}** - Get full document with all sources
- **GET /v2/countries** - List all countries
- **GET /v2/statuses** - List all statuses
- **GET /v2/stats** - Collection statistics

Each endpoint:
- Uses MongoDB when available
- Falls back to CSV if MongoDB is down
- Returns `"source": "mongodb"` or `"source": "csv_fallback"` in response

### 4. **requirements-mongodb.txt**
Dependencies:
```
pymongo>=4.0.0
```

### 5. **MONGODB_SETUP.md** - Complete Setup Guide
Comprehensive documentation including:
- Architecture overview
- Installation steps
- API endpoint reference with examples
- Python programmatic usage
- Periodic refresh setup (cron jobs)
- Database schema documentation
- Troubleshooting guide

## Key Design Decisions

### 1. Envelope Pattern (Multi-Source)
**Rationale**: Satellites have data from multiple sources (UNOOSA, CelesTrak, Space-Track). The envelope pattern allows:
- Keeping source data intact (audit trail)
- Deriving canonical from rules
- Easy addition of new sources
- No data loss when sources conflict

### 2. Priority-Based Canonical Resolution
**Rationale**: Rather than manual field-level rules, use source priority:
- UNOOSA (most authoritative)
- CelesTrak (TLE data specialists)
- Space-Track (alternative source)

Benefits:
- Simple, consistent rule system
- Easy to adjust if priorities change
- Transparent about which source provided each field

### 3. CSV Fallback in API
**Rationale**: MongoDB is optional, not required
- API works with or without MongoDB
- Graceful degradation if MongoDB is down
- Allows gradual migration path
- No breaking changes to existing code

### 4. Automatic Indexing
**Rationale**: Performance
- Indexes on `international_designator`, `registration_number`, `identifier`
- Fast searches even with millions of documents
- Unique constraint on `identifier` prevents duplicates

## Usage Flow

### Initial Setup
```bash
# 1. Install dependencies
pip install pymongo

# 2. Ensure MongoDB is running
mongosh localhost:27017

# 3. Import UNOOSA data
python3 import_to_mongodb.py --clear

# 4. Start API
python -m uvicorn api:app --host 127.0.0.1 --port 8000
```

### Adding New Sources
To add CelesTrak or Space-Track data:

```python
from db import create_satellite_document

# Extract TLE data from CelesTrak
data = {
    "name": "ISS (ZARYA FGB)",
    "tle_line1": "1 25544U...",
    "tle_line2": "2 25544...",
    "apogee_km": 408.5,
    ...
}

# Add to existing satellite document
create_satellite_document("1998-067A", "celestrak", data)

# Canonical is automatically updated based on priority!
```

### Querying
```python
from db import search_satellites, find_satellite

# Search
results = search_satellites("ISS", country="Russia", limit=10)

# Get specific satellite
sat = find_satellite(international_designator="1998-067A")
print(sat["canonical"]["name"])  # From highest-priority source

# See all sources
for source, data in sat["sources"].items():
    print(f"{source}: {data.get('name')}")
```

## Periodic Updates

Setup automatic refreshes via cron:
```bash
# Run import daily at 2 AM
crontab -e
# Add: 0 2 * * * cd /path/to/kessler && python3 import_to_mongodb.py
```

Or create a scheduled import script that:
1. Fetches latest TLE data from CelesTrak
2. Calls `create_satellite_document(..., "celestrak", data)`
3. MongoDB automatically updates canonical fields

## Integration Points

### For React Frontend
Update components to use v2 endpoints:
```javascript
// Before (CSV)
fetch('/satellites')

// After (MongoDB)
fetch('/v2/search?q=ISS&limit=50')
fetch('/v2/satellite/1998-067A')
fetch('/v2/countries')
```

### For Additional Sources
Create import scripts similar to `import_to_mongodb.py`:
```python
# import_celestrak_tle.py
from db import create_satellite_document

# Fetch TLE, parse it
create_satellite_document(designator, "celestrak", tle_data)
```

The canonical section automatically updates based on source priority!

## Benefits

1. **Flexible Multi-Source Support**: Add CelesTrak, Space-Track without touching canonical section
2. **Audit Trail**: Keep source data intact, see what came from where
3. **Conflict Resolution**: Priority-based rules, no manual intervention
4. **Performance**: MongoDB indexes for fast queries
5. **Zero Data Loss**: All source data preserved
6. **Backward Compatible**: Existing API continues to work
7. **Graceful Degradation**: Works with or without MongoDB

## Next Steps

1. Install pymongo: `pip install -r requirements-mongodb.txt`
2. Import UNOOSA data: `python3 import_to_mongodb.py --clear`
3. Test endpoints: `curl http://localhost:8000/v2/health`
4. Update React frontend to use `/v2/*` endpoints
5. Create CelesTrak TLE import script (optional)
6. Setup periodic refresh via cron (optional)

See **MONGODB_SETUP.md** for detailed instructions.
