# Data Import Quick Reference

All commands to import and manage satellite data in Kessler.

## Prerequisites

```bash
# 1. Install dependencies
pip install pymongo

# 2. Ensure MongoDB is running
mongosh localhost:27017  # Should connect

# 3. Ensure API is running (in another terminal)
python3 -m uvicorn api:app --host 127.0.0.1 --port 8000
```

## Import Workflows

### Fresh Setup (Recommended)

```bash
# 1. Clear and import UNOOSA registry (5,197 satellites)
python3 import_to_mongodb.py --clear

# 2. Add CelesTrak TLE data
python3 import_celestrak_tle_sample.py --test-only
```

**Result**: Full satellite database with registration + TLE data

### Development/Testing

```bash
# Import with sample data only (no network)
python3 import_celestrak_tle_sample.py --test-only
```

### Production (with Network)

```bash
# Fetch latest from CelesTrak (requires internet)
python3 import_celestrak_tle_sample.py
```

Falls back to sample data if CelesTrak is unreachable.

### Full Network Import

```bash
# Fetch from all CelesTrak categories (requires internet)
python3 import_celestrak_tle.py
```

For advanced use - doesn't have fallback.

## Command Reference

### UNOOSA Import

```bash
# Import fresh (clears existing data)
python3 import_to_mongodb.py --clear

# Append to existing data (keeps existing)
python3 import_to_mongodb.py
```

**Output**:
```
Connected to MongoDB: kessler.satellites
🗑️  Clearing existing data...
📥 Importing UNOOSA data from unoosa_registry.csv...
  ✓ Imported 100 satellites...
✅ Successfully imported 5197 satellites from UNOOSA
📊 MongoDB now contains 5197 satellites
```

### CelesTrak TLE Import (Recommended)

```bash
# Try network, fallback to sample data
python3 import_celestrak_tle_sample.py

# Force sample data (no network)
python3 import_celestrak_tle_sample.py --test-only
```

**Output**:
```
============================================================
🛰️  CelesTrak TLE Data Import
============================================================
📡 Fetching Space Stations from stations...
  ✓ Parsed 42 satellites...
  ✓ Processed 50 satellites...
============================================================
🎯 CelesTrak Import Summary
============================================================
Total TLE records fetched:  500
Matched to existing docs:   450
New documents created:      40
Existing docs updated:      450
```

### CelesTrak TLE Import (Full)

```bash
# Fetch from all categories
python3 import_celestrak_tle.py
```

Takes longer, fetches more satellites.

## Verification

### Check MongoDB Connection

```bash
python3 -c "
from pymongo import MongoClient
client = MongoClient('localhost:27017')
client.admin.command('ping')
print('✓ Connected')
"
```

### Count Satellites in MongoDB

```bash
python3 -c "
from db import connect_mongodb, count_satellites
connect_mongodb()
total = count_satellites()
print(f'Total satellites: {total}')
"
```

### List Available Sources

```bash
python3 -c "
from db import connect_mongodb
from pymongo import MongoClient

connect_mongodb()
client = MongoClient('localhost:27017')
db = client['kessler']

docs_with_sources = {}
for doc in db.satellites.find():
    sources = ','.join(doc.get('metadata', {}).get('sources_available', []))
    docs_with_sources[sources] = docs_with_sources.get(sources, 0) + 1

for sources, count in sorted(docs_with_sources.items()):
    print(f'{sources}: {count} documents')
"
```

### Export Statistics

```bash
python3 -c "
from db import connect_mongodb, count_satellites, get_all_countries

connect_mongodb()
print(f'Total satellites: {count_satellites()}')
print(f'Countries: {len(get_all_countries())}')
"
```

## API Testing

### Health Check

```bash
curl http://localhost:8000/v2/health | jq .
```

### Search Satellites

```bash
# Search by name
curl 'http://localhost:8000/v2/search?q=ISS' | jq .

# Filter by country
curl 'http://localhost:8000/v2/search?country=Russian%20Federation&limit=5' | jq .

# Filter by status
curl 'http://localhost:8000/v2/search?status=in%20orbit&limit=10' | jq .

# Combined filters
curl 'http://localhost:8000/v2/search?country=USA&status=active&limit=20' | jq .
```

### Get Satellite Details

```bash
# By international designator
curl 'http://localhost:8000/v2/satellite/2025-206B' | jq .

# By registration number
curl 'http://localhost:8000/v2/satellite/3832-2025-014' | jq .
```

### List Countries

```bash
curl 'http://localhost:8000/v2/countries' | jq '.countries | .[0:10]'
```

### Get Statistics

```bash
# All satellites
curl 'http://localhost:8000/v2/stats' | jq .

# Filtered by country
curl 'http://localhost:8000/v2/stats?country=Russian%20Federation' | jq .
```

## Scheduled Imports

### Set Up Daily Import (macOS/Linux)

```bash
# Edit crontab
crontab -e

# Add this line (runs daily at 2 AM)
0 2 * * * cd /path/to/kessler && python3 import_celestrak_tle_sample.py >> /tmp/kessler-tle.log 2>&1
```

### Verify Cron Job

```bash
crontab -l
```

### Check Cron Logs

```bash
tail -f /tmp/kessler-tle.log
```

## Troubleshooting

### MongoDB Not Running

```bash
# Check if running
ps aux | grep mongod

# Start MongoDB (Homebrew)
brew services start mongodb-community

# Or manually
mongod --dbpath /path/to/data
```

### Import Fails

```bash
# Check MongoDB connection
python3 -c "from db import connect_mongodb; print('✓' if connect_mongodb() else '✗')"

# Check CSV file exists
ls -lh unoosa_registry.csv

# Check Python can read CSV
python3 -c "import pandas as pd; df = pd.read_csv('unoosa_registry.csv'); print(f'{len(df)} rows')"
```

### API Returns CSV Fallback

```bash
# Check MongoDB status
curl http://localhost:8000/v2/health | jq '.mongodb_available'

# If false, start MongoDB
mongosh localhost:27017
```

### Network Timeouts

CelesTrak is unreachable:
- Use `--test-only` flag for sample data
- Check your internet connection
- Check if CelesTrak is down: https://celestrak.org/

## Database Maintenance

### Clear All Data

```bash
python3 -c "
from db import connect_mongodb, clear_collection
connect_mongodb()
clear_collection()
print('✓ Cleared all documents')
"
```

### Backup MongoDB

```bash
mongodump --out=/path/to/backup
```

### Restore MongoDB

```bash
mongorestore /path/to/backup
```

## Performance Metrics

| Operation | Time | Notes |
|-----------|------|-------|
| Import UNOOSA (5,197 docs) | ~5 seconds | From CSV file |
| Import CelesTrak TLE | ~30 seconds | Network dependent |
| Search (1,000 results) | <100 ms | With indexes |
| Full scan (5,000 docs) | <500 ms | Count only |

## Complete Setup Checklist

- [ ] MongoDB installed and running
- [ ] Python 3.11+ with pymongo installed
- [ ] UNOOSA CSV file present
- [ ] Import UNOOSA: `python3 import_to_mongodb.py --clear`
- [ ] Import TLE: `python3 import_celestrak_tle_sample.py --test-only`
- [ ] API running: `python3 -m uvicorn api:app --port 8000`
- [ ] Test API: `curl http://localhost:8000/v2/health`
- [ ] Setup cron for periodic updates (optional)

## Next Steps

1. **For Development**: Use `--test-only` flag
2. **For Testing**: Run full import without flags
3. **For Production**: Schedule periodic imports with cron
4. **For Scale**: Monitor MongoDB performance, add replicas

See **MULTI_SOURCE_DATA_ARCHITECTURE.md** for design details.
