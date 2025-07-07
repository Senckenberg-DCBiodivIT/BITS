"""
Main module for content handling and annotation processing.

Setup Instructions:
------------------
1. Package Requirements:
   - requests: pip3 install requests
   - spacy: pip3 install spacy
   
2. Language Models:
   - English: python3 -m spacy download en_core_web_lg
   - German: python3 -m spacy download de_core_news_lg

Dependencies:
------------
- helper.file_handler: File I/O operations, configuration handling
- helper.cache: Caching mechanism
- helper.validator: Data validation
- helper.statistics_helper: Statistical analysis
- helper.annotation_helper: Annotation processing
- helper.bits_helper: BITS TS operations
- helper.text_helper: Text processing utilities
- helper.web_ui: Web UI functionality
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
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(message)s\n")


class ContentHandler(TH, BH, AH, SH, Validator, Cache, File, WebUI):
    """
    Main handler for content processing and annotation.

    Inherits from multiple helper classes to provide comprehensive functionality
    for text processing, BITS TS operations, annotations, statistics, validation,
    caching, and file operations.

    Attributes:
        explicit_terminologies (dict): Configuration for explicit terminology sources
        max_iterations (int): Maximum number of iterations for processing
        relevant_fields (dict): Fields to process by language
        max_threads (int): Maximum number of concurrent threads
    """

    def __init__(self) -> None:
        """
        Initialize the ContentHandler with configuration settings and prepare
        for content processing.
        """
        # Initialize base classes in correct order
        File.__init__(self)
        Cache.__init__(self)
        SH.__init__(self)

        # Load configuration settings
        self.explicit_terminologies = self.config["annotation"]["ts_sources"]["explicit_terminologies"]
        self.bits_ts_collection = self.config["annotation"]["ts_sources"]["collection"]
        self.ignore_cell_value = self.config["annotation"]["ignore_cell_value"]
        self.relevant_fields = self.config["annotation"]["relevant_fields"]
        self.max_iterations = self.config["annotation"]["max_iterations"]
        self.max_threads = self.config["max_threads"]
        self.ai_use = self.config["ai_use"]

        # Start WebUI in separate thread if enabled
        if self.config["web_ui"]["enabled"]:
            logging.debug("Web UI is enabled, starting server...")
            WebUI.__init__(self, TH())  # Initialize WebUI before using it

        self.__handle_json_loads()

    def __handle_json_loads(self):
        """
        Process JSON data for annotation.

        Steps:
        1. Load and truncate JSON data based on max_iterations
        2. Create a deep copy for validation
        3. Process each item across relevant fields and languages
        4. Perform noun phrase recognition
        5. Handle BITS requests based on terminology configuration
        6. Annotate the dataset
        7. Export results if configured
        8. Validate results if configured
        9. Persist statistics and cache if configured
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

        # Handle BITS requests
        if self.explicit_terminologies != False:
            self.bh_request("explicit_terminologies", 50000)
        if self.bits_ts_collection != False:
            self.bh_request("collection", 50000)
        if not self.explicit_terminologies and not self.bits_ts_collection:
            self.bh_request("complete", 50000)

        # Annotate
        self.ah_annotate_dataset()

        # Export annotation
        if self.config["annotation"]["perform_export"]:
            self.export_csv(self.load_json_loads)

        # Perform validation
        if self.config["annotation"]["perform_validation"]:
            self.vh_bijective_validation()

        # Persist statistics
        if self.config["persist_statistics"]:
            self.sh_persist_data()

        # Persist TS cache
        if self.config["persist_cache"]:
            self.cache_persist()


if __name__ == "__main__":
    """
    Main execution block for content annotation processing.
    Measures and logs execution time.
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
