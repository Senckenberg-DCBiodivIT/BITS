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

    def __load_cache(self) -> None:
        """
        Load cached data from the JSON file.
        
        This method handles loading cache data from the JSON file with
        proper error handling for file reading and JSON parsing issues.
        It also filters out expired cache entries based on the cache
        time window.
        
        The cache structure is: {item_normalized: {kind: {name: value}}}
        where kind can be "terminology", "collection", or "all_terminologies".
        
        Raises:
            FileNotFoundError: If the cache file doesn't exist (handled gracefully)
            json.JSONDecodeError: If the cache file contains invalid JSON (handled gracefully)
        """
        if not self.__CACHE_ENABLED or not self.__CACHE_PERSIST:
            logging.debug("Cache loading skipped (disabled or persist disabled)")
            return
        
        try:
            with open(self.__CACHE_FILENAME, 'r', encoding='utf-8') as file:
                loaded_data = json.load(file)
            
            if not loaded_data:
                logging.info("Cache file is empty. Starting with empty cache.")
                return
            
            # Load the cache structure directly
            with self.__cache_items_lock:
                self.__cache_items = loaded_data
            
            # Count loaded items for logging
            total_items = len(self.__cache_items)
            logging.info(f"Cache loaded successfully: {total_items} normalized items")
            
            # Clean expired entries after loading
            self.__clean_cache()
            
        except FileNotFoundError:
            logging.info(f"Cache file {self.__CACHE_FILENAME} not found. Starting with empty cache.")
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON in cache file {self.__CACHE_FILENAME}: {e}. Starting with empty cache.")
        except Exception as e:
            logging.error(f"Error loading cache from {self.__CACHE_FILENAME}: {e}. Starting with empty cache.")

    def __clean_cache(self) -> None:
        """
        Clean cache depending on the expiration threshold.
        
        This method removes expired cache entries based on the __CACHE_THRESHOLD
        (configured in days, converted to seconds). It iterates through all
        cache entries and removes those whose cache_time exceeds the threshold.
        
        The cache structure is: {item_normalized: {kind: {name: value}}}
        where each value contains a "cache_time" timestamp.
        """
        if not self.__CACHE_ENABLED:
            return
        
        current_time = time.time()
        items_removed = 0
        
        with self.__cache_items_lock:
            # Create a list of items to remove to avoid modifying dict during iteration
            items_to_remove = []
            
            for item_normalized, kinds_dict in self.__cache_items.items():
                # Check each kind (terminology, collection, all_terminologies)
                for kind, names_dict in kinds_dict.items():
                    names_to_remove = []
                    
                    for name, value in names_dict.items():
                        # Check if cache_time exists and if entry is expired
                        if "cache_time" in value:
                            cache_time = value["cache_time"]
                            if (current_time - cache_time) > self.__CACHE_THRESHOLD:
                                names_to_remove.append(name)
                                items_removed += 1
                    
                    # Remove expired entries from this kind
                    for name in names_to_remove:
                        del names_dict[name]
                
                # If all kinds are empty for this item, mark item for removal
                if all(len(names_dict) == 0 for names_dict in kinds_dict.values()):
                    items_to_remove.append(item_normalized)
            
            # Remove items that have no cached data left
            for item_normalized in items_to_remove:
                del self.__cache_items[item_normalized]
        
        if items_removed > 0:
            logging.info(f"Cache cleaned: {items_removed} expired entries removed")
