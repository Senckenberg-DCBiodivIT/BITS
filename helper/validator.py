"""
Validator Module

This module provides functionality for validating annotation results by comparing
original and annotated content. It ensures that annotations are applied correctly
and maintains data integrity throughout the annotation process.

The validator performs bijective validation to ensure that annotated content
can be reconstructed back to the original form by removing annotations.

Classes:
    Validator: Main class for annotation validation
"""

import logging
import copy
from typing import Dict, Any, List


class Validator:
    """
    A class for validating annotation results and ensuring data integrity.
    
    This class provides methods to verify that annotations are applied correctly
    and that the original content can be reconstructed from annotated content
    by removing the annotation markers.
    
    The validator compares original and annotated datasets to detect any
    inconsistencies or errors in the annotation process.
    """

    def vh_bijective_validation(self) -> None:
        """
        Perform bijective validation of annotation results.
        
        This method validates that:
        1. The number of rows in original and annotated datasets match
        2. Each annotated field can be reconstructed to its original form
        3. No data corruption occurred during annotation
        
        The validation process:
        - Compares dataset lengths
        - Iterates through each row and relevant field
        - Compares original vs annotated content
        - Records validation errors for any discrepancies
        
        Raises:
            None: Errors are logged and recorded in statistics rather than raised
        """
        logging.debug(f"vh_bijective_validation")
        error_flag = False

        # Check if dataset lengths match
        if len(self.original_json_loads) != len(self.load_json_loads):
            self.sh_set_validation_error("different_length", True)

        # Validate each row and field
        for item_index in range(len(self.load_json_loads)):  # Rows
            for language in self.relevant_fields.keys():
                for field in self.relevant_fields[language]:
                    if field in self.load_json_loads[item_index].keys():
                        original_field = self.original_json_loads[item_index][field]
                        annotated_field = self.load_json_loads[item_index][field]

                        comparison = self.__compare_cells(
                            original_field, annotated_field)

                        if comparison == False:
                            error_flag = True
                            self.sh_set_validation_error(
                                f"{original_field}", f"{annotated_field}")

                        if error_flag != True:
                            self.sh_set_validation_error(
                                f"Error detected", f"False")

    def __compare_cells(self, original: str, annotated: str) -> bool:
        """
        Compare original and annotated cell content for validation.
        
        This method reconstructs the original content from annotated content
        by removing all annotation markers and comparing the result with
        the original content.
        
        Args:
            original (str): The original cell content before annotation
            annotated (str): The annotated cell content to validate
            
        Returns:
            bool: True if the annotated content can be reconstructed to match
                  the original content, False otherwise
                  
        Example:
            >>> validator = Validator()
            >>> original = "metal oxide"
            >>> annotated = "metal oxide{'metal oxide': {'id': '123', 'iri': 'http://...'}}"
            >>> validator.__compare_cells(original, annotated)
            True
        """
        copy_annotated = copy.deepcopy(annotated)

        # Remove all annotation markers to reconstruct original content
        for key, value in self.bh_request_results.items():
            if value != {}:
                value_replace = f"{{'{key}': {value}}}"
                copy_annotated = copy_annotated.replace(value_replace, key)

        return True if copy_annotated == original else False
