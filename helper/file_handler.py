"""
FileHandler Module

This module provides functionality for handling file operations, particularly focused on
CSV file processing and configuration management for AI-related tasks.

The module handles comprehensive file and configuration management:
- CSV file loading and exporting with pandas integration
- Configuration file management and validation with version checking
- AI-specific configuration loading for multiple services
- Text file storage operations
- Configuration version checking and compatibility validation
- Error handling and logging for file operations

The module ensures data integrity and provides robust error handling
for file operations, making it suitable for production environments.

Dependencies:
    - pandas: For CSV file handling
        Install using one of:
        - pip install pandas
        - pip3 install pandas
        - sudo apt install python3-pandas

Classes:
    FileHandler: Main class for handling file operations and configuration management
"""

import pandas as pd
import logging
import json
from typing import Dict, Any, List, Union


class FileHandler:
    """
    A class to handle file operations and configuration management for the annotation system.

    This class manages:
        - CSV file loading and exporting
        - Configuration file loading and validation
        - AI-specific configuration management
        - Text file storage operations
        - Configuration version checking

    Attributes:
        annotate_me_json (str): JSON data loaded from the input CSV file (as string)
        config (Dict[str, Any]): Main configuration data
        ai_config (Dict[str, Dict[str, Any]]): AI-specific configuration data for different AI services
        __CONFIG_VERSION (float): Required configuration version (0.4)
    """

    __CONFIG_VERSION: float = 0.7

    def __init__(self) -> None:
        """
        Initialize the FileHandler and load configuration and CSV data.
        
        This method:
        1. Initializes configuration dictionaries
        2. Loads the main configuration file
        3. Loads AI-specific configuration files if enabled
        4. Loads the input CSV file for processing
        
        Raises:
            Exception: If configuration or CSV file loading fails
        """
        logging.debug(f"Start file handler")

        self.config = {}  # Here you go the config data from the config file
        # Here you go the ai config data from the ai config files
        self.ai_config = {"ollama": {}, "gpt4all": {}, "gpt4all_local": {}}

        self.__load_config()

        # Load data sources
        if self.config["data_provider"]["type"] == "data_provider_connector" or self.config["data_export"]["type"] == "data_provider_connector":
            self.__load_data_provider()

        if self.config["data_provider"]["type"] == "csv":
            self.__load_csv(self.config["data_provider"]["file"])
        
        if self.config["data_provider"]["type"] != "data_provider_connector" and self.config["data_provider"]["type"] != "csv":
            logging.critical(f"FileHandler, data provider type not supported: {self.config['data_provider']['type']}")
            raise Exception(f"FileHandler, data provider type not supported: {self.config['data_provider']['type']}")

    def __load_csv(self, csv_filename: str) -> None:
        """
        Load and parse a CSV file into JSON format.
        
        This method reads a CSV file using pandas and converts it to JSON format
        for processing. The JSON is stored as a string to maintain compatibility
        with existing code.
        
        Args:
            csv_filename (str): Path to the CSV file to load

        Raises:
            Exception: If the CSV file cannot be loaded or converted to JSON
            
        Example:
            >>> handler = FileHandler()
            >>> handler.__load_csv("data.csv")
            >>> print(handler.annotate_me_json[:100])
            '[{"column1": "value1", "column2": "value2"}, ...]'
        """
        try:
            csv_dataframe = pd.read_csv(csv_filename)
            logging.debug(f"FileHandler, loaded '{csv_filename}'")

        except Exception as e:
            error = f"FileHandler, unable to load '{csv_filename}': {str(e)}"
            logging.critical(error)
            raise Exception(error)

        try:
            self.annotate_me_json = csv_dataframe.to_json(orient='records')[
                :]  # Here you go str only, not a Dict
            logging.debug(f"FileHandler, CSV Dataframe converted to JSON")

        except Exception as e:
            error = f"FileHandler, unable to convert CSV Dataframe to JSON: {str(e)}"
            logging.critical(error)
            raise Exception(error)

    def export_csv(self, list_data: List[Dict[str, Any]], original_data: List[Dict[str, Any]] = None) -> None:
        """
        Export data to a CSV file.
        
        This method converts a list of dictionaries to a pandas DataFrame
        and exports it to a CSV file specified in the configuration.
        
        Args:
            list_data (List[Dict[str, Any]]): Data to be exported to CSV.
                Each dictionary represents a row in the CSV file.

        Raises:
            Exception: If the data cannot be exported to CSV
            
        Example:
            >>> handler = FileHandler()
            >>> data = [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]
            >>> handler.export_csv(data)
        """
        # Case CSV to CSV
        if self.config["data_provider"]["type"] == "csv":
            try:
                pd.DataFrame(list_data).to_csv(
                    self.config["data_export"]["file"], index=False)
                logging.debug(f"FileHandler, annotation exported to {
                            self.config['data_export']['file']}")

            except Exception as e:
                error = f"FileHandler, unable to export annotation to {
                    self.config['data_export']['file']}: {str(e)}"
                logging.critical(error)
                raise Exception(error)

        # Case Data Provider Connector to CSV
        elif self.config["data_provider"]["type"] == "data_provider_connector":
            try:
                pd.DataFrame({
                    'original': original_data,
                    'annotated': list_data
                }).to_csv(self.config["data_export"]["file"], index=False)
                logging.debug(f"FileHandler, annotation exported to {
                            self.config['data_export']['file']}")

            except Exception as e:
                error = f"FileHandler, unable to export annotation to {
                    self.config['data_export']['file']}: {str(e)}"
                logging.critical(error)
                raise Exception(error)

    def __load_live_data(self) -> None:
        """
        Load data from a live system (Not implemented).
        
        This method is a placeholder for future implementation of live data
        loading functionality. Currently not implemented.
        
        TODO: Implement this method for real-time data processing
        """
        pass

    def get_json_data(self) -> str:
        """
        Get the JSON data loaded from the input CSV file.
        
        Returns:
            str: JSON data from the input CSV file as a string
        """
        return self.annotate_me_json

    def store_text_file(self, content: str, filename: str) -> None:
        """
        Store content in a text file.
        
        This method writes text content to a file with proper error handling.
        It's used for storing various outputs like logs, reports, or processed data.
        
        Args:
            content (str): Content to be written to the file
            filename (str): Name of the file to write to

        Raises:
            Exception: If the file cannot be written
            
        Example:
            >>> handler = FileHandler()
            >>> handler.store_text_file("Hello, World!", "output.txt")
        """
        try:
            with open(filename, 'w') as f:
                f.write(content)
            logging.debug(f"FileHandler, store file '{filename}'")

        except Exception as e:
            error = f"FileHandler, unable to store file '{filename}': {str(e)}"
            logging.error(error)
            raise Exception(error)

    def __load_config(self) -> None:
        """
        Load and validate the main configuration file.
        
        This method loads the main configuration file and processes it:
        1. Loads config.json from the current directory
        2. Validates the configuration version
        3. Converts string boolean values to actual boolean types
        4. Loads AI-specific configuration files if enabled
        
        The method supports loading multiple AI service configurations
        based on the ai_use settings in the main configuration.
        
        Raises:
            Exception: If the configuration file cannot be loaded or is invalid
        """
        try:
            with open('config.json', 'r') as file:
                self.config = json.load(file)

            logging.debug(f"FileHandler, config ready")
            self.__check_config_version()

        except Exception as e:
            error = f"FileHandler, unable to load config.json: {str(e)}"
            logging.critical(error)
            raise Exception(error)

        self.__convert_true_false_values(self.config)

        # Load AI config
        if self.config["ai_use"]["ollama"] == True:
            self.__load_ai_config("ollama")
        if self.config["ai_use"]["gpt4all"] == True:
            self.__load_ai_config("gpt4all")
        if self.config["ai_use"]["gpt4all_local"] == True:
            self.__load_ai_config("gpt4all_local")

    def __load_ai_config(self, name: str) -> None:
        """
        Load AI-specific configuration file.
        
        This method loads configuration files for specific AI services
        (e.g., config_ollama.json, config_gpt4all.json) and processes
        them to convert string boolean values to actual boolean types.
        
        Args:
            name (str): Name of the AI service (e.g., 'ollama', 'gpt4all')

        Raises:
            Exception: If the AI configuration file cannot be loaded
            
        Example:
            >>> handler = FileHandler()
            >>> handler.__load_ai_config("ollama")
            # Loads config_ollama.json and stores in handler.ai_config["ollama"]
        """
        try:
            with open(f"config_{name}.json", 'r') as file:
                self.ai_config[name] = json.load(file)
                logging.debug(f"FileHandler, AI config for {name} loaded")
                self.__convert_true_false_values(self.ai_config[name])
                # logging.debug(
                #     f"FileHandler, AI config for {name} converted to boolean values")
        except Exception as e:
            error = f"FileHandler, unable to load config_{name}.json: {str(e)}"
            logging.critical(error)
            raise Exception(error)

    def __convert_true_false_values(self, data: Dict[str, Any]) -> None:
        """
        Recursively converts string representations of boolean values ('True'/'False') 
        to actual boolean types (True/False) in a dictionary.
        
        This method is necessary because JSON files store boolean values as strings,
        but the application expects actual boolean types for proper functionality.
        
        Args:
            data (Dict[str, Any]): The dictionary containing potential string boolean 
                values to convert. The conversion is done in-place.

        Example:
            Input dictionary:  {'key1': 'True', 'key2': {'nested_key': 'False'}}
            Output dictionary: {'key1': True, 'key2': {'nested_key': False}}
        """
        for key, value in data.items():
            if isinstance(value, dict):
                self.__convert_true_false_values(value)
            elif value == "True" or value == "true":
                data[key] = True
            elif value == "False" or value == "false":
                data[key] = False

    def __check_config_version(self) -> None:
        """
        Verify the configuration file version.
        
        This method checks if the configuration file version meets the minimum
        required version. This ensures compatibility and prevents issues with
        outdated configuration formats.
        
        Raises:
            Exception: If the configuration version is below the required version
        """
        if self.config["version"] < self.__CONFIG_VERSION:
            logging.critical("This config version is outdated.")
            raise Exception("This config version is outdated.")

# Data Provider Connector
    def __load_data_provider(self) -> None:
        """
        Load the data provider connector.
        """
        self.config["data_provider_connection"] = {"data_provider":{}, "data_export":{}}
        
        # Source data provider
        """
        if self.config["data_provider"]["type"] == "data_provider_connector":
            self.data_provider_source.load_config(self.config, # Common config
                self.config["data_provider"]["data_provider_connector"], # Private provider config file
                "data_provider") # Role later in the self.config["data_provider_connection"]
        """

        # Target data provider TOTO: Update this to use the new data provider connector in the main.py
        if self.config["data_export"]["type"] == "data_provider_connector":
            self.data_provider_target.load_config(self.config,
                self.config ["data_export"]["data_provider_connector"],
                "data_export")

if __name__ == "__main__":
    print("Start FileHandler instance here")
