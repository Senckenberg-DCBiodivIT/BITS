"""
BitsHelper Module - BITS TIB Terminology Service Integration

This module provides functionality for handling terminology requests and annotations
using the TIB API. It manages semantic similarity matching against various terminologies
and supports different request types including explicit terminologies, collections,
and complete terminology searches.

The module integrates with the TIB terminology service API to perform semantic
matching and provides caching capabilities for improved performance. It supports
multiple terminology sources and provides flexible search configurations.

Key Features:
- TIB API integration for terminology searches
- Semantic similarity matching using SpaCy
- Multiple request types (explicit, collection, all terminologies)
- Caching support for improved performance
- Configurable result limits and filtering
- Error handling and logging

Classes:
    BitsHelper: Main class for terminology requests and semantic matching
"""

import requests
import logging
import time
from typing import Dict, Any, List, Set


class BitsHelper:
    """
    A helper class for managing terminology requests and semantic matching.
    
    This class provides comprehensive functionality to search and match terms 
    against various terminologies using semantic similarity matching. It supports 
    multiple request types and integrates with the TIB terminology service API.
    
    The class handles different types of terminology searches:
    - Explicit terminology searches: Search in specific terminologies
    - Collection-based searches: Search within specified collections
    - Complete terminology searches: Search across all available terminologies
    - Semantic similarity matching using SpaCy for accurate term matching
    - Caching of query results for improved performance
    
    The class provides flexible configuration options and supports various
    terminology sources, making it suitable for different use cases and
    research domains.
    
    Attributes:
        bh_request_results (Dict[str, Dict[str, Dict]]): A nested dictionary storing
            request results in the format:
            {term: {terminology_name: {id, iri, original_label, similarity}}}
        __TIB_URL (str): Base URL for the TIB terminology service API
        __TIB_URL_SEARCH (str): Search endpoint URL for the TIB API
        __ONTOLOGY_SIZE (int): Maximum number of ontologies to retrieve
    """

    bh_request_results: Dict[str, Dict[str, Dict]] = dict()
    __TIB_URL = "https://api.terminology.tib.eu/api/v2/"
    __TIB_URL_SEARCH = "https://api.terminology.tib.eu/api/search?" # TODO: Check https://api.terminology.tib.eu/api/v2/entities?search= instead.

    __ONTOLOGY_SIZE = 1000

    def bh_request(self, kind: str, number_results: int = 30000) -> None:
        """
        Initiates terminology requests based on the specified kind.
        
        This method orchestrates different types of terminology requests:
        - explicit_terminologies: Search in specific terminologies
        - use_collection: Search in the specified collection
        - use_all_ts: Perform complete search across all terminologies
        
        Args:
            kind (str): Type of request to perform. Valid values are:
                - "explicit_terminologies": Search in specific terminologies
                - "use_collection": Search in the specified collection
                - "use_all_ts": Perform complete search
            number_results (int, optional): Maximum number of results to return.
                Defaults to 30000.
                
        Raises:
            ValueError: If an invalid request kind is specified
        """
         
        logging.debug(f"BitsHelper, start {kind} requesting")
        bh_start_time = time.time()

        if kind == "explicit_terminologies":
            self.bh_request_explicit_terminologies(self.__class__.th_np_collection)
            
        elif kind == "use_collection":
            self.__bh_request_collection(self.__class__.th_np_collection, self.use_collection) # Here we use a parameter for the collection, because we also have an interactive collection selection in the WebUI later.

        elif kind == "use_all_ts":
            self.__bh_request_all_terminologies(self.__class__.th_np_collection)

        else:
            raise ValueError(f"Invalid request kind: {kind}")

        print(f"BitsHelper, requests are done in {
              time.time() - bh_start_time}")

    def __perform_query(self, url: str) -> Dict[str, Any]:
        """
        Performs HTTP GET request to the TIB API and processes the response.
        
        This method handles basic API queries to the TIB terminology service.
        It includes proper error handling and returns structured response data.
        
        Args:
            url (str): The complete URL for the API request
            
        Returns:
            Dict[str, Any]: Response data from the API, or empty dict if request fails
            
        Note:
            Uses a simple user-agent header for API requests
        """
        headers = {'user-agent': 'my-app/0.0.1'}
        params = {'key': 'value'}

        try:
            response_json = requests.get(
                url, headers=headers, params=params).json()
            if response_json:
                return response_json
            else:
                return dict()
        except Exception as e:
            logging.error(f"Error performing query to {url}: {e}")
            return dict()

    def __perform_query_search(self, url: str) -> Dict[str, Any]:
        """
        Performs HTTP GET request to the TIB API search endpoint and processes the response.
        
        This method handles search-specific API queries and includes detailed
        response processing for search results. It handles the specific response
        structure of the search endpoint.
        
        Args:
            url (str): The complete URL for the API search request

        Returns:
            Dict[str, Any]: Response data containing matching results, or empty dict
                if no matches found or request fails
        """
        headers = {'user-agent': 'my-app/0.0.1'}
        params = {'key': 'value'}

        try:
            response_json = requests.get(
                url, headers=headers, params=params).json()
        except Exception as e:
            logging.error(f"Error performing search query to {url}: {e}")
            return dict()

        # dict_keys(['responseHeader', 'response', 'facet_counts', 'highlighting'])
        # logging.debug(f"__perform_query_search, response_json is\n{response_json}")

        # print("\nresponseHeader")
        # print(response_json["responseHeader"])
        # print("\nresponse")
        # print(response_json["response"])
        # print("\nfacet_counts")
        # print(response_json["facet_counts"])
        # print("\nhighlighting")
        # print(response_json["highlighting"])

        try:
            if response_json["response"]["numFound"] == 0:
                return dict()
            else:
                return response_json["response"]
        except Exception as e:
            print("\n"*4)
            logging.error(f"__perform_query_search, error: {e}")
            logging.error(f"__perform_query_search, response_json: {response_json}")
            print("\n"*4)
            return dict()

    def __create_item_results_from_query(self, query_result: Dict[str, Any], item_normalized: str, 
                                       result_temp: Dict[str, Any], terminology_name: str = "", item_normalized_translated: str = "") -> Dict[str, Any]:
        """
        Processes query results and creates terminology matches based on similarity threshold.
        
        This method processes raw API query results and applies semantic similarity
        matching using SpaCy. It filters results based on a similarity threshold
        and creates standardized terminology result objects.
        
        Args:
            query_result (Dict[str, Any]): Raw query results from the TIB API
            item_normalized (str): Normalized form of the search term
            result_temp (Dict[str, Any]): Temporary storage for results
            terminology_name (str): Name of the terminology being searched

        Returns:
            Dict[str, Any]: Updated result_temp dictionary with new matches that
                meet the similarity threshold
                
        Note:
            Uses English SpaCy model for similarity checking, which works well
            for both English and German terms
        """
        # logging.info(
        #     f"__create_item_results_from_query for {item_normalized} and result: {query_result}")

        language = "en" # here we use english for the similarity check. It seems not to be a problem for the similarity check for german terms as well. 

        #item_normalized_similarity = self.SPACY_HANDLER[language](
        #    item_normalized)

        if "docs" in query_result.keys():
            for single_result in query_result["docs"]:
                # print(f"Single result: {single_result}")

                # Check if the result has a label field
                if "label" not in single_result:
                    continue  # Skip results without a label
                    
                label = self.SPACY_HANDLER[language](
                    single_result["label"].lower())
                # print(f"single_result: {single_result}")

                # If we have a terminology name, we can check if the result is already in the result_temp
                # If there is no specific terminology name, we have to use each result for each terminology.
                if (terminology_name != "" and terminology_name in result_temp.keys()) or terminology_name == "":
                    terminology_name_single_result = terminology_name if terminology_name != "" else single_result["ontology_name"]
                    #similarity_factor = item_normalized_similarity.similarity(
                    #    label)
                    similarity_factor = self.th_similarity_check(item_normalized, label)
                    if item_normalized_translated != "":
                        similarity_factor_translated = self.th_similarity_check(item_normalized_translated, label)
                        similarity_factor = max(similarity_factor, similarity_factor_translated)
                    # print(f"Similarity: {similarity_factor}")
                    
                    if similarity_factor >= self.SIMILARITY_ACK:
                        # print("similarity_factor ok")
                        # Check if we need to update an existing result or create a new one
                        existing_result = result_temp.get(terminology_name_single_result)
                        if existing_result is None or existing_result["similarity"] < similarity_factor:
                            result_temp[terminology_name_single_result] = self.ah_create_terminology_result(
                                single_result, similarity_factor)

        else:
            pass  # Here it's about a helper like "query_time" or other results, we can't use for an annotation. Just ignore them

        return result_temp

    def bh_request_explicit_terminologies(self, np_collection: Set[str]) -> Dict[str, Dict[str, Dict]]:
        """
        Processes requests for explicitly specified terminologies.
        
        This method handles terminology searches for a specific set of noun phrases
        against explicitly configured terminologies. For each term in the collection:
        1. Normalizes the term
        2. Checks cache for existing results
        3. Performs API query if needed
        4. Processes results and stores matches that meet similarity threshold
        
        Args:
            np_collection (Set[str]): Collection of noun phrases to search for
            
        Returns:
            Dict[str, Dict[str, Dict]]: Dictionary containing search results for each
                noun phrase, organized by terminology
        """
        for item in np_collection:
            item_normalized = item.strip().lower()
            self.sh_set_np(item, item_normalized)

            # result_temp = {terminology_name: {id, iri, original_label, similarity}}
            result_temp = dict()

            # Check if fallback translation is enabled and get translated term
            item_normalized_translated = ""
            if self.fallback_translation_libretranslate["enabled"]:
                item_normalized_translated = self.th_language_translation(item_normalized, self.fallback_translation_libretranslate["source_language"], self.fallback_translation_libretranslate["target_language"])
                print(f"\nitem_normalized_translated: {item_normalized_translated}\n")
            
            self.sh_set_np_translation(item, item_normalized_translated)

            for terminology_name in self.explicit_terminologies:
                # Check query cache. Maybe there is a result from another one instance or a stored result
                
                # cache_result = self.cache_get_query_item(
                #     terminology_name, item_normalized)
                cache_result = False # TODO: Enable Cache later, after all kinds of requests are implemented

                if cache_result:
                    query_result = cache_result
                    # logging.debug(
                    #     f"bh_request_explicit_terminologies, use, handler cached result")

                else:
                    # Perform query
                    
                    # logging.debug(
                    #     f"bh_request_explicit_terminologies, not, handler in cache")

                    url = self.__TIB_URL_SEARCH + f'ontology={terminology_name}&q={item_normalized}'
                    # logging.debug(f"bh_request_explicit_terminologies, url, handler: {url}")   
                    query_result = self.__perform_query_search(url)

                    # self.cache_set_query_item(  TODO: Enable Cache later, after all kinds of requests are implemented
                    #     terminology_name, item_normalized, query_result)

                # Here we have cached results and query responses for each terminology.
                result_temp = self.__create_item_results_from_query(
                    query_result, item_normalized, result_temp, terminology_name, item_normalized_translated)
           
            BitsHelper.bh_request_results[item] = result_temp

        return BitsHelper.bh_request_results # For the WebUI or in general for the external requests

    def __bh_request_all_terminologies(self, np_collection: Set[str]) -> Dict[str, Dict[str, Dict]]:
        """
        Processes requests for all terminologies.
        
        This method performs comprehensive terminology searches across all available
        terminologies in the TIB API. For each term in the collection:
        1. Normalizes the term
        2. Checks cache for existing results using the key __ALL_TS_KEY
        3. Performs API query if needed
        4. Processes results and stores matches that meet similarity threshold
        5. Store the results in the cache using the key __ALL_TS_KEY
        
        Args:
            np_collection (Set[str]): Collection of noun phrases to search for
            
        Returns:
            Dict[str, Dict[str, Dict]]: Dictionary containing search results for each
                noun phrase across all terminologies
        """
        def perform_query(item_normalized: str) -> Dict[str, Any]:
            url = self.__TIB_URL_SEARCH + f'q={item_normalized}'
            return self.__perform_query_search(url)
        
        for item in np_collection:
            item_normalized = item.strip().lower()
            self.sh_set_np(item, item_normalized)
            
            # result_temp = {terminology_name: {id, iri, original_label, similarity}}
            result_temp = dict()

            # Check cache for existing results using the key __ALL_TS_KEY
            # cache_result = self.cache_get_query_item(
            #     self.ALL_TS_KEY, item_normalized, self.CACHE_KEY_ALL_TS)
            cache_result = False # TODO: Enable Cache later, after all kinds of requests are implemented
            if cache_result:
                query_result = cache_result
                # logging.debug(
                #     f"bh_request_all_terminologies, use, handler cached result")

            else:
                # Perform query
                # url = self.__TIB_URL_SEARCH + f'q={item_normalized}'
                # logging.debug(f"bh_request_all_terminologies, url, handler: {url}")   
                # query_result = self.__perform_query_search(url)
                query_result = perform_query(item_normalized)
                print(f"\nquery_result: {query_result}")
                print(f"query_result length: {len(query_result)}\n")

                # self.cache_set_query_item(  TODO: Enable Cache later, after all kinds of requests are implemented
                #     self.CACHE_KEY_ALL_TS, item_normalized, query_result)
            
            # Here we have cached results and query responses for all terminologies.
            # Check if query_result is empty and the fallback translation is enabled
            item_normalized_translated = ""
            #if len(query_result) == 0 and self.fallback_translation_libretranslate["enabled"]:
            if self.fallback_translation_libretranslate["enabled"]:
                item_normalized_translated = self.th_language_translation(item_normalized, self.fallback_translation_libretranslate["source_language"], self.fallback_translation_libretranslate["target_language"])
                print(f"\nitem_normalized_translated: {item_normalized_translated}\n")
            
            self.sh_set_np_translation(item, item_normalized_translated)

            result_temp = self.__create_item_results_from_query(query_result, item_normalized, result_temp, item_normalized_translated=item_normalized_translated)
            print(f"\nresult_temp: {result_temp}\n")
            
            BitsHelper.bh_request_results[item] = result_temp
            
        return BitsHelper.bh_request_results # For the WebUI or in general for the external requests

    def __bh_request_collection(self, np_collection: Set[str], ts_collections: Set[str]) -> Dict[str, Dict[str, Dict]]:
        """
        Processes requests for specific terminology collections.
        
        This method performs terminology searches within specified collections
        using the TIB API. For each term in the collection:
        1. Normalizes the term
        2. Checks cache for existing results using collection-specific keys
        3. Performs API query if needed with collection parameters
        4. Processes results and stores matches that meet similarity threshold
        5. Accumulates results across all collections for each term
        
        Args:
            np_collection (Set[str]): Collection of noun phrases to search for
            ts_collections (Set[str]): Collection of terminology collection names
                to search within
            
        Returns:
            Dict[str, Dict[str, Dict]]: Dictionary containing search results for each
                noun phrase across all specified collections
        """
        for item in np_collection:
            item_normalized = item.strip().lower()
            self.sh_set_np(item, item_normalized)
            
            # Check if fallback translation is enabled and get translated term
            item_normalized_translated = ""
            if self.fallback_translation_libretranslate["enabled"]:
                item_normalized_translated = self.th_language_translation(item_normalized, self.fallback_translation_libretranslate["source_language"], self.fallback_translation_libretranslate["target_language"])
                print(f"\nitem_normalized_translated: {item_normalized_translated}\n")
            
            self.sh_set_np_translation(item, item_normalized_translated)
            
            # Initialize results for this item if not exists
            if item not in BitsHelper.bh_request_results:
                BitsHelper.bh_request_results[item] = dict()
            
            for ts_collection in ts_collections:

                # result_temp = {terminology_name: {id, iri, original_label, similarity}}
                result_temp = dict()

                # Check cache for existing results using collection-specific key
                # cache_result = self.cache_get_query_item(
                #     ts_collection, item_normalized)
                cache_result = False # TODO: Enable Cache later, after all kinds of requests are implemented
                if cache_result:
                    query_result = cache_result
                    # logging.debug(
                    #     f"__bh_request_collection, use cached result for collection {ts_collection}")

                else:
                    # Perform query with collection parameters
                    url = self.__TIB_URL_SEARCH + f'q={item_normalized}&schema=collection&classification={ts_collection}'
                    # logging.debug(f"__bh_request_collection, url: {url}")   
                    query_result = self.__perform_query_search(url)

                    # self.cache_set_query_item(  TODO: Enable Cache later, after all kinds of requests are implemented
                    #     ts_collection, item_normalized, query_result)
                
                # Here we have cached results and query responses for all terminologies.
                result_temp = self.__create_item_results_from_query(
                    query_result, item_normalized, result_temp, item_normalized_translated=item_normalized_translated)
            
                # Accumulate results from this collection
                BitsHelper.bh_request_results[item].update(result_temp)
            
        return BitsHelper.bh_request_results # For the WebUI or in general for the external requests

    def bh_request_terminology_names(self) -> List[str]:
        """
        Request list of available terminologies from TIB API.
        
        This method queries the TIB API to retrieve a list of all available
        terminologies/ontologies that can be used for searches.
        
        Returns:
            List[str]: List of terminology names that are available in TIB API,
                sorted alphabetically
        """
        logging.debug("BitsHelper, start terminology names requesting")
        url = self.__TIB_URL + f'ontologies?size={self.__ONTOLOGY_SIZE}'
        response = self.__perform_query(url)
        
        if "elements" not in response.keys():
            return []
        
        terminologies = []
        for ontology in response["elements"]:
            if "ontologyId" in ontology.keys():
                terminologies.append(ontology["ontologyId"])
        
        return sorted(terminologies)