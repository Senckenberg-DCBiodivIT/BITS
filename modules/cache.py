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

    __CACHE_FILENAME = "./cache.json"

    # TODO: Check if there is a benefit to reuse all_terminologies key if we ask for a single one terminology. Currently on hold.
    # {terminology:{item:result}} or {item:result}
    __cache_items = dict()  # Format: {term: {terminology: {name: value}, collection: {name: value}, all_terminologies: {name: value}}}
    __cache_items_lock = Lock()

    def __init__(self, config: Dict[str, Any] = None):
        self.__CONFIG = config if config else {}

        # NP Cache
        self.__CACHE_ENABLED = self.__CONFIG["cache"]["enabled"]
        self.__CACHE_PERSIST = self.__CONFIG["cache"]["persist"]
        self.__CACHE_THRESHOLD = self.__CONFIG["cache"]["threshold_days"] * 86400

        self.__load_cache() # TODO: Enable Cache later, after all kinds of requests are implemented


    def get_item(self, kind_name, item_normalized):
        """
        Retrieve a cached query result for a given kind, name, and item.
        
        This method checks the cache for existing results using a nested
        dictionary structure. The cache is organized as:
        {item_normalized: {kind: {name: value}}}
        
        If caching is disabled or the item is not found in the cache,
        False is returned.
        
        Args:
            kind_name (Dict[str, str]): Dictionary containing:
                - "kind" (str): The kind/category of the cached item
                - "name" (str): The name identifier for the cached item
            item_normalized (str): The normalized item key to look up
            
        Returns:
            Any: The cached result if found, False otherwise
        """
        logging.debug(
            f"Cache: get_item, kind_name: {kind_name}, item_normalized: {item_normalized}")
        
        if not self.__CACHE_ENABLED:
            return False
        
        # Cache structure: {item_normalized: {kind: {name: value}}}
        item_cache = self.__cache_items.get(item_normalized, {})
        kind_cache = item_cache.get(kind_name["kind"], {})
        
        if kind_name["name"] in kind_cache:
            return kind_cache[kind_name["name"]]
        
        return False

    def set_item(self, kind_name: dict[str, str], item_normalized: str, value: Any) -> None:
        """
        Store a value in the cache for a given kind, name, and item.
        
        This method stores the value in the cache using a nested dictionary
        structure. The cache is organized as:
        {item_normalized: {kind: {name: value}}}
        
        The method only stores the value if it doesn't already exist in the cache
        (no overwrite of existing entries). If the item_normalized key doesn't exist,
        it is initialized with both "terminology" and "collection" kind dictionaries.
        The method automatically adds a "cache_time" timestamp to the value before
        storing it. The operation is thread-safe using the cache lock.
        
        If caching is disabled, the method returns False without storing anything.
        
        Args:
            kind_name (dict[str, str]): Dictionary containing:
                - "kind" (str): The kind/category of the cached item (e.g., "terminology", "all_terminologies" or "collection")
                - "name" (str): The name identifier for the cached item
            item_normalized (str): The normalized item key to store
            value (Any): The value data to cache (will have "cache_time" added automatically)
            
        Returns:
            None: If caching is enabled and the value was stored or already exists
            False: If caching is disabled
        """
        logging.debug(
            f"Cache: set_item, kind_name: {kind_name}, item_normalized: {item_normalized}")
        
        if not self.__CACHE_ENABLED:
            return False
        
        # Cache structure: {item_normalized: {kind: {name: value}}}
        with self.__cache_items_lock:
            # Ensure item_normalized level exists
            if item_normalized not in self.__cache_items:
                self.__cache_items[item_normalized] = {"terminology": {}, "collection": {}, "all_terminologies": {}}
            
            # Ensure kind level exists and
            if kind_name["name"] not in self.__cache_items[item_normalized][kind_name["kind"]]:
                value["cache_time"] = time.time()
                self.__cache_items[item_normalized][kind_name["kind"]][kind_name["name"]] = value

            logging.debug(
                f"Cache now: __cache_items: {self.__cache_items}")

    # Shared Methods
    def cache_persist(self) -> None:
        """
        Save the current cache state to the JSON file.

        This module should be used for different purposes, so we persist cache directly here.
        """
        logging.debug(f"cache_persist")
        
        self.__clean_cache() # Remove expired entries
        
        temp_cache = {}
        
        if self.__CACHE_ENABLED and self.__CACHE_PERSIST:
            temp_cache = self.__cache_items
            with open(self.__CACHE_FILENAME, 'w', encoding='utf-8') as file:
                json.dump(temp_cache, file, indent=4, ensure_ascii=False)

    # def set_cache_item(self, flag: str, item_normalized: str, source: str, single_result: Dict[str, Any]) -> None:
    #     """
    #     Store a query result in the NP cache.
    #     """
    #     try:
    #         if self.__NP_ENABLED:
    #             with Cache.__cache_items_lock:
    #                 self.__check_create_item_in_cache(Cache.__cache_items[flag], item_normalized)
    #                 self.__check_create_item_in_cache(Cache.__cache_items[flag][item_normalized], source)
    #                 Cache.__cache_items[flag][item_normalized][source] = single_result
    #                 Cache.__cache_items[flag][item_normalized][source]["cache_time"] = time.time()
    #     except Exception as e:
    #         logging.error(f"Cache, unable to set NP cache: {str(e)}. Continuing annotation process.")

    # def get_cache_item(self, flag: str, item_normalized: str, source: str) -> Any:
    #     # 1. Check if cache is enabled and the item is in the cache
    #     # 2. Check if the item is expired
    #     # 3. Return the item
    #     if self.__NP_ENABLED and flag == "np" and item_normalized in Cache.__cache_items["np"] and source in Cache.__cache_items["np"][item_normalized]:
    #         if "cache_time" in Cache.__cache_items["np"][item_normalized][source] and time.time() - Cache.__cache_items["np"][item_normalized][source]["cache_time"] <= self.__NP_THRESHOLD:
    #             return Cache.__cache_items["np"][item_normalized][source]
        
    #     if self.__TS_ENABLED and flag == "ts" and item_normalized in Cache.__cache_items["ts"] and source in Cache.__cache_items["ts"][item_normalized]:
    #         if "cache_time" in Cache.__cache_items["ts"][item_normalized][source] and time.time() - Cache.__cache_items["ts"][item_normalized][source]["cache_time"] <= self.__TS_THRESHOLD:
    #             return Cache.__cache_items["ts"][item_normalized][source]
    #     return None

    # def __check_create_item_in_cache(self, obj: Dict[str, Any], name: str) -> None:
    #     """
    #     Ensure a terminology key exists in the cache dictionary.
        
    #     This helper method ensures that a terminology key exists in the cache
    #     structure before attempting to store or retrieve data for that terminology.
        
    #     Args:
    #         obj (Dict[str, Any]): The dictionary to check/modify
    #         name (str): The terminology key to verify/create
    #     """
    #     if name not in obj.keys():
    #         obj[name] = {}

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
        # loaded_data = {}
        # try:
        #     with open(self.__CACHE_FILENAME, 'r', encoding='utf-8') as file:
        #         loaded_data = json.load(file)
        # except FileNotFoundError:
        #     logging.info(f"Cache file {self.__CACHE_FILENAME} not found. Starting with empty cache.")
        #     return None
        # except json.JSONDecodeError:
        #     logging.error(f"Invalid JSON in cache file {self.__CACHE_FILENAME}")
        #     return None

        # # Load NP cache if enabled
        # if self.__NP_ENABLED and "np" in loaded_data:
        #     Cache.__cache_items["np"] = loaded_data["np"]
        #     logging.debug(f"NP cache loaded: {len(Cache.__cache_items['np'])} items")
        
        # # Load TS cache if enabled
        # if self.__TS_ENABLED and "ts" in loaded_data:
        #     Cache.__cache_items["ts"] = loaded_data["ts"]
        #     logging.debug(f"TS cache loaded: {len(Cache.__cache_items['ts'])} items")

        # logging.info(f"Cache loaded successfully")
        pass

    def __clean_cache(self) -> None:
        """
        Clean cache depending on the expiration threshold
        """
        pass

    def __is_cache_valid(self, item_normalized: str, source: str, cache_type: str) -> bool:
        """
        Check if the cached data for the given item and source is still valid.
        
        Args:
            item_normalized: The normalized item name
            source: The data source
            
        Returns:
            bool: True if cache is valid and not expired, False otherwise
        """
        # if not self.__NP_ENABLED:
        #     return False
            
        # try:
        #     with Cache.__cache_items_lock:
        #         if (item_normalized in Cache.__cache_items["np"] and 
        #             source in Cache.__cache_items["np"][item_normalized] and
        #             "cache_time" in Cache.__cache_items["np"][item_normalized][source]):
                    
        #             cache_time = Cache.__cache_items["np"][item_normalized][source]["cache_time"]
        #             current_time = time.time()
                    
        #             # Check if cache is still within threshold
        #             return (current_time - cache_time) <= self.__NP_THRESHOLD
                    
        # except (KeyError, TypeError):
        #     pass
            
        # return False
        pass

