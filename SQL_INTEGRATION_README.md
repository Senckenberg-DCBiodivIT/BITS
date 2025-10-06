# PostgreSQL Integration for BITS

## Overview

The PostgreSQL integration allows accessing and querying PostgreSQL databases through the `data_provider_connector` in `config.json`. The system is now optimized for PostgreSQL-only operation, providing better performance and maintainability for large datasets.

## Implemented Functions

### DataProvider Class (`helper/data_provider.py`)

The streamlined `DataProvider` class offers the following functions:

- **PostgreSQL Connection**: Direct connection to PostgreSQL server
- **SQL Dump Import**: Automatic import of PostgreSQL dump files
- **Large File Handling**: Chunked processing for files >5GB
- **Memory-safe Processing**: Optimized for large datasets without RAM overflow
- **Table Information**: Retrieving metadata about database structures
- **Data Import/Export**: Loading and saving data with batch operations

### Main Methods

```python
# Load configuration and connect
provider.load_config(common_config, config_file, role)
provider.connect()

# Execute SQL queries
results = provider.execute_query("SELECT * FROM table_name")

# Load data
data = provider.load_data(table_name="table_name", limit=100)

# Save data
provider.save_data(data, "table_name")

# Table information
tables = provider.get_table_info()
```

## Configuration

### config.json

```json
{
    "data_provider": {
        "type": "data_provider_connector",
        "data_provider_connector": "data_provider_connector/confidential/sgn_local_connector.json"
    }
}
```

### sgn_local_connector.json

```json
{
    "type": "PostgreSQL",
    "source_type": "file",
    "sql_filename": "confidential/DB/sesam_dump/sesam_dump.sql"
}
```

## PostgreSQL Requirements

### Dependencies
- **psycopg2-binary**: `pip install psycopg2-binary`
- **PostgreSQL Server**: Running locally on port 5432
- **Database**: `sesam_dump` (automatically created)

### Server Setup
The system requires a local PostgreSQL server with:
- Host: `localhost`
- Port: `5432` (default)
- User: `postgres`
- Password: `postgres`
- Database: `sesam_dump` (auto-created)

## Large SQL File Processing

The system automatically handles different file sizes:

### Small Files (<5GB)
- Direct import using `psql` command
- Fast processing with minimal overhead

### Large Files (>5GB)
- **Chunked Processing**: Files split into 2GB chunks
- **Sequential Import**: Chunks imported one by one
- **Progress Monitoring**: Real-time logging of import progress
- **Memory Safety**: No RAM overflow issues

## Usage Examples

### Basic Usage

```python
from helper.data_provider import DataProvider

# Initialize DataProvider
provider = DataProvider()

# Load configuration
provider.load_config(common_config, config_file, "data_provider")

# Establish connection (automatically imports SQL file if needed)
provider.connect()

# Query data
results = provider.execute_query("SELECT * FROM objects LIMIT 10")

# Get table information
tables = provider.get_table_info()

# Close connection
provider.close_connection()
```

### Advanced Usage

```python
# Load data from specific table with limit
data = provider.load_data(table_name="specimens", limit=1000)

# Execute custom query
results = provider.execute_query(
    "SELECT * FROM objects WHERE collection_id = %s", 
    (123,)
)

# Save new data
new_data = [{"name": "sample", "type": "specimen"}]
provider.save_data(new_data, "objects")
```

## Current SQL File

The existing SQL file (`confidential/DB/sesam_dump/sesam_dump.sql`):
- **Size**: 19.4 GB
- **Type**: PostgreSQL dump
- **Tables**: 68+ tables
- **Structure**: Senckenberg database with objects, persons, locations, etc.

## Error Handling

### PostgreSQL Server Not Available
If PostgreSQL server is not running, the system displays helpful setup instructions:
- Installation commands
- Service start commands
- User configuration steps
- Link to detailed setup guide

### Import Failures
- Automatic retry mechanisms for chunked imports
- Detailed error logging
- Graceful fallback handling

## Performance Optimizations

1. **Chunked Processing**: Large files processed in 2GB chunks
2. **Batch Operations**: Data saved in batches for efficiency
3. **Connection Pooling**: Reuses database connections
4. **Memory Management**: Streaming operations prevent RAM overflow
5. **Progress Monitoring**: Real-time feedback for long operations

## Integration in file_handler.py

The `FileHandler` automatically initializes DataProvider instances:
- Detects `data_provider_connector` configuration
- Loads connector configuration files
- Initializes source and target DataProvider instances

## Troubleshooting

### Common Issues

1. **PostgreSQL Server Not Running**
   ```bash
   sudo systemctl start postgresql
   ```

2. **Permission Denied**
   ```bash
   sudo -u postgres psql
   ALTER USER postgres PASSWORD 'postgres';
   ```

3. **Import Failures**
   - Check file permissions
   - Verify PostgreSQL server status
   - Review error logs for specific issues

### Debug Mode
Enable detailed logging by setting log level to DEBUG in your application.

## Next Steps

1. **Performance Monitoring**: Track import times and query performance
2. **Query Optimization**: Develop optimized queries for Senckenberg data
3. **Indexing Strategy**: Create appropriate indexes for large datasets
4. **Backup Strategy**: Implement regular database backups