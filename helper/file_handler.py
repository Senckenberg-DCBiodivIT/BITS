"""FileHandler Module

This module provides functionality for handling file operations, particularly focused on
CSV file processing and configuration management for AI-related tasks.

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


class FileHandler:
    """
    A class to handle file operations and configuration management for the annotation system.

    This class manages:
        - CSV file loading and exporting
        - Configuration file loading and validation
        - AI-specific configuration management
        - Text file storage operations

    Attributes:
        annotate_me_json (dict): JSON data loaded from the input CSV file
        config (dict): Main configuration data
        ai_config (dict): AI-specific configuration data for different AI services
    """

    __CONFIG_VERSION: float = 0.4

    def __init__(self) -> None:
        logging.debug(f"Start file handler")

        self.config = {}  # Here you go the config data from the config file
        # Here you go the ai config data from the ai config files
        self.ai_config = {"ollama": {}, "gpt4all": {}, "gpt4all_local": {}}

        self.__load_config()
        # TODO: Currently only the input file is loaded. In  later steps we will load the live data.
        self.__load_csv(self.config["annotation"]["input_file"])

    # CSV
    def __load_csv(self, csv_filename) -> None:
        """
        Load and parse a CSV file into JSON format.

        Args:
            csv_filename (str): Path to the CSV file to load

        Raises:
            Exception: If the CSV file cannot be loaded or converted to JSON
        """
        try:
            csv_dataframe = pd.read_csv(csv_filename)
            logging.debug(f"FileHandler, loaded '{csv_filename}'")

        except:
            error = f"FileHandler, unable to load '{csv_filename}'"
            logging.critical(error)
            raise Exception(error)

        try:
            self.annotate_me_json = csv_dataframe.to_json(orient='records')[
                :]  # Here you go str only, not a Dict
            logging.debug(f"FileHandler, CSV Dataframe converted to JSON")

        except:
            error = "FileHandler, unable to convert CSV Dataframe to JSON"
            logging.critical(error)
            raise Exception(error)

    def export_csv(self, list_data) -> None:
        """
        Export data to a CSV file.

        Args:
            list_data (list): Data to be exported to CSV

        Raises:
            Exception: If the data cannot be exported to CSV
        """
        try:
            list_data = pd.DataFrame(list_data).to_csv(
                self.config["annotation"]["output_file"], index=False)
            logging.debug(f"FileHandler, annotation exported to {
                          self.config['annotation']['output_file']}")

        except:
            error = f"FileHandler, unable to export annotation to {
                self.config['annotation']['output_file']}"
            logging.critical(error)
            raise Exception(error)

    # Live System
    def __load_live_data(self) -> None:
        """
        Load data from a live system (Not implemented).

        TODO: Implement this method
        """
        pass

    # Data
    def get_json_data(self) -> dict:
        """
        Get the JSON data loaded from the input CSV file.

        Returns:
            dict: JSON data from the input CSV file
        """
        return self.annotate_me_json

    def store_text_file(self, content, filename) -> None:
        """
        Store content in a text file.

        Args:
            content (str): Content to be written to the file
            filename (str): Name of the file to write to

        Raises:
            Exception: If the file cannot be written
        """
        try:
            with open(filename, 'w') as f:
                f.write(content)
            logging.debug(f"FileHandler, store file '{filename}'")

        except:
            error = f"FileHandler, unable to store file '{filename}'"
            logging.error(error)
            raise Exception(error)

    # Config
    def __load_config(self) -> None:
        """
        Load and validate the main configuration file.

        Loads config.json and relevant AI configuration files based on settings.
        Converts string boolean values to actual boolean types.

        Raises:
            Exception: If the configuration file cannot be loaded or is invalid
        """
        try:
            with open('config.json', 'r') as file:
                self.config = json.load(file)

            logging.debug(f"FileHandler, config ready")
            self.__check_config_version()

        except:
            error = f"FileHandler, unable to load config.json"
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

    def __load_ai_config(self, name) -> None:
        """
        Load AI-specific configuration file.

        Args:
            name (str): Name of the AI service (e.g., 'ollama', 'gpt4all')

        Raises:
            Exception: If the AI configuration file cannot be loaded
        """
        try:
            with open(f"config_{name}.json", 'r') as file:
                self.ai_config[name] = json.load(file)
                logging.debug(f"FileHandler, AI config for {name} loaded")
                self.__convert_true_false_values(self.ai_config[name])
                # logging.debug(
                #     f"FileHandler, AI config for {name} converted to boolean values")
        except:
            error = f"FileHandler, unable to load config_{name}.json"
            logging.critical(error)
            raise Exception(error)

    def __convert_true_false_values(self, data) -> None:
        """
        Recursively converts string representations of boolean values ('True'/'False') to actual boolean types (True/False)
        in a dictionary.

        Args:
            data (dict): The dictionary containing potential string boolean values to convert

        Example:
            Input dictionary:  {'key1': 'True', 'key2': {'nested_key': 'False'}}
            Output dictionary: {'key1': True, 'key2': {'nested_key': False}}
        """

        for key, value in data.items():
            if isinstance(value, dict):
                self.__convert_true_false_values(value)
            elif value == "True":
                data[key] = True
            elif value == "False":
                data[key] = False

    def __check_config_version(self) -> None:
        """
        Verify the configuration file version.

        Raises:
            Exception: If the configuration version is below 0.4
        """

        if self.config["version"] < self.__CONFIG_VERSION:
            logging.critical("This config version is outdated.")
            raise Exception("This config version is outdated.")


if __name__ == "__main__":
    print("Start FileHandler instance here")
