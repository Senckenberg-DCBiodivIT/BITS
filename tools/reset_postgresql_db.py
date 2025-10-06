#!/usr/bin/env python3
"""
PostgreSQL Database Reset Script for BITS Project

This script removes the PostgreSQL database that was imported from SQL files.
It reads the configuration from the connector file to determine which database to reset.

Usage:
    python3 tools/reset_postgresql_db.py
    python3 tools/reset_postgresql_db.py --config data_provider_connector/confidential/sgn_local_connector.json
"""

import os
import sys
import json
import logging
import argparse
import psycopg2
from psycopg2 import sql

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_config(config_file):
    """Load configuration from connector file."""
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"❌ Error loading config file {config_file}: {e}")
        sys.exit(1)

def check_postgresql_connection():
    """Check if PostgreSQL server is available."""
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='postgres',
            user='postgres',
            password='postgres'
        )
        conn.close()
        return True
    except Exception as e:
        print(f"❌ PostgreSQL server not available: {e}")
        return False

def get_database_info(config):
    """Extract database information from config."""
    if config.get('type') != 'PostgreSQL':
        print("❌ This script only works with PostgreSQL databases")
        sys.exit(1)
    
    # Extract database name from SQL filename
    sql_filename = config.get('sql_filename', '')
    if not sql_filename:
        print("❌ No SQL filename found in config")
        sys.exit(1)
    
    # Default database name (can be customized)
    db_name = 'sesam_dump'
    
    return {
        'db_name': db_name,
        'sql_filename': sql_filename
    }

def check_database_exists(db_name):
    """Check if the database exists."""
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='postgres',
            user='postgres',
            password='postgres'
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 1 FROM pg_database WHERE datname = %s
        """, (db_name,))
        
        exists = cursor.fetchone() is not None
        cursor.close()
        conn.close()
        
        return exists
    except Exception as e:
        print(f"❌ Error checking database existence: {e}")
        return False

def get_database_stats(db_name):
    """Get statistics about the database."""
    try:
        conn = psycopg2.connect(
            host='localhost',
            database=db_name,
            user='postgres',
            password='postgres'
        )
        cursor = conn.cursor()
        
        # Get table count
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        table_count = cursor.fetchone()[0]
        
        # Get database size
        cursor.execute("""
            SELECT pg_size_pretty(pg_database_size(%s))
        """, (db_name,))
        db_size = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return {
            'table_count': table_count,
            'db_size': db_size
        }
    except Exception as e:
        print(f"⚠️  Could not get database stats: {e}")
        return None

def drop_database(db_name):
    """Drop the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='postgres',
            user='postgres',
            password='postgres'
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Terminate all connections to the database
        cursor.execute("""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = %s AND pid <> pg_backend_pid()
        """, (db_name,))
        
        # Drop the database
        cursor.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(
            sql.Identifier(db_name)
        ))
        
        cursor.close()
        conn.close()
        
        return True
    except Exception as e:
        print(f"❌ Error dropping database: {e}")
        return False

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Reset PostgreSQL database for BITS project')
    parser.add_argument('--config', 
                       default='data_provider_connector/confidential/sgn_local_connector.json',
                       help='Path to connector config file')
    parser.add_argument('--force', action='store_true',
                       help='Skip confirmation prompt')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    print("🗑️  PostgreSQL Database Reset Script")
    print("=" * 50)
    
    # Load configuration
    config_file = args.config
    if not os.path.exists(config_file):
        print(f"❌ Config file not found: {config_file}")
        sys.exit(1)
    
    config = load_config(config_file)
    db_info = get_database_info(config)
    
    print(f"📁 Config file: {config_file}")
    print(f"🗄️  Database: {db_info['db_name']}")
    print(f"📄 SQL file: {db_info['sql_filename']}")
    print()
    
    # Check PostgreSQL connection
    if not check_postgresql_connection():
        print("❌ PostgreSQL server is not available")
        print("Please start PostgreSQL server first:")
        print("  sudo systemctl start postgresql")
        sys.exit(1)
    
    # Check if database exists
    if not check_database_exists(db_info['db_name']):
        print(f"ℹ️  Database '{db_info['db_name']}' does not exist")
        print("Nothing to reset.")
        sys.exit(0)
    
    # Get database statistics
    stats = get_database_stats(db_info['db_name'])
    if stats:
        print(f"📊 Database Statistics:")
        print(f"   Tables: {stats['table_count']}")
        print(f"   Size: {stats['db_size']}")
        print()
    
    # Safety confirmation
    if not args.force:
        print("⚠️  WARNING: This will permanently delete the PostgreSQL database!")
        print(f"   Database: {db_info['db_name']}")
        print(f"   Tables: {stats['table_count'] if stats else 'Unknown'}")
        print()
        
        response = input("Are you sure you want to continue? Type 'DELETE' to confirm: ")
        if response != 'DELETE':
            print("❌ Operation cancelled")
            sys.exit(0)
    
    # Drop the database
    print(f"🗑️  Dropping database '{db_info['db_name']}'...")
    
    if drop_database(db_info['db_name']):
        print("✅ Database successfully dropped")
        print()
        print("📝 Next steps:")
        print("1. Run your BITS application again")
        print("2. The system will automatically re-import the SQL file")
        print("3. This may take some time for large files (19GB)")
    else:
        print("❌ Failed to drop database")
        sys.exit(1)

if __name__ == '__main__':
    main()
