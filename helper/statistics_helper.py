"""
StatisticsHelper Module

This module provides functionality for collecting and managing statistics during
the annotation process. It tracks noun phrase identification, cache performance,
AI service errors, and validation results.

The module maintains statistics in a structured format and provides methods
for persisting data to JSON files for later analysis. It supports comprehensive
performance monitoring and quality assessment of the annotation workflow.

Key Features:
- Noun phrase identification statistics
- Cache performance tracking (hits/misses)
- AI service error monitoring
- Validation result tracking
- JSON-based statistics persistence
- Performance metrics collection
- Quality assessment reporting

Classes:
    StatisticsHelper: Main class for statistics collection and management
"""

import json
import time
import logging
from typing import Dict, Any, List


class StatisticsHelper:
    """
    A helper class for collecting and managing statistics during annotation processing.
    
    This class tracks various metrics including:
    - Noun phrase identification and annotation status
    - Cache hit/miss performance
    - AI service errors
    - Validation results
    
    Attributes:
        statistics (Dict[str, Any]): Main statistics dictionary containing:
            - NP: Noun phrase statistics
            - cache: Cache performance metrics
            - gpt: AI service error tracking
            - validation: Validation results
    """

    def __init__(self):
        """
        Initialize the StatisticsHelper with an empty statistics structure.
        
        Creates a nested dictionary structure to organize different types
        of statistics collected during the annotation process.
        """
        self.statistics = {
            "NP": {
                "identified": {},
                "missed_declined_annotations": []
            }, 
            "cache": {
                "hit": {}, 
                "miss": {}
            }, 
            "gpt": {
                "error": []
            },
            "validation": {}
        }

    def __check_create_in_dict(self, obj: Dict[str, Any], name: str) -> None:
        """
        Ensure a key exists in a dictionary, creating it if necessary.
        
        Args:
            obj (Dict[str, Any]): The dictionary to check/modify
            name (str): The key to verify/create
        """
        if name not in obj.keys():
            obj[name] = {}

    # Cache Statistics Methods
    def sh_set_cache_hit(self, item: str) -> None:
        """
        Record a cache hit for a specific item.
        
        Args:
            item (str): The item that was found in cache
        """
        self.__check_create_in_dict(self.statistics["cache"]["hit"], item)
        self.statistics["cache"]["hit"][item]["last_hit"] = time.time()

    def sh_set_cache_miss(self, item: str) -> None:
        """
        Record a cache miss for a specific item.
        
        Args:
            item (str): The item that was not found in cache
        """
        self.__check_create_in_dict(self.statistics["cache"]["miss"], item)
        self.statistics["cache"]["miss"][item]["last_miss"] = time.time()

    # Noun Phrase Statistics Methods
    def sh_set_np(self, np: str, np_normalized: str) -> None:
        """
        Record an identified noun phrase with its normalized form.
        
        Args:
            np (str): The original noun phrase
            np_normalized (str): The normalized version of the noun phrase
        """
        self.__check_create_in_dict(self.statistics["NP"]["identified"], np)
        self.statistics["NP"]["identified"][np] = {
            "normalized": np_normalized, 
            "annotation": "",
            "translation": ""
        }

    def sh_set_np_missing_annotation(self, np: str) -> None:
        """
        Record a noun phrase that could not be annotated.
        
        Args:
            np (str): The noun phrase that was missed or declined
        """
        self.statistics["NP"]["missed_declined_annotations"].append(np)

    def sh_set_np_annotation(self, np: str, annotation: Dict[str, Any]) -> None:
        """
        Record the annotation result for a noun phrase.
        
        Note: This method should be called after sh_set_np() to ensure
        the noun phrase is properly initialized in the statistics.
        
        Args:
            np (str): The noun phrase being annotated
            annotation (Dict[str, Any]): The annotation result dictionary
        """
        self.statistics["NP"]["identified"][np]["annotation"] = annotation

    def sh_set_np_translation(self, np: str, translation: str) -> None:
        """
        Record the translation of a noun phrase.
        
        Args:
            np (str): The noun phrase being translated
            translation (str): The translation of the noun phrase
        """
        self.statistics["NP"]["identified"][np]["translation"] = translation

    # Validation Statistics Methods
    def sh_set_validation_error(self, item: str, message: str) -> None:
        """
        Record a validation error for a specific item.
        
        Args:
            item (str): The item that failed validation
            message (str): Description of the validation error
        """
        self.statistics["validation"][item] = message

    # AI Services Error Tracking
    def sh_set_ai_error(self, cell: str, np_detection: str) -> None:
        """
        Record an error from AI services during noun phrase detection.
        
        Args:
            cell (str): The cell content that caused the error
            np_detection (str): Description of the noun phrase detection error
        """
        self.statistics["ai"]["error"].append({cell: np_detection})

    # Data Persistence
    def sh_persist_data(self) -> None:
        """
        Save the current statistics to a JSON file.
        
        Converts the statistics dictionary to a formatted JSON string
        and uses the FileHandler's store_text_file method for reliable
        file writing with proper error handling.
        """
        try:
            # Prepare the content as a formatted JSON string
            content = json.dumps(self.statistics, indent=4, ensure_ascii=False)
            
            # Use FileHandler's store_text_file method for reliable file writing
            self.store_text_file(content, "./statistics.json")
            
        except Exception as e:
            error = f"StatisticsHelper, unable to persist statistics data: {str(e)}"
            logging.error(error)
            raise Exception(error)
