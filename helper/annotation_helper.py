"""
AnnotationHelper Module - Annotation Processing and Result Formatting

This module provides functionality for processing and applying terminology annotations
to text content. It handles the creation of standardized terminology results and
manages the annotation process across datasets.

The module supports multiple terminology sources and provides methods for
creating consistent annotation results that can be used across different
terminology services and APIs. It includes support for MIDS (Minimum Information
about a Digital Sequence) metadata and flexible annotation formatting.

Key Features:
- Standardized terminology result creation
- Multi-source terminology support
- MIDS metadata integration
- Flexible annotation formatting
- Dataset-wide annotation processing
- Result validation and statistics

Classes:
    AnnotationHelper: Main class for annotation processing
"""

import logging
from datetime import datetime
from typing import Dict, List, Any


class AnnotationHelper:
    """
    Helper class for handling annotation processing.
    
    This class provides functionality for:
    - Creating standardized terminology results from API responses
    - Processing and annotating entire datasets
    - Applying annotations to individual cells
    - Managing annotation statistics and validation
    
    The class handles different API response structures and ensures
    consistent formatting of annotation results across various
    terminology services.
    """

    def ah_create_terminology_result(self, single_result: Dict[str, str], similarity: float) -> Dict[str, Any]:
        """
        Creates a standardized terminology result dictionary from a single annotation result.
        
        This method normalizes API responses from different terminology services
        (e.g., OLS4 API, TIB API) into a consistent format for use throughout
        the annotation system.
        
        Args:
            single_result (Dict[str, str]): Dictionary containing the annotation result.
                Expected keys include:
                - 'id' or 'short_form': The terminology identifier
                - 'iri': The Internationalized Resource Identifier
                - 'label': The original terminology label
            similarity (float): Similarity score for the annotation match (0.0 to 1.0)
            
        Returns:
            Dict[str, Any]: Formatted terminology result containing:
                - id: The terminology identifier
                - iri: The Internationalized Resource Identifier
                - original_label: The original terminology label
                - similarity: The similarity score
                - mids: Metadata information (only if enabled)
                
        Example:
            >>> helper = AnnotationHelper()
            >>> result = {'id': '123', 'iri': 'http://example.org/123', 'label': 'metal oxide'}
            >>> formatted = helper.ah_create_terminology_result(result, 0.95)
            >>> print(formatted)
            {'id': '123', 'iri': 'http://example.org/123', 'original_label': 'metal oxide', 'similarity': 0.95}
        """
        # Handle different API response structures:
        # - OLS4 API uses 'id' field
        # - TIB API uses 'short_form' field
        result_id = single_result.get("id") or single_result.get("short_form", "")
        
        result = {
            "id": result_id,
            "iri": single_result["iri"],
            "original_label": single_result["label"],
            "similarity": similarity
        }
        
        # Only create mids object if mids_terms is enabled
        if self.mids_terms["enabled"]:
            result["mids"] = {}
            result["mids"]["identifier"] = self.mids_terms["identifier"]
            result["mids"]["label"] = self.mids_terms["label"]
            result["mids"]["description"] = self.mids_terms["description"]
            result["mids"]["creator"] = self.mids_terms["creator"]
            result["mids"]["digital_representation_type"] = self.mids_terms["digital_representation_type"]
            result["mids"]["provenance"] = self.mids_terms["provenance"]

            if self.mids_terms["creation_date"] != "default":
                result["mids"]["creation_date"] = self.mids_terms["creation_date"]
            else:
                result["mids"]["creation_date"] = datetime.now().strftime("%Y-%m-%d")

        return result

    def ah_annotate_dataset(self) -> None:
        """
        Processes and annotates the entire dataset using BITS results.
        
        This method performs the main annotation workflow:
        1. Sorts annotation keys by length (longest first) to prioritize
           longer matches over shorter ones
        2. Iterates through each row and relevant field in the dataset
        3. Applies annotations to each cell using the sorted keys
        4. Updates statistics for successful and missed annotations
        
        The method ensures that longer terminology matches are applied
        before shorter ones to prevent partial matches from interfering
        with complete terminology annotations.
        
        Note: This method requires bh_request_results to be populated
        with terminology search results before execution.
        """
        logging.debug("ah_annotate_dataset")

        # Use e.g. "metal oxide" before "metal" to annotate longest chunk at first
        sorted_keys: List[str] = self.__sort_keys(self.bh_request_results)

        # logging.debug(f"AnnotationHelper, sorted_keys: {sorted_keys}")

        for item in range(len(self.load_json_loads)):  # Rows
            for field in self.relevant_fields:
                if field in self.load_json_loads[item].keys():
                    self.load_json_loads[item][field] = self.ah_annotate_cell(
                        self.load_json_loads[item][field], sorted_keys)

        self.__set_statistics()

    def ah_annotate_cell(self, cell: str, sorted_keys: List[str] = None) -> str:
        """
        Annotates a single cell's content with matching terminology.
        
        This method applies terminology annotations to a cell by replacing
        matching terms with their annotated representations. The method
        processes keys in order (typically longest first) to ensure
        complete matches are applied before partial matches.
        
        Args:
            cell (str): The cell content to be annotated
            sorted_keys (List[str], optional): Sorted list of annotation keys to apply.
                If None, keys will be sorted by length in descending order.
                
        Returns:
            str: The annotated cell content with terminology annotations applied
            
        Example:
            >>> helper = AnnotationHelper()
            >>> cell = "This contains metal oxide and other materials"
            >>> keys = ["metal oxide", "metal"]
            >>> result = helper.ah_annotate_cell(cell, keys)
            >>> print(result)
            "This contains {'metal oxide': {...}} and other materials"
        """
        if sorted_keys is None:
            sorted_keys = self.__sort_keys(self.bh_request_results)

        logging.debug(f"AnnotationHelper, ah_annotate_cell: {cell}")
        for annotation_key in sorted_keys:
            cell = self.th_replace_except_braces(
                cell, annotation_key, str({annotation_key: self.bh_request_results[annotation_key]})) if self.bh_request_results[annotation_key] != {} else cell

        logging.debug(f"AnnotationHelper, return cell: {cell}")    
        return cell

    def __sort_keys(self, target: Dict[str, Any]) -> List[str]:
        """
        Sorts dictionary keys by length in descending order.
        
        This method is used to prioritize longer terminology matches
        over shorter ones during annotation. This prevents shorter
        terms from being annotated when they are part of longer
        terminology matches.
        
        Args:
            target (Dict[str, Any]): Dictionary whose keys need to be sorted
            
        Returns:
            List[str]: Sorted list of keys in descending length order
            
        Example:
            >>> helper = AnnotationHelper()
            >>> keys = {"metal": {...}, "metal oxide": {...}, "oxide": {...}}
            >>> sorted_keys = helper.__sort_keys(keys)
            >>> print(sorted_keys)
            ['metal oxide', 'metal', 'oxide']
        """
        return sorted(target.keys(), key=lambda x: len(x), reverse=True)

    def __set_statistics(self) -> None:
        """
        Updates statistics for annotations, tracking both successful matches
        and missing/declined annotations.
        
        This method processes the bh_request_results to update statistics:
        - Records successful annotations with their results
        - Tracks missed or declined annotations
        - Logs warnings for unexpected cases
        
        Note: This method requires sh_set_np() to be called before
        processing annotations to properly initialize the statistics structure.
        """
        # logging.debug(
        #     f"AnnotationHelper.__set_statistics, self.bh_request_results.items(): {self.bh_request_results.items()}")
        for key, value in self.bh_request_results.items():
            if value == {} and key != "":
                self.sh_set_np_missing_annotation(key)

        # Attention: Before you use sh_set_np_annotation you have to have to perform self.sh_set_np()
            elif value != {}:
                self.sh_set_np_annotation(key, value)

            else:
                logging.warning(f"__set_statistics, missing case. Key: {key}, value: {value}")
