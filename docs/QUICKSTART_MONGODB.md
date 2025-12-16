# MongoDB Quick Start

Get MongoDB running with Kessler in 5 minutes.

## 1. Install pymongo

```bash
pip install pymongo>=4.0.0
```

## 2. Start MongoDB

```bash
# If installed via Homebrew (macOS)
brew services start mongodb-community

# Or manually
mongod --dbpath /path/to/data
```

**Verify**: 
```bash
mongosh localhost:27017
# Should connect without error
```

## 3. Import Data

```bash
python3 import_to_mongodb.py --clear
```

Expected output:
```
📥 Importing UNOOSA data from unoosa_registry.csv...
  ✓ Imported 100 satellites...
  ✓ Imported 200 satellites...
  ✓ Imported 300 satellites...
✅ Successfully imported 4000+ satellites from UNOOSA
```

## 4. Test API

```bash
# Check health
curl http://localhost:8000/v2/health

# Search satellites
curl "http://localhost:8000/v2/search?q=ISS"

# Get details
curl "http://localhost:8000/v2/satellite/1998-067A"

# Get countries
curl "http://localhost:8000/v2/countries"

# Get stats
curl "http://localhost:8000/v2/stats"
```

## 5. Use in Code

```python
from db import search_satellites, find_satellite

# Search
results = search_satellites("ISS", limit=10)
print(f"Found {len(results)} satellites")

# Get one
sat = find_satellite(international_designator="1998-067A")
print(f"Canonical name: {sat['canonical']['name']}")
print(f"Sources: {sat['metadata']['sources_available']}")
```

## Understanding Your Data

Each satellite document has:

```json
{
  "identifier": "1998-067A",
  
  "canonical": {
    "name": "ISS",
    "country_of_origin": "Russian Federation",
    "status": "in orbit",
    "orbit": {...},
    "tle": {...}
  },
  
  "sources": {
    "unoosa": {...}
  },
  
  "metadata": {
    "sources_available": ["unoosa"],
    "created_at": "2025-12-15T..."
  }
}
```

- **canonical**: Merged data from all sources (priority: UNOOSA > CelesTrak > Space-Track)
- **sources**: Raw data from each source (preserved for audit trail)
- **metadata**: Timestamps and source information

## Add More Data Sources

To add CelesTrak TLE data to existing documents:

```python
from db import create_satellite_document

# Add TLE data to ISS
create_satellite_document("1998-067A", "celestrak", {
    "name": "ISS (ZARYA FGB)",
    "tle_line1": "1 25544U 98067A...",
    "tle_line2": "2 25544  51.6416...",
    "apogee_km": 408.5,
    "perigee_km": 393.2
})

# Canonical is automatically updated!
```

The `canonical` section now has TLE data from CelesTrak (while keeping UNOOSA fields because of source priority).

## Troubleshooting

**API says MongoDB not available?**
```bash
# Check if MongoDB is running
ps aux | grep mongod

# Try connecting manually
mongosh localhost:27017
```

**Import fails?**
```bash
# Verify CSV file
ls -lh unoosa_registry.csv

# Test connection
python3 -c "from pymongo import MongoClient; MongoClient('localhost', 27017).admin.command('ping'); print('✓')"
```

**Want to start over?**
```bash
python3 import_to_mongodb.py --clear
```

## Architecture

**Envelope Pattern**: Each document contains:
1. **Canonical section** - merged data from all sources
2. **Source sections** - raw data from each source
3. **Metadata** - tracking info

**Priority resolution**: When deriving canonical from sources:
- Use UNOOSA data first (most authoritative)
- Fall back to CelesTrak for missing fields
- Use Space-Track as last resort
- This happens automatically!

## API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /v2/health` | Check MongoDB status |
| `GET /v2/search` | Search satellites |
| `GET /v2/satellite/{id}` | Get full details |
| `GET /v2/countries` | List countries |
| `GET /v2/statuses` | List statuses |
| `GET /v2/stats` | Get statistics |

All fall back to CSV if MongoDB is unavailable.

## Next: Add More Sources

1. Create import script for CelesTrak TLE data
2. Create import script for Space-Track data
3. Schedule periodic imports with cron
4. Canonical data automatically merges everything!

See **MONGODB_SETUP.md** for detailed guide.
