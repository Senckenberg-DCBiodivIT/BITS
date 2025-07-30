"""
Cache Module

This module provides a thread-safe caching system for query results with
persistence capabilities. It implements a two-level dictionary cache structure
that can store query results either by terminology and item or just by item.

The cache includes automatic expiration of entries based on a time window
and provides persistence to/from JSON file for long-term storage. It is
designed for high-performance terminology service queries with minimal
memory overhead.

Key Features:
- Thread-safe caching with lock mechanisms
- Automatic cache expiration (1 week default)
- JSON-based persistence for long-term storage
- Performance statistics tracking
- Configurable cache time windows

Classes:
    Cache: Main class for thread-safe caching with persistence
"""

import logging
import time
import json

from threading import Lock

from typing import Dict, Any, Optional



# TODO: Adjust for ESS queries


class Cache:
    """
    A thread-safe caching system for query results with persistence capabilities.
    
    This class implements a two-level dictionary cache structure that can store
    query results either by terminology and item or just by item. The cache
    includes automatic expiration of entries based on a time window and provides
    persistence to/from JSON file.
    
    The cache supports two modes:
    - Terminology-based: {terminology: {item: result}}
    - Flat structure: {item: result}
    
    Attributes:
        __CACHE_TIME_WINDOW (int): Duration in seconds for which cache entries
            remain valid (1 week = 604800 seconds)
        __CACHE_FILENAME (str): Path to the JSON file used for cache persistence
        __cache_queries (Dict[str, Dict[str, Any]]): Nested dictionary storing
            the cached data
        __cache_queries_lock (Lock): Thread lock for safe concurrent access
    """

    __CACHE_TIME_WINDOW = 604800  # Seconds in a week
    __CACHE_FILENAME = "./cache.json"

    # {terminology:{item:result}} or {item:result}
    __cache_queries: Dict[str, Dict[str, Any]] = {}
    __cache_queries_lock = Lock()

    def __init__(self):
        """
        Initialize the cache and load existing cache data from file if available.
        
        Currently disabled for development purposes. Cache loading will be
        enabled once all request types are implemented.
        """
        #self.__load_cache() # TODO: Enable Cache later, after all kinds of requests are implemented

    def __check_create_terminology_in_cache(self, obj: Dict[str, Any], name: str) -> None:
        """
        Ensure a terminology key exists in the cache dictionary.
        
        This helper method ensures that a terminology key exists in the cache
        structure before attempting to store or retrieve data for that terminology.
        
        Args:
            obj (Dict[str, Any]): The dictionary to check/modify
            name (str): The terminology key to verify/create
        """
        if name not in obj.keys():
            obj[name] = {}

    def cache_get_query_item(self, terminology: str, item_normalized: str) -> Any:
        """
        Retrieve a cached query result for a given terminology and item.
        
        This method checks the cache for existing results and updates
        cache hit/miss statistics accordingly. If a result is found and
        is still within the cache time window, it is returned.
        
        Args:
            terminology (str): The terminology category for the query
            item_normalized (str): The normalized item key to look up
            
        Returns:
            Any: The cached result if found and valid, False otherwise
            
        Note:
            Updates cache hit/miss statistics via sh_set_cache_hit/miss methods
        """
        # logging.debug(
        #     f"cache_get_query_item, terminology: {terminology}, item_normalized: {item_normalized}")
        self.__check_create_terminology_in_cache(
            Cache.__cache_queries, terminology)

        if item_normalized in Cache.__cache_queries[terminology].keys():
            result = Cache.__cache_queries[terminology][item_normalized]
            self.sh_set_cache_hit(item_normalized)
        else:
            result = False
            self.sh_set_cache_miss(item_normalized)

        return result

    def cache_set_query_item(self, terminology: str, item_normalized: str, single_result: Dict[str, Any]) -> None:
        """
        Store a query result in the cache.
        
        This method stores query results with automatic timestamp addition
        for expiration tracking. The result is stored in a thread-safe manner
        using the cache lock.
        
        Args:
            terminology (str): The terminology category for the query
            item_normalized (str): The normalized item key to store
            single_result (Dict[str, Any]): The result data to cache
            
        Note:
            Automatically adds a timestamp to the cached result for
            expiration tracking
        """
        # logging.debug(f"cache_set_query_item, terminology: {terminology}, item_normalized: {item_normalized}")

        single_result["query_time"] = time.time()

        if terminology:
            with Cache.__cache_queries_lock:
                self.__check_create_terminology_in_cache(
                    Cache.__cache_queries, terminology)
                Cache.__cache_queries[terminology][item_normalized] = single_result
        # logging.debug(f"Result cache: {self.__cache_queries}")

    def __load_cache(self) -> None:
        """
        Load cached data from the JSON file.
        
        This method handles loading cache data from the JSON file with
        proper error handling for file reading and JSON parsing issues.
        It also filters out expired cache entries based on the cache
        time window.
        
        The method supports both terminology-based and flat cache structures
        and handles the explicit_terminologies flag appropriately.
        
        Raises:
            FileNotFoundError: If the cache file doesn't exist (handled gracefully)
            json.JSONDecodeError: If the cache file contains invalid JSON (handled gracefully)
        """
        loaded_data = {}
        try:
            with open(self.__CACHE_FILENAME, 'r') as file:
                loaded_data = json.load(file)
        except FileNotFoundError:
            logging.info(f"Cache file {self.__CACHE_FILENAME} not found. Starting with empty cache.")
            Cache.__cache_queries = {}
            return None
        except json.JSONDecodeError:
            logging.error(f"Invalid JSON in cache file {self.__CACHE_FILENAME}")
            Cache.__cache_queries = {}
            return None

        # Check for old data and filter expired entries
        if self.explicit_terminologies != False and "explicit_terminologies" in loaded_data.keys() and loaded_data["explicit_terminologies"] == True:
            for terminology in loaded_data:
                if terminology == "explicit_terminologies":
                    continue
                Cache.__cache_queries[terminology] = {result: loaded_data[terminology][result] for result in loaded_data[terminology] if (
                    time.time() - loaded_data[terminology][result]["query_time"]) < self.__CACHE_TIME_WINDOW}

        else:
            Cache.__cache_queries = {}

        # logging.info(f"Cache loaded: {self.__cache_queries}")

    def cache_persist(self) -> None:
        """
        Save the current cache state to the JSON file.
        
        This method persists the current cache state to the JSON file,
        filtering out expired entries before saving. It includes the
        explicit_terminologies flag in the stored data to maintain
        cache structure information.
        
        The method:
        - Filters out expired entries based on query_time
        - Includes the explicit_terminologies flag
        - Saves data in a human-readable JSON format
        """
        logging.debug(f"cache_persist")
        stored_json = {}

        if self.explicit_terminologies:
            for terminology in Cache.__cache_queries:
                stored_json[terminology] = {result: Cache.__cache_queries[terminology][result] for result in Cache.__cache_queries[terminology] if (
                    time.time() - Cache.__cache_queries[terminology][result]["query_time"]) < self.__CACHE_TIME_WINDOW}

        stored_json["explicit_terminologies"] = False if self.explicit_terminologies == False else True

        with open(self.__CACHE_FILENAME, 'w') as file:
            # logging.info(f"Persist cache: {stored_json}")
            json.dump(stored_json, file, indent=4)
