"""
Main Module for Content Handling and Annotation Processing

This module provides the main entry point for the BITS annotation system.
It orchestrates the entire annotation workflow including text processing,
terminology matching, and result generation.

The system integrates multiple AI services for noun phrase recognition and
provides both batch processing and interactive web-based annotation capabilities.

Setup Instructions:
------------------
1. Package Requirements:
   - requests: pip3 install requests
   - spacy: pip3 install spacy
   - gpt4all: pip3 install gpt4all
   - flask: pip3 install flask
   
2. Language Models:
   - English: python3 -m spacy download en_core_web_lg
   - German: python3 -m spacy download de_core_news_lg

Dependencies:
------------
- helper.file_handler: File I/O operations, configuration handling
- helper.cache: Thread-safe caching mechanism
- helper.validator: Data validation and integrity checking
- helper.statistics_helper: Statistical analysis and reporting
- helper.annotation_helper: Annotation processing and result formatting
- helper.bits_helper: TIB terminology service operations
- helper.text_helper: Text processing and noun phrase recognition
- ui.web_ui: Web interface and API endpoints

Classes:
    ContentHandler: Main handler for content processing and annotation workflow
"""

from helper.file_handler import FileHandler as File
from helper.cache import Cache as Cache
from helper.validator import Validator as Validator

from helper.statistics_helper import StatisticsHelper as SH
from helper.annotation_helper import AnnotationHelper as AH
from helper.bits_helper import BitsHelper as BH
from helper.text_helper import TextHelper as TH

from ui.web_ui import WebUI

import copy
import json

import time
import logging
import threading
from typing import Dict, Any, List

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(message)s\n")


class ContentHandler(TH, BH, AH, SH, Validator, Cache, File, WebUI):
    """
    Main handler for content processing and annotation workflow.

    This class inherits from multiple helper classes to provide comprehensive
    functionality for text processing, TIB terminology service operations, 
    annotations, statistics, validation, caching, and file operations. 
    It orchestrates the entire annotation workflow from data loading to 
    result generation.

    The class implements a multi-inheritance pattern to combine functionality
    from specialized helper classes while maintaining a clean interface for
    the main application logic. This design allows for modular functionality
    while providing a unified interface for the annotation system.

    The workflow includes:
    1. Data loading and preprocessing
    2. Noun phrase recognition using AI services
    3. Terminology matching against TIB service
    4. Annotation application and validation
    5. Result export and statistics collection

    Attributes:
        explicit_terminologies (List[str]): Configuration for explicit terminology sources
        use_collection (bool): Whether to use collection-based terminology search
        use_all_ts (bool): Whether to use all available terminologies
        ignore_cell_value (List[str]): Values to ignore during processing
        relevant_fields (Dict[str, List[str]]): Fields to process by language
        max_iterations (int): Maximum number of iterations for processing
        max_threads (int): Maximum number of concurrent threads
        ai_use (Dict[str, bool]): Configuration for AI services
        load_json_loads (List[Dict[str, Any]]): Processed JSON data
        original_json_loads (List[Dict[str, Any]]): Original data for validation
        fallback_translation_libretranslate (Dict[str, Any]): Translation service configuration
        mids_terms (Dict[str, Any]): MIDS terms configuration for metadata
    """

    def __init__(self) -> None:
        """
        Initialize the ContentHandler with configuration settings and prepare
        for content processing.
        
        This method initializes all inherited classes in the correct order
        and loads configuration settings. It also starts the WebUI in a
        separate thread if enabled.
        
        The initialization process:
        1. Initializes base classes (File, Cache, StatisticsHelper)
        2. Loads configuration settings
        3. Sets up terminology search configuration
        4. Initializes WebUI if enabled
        5. Processes JSON data for annotation
        """
        # Initialize base classes in correct order
        File.__init__(self)
        Cache.__init__(self)
        SH.__init__(self)

        # Load configuration settings
        self.explicit_terminologies = self.config["annotation"]["ts_sources"]["explicit_terminologies"]
        self.use_collection = self.config["annotation"]["ts_sources"]["collection"]
        self.use_all_ts = not self.explicit_terminologies and not self.use_collection

        self.ignore_cell_value = self.config["annotation"]["ignore_cell_value"]
        self.relevant_fields = self.config["annotation"]["relevant_fields"]
        self.max_iterations = self.config["annotation"]["max_iterations"]
        self.max_threads = self.config["max_threads"]
        self.ai_use = self.config["ai_use"]

        self.fallback_translation_libretranslate = self.config["fallback_translation_libretranslate"]
        self.mids_terms = self.config["mids_terms"]

        
        # Start WebUI in separate thread if enabled
        if self.config["web_ui"]["enabled"]:
            logging.debug("Web UI is enabled, starting server...")
            WebUI.__init__(self, TH())  # Initialize WebUI before using it

        self.__handle_json_loads()

    def __handle_json_loads(self) -> None:
        """
        Process JSON data for annotation workflow.
        
        This method orchestrates the complete annotation workflow:
        1. Load and truncate JSON data based on max_iterations
        2. Create a deep copy for validation purposes
        3. Process each item across relevant fields and languages
        4. Perform noun phrase recognition using configured AI services
        5. Handle TIB terminology service requests based on configuration
        6. Apply annotations to the dataset
        7. Export results if configured
        8. Validate results if configured
        9. Persist statistics and cache if configured
        
        The method processes data in a structured manner, ensuring that
        all steps are completed before moving to the next phase of
        the annotation pipeline. It maintains data integrity throughout
        the process and provides comprehensive logging for debugging.
        
        The workflow supports multiple AI services (spaCy, GPT4All, Ollama)
        and can handle different terminology source configurations including
        explicit terminologies, collections, or complete terminology searches.
        """
        # logging.debug(f"ContentHandler, handle loads for the relevant fields: {
        #               self.relevant_fields}")

        # Load and truncate JSON data based on max_iterations
        self.load_json_loads = json.loads(
            self.annotate_me_json)[0:self.max_iterations] if self.max_iterations < len(self.annotate_me_json) else json.loads(self.annotate_me_json)

        # logging.debug(f"ContentHandler, load_json_loads: {self.load_json_loads}")

        # Store original data for validation
        self.original_json_loads = copy.deepcopy(self.load_json_loads)

        threads = []

        # Process each item across relevant fields
        for item in range(len(self.load_json_loads)):  # Rows
            # logging.debug(f"ContentHandler, row {item} (+2 using Excel)")
            for field in self.relevant_fields:
                if field in self.load_json_loads[item].keys():
                    threads.append((item, field))
                    # logging.debug(f"ContentHandler, row {item}, field {field}")
                    self.th_np_recognition_collect_cells(
                        self.load_json_loads[item][field])

        logging.debug(
            f"ContentHandler, th_cells:{self.th_cells}")

        # Perform noun phrase recognition
        self.th_np_recognition()

        logging.debug(
            f"ContentHandler, th_np_collection: {TH.th_np_collection}")

        # Handle BITS requests based on terminology configuration
        if self.explicit_terminologies != False:
            self.bh_request("explicit_terminologies", 50000)
        elif self.use_collection != False:
            self.bh_request("use_collection", 50000)
        elif self.use_all_ts:
            self.bh_request("use_all_ts", 50000)

        # Annotate the dataset
        self.ah_annotate_dataset()

        # Export annotation results if configured
        if self.config["annotation"]["perform_export"]:
            self.export_csv(self.load_json_loads)

        # Perform validation if configured
        if self.config["annotation"]["perform_validation"]:
            self.vh_bijective_validation()

        # Persist statistics if configured
        if self.config["persist_statistics"]:
            self.sh_persist_data()

        # Persist TS cache if configured
        if self.config["persist_cache"]:
            self.cache_persist()


if __name__ == "__main__":
    """
    Main execution block for content annotation processing.
    
    This block serves as the entry point for the BITS annotation system.
    It initializes the ContentHandler, measures execution time, and provides
    user feedback about the process completion. The system supports both
    command-line processing and web interface access.
    
    The execution flow:
    1. Create ContentHandler instance (initializes all helper classes)
    2. Log WebUI availability if enabled
    3. Measure and log execution time
    4. Wait for user input before exit
    
    The system automatically starts the web interface in a separate thread
    if enabled in the configuration, allowing for interactive annotation
    while batch processing continues in the background.
    """
    start_time = time.time()
    annotator = ContentHandler()

    # Debug output
    if annotator.config["web_ui"]["enabled"]:
        port = annotator.config["web_ui"]["port"]
        logging.info(f"Web UI should be available at http://localhost:{port}")

    execution_time = time.time() - start_time
    logging.info(f"DONE in {execution_time} seconds")

    input("Press Enter to exit...")
