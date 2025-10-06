import json
import logging
import sys
import subprocess
from typing import Dict, Any, List, Union, Optional
import os
import tempfile
import shutil

# Try to import psycopg2, but don't fail if it's not available
try:
    import psycopg2
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    logging.warning("psycopg2 not available. PostgreSQL functionality will be limited.")


class DataProvider:
    """
    Data provider for PostgreSQL databases.
    
    This class handles connections to PostgreSQL databases,
    including importing SQL dump files and providing query execution capabilities.
    """

    def __init__(self):
        """
        Initialize the DataProvider.
        """
        self.common_config = {}
        self.instance_config = {}
        
        # Database connection attributes
        self.connection = None
        self.cursor = None
        self.db_type = "postgresql"
        self.sql_file_path = None
        self.postgresql_import_completed = False

    ########################################
    # SHARED/CORE FUNCTIONALITY
    ########################################

    def load_config(self, common_config: dict, config_file: str, role: str):
        """
        Load the configuration for the data provider.
        """
        self.common_config = common_config
        self.instance_config = self.common_config["data_provider_connection"][role]

        # Connector config from the config file
        # Convert relative path to absolute path
        if not os.path.isabs(config_file):
            config_file = os.path.abspath(config_file)
        if os.path.exists(config_file):
            with open(config_file, "r", encoding="utf-8") as f:
                connector_data = f.read()
            try:
                # Try to parse as JSON
                connector_dict = json.loads(connector_data)
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse connector file as JSON: {e}")
                raise ValueError(f"Connector file must be valid JSON: {e}")
            self.instance_config = {"connector" : connector_dict}
        else:
            logging.warning(f"Connector file not found: {config_file}")

        # Load SQL file path from config if source_type is file
        if self.instance_config["connector"]["source_type"] == "file":
            if (os.path.exists(self.instance_config["connector"]["sql_filename"])):
                self.sql_file_path = self.instance_config["connector"]["sql_filename"]
                logging.debug(f"DataProvider, SQL file path loaded: {self.sql_file_path}")
            else:
                error_msg = f"SQL file not found: {self.instance_config['connector']['sql_filename']}"
                logging.error(error_msg)
                print(f"ERROR: {error_msg}")
                sys.exit(1)

            # Connect to the SQL file
            self.connect_to_sql_file()

        # Load connection parameters from config if source_type is service
        elif self.instance_config["connector"]["source_type"] == "service":
            pass

    def connect(self):
        """
        Connect to the PostgreSQL data source based on the configuration.
        """
        if not hasattr(self, 'instance_config') or not self.instance_config:
            raise Exception("Configuration not loaded. Call load_config() first.")
        
        source_type = self.instance_config["connector"]["source_type"]
        
        if source_type == "file":
            if not self.postgresql_import_completed:
                logging.info("Connecting to PostgreSQL database...")
                self.connect_to_sql_file()
            else:
                logging.info("PostgreSQL import already completed, skipping database check")
        elif source_type == "service":
            logging.info("Connecting to PostgreSQL service...")
            # This would need connection parameters from config
            raise NotImplementedError("Service connection not yet implemented")
        else:
            raise Exception(f"Unknown source type: {source_type}")

    def connect_to_sql_file(self):
        """
        Connect to a PostgreSQL SQL file.
        """
        if not self.sql_file_path or not os.path.exists(self.sql_file_path):
            raise Exception(f"SQL file not found: {self.sql_file_path}")
        
        # Check if PostgreSQL server is available
        if not self._check_postgresql_server_available():
            self._show_postgresql_not_available_message()
            raise Exception("PostgreSQL server not available")
        
        # Check if PostgreSQL database already exists
        if self._check_postgresql_database_exists():
            logging.info("PostgreSQL database already exists, connecting...")
            self._connect_to_existing_postgresql()
            return
        
        # Database doesn't exist - import SQL file
        logging.info("PostgreSQL database not found, importing SQL file...")
        file_size_mb = os.path.getsize(self.sql_file_path) / (1024 * 1024)
        
        if file_size_mb > 5000:  # Files larger than 5GB
            logging.info(f"Large file detected ({file_size_mb:.1f}MB), using chunked import")
            self._split_and_import_large_file()
        else:
            logging.info(f"Small file detected ({file_size_mb:.1f}MB), using direct import")
            self._import_small_sql_file()

    def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """
        Execute a SQL query and return results.
        
        Args:
            query (str): SQL query to execute
            params (tuple): Query parameters for prepared statements
            
        Returns:
            List[Dict[str, Any]]: Query results as list of dictionaries
        """
        if not self.connection or not self.cursor:
            raise Exception("Database not connected. Call connect() first.")
            
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
                
            # Get column names
            columns = [description[0] for description in self.cursor.description] if self.cursor.description else []
            
            # Fetch results
            rows = self.cursor.fetchall()
            
            # Convert to list of dictionaries
            results = []
            for row in rows:
                row_dict = {}
                for i, value in enumerate(row):
                    if i < len(columns):
                        row_dict[columns[i]] = value
                results.append(row_dict)
                
            logging.debug(f"DataProvider, query executed successfully, {len(results)} rows returned")
            return results
            
        except Exception as e:
            logging.error(f"DataProvider, query execution failed: {str(e)}")
            raise Exception(f"Query execution failed: {str(e)}")

    def get_table_info(self, table_name: str = None) -> List[Dict[str, Any]]:
        """
        Get information about database tables.
        
        Args:
            table_name (str): Specific table name (optional)
            
        Returns:
            List[Dict[str, Any]]: Table information
        """
        if not self.connection or not self.cursor:
            raise Exception("Database not connected. Call connect() first.")
            
        try:
            if table_name:
                query = """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = %s
                ORDER BY ordinal_position
                """
                return self.execute_query(query, (table_name,))
            else:
                query = """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
                """
                return self.execute_query(query)
                    
        except Exception as e:
            logging.error(f"DataProvider, get_table_info failed: {str(e)}")
            raise Exception(f"Get table info failed: {str(e)}")

    def load_data(self, query: str = None, table_name: str = None, limit: int = None):
        """
        Load data from the database.

        Args:
            query (str): Custom SQL query (optional)
            table_name (str): Table name to load from (optional)
            limit (int): Maximum number of rows to return (optional)

        Returns:
            List[Dict[str, Any]]: The loaded data.
        """
        if not self.connection or not self.cursor:
            raise Exception("Database not connected. Call connect() first.")
            
        try:
            if query:
                # Use custom query
                sql_query = query
                if limit:
                    sql_query += f" LIMIT {limit}"
                return self.execute_query(sql_query)
                
            elif table_name:
                # Load from specific table
                sql_query = f"SELECT * FROM {table_name}"
                if limit:
                    sql_query += f" LIMIT {limit}"
                return self.execute_query(sql_query)
                
            else:
                # Load all tables info
                return self.get_table_info()
                
        except Exception as e:
            logging.error(f"DataProvider, load_data failed: {str(e)}")
            raise Exception(f"Load data failed: {str(e)}")

    def save_data(self, data: List[Dict[str, Any]], table_name: str):
        """
        Save data to the database.

        Args:
            data (List[Dict[str, Any]]): The data to save.
            table_name (str): Target table name.
        """
        if not self.connection or not self.cursor:
            raise Exception("Database not connected. Call connect() first.")
            
        if not data:
            logging.warning("DataProvider, no data to save")
            return
            
        try:
            # Get column names from first row
            columns = list(data[0].keys())
            columns_str = ", ".join(columns)
            placeholders = ", ".join(["%s"] * len(columns))
            
            query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
            
            # Prepare data for insertion
            values_list = []
            for row in data:
                values = tuple(row[col] for col in columns)
                values_list.append(values)
            
            # Execute batch insert
            self.cursor.executemany(query, values_list)
            self.connection.commit()
            
            logging.debug(f"DataProvider, saved {len(data)} rows to table {table_name}")
            
        except Exception as e:
            logging.error(f"DataProvider, save_data failed: {str(e)}")
            self.connection.rollback()
            raise Exception(f"Save data failed: {str(e)}")

    def close_connection(self):
        """
        Close the database connection.
        """
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        logging.debug("DataProvider, database connection closed")

    ########################################
    # POSTGRESQL FUNCTIONALITY
    ########################################

    def _check_postgresql_server_available(self) -> bool:
        """
        Check if PostgreSQL server is available.
        """
        try:
            # Try to connect to PostgreSQL server
            conn_params = {
                'host': 'localhost',
                'database': 'postgres',
                'user': 'postgres',
                'password': 'postgres'
            }
            
            test_conn = psycopg2.connect(**conn_params)
            test_conn.close()
            
            logging.info("PostgreSQL server is available")
            return True
            
        except Exception as e:
            logging.warning(f"PostgreSQL server not available: {str(e)}")
            return False

    def _show_postgresql_not_available_message(self):
        """
        Show helpful message when PostgreSQL is not available.
        """
        print("\n" + "="*80)
        print("❌ POSTGRESQL SERVER NOT AVAILABLE")
        print("="*80)
        print("PostgreSQL is required to process PostgreSQL dump files.")
        print("Please install and start PostgreSQL server.")
        print("\n📖 SETUP INSTRUCTIONS:")
        print("1. Check if PostgreSQL is installed:")
        print("   ps aux | grep postgres")
        print("\n2. If not installed, install PostgreSQL:")
        print("   sudo apt update")
        print("   sudo apt install postgresql postgresql-contrib")
        print("\n3. Start PostgreSQL service:")
        print("   sudo systemctl start postgresql")
        print("   sudo systemctl enable postgresql")
        print("\n4. Set up PostgreSQL user:")
        print("   sudo -u postgres psql")
        print("   ALTER USER postgres PASSWORD 'postgres';")
        print("   \\q")
        print("\n📋 For detailed instructions, see: POSTGRESQL_SETUP.md")
        print("="*80 + "\n")

    def _check_postgresql_database_exists(self) -> bool:
        """
        Check if the PostgreSQL database already exists.
        """
        try:
            # Try to connect to the database
            conn_params = {
                'host': 'localhost',
                'database': 'sesam_dump',
                'user': 'postgres',
                'password': 'postgres'
            }
            
            test_conn = psycopg2.connect(**conn_params)
            test_cursor = test_conn.cursor()
            test_cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
            table_count = test_cursor.fetchone()[0]
            test_conn.close()
            
            if table_count > 0:
                logging.info(f"PostgreSQL database exists with {table_count} tables")
                return True
            else:
                logging.info("PostgreSQL database exists but is empty")
                return False
                
        except Exception as e:
            logging.info(f"PostgreSQL database does not exist: {str(e)}")
            return False

    def _connect_to_existing_postgresql(self):
        """
        Connect to existing PostgreSQL database.
        """
        try:
            conn_params = {
                'host': 'localhost',
                'database': 'sesam_dump',
                'user': 'postgres',
                'password': 'postgres'
            }
            
            self.connection = psycopg2.connect(**conn_params)
            self.cursor = self.connection.cursor()
            
            logging.info("Successfully connected to existing PostgreSQL database")
            
        except Exception as e:
            logging.error(f"Failed to connect to existing PostgreSQL database: {str(e)}")
            raise

    def _import_small_sql_file(self):
        """
        Import small SQL file directly into PostgreSQL.
        """
        try:
            # Create database
            self._create_postgresql_database()
            
            # Import SQL file
            self._import_sql_file_to_postgresql()
            
            # Connect to imported database
            self._connect_to_existing_postgresql()
            
        except Exception as e:
            logging.error(f"Failed to import small SQL file: {str(e)}")
            raise

    def _create_postgresql_database(self):
        """
        Create PostgreSQL database for the SQL file.
        """
        try:
            # Connect to default database to create new database
            conn_params = {
                'host': 'localhost',
                'database': 'postgres',
                'user': 'postgres',
                'password': 'postgres'
            }
            
            conn = psycopg2.connect(**conn_params)
            conn.autocommit = True
            cursor = conn.cursor()
            
            # Drop and create database
            cursor.execute("DROP DATABASE IF EXISTS sesam_dump")
            cursor.execute("CREATE DATABASE sesam_dump")
            
            cursor.close()
            conn.close()
            
            logging.info("PostgreSQL database 'sesam_dump' created successfully")
            
        except Exception as e:
            logging.error(f"Failed to create PostgreSQL database: {str(e)}")
            raise

    def _import_sql_file_to_postgresql(self):
        """
        Import SQL file into PostgreSQL database.
        """
        try:
            # Import SQL file with psql
            env = os.environ.copy()
            env['PGPASSWORD'] = 'postgres'
            psql_cmd = f"psql -h localhost -U postgres -d sesam_dump -f {self.sql_file_path}"
            
            logging.info(f"Importing SQL file: {self.sql_file_path}")
            result = subprocess.run(psql_cmd, shell=True, capture_output=True, text=True, env=env)
            
            if result.returncode != 0:
                raise Exception(f"SQL import failed: {result.stderr}")
            
            logging.info("SQL file imported successfully")
            
        except Exception as e:
            logging.error(f"Failed to import SQL file: {str(e)}")
            raise

    def _split_and_import_large_file(self):
        """
        Split large SQL file into chunks and import them sequentially.
        Based on Perplexity recommendations for 19GB files.
        """
        try:
            # Create temporary directory for chunks in the same directory as the SQL file
            sql_dir = os.path.dirname(self.sql_file_path)
            temp_dir = os.path.join(sql_dir, "temp_chunks")
            os.makedirs(temp_dir, exist_ok=True)
            logging.info(f"Created temporary directory: {temp_dir}")
            
            # Split file into 2GB chunks
            chunk_size = "2G"
            split_cmd = f"split -b {chunk_size} {self.sql_file_path} {temp_dir}/chunk_"
            logging.info(f"Splitting file with command: {split_cmd}")
            
            result = subprocess.run(split_cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"File splitting failed: {result.stderr}")
            
            # Get list of chunk files
            chunk_files = sorted([f for f in os.listdir(temp_dir) if f.startswith("chunk_")])
            logging.info(f"Created {len(chunk_files)} chunks")
            
            # Import chunks sequentially
            for i, chunk_file in enumerate(chunk_files):
                chunk_path = os.path.join(temp_dir, chunk_file)
                logging.info(f"Importing chunk {i+1}/{len(chunk_files)}: {chunk_file}")
                
                # Import chunk with psql (set password via environment variable)
                env = os.environ.copy()
                env['PGPASSWORD'] = 'postgres'
                psql_cmd = f"psql -h localhost -U postgres -d sesam_dump -f {chunk_path}"
                result = subprocess.run(psql_cmd, shell=True, capture_output=True, text=True, env=env)
                
                if result.returncode != 0:
                    logging.warning(f"Chunk {chunk_file} had errors: {result.stderr}")
                else:
                    logging.info(f"Successfully imported chunk {chunk_file}")
                    
                # DEBUG: Check if data actually exists in PostgreSQL
                try:
                    debug_conn = psycopg2.connect(
                        host='localhost',
                        database='sesam_dump',
                        user='postgres',
                        password='postgres'
                    )
                    debug_cursor = debug_conn.cursor()
                    debug_cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
                    table_count = debug_cursor.fetchone()[0]
                    logging.info(f"DEBUG: PostgreSQL has {table_count} tables after chunk {chunk_file}")
                    debug_conn.close()
                except Exception as e:
                    logging.warning(f"DEBUG: Could not check PostgreSQL after chunk {chunk_file}: {e}")
            
            # Clean up temporary directory
            shutil.rmtree(temp_dir)
            logging.info("File splitting and import completed successfully")
            
            # Connect to the imported database
            self._connect_to_imported_postgresql()
            self.postgresql_import_completed = True
            
        except Exception as e:
            logging.error(f"File splitting approach failed: {str(e)}")
            # No fallback - PostgreSQL is required for large files
            raise Exception(f"PostgreSQL import failed: {str(e)}")

    def _connect_to_imported_postgresql(self):
        """
        Connect to the PostgreSQL database after successful import.
        """
        try:
            conn_params = {
                'host': 'localhost',
                'database': 'sesam_dump',
                'user': 'postgres',
                'password': 'postgres'
            }
            
            self.connection = psycopg2.connect(**conn_params)
            self.cursor = self.connection.cursor()
            
            logging.info("Successfully connected to imported PostgreSQL database")
            
        except Exception as e:
            logging.error(f"Failed to connect to imported database: {str(e)}")
            raise