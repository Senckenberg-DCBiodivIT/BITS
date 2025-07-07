import logging
from typing import Dict, List, Any


class AnnotationHelper:
    """
    Helper class for handling annotation processing and terminology mapping.
    Provides functionality for dataset annotation and terminology result creation.
    """

    def ah_create_terminology_result(self, single_result: Dict[str, str], similarity: float) -> Dict[str, Any]:
        """
        Creates a standardized terminology result dictionary from a single annotation result.

        Args:
            single_result (Dict[str, str]): Dictionary containing the annotation result with id, iri, and label
            similarity (float): Similarity score for the annotation match

        Returns:
            Dict[str, Any]: Formatted terminology result containing id, iri, original label, and similarity score
        """
        return {
            "id": single_result["id"],
            "iri": single_result["iri"],
            "original_label": single_result["label"],
            "similarity": similarity
        }

    # TODO: Here we use BITS results. Keep in mind __statistics_missed_annotations
    def ah_annotate_dataset(self) -> None:
        """
        Processes and annotates the entire dataset using BITS results.
        Iterates through each row and relevant field to apply annotations.
        Updates statistics for successful and missed annotations.
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

        Args:
            cell (str): The cell content to be annotated
            sorted_keys (List[str]): Sorted list of annotation keys to apply

        Returns:
            str: The annotated cell content
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

        Args:
            target (Dict[str, Any]): Dictionary whose keys need to be sorted

        Returns:
            List[str]: Sorted list of keys
        """
        return sorted(target.keys(), key=lambda x: len(x), reverse=True)

    def __set_statistics(self) -> None:
        """
        Updates statistics for annotations, tracking both successful matches
        and missing/declined annotations. Requires sh_set_np() to be called
        before processing annotations.
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
