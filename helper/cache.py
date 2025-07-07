import logging
import time
import json

from threading import Lock

from typing import Dict, Any, Optional



# TODO: Adjust for ESS queries


class Cache:
    """A thread-safe caching system for query results with persistence capabilities.
    
    This class implements a two-level dictionary cache structure that can store query results
    either by terminology and item or just by item. The cache includes automatic expiration
    of entries based on a time window and provides persistence to/from JSON file.

    Attributes:
        __CACHE_TIME_WINDOW (int): Duration in seconds for which cache entries remain valid (1 week)
        __CACHE_FILENAME (str): Path to the JSON file used for cache persistence
        __cache_queries (Dict[str, Dict[str, Any]]): Nested dictionary storing the cached data
        __cache_queries_lock (Lock): Thread lock for safe concurrent access
    """

    __CACHE_TIME_WINDOW = 604800  # Seconds in a week
    __CACHE_FILENAME = "./cache.json"

    # {terminology:{item:result}} or {item:result}
    __cache_queries: Dict[str, Dict[str, Any]] = {}
    __cache_queries_lock = Lock()

    def __init__(self):
        """Initialize the cache and load existing cache data from file if available."""
        self.__load_cache()

    def __check_create_terminology_in_cache(self, obj: dict, name: str) -> None:
        """Ensure a terminology key exists in the cache dictionary.

        Args:
            obj (dict): The dictionary to check/modify
            name (str): The terminology key to verify/create
        """
        if name not in obj.keys():
            obj[name] = {}

    # Getter
    def cache_get_query_item(self, terminology: str, item_normalized: str) -> Any:
        """Retrieve a cached query result for a given terminology and item.

        Args:
            terminology (str): The terminology category for the query
            item_normalized (str): The normalized item key to look up

        Returns:
            Any: The cached result if found, False otherwise

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

    # Setter
    def cache_set_query_item(self, terminology: str, item_normalized: str, single_result: dict) -> None:
        """Store a query result in the cache.

        Args:
            terminology (str): The terminology category for the query
            item_normalized (str): The normalized item key to store
            single_result (dict): The result data to cache

        Note:
            Automatically adds a timestamp to the cached result
        """
        # logging.debug(f"cache_set_query_item, terminology: {terminology}, item_normalized: {item_normalized}")

        single_result["query_time"] = time.time()

        if terminology:
            with Cache.__cache_queries_lock:
                self.__check_create_terminology_in_cache(
                    Cache.__cache_queries, terminology)
                Cache.__cache_queries[terminology][item_normalized] = single_result
        # logging.debug(f"Result cache: {self.__cache_queries}")

    # Filesystem
    def __load_cache(self) -> None:
        """Load cached data from the JSON file.

        Handles file reading errors and filters out expired cache entries based on
        __CACHE_TIME_WINDOW. Supports both terminology-based and flat cache structures.
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

        # Check for old data
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
        """Save the current cache state to the JSON file.

        Filters out expired entries before saving and includes the explicit_terminologies
        flag in the stored data.
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
