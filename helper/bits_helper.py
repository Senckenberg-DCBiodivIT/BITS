"""
BitsHelper module for handling terminology requests and annotations using the TIB API.
This module provides functionality to search and match terms against various terminologies
using semantic similarity matching.
"""
import requests
import logging
import time


class BitsHelper:
    """
    A helper class for managing terminology requests and semantic matching.
    
    Attributes:
        bh_request_results (dict): A nested dictionary storing request results in the format:
            {term: {terminology_name: {id, iri, original_label, similarity}}}
        __TIB_URL_SEARCH (str): Base URL for the TIB terminology service API
    """

    bh_request_results: dict[str, dict[str, dict]] = dict()
    __TIB_URL = "https://api.terminology.tib.eu/api/v2/"
    __TIB_URL_SEARCH = "https://api.terminology.tib.eu/api/search?"

    __ONTOLOGY_SIZE = 1000

    def bh_request(self, kind: str, number_results: int = 30000) -> None:
        """
        Initiates terminology requests based on the specified kind.

        Args:
            kind (str): Type of request to perform. Valid values are:
                - "explicit_terminologies": Search in specific terminologies
                - "use_collection": Search in the specified collection
                - "use_all_ts": Perform complete search
            number_results (int, optional): Maximum number of results to return. Defaults to 30000.
        """
         
        logging.debug(f"BitsHelper, start {kind} requesting")
        bh_start_time = time.time()

        if kind == "explicit_terminologies":
            self.bh_request_explicit_terminologies(self.__class__.th_np_collection)
            
        elif kind == "use_collection":
            self.__bh_request_collection()

        elif kind == "use_all_ts":
            self.__bh_request_complete()

        print(f"BitsHelper, requests are done in {
              time.time() - bh_start_time}")

    def __perform_query(self, url: str) -> dict:
        """
        Performs HTTP GET request to the TIB API and processes the response.
        """
        headers = {'user-agent': 'my-app/0.0.1'}
        params = {'key': 'value'}

        response_json = requests.get(
            url, headers=headers, params=params).json()
        if response_json:
            return response_json
        else:
            return dict()   


    def __perform_query_search(self, url: str) -> dict:
        """
        Performs HTTP GET request to the TIB API and processes the response.

        Args:
            url (str): The complete URL for the API request

        Returns:
            dict: Response data containing matching results, or empty dict if no matches found
        """

        headers = {'user-agent': 'my-app/0.0.1'}
        params = {'key': 'value'}

        # dict_keys(['responseHeader', 'response', 'facet_counts', 'highlighting'])
        response_json = requests.get(
            url, headers=headers, params=params).json()
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

    def __create_item_results_from_query(self, query_result: dict, item_normalized: str, 
                                       result_temp: dict, terminology_name: str) -> dict:
        """
        Processes query results and creates terminology matches based on similarity threshold.

        Args:
            query_result (dict): Raw query results from the TIB API
            item_normalized (str): Normalized form of the search term
            result_temp (dict): Temporary storage for results
            terminology_name (str): Name of the terminology being searched

        Returns:
            dict: Updated result_temp dictionary with new matches that meet the similarity threshold
        """
        # logging.info(
        #     f"__create_item_results_from_query for {item_normalized} and result: {query_result}")

        language = "en" # here we use english for the similarity check. It seems not to be a problem for the similarity check for german terms as well. 

        item_normalized_similarity = self.SPACY_HANDLER[language](
            item_normalized)

        if "docs" in query_result.keys():
            for single_result in query_result["docs"]:
                # print(f"Single result: {single_result}")

                label = self.SPACY_HANDLER[language](
                    single_result["label"].lower())

                similarity_factor = item_normalized_similarity.similarity(
                    label)

                # print(f"Similarity: {similarity_factor}")
                if similarity_factor >= self.SIMILARITY_ACK:
                    # print("similarity_factor ok")

                    if terminology_name in result_temp.keys():
                        # print("Update result")
                        # Need for an result update?
                        if result_temp[terminology_name]["similarity"] < similarity_factor:
                            result_temp[terminology_name] = self.ah_create_terminology_result(
                                single_result, similarity_factor)

                    # No update necessary, just use the result and set in cache
                    else:
                        # print("Set new result")
                        result_temp[terminology_name] = self.ah_create_terminology_result(
                            single_result, similarity_factor)

        else:
            pass  # Here it's about a helper like "query_time" or other results, we can't use for an annotation. Just ignore them

        return result_temp

    def bh_request_explicit_terminologies(self, np_collection: set[str]) -> any:
        """
        Processes requests for explicitly specified terminologies.
        
        For each term in the collection:
        1. Normalizes the term
        2. Checks cache for existing results
        3. Performs API query if needed
        4. Processes results and stores matches that meet similarity threshold
        """

        for item in np_collection:
            item_normalized = item.strip().lower()
            self.sh_set_np(item, item_normalized)

            # result_temp = {terminology_name: {id, iri, original_label, similarity}}
            result_temp = dict()

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
                    query_result, item_normalized, result_temp, terminology_name)
           
            BitsHelper.bh_request_results[item] = result_temp

        return BitsHelper.bh_request_results # For the WebUI or in general for the external requests

    def __bh_request_all_terminologies(self, np_collection: set[str]) -> any:
        """
        Processes requests for all terminologies.
        
        For each term in the collection:
        1. Normalizes the term
        2. Checks cache for existing results using the key __ALL_TS_KEY
        3. Performs API query if needed
        4. Processes results and stores matches that meet similarity threshold
        5. Store the results in the cache using the key __ALL_TS_KEY
        """
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
                url = self.__TIB_URL_SEARCH + f'q={item_normalized}'
                # logging.debug(f"bh_request_all_terminologies, url, handler: {url}")   
                query_result = self.__perform_query_search(url)

                print(f"\n\nquery_result: {query_result}\n\n")
                # self.cache_set_query_item(  TODO: Enable Cache later, after all kinds of requests are implemented
                #     self.CACHE_KEY_ALL_TS, item_normalized, query_result)
            
            # Here we have cached results and query responses for all terminologies.
            result_temp = self.__create_item_results_from_query(
                query_result, item_normalized, result_temp, self.CACHE_KEY_ALL_TS)
            
            BitsHelper.bh_request_results[item] = result_temp
            
        return BitsHelper.bh_request_results # For the WebUI or in general for the external requests

    def __bh_request_collection(self) -> None:
        """
        Placeholder for collection request implementation.
        """
        pass

    def bh_request_terminology_names(self) -> list:
        """
        Request list of available terminologies from TIB API.
        
        Returns:
            list: List of terminology names that are available in TIB API
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