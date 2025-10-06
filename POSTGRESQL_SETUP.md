# PostgreSQL Setup for BITS Project

## Overview
This project now uses PostgreSQL exclusively for database operations. PostgreSQL provides superior performance and scalability for large datasets like the 19GB sesam_dump.sql file.

## Installation

### 1. Install PostgreSQL
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

### 2. Start PostgreSQL Service
```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 3. Configure PostgreSQL User
```bash
sudo -u postgres psql
```

In PostgreSQL console:
```sql
ALTER USER postgres PASSWORD 'postgres';
\q
```

### 4. Install Python Dependencies
```bash
pip install psycopg2-binary
```

### 5. Verify Installation
```bash
# Check if PostgreSQL is running
ps aux | grep postgres

# Test connection
psql -h localhost -U postgres -d postgres
```

## Automatic Database Management

The BITS system automatically handles PostgreSQL database operations:

### Database Creation
- **Database Name**: `sesam_dump`
- **Auto-creation**: Created automatically when importing SQL files
- **Auto-cleanup**: Recreated if import fails

### SQL File Import
The system automatically detects file size and chooses the appropriate import method:

#### Small Files (<5GB)
- Direct import using `psql` command
- Fast processing with minimal overhead

#### Large Files (>5GB)
- **Chunked Import**: Files split into 2GB chunks
- **Sequential Processing**: Chunks imported one by one
- **Progress Monitoring**: Real-time logging
- **Error Recovery**: Continues processing even if individual chunks fail

## Configuration

### Database Connection Parameters
The system uses these default connection parameters:
```python
{
    'host': 'localhost',
    'database': 'sesam_dump',
    'user': 'postgres',
    'password': 'postgres'
}
```

### Connector Configuration
Update your connector file (`data_provider_connector/confidential/sgn_local_connector.json`):
```json
{
    "type": "PostgreSQL",
    "source_type": "file",
    "sql_filename": "confidential/DB/sesam_dump/sesam_dump.sql"
}
```

## Usage in BITS Project

### Automatic Detection
The system automatically:
1. Detects PostgreSQL server availability
2. Checks if `sesam_dump` database exists
3. Imports SQL file if database doesn't exist
4. Connects to existing database if available

### First Run Process
When running BITS for the first time with a PostgreSQL dump:
1. **Server Check**: Verifies PostgreSQL server is running
2. **Database Check**: Checks if `sesam_dump` database exists
3. **File Import**: Imports SQL file (chunked for large files)
4. **Connection**: Establishes connection to imported database

## Performance Considerations

### Memory Usage
- **Chunked Processing**: Large files processed in 2GB chunks
- **Streaming Operations**: No RAM overflow for any file size
- **Batch Operations**: Data operations optimized for large datasets

### Storage Requirements
- **Database Size**: Expect ~2-3x the SQL file size
- **Temporary Files**: Chunked imports use temporary directories
- **Auto-cleanup**: Temporary files automatically removed

## Troubleshooting

### PostgreSQL Server Issues

#### Server Not Running
```bash
sudo systemctl start postgresql
sudo systemctl status postgresql
```

#### Permission Issues
```bash
# Reset postgres user password
sudo -u postgres psql
ALTER USER postgres PASSWORD 'postgres';
\q
```

#### Connection Refused
```bash
# Check if PostgreSQL is listening
sudo netstat -tlnp | grep 5432

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### Import Issues

#### Large File Import Failures
- **Disk Space**: Ensure sufficient disk space (3x SQL file size)
- **Memory**: PostgreSQL will use available system memory
- **Permissions**: Ensure read access to SQL file

#### Chunk Import Errors
- **Partial Success**: System continues with remaining chunks
- **Log Review**: Check logs for specific chunk errors
- **Retry**: Delete database and retry import

### Database Management

#### Reset Database
```python
# Using the reset script
python tools/reset_postgresql_db.py
```

#### Manual Database Operations
```bash
# Connect to database
psql -h localhost -U postgres -d sesam_dump

# List tables
\dt

# Check database size
SELECT pg_size_pretty(pg_database_size('sesam_dump'));

# Drop and recreate database
DROP DATABASE sesam_dump;
CREATE DATABASE sesam_dump;
```

## Monitoring and Maintenance

### Performance Monitoring
```sql
-- Check active connections
SELECT count(*) FROM pg_stat_activity WHERE datname = 'sesam_dump';

-- Check database size
SELECT pg_size_pretty(pg_database_size('sesam_dump'));

-- Check table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Regular Maintenance
- **Backup Strategy**: Regular database backups recommended
- **Vacuum Operations**: PostgreSQL handles automatically
- **Index Maintenance**: Consider adding indexes for frequently queried columns

## Security Considerations

### Production Deployment
For production environments:
1. **Change Default Password**: Use strong passwords
2. **Network Security**: Restrict PostgreSQL access
3. **User Permissions**: Create dedicated database users
4. **SSL/TLS**: Enable encrypted connections

### Development Environment
Current setup is optimized for development:
- **Local Access Only**: PostgreSQL bound to localhost
- **Simple Authentication**: Password-based authentication
- **Default Credentials**: `postgres/postgres` for easy setup

## Migration from SQLite

If migrating from previous SQLite setup:
1. **Data Export**: Export data from SQLite if needed
2. **Configuration Update**: Update connector configuration
3. **Dependency Installation**: Install `psycopg2-binary`
4. **Server Setup**: Follow PostgreSQL installation steps

## Support and Documentation

### Additional Resources
- **PostgreSQL Documentation**: https://www.postgresql.org/docs/
- **psycopg2 Documentation**: https://www.psycopg.org/docs/
- **System Logs**: Check application logs for detailed error information

### Getting Help
1. Check system logs for error messages
2. Verify PostgreSQL server status
3. Test database connectivity manually
4. Review configuration files