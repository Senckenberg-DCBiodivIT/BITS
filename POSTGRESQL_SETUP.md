# PostgreSQL Setup for BITS Project

## Overview
This project supports both PostgreSQL and SQLite databases. For large PostgreSQL dumps (like the 19GB sesam_dump.sql), PostgreSQL is recommended.

## Installation

### 1. Install PostgreSQL
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

### 2. Start PostgreSQL
```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 3. Configure PostgreSQL
```bash
sudo -u postgres psql
```

In PostgreSQL:
```sql
ALTER USER postgres PASSWORD 'postgres';
\q
```

### 4. Check PostgreSQL Status
```bash
ps aux | grep postgres
```

### 5. Start PostgreSQL (if not running)
```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 6. Test Installation
```bash
psql -h localhost -U postgres -d postgres
```

## Usage in BITS Project

### Automatic Detection
The system automatically detects the database type based on configuration:

- **PostgreSQL Dumps** → **PostgreSQL Server** (no local .db file!)
- **SQLite Dumps** → **SQLite Database** (local .db file)

### Configuration
Configuration is done in `data_provider_connector/confidential/sgn_local_connector.json`:

```json
{
    "type": "PostgreSQL",
    "source_type": "file",
    "sql_filename": "confidential/DB/sesam_dump/sesam_dump.sql"
}
```

### System Behavior

#### With PostgreSQL (recommended for large files):
1. **Check PostgreSQL Server Availability** → Helpful setup instructions on errors
2. **Check Database Existence** → Direct connection if `sesam_dump` exists
3. **Check File Size** → Chunked import for large files (≥5GB)
4. **Perform Import** → `psql` with RAM-optimized chunking
5. **Establish Connection** → PostgreSQL Server (no local .db file!)

#### Important Note:
- **PostgreSQL data is stored in the PostgreSQL Server**
- **No local .db file** is created
- **Data is available in the PostgreSQL Server** (e.g., 92 tables)
- **Much more performant** for large datasets (19GB)

## Testing the System

### 1. Check PostgreSQL Status
```bash
ps aux | grep postgres
```

### 2. Start PostgreSQL (if needed)
```bash
sudo systemctl start postgresql
```

### 3. Test System
```bash
cd /home/alex/Schreibtisch/Projects/BITS
python3 -c "
from helper.data_provider import DataProvider
import logging
logging.basicConfig(level=logging.INFO)

data_provider = DataProvider()
data_provider.load_config(
    common_config={'data_provider_connection': {'sgn_local': {}}},
    config_file='data_provider_connector/confidential/sgn_local_connector.json',
    role='sgn_local'
)

try:
    data_provider.connect()
    print('✓ Database connection successful!')
    print(f'Database type: {data_provider.db_type}')
    
    # Test query
    if data_provider.db_type == 'postgresql':
        data_provider.cursor.execute('SELECT tablename FROM pg_tables LIMIT 5')
        tables = data_provider.cursor.fetchall()
        print(f'Found {len(tables)} tables: {[t[0] for t in tables]}')
    else:
        data_provider.cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\" LIMIT 5')
        tables = data_provider.cursor.fetchall()
        print(f'Found {len(tables)} tables: {[t[0] for t in tables]}')
        
except Exception as e:
    print(f'✗ Connection failed: {e}')
finally:
    if data_provider.connection:
        data_provider.close_connection()
"
```

## Benefits of PostgreSQL Installation

### For Large Files (19GB+):
- ✅ **Chunked Import** with `split -b 2G` for RAM-optimized processing
- ✅ **PostgreSQL Server** instead of local files (more performant)
- ✅ **Automatic Database Detection** (92 tables already present)
- ✅ **SSD-friendly Processing** (chunks in same directory)
- ✅ **Direct PostgreSQL Processing** without conversion

### For Small Files (<5GB):
- ✅ **Direct Import** with `psql` without chunking
- ✅ **Flexible Configuration** depending on file type
- ✅ **Intelligent Detection** of database type

### Important Differences:
- **PostgreSQL:** Data in server (no .db file visible)
- **SQLite:** Local .db file in filesystem

## Troubleshooting

### PostgreSQL Connection Failed:
```bash
sudo systemctl status postgresql
psql -h localhost -U postgres -d postgres
sudo journalctl -u postgresql
```

### SQLite Fallback:
- System automatically uses SQLite conversion
- PostgreSQL-specific commands are filtered
- Works even without PostgreSQL installation

## Files in Project

- `helper/data_provider.py` - Main logic for database connections
- `data_provider_connector/confidential/sgn_local_connector.json` - Configuration
- `confidential/DB/sesam_dump/sesam_dump.sql` - PostgreSQL dump (19GB)
- `POSTGRESQL_SETUP.md` - This guide

## Important Notes

### No .db File Visible?
**That's correct!** PostgreSQL stores data in the server, not as a local file.

### Check Database:
```bash
# Connect to PostgreSQL database
psql -U postgres -d sesam_dump

# Show tables
\dt

# Check table count
SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';
```

### System Status:
- ✅ **PostgreSQL Server running**
- ✅ **Database `sesam_dump` exists** (92 tables)
- ✅ **No local .db file** = **Correct!**
- ✅ **Data is available in PostgreSQL Server**