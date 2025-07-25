"""
TextHelper Module

This module provides comprehensive text processing and noun phrase recognition
functionality using multiple AI services. It supports SpaCy for NLP tasks,
GPT4All for local AI processing, and Ollama for remote AI services.

The module handles text preprocessing, noun phrase extraction, and provides
thread-safe processing capabilities for improved performance.

Classes:
    TextHelper: Main class for text processing and noun phrase recognition
"""

import re
import time
import logging
import json
import requests
from threading import Lock
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote
from typing import Dict, Any, List, Set, Optional

import spacy
from gpt4all import GPT4All


class TextHelper:
    """
    A helper class for text processing and noun phrase (NP) recognition using multiple AI services.

    This class provides functionality to:
    - Process text using SpaCy for English and German language models
    - Extract noun phrases using local GPT4All models
    - Support for additional AI services (GPT4All online and Ollama)
    - Thread-safe processing for improved performance
    - Text preprocessing and normalization

    Attributes:
        SIMILARITY_ACK (float): Similarity acknowledgment threshold (0.90)
        SPACY_HANDLER (Dict[str, spacy.Language]): SpaCy language models for English and German
        th_cells (List[str]): Storage for input text cells
        th_np_collection (Set[str]): Collection of noun phrases from all services
        __th_spacy_cells (List[str]): Preprocessed cells for SpaCy processing
        __th_spacy_np_collection (Set[str]): Noun phrases identified by SpaCy
        __th_gpt4all_local_np_collection (Set[str]): Noun phrases from local GPT4All
        __th_gpt4all_service_np_collection (Set[str]): Noun phrases from GPT4All service
        __th_ollama_np_collection (Set[str]): Noun phrases from Ollama service
    """

    SIMILARITY_ACK = 0.90
    th_cells = list()

    # SpaCy
    SPACY_HANDLER: Dict[str, spacy.Language] = {
        "en": spacy.load('en_core_web_lg'), 
        "ger": spacy.load('de_core_news_lg')
    }
    # Currently we use a list of cells to have the same order as the input file for later use
    __th_spacy_cells: List[str] = list()
    # Split string to improve the NP recognition for SpaCy preprocessing
    __TH_SGN_SPLIT_SENTENCE: List[str] = [":", ",", ".", "(", ")", "[", "]", "="]
    __TH_REPLACE_SIGN: str = " . "
    __TH_MIN_NP_LENGTH: int = 2

    # In the future steps we annotate the cells independently from the language
    __th_spacy_np_collection: Set[str] = set()
    # Here we go a better performance using threads. In this case we have a lock for the collection
    __th_spacy_np_collection_lock: Lock = Lock()

    # Other AI services
    # Here we dont need a Lock() for the collection because service performance is the bottleneck
    __th_gpt4all_local_np_collection: Set[str] = set()
    __th_gpt4all_service_np_collection: Set[str] = set()
    __th_ollama_np_collection: Set[str] = set()

    th_np_collection: Set[str] = set()

    def __init__(self, config: Dict[str, Any] = None) -> None:
        """
        Initialize the TextHelper with optional configuration.
        
        Args:
            config (Dict[str, Any], optional): Configuration dictionary for AI services
                and processing settings. If provided, loads configuration using
                __load_manual_config method.
        """
        if config is not None:
            self.__load_manual_config(config) # This is necessary for sub objekts that are not initialized in the main.py

    def __load_manual_config(self, config: Dict[str, Any]) -> None:
        """
        Load configuration for AI services and other settings from the provided config dictionary.
        
        This method is necessary for sub objects that are not initialized in the main.py.
        It sets attributes on the instance based on the provided configuration.
        
        Args:
            config (Dict[str, Any]): Configuration dictionary containing AI service
                settings and processing parameters
        """
        for key, value in config.items():
            setattr(self, key, value)

    def th_np_recognition(self) -> None:
        """
        Perform noun phrase recognition using configured AI services in parallel.
        
        This method orchestrates the NP recognition process through multiple steps
        running concurrently:
        1. SpaCy processing (always active)
        2. Local GPT4All (if configured)
        3. GPT4All online service (if configured)
        4. Ollama service (if configured)
        
        The method uses ThreadPoolExecutor to run different AI services in parallel,
        improving overall processing time. Results from all services are combined
        into the final th_np_collection.
        """
        logging.debug("Start NP recognition")
        np_start_time = time.time()

        # Create thread pool for parallel execution
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            
            # Step 1: Spacy
            if self.ai_use["spacy"]:
                futures.append(executor.submit(self.__np_recognition_spacy_single_cell_threader))
            
            # Step 2: GPT4All locally
            if self.ai_use["gpt4all_local"]:
                futures.append(executor.submit(self.__np_recognition_gpt4all_local))
            
            # Step 3: GPT4All online service (commented out for now)
            # if self.ai_use["gpt4all_service"] == "True":
            #     futures.append(executor.submit(self.__np_recognition_gpt4all_service))
            
            # Step 4: Ollama service
            if self.ai_use["ollama"]:
                futures.append(executor.submit(self.__np_recognition_ollama))
                
            # Wait for all tasks to complete
            for future in futures:
                future.result()

        logging.debug(f"NP done in {time.time() - np_start_time}")
        logging.debug(f"NPs from spacy: {self.__th_spacy_np_collection}")
        logging.debug(
            f"NPs from gpt4all local: {self.__th_gpt4all_local_np_collection}")
        logging.debug(
            f"NPs from gpt4all service: {self.__th_gpt4all_service_np_collection}")
        logging.debug(
            f"NPs from ollama service: {self.__th_ollama_np_collection}")

        # Combine results from all services, filtering by minimum length
        TextHelper.th_np_collection = {item for item in self.__th_spacy_np_collection if len(item) >= self.__TH_MIN_NP_LENGTH} | {
            item for item in self.__th_gpt4all_local_np_collection if len(item) >= self.__TH_MIN_NP_LENGTH} | {
            item for item in self.__th_gpt4all_service_np_collection if len(item) >= self.__TH_MIN_NP_LENGTH} | {
            item for item in self.__th_ollama_np_collection if len(item) >= self.__TH_MIN_NP_LENGTH}

    def th_np_recognition_collect_cells(self, cell: str) -> None:
        """
        Collect and preprocess text cells for NP recognition.
        
        This method processes and stores text cells for later noun phrase
        recognition. It filters out ignored values and prepares cells for
        different AI services.
        
        Args:
            cell (str): The text cell to process and store
        """
        # logging.debug(f"th_np_recognition_collect_cells: {cell}")
        if cell not in self.ignore_cell_value:
            # logging.debug(f"Store th_np_recognition_collect_cells: {cell}")
            self.th_cells.append(cell[:])  # Use a shallow copy of the cell

            # For SpaCy only
            # Use a shallow copy of the cell
            cell = self.__prepare_spacy_cell(cell[:])
            self.__th_spacy_cells.append(cell)

        # else:
        #     logging.debug(f"Ignore th_np_recognition_collect_cells: {cell}")

    def __np_recognition_spacy_single_cell_threader(self) -> None:
        """
        Orchestrate SpaCy noun phrase recognition using threading.
        
        This method manages the parallel processing of cells using SpaCy
        for both English and German language models. It creates a thread
        pool to process cells concurrently for better performance.
        """
        logging.debug(f"Start Spacy NP recognition")

        threads = []
        self.__th_spacy_np_collection = set()  # Reset the collection

        for language in ["en", "ger"]:  # Here we use the language models for english and german
            for cell in self.th_cells:
                # Here we try to perform a better recognition using english and german language models
                threads.append((language, cell))

            with ThreadPoolExecutor(self.max_threads) as executor:
                [executor.submit(self.__np_recognition_spacy_single_cell,
                                 language, cell) for language, cell in threads]
        logging.debug(f"NPs from spacy: {self.__th_spacy_np_collection}")

    def __np_recognition_spacy_single_cell(self, language: str, cell: str) -> None:
        """
        Process a single cell using SpaCy for noun phrase recognition.
        
        This method applies SpaCy's noun chunk detection to a single cell
        using the specified language model. It preprocesses the text to
        improve noun phrase recognition and filters results by length.
        
        Args:
            language (str): The language model to use ('en' or 'ger')
            cell (str): The text cell to process
        """
        cell_temp = cell[:]
        for sign in self.__TH_SGN_SPLIT_SENTENCE:
            cell_temp = cell_temp.replace(sign, self.__TH_REPLACE_SIGN)

        spacy_cell = self.SPACY_HANDLER[language](cell_temp)

        # nominal phrases with more than 1 character
        temp = [
            # "  " is a typical case for SpaCy in this context if it is a bigger NP. We dont want to include this because we will have the splitted sub-groups allready in the list
            str(chunk.text) for chunk in spacy_cell.noun_chunks if len(chunk.text) >= self.__TH_MIN_NP_LENGTH and "  " not in chunk.text]

        with self.__th_spacy_np_collection_lock:
            self.__th_spacy_np_collection.update(temp)

    def __prepare_spacy_cell(self, cell: str) -> str:
        """
        Preprocess a cell for SpaCy noun phrase recognition.
        
        This method prepares text cells for optimal SpaCy processing by:
        1. Replacing punctuation with sentence boundaries
        2. Ensuring proper sentence endings
        3. Normalizing text structure for better noun chunk detection
        
        Args:
            cell (str): The raw text cell to preprocess
            
        Returns:
            str: The preprocessed cell ready for SpaCy processing
        """
        # Use smaller text chunks for SpaCy
        for split_sign in self.__TH_SGN_SPLIT_SENTENCE:
            cell = cell.replace(
                split_sign, self.__TH_REPLACE_SIGN)

        # Fix for a better NP recognition
        if cell[-1] != ".":
            cell += self.__TH_REPLACE_SIGN

        return cell

    def __np_recognition_gpt4all_local(self) -> None:
        """
        Perform noun phrase recognition using local GPT4All model.
        
        This method processes each cell using a local GPT4All model to
        extract noun phrases. It handles model initialization, text generation,
        and result extraction with proper error handling.
        
        The method:
        1. Initializes the GPT4All model with specified configuration
        2. Processes each cell with the configured prompt
        3. Extracts noun phrases from the generated response
        4. Updates the local GPT4All noun phrase collection
        """
        logging.debug(f"Start GPT4All local NP recognition")

        start_time_recognition = time.time()
        self.__th_gpt4all_local_np_collection = set()  # reset the collection

        if self.ai_config["gpt4all_local"]["local_path"]:
            pass  # TODO: Implement in later steps if we have a local instance
        else:
            logging.debug(
                f"Use model: {self.ai_config['gpt4all_local']['model_name']}")
            model = GPT4All(self.ai_config["gpt4all_local"]["model_name"],
                            allow_download=True, n_threads=self.max_threads)

        for cell in self.th_cells:
            start_time_cell = time.time()
            with model.chat_session():
                cell_np = model.generate(
                    self.ai_config["gpt4all_local"]["prompt"].replace("{input-string}", cell))
                logging.debug(
                    f"cell_np before extraction: {cell_np}")

                try:
                    cell_np = self.__extract_list_from_response(cell_np)
                except:
                    logging.error(f"Error extracting GPT list: {cell_np}")
                    self.sh_set_ai_error(cell, cell_np)
                    cell_np = []

                logging.debug(
                    f"self.__th_gpt4all_local_np_collection: {self.__th_gpt4all_local_np_collection}")
                logging.debug(
                    f"cell_np after extraction: {cell_np}")

                self.__th_gpt4all_local_np_collection.update(cell_np)
                execution_time_cell = time.time() - start_time_cell

                logging.debug(
                    f"GPT NP detection, cell: {cell}\n cell_np: {cell_np}\n in {execution_time_cell} seconds")

        execution_time_recognition = time.time() - start_time_recognition
        logging.info(f"GPT NP recognition done in {
                     execution_time_recognition} seconds")

    # GPT4All online service NP recognition
    # TODO: Implement

    # Ollama service NP recognition
    def __np_recognition_ollama(self) -> None:
        """
        Process text using Ollama service for noun phrase recognition.
        
        Uses the Ollama API to extract noun phrases based on the configuration
        in config_ollama.json. Processes each cell and updates the ollama 
        noun phrase collection.
        
        The method:
        1. Prepares API requests with proper headers and authentication
        2. Sends requests to the Ollama service for each cell
        3. Processes responses and extracts noun phrases
        4. Handles errors and updates statistics
        """
        logging.debug("Start Ollama service NP recognition")
        start_time = time.time()
        
        self.__th_ollama_np_collection = set()  # Reset collection
        
        # Prepare API parameters
        headers = {'Content-Type': 'application/json'}
        if self.ai_config["ollama"]["NP_RECOGNITION"]["api_key"]:
            headers['Authorization'] = f'Bearer {self.ai_config["ollama"]["NP_RECOGNITION"]["api_key"]}'
            
        for cell in self.th_cells:
            try:
                # Prepare request payload
                payload = {
                    "model": self.ai_config["ollama"]["NP_RECOGNITION"]["model"],
                    "prompt": cell,
                    "system": self.ai_config["ollama"]["NP_RECOGNITION"]["system"],
                    "temperature": self.ai_config["ollama"]["NP_RECOGNITION"]["temperature"],
                    "reasoning_effort": self.ai_config["ollama"]["NP_RECOGNITION"]["reasoning_effort"],
                    "top_k": self.ai_config["ollama"]["NP_RECOGNITION"]["top_k"],
                    "top_p": self.ai_config["ollama"]["NP_RECOGNITION"]["top_p"],
                    "context_length": self.ai_config["ollama"]["NP_RECOGNITION"]["context_length"],
                    "stream": self.ai_config["ollama"]["NP_RECOGNITION"]["stream"],
                }
                
                # Make API request
                response = requests.post(
                    f"{self.ai_config['ollama']['NP_RECOGNITION']['link_port']}/api/generate",
                    headers=headers,
                    json=payload,
                    timeout=self.ai_config['ollama']["NP_RECOGNITION"]["timeout"]
                )
                
                if response.status_code == 200:
                    result = response.json()
                    response_text = result.get('response', '')
                    response_text = self.__remove_think_tags(response_text)

                    logging.debug(f"Ollama response: {response_text}")  
                    
                    # Extract noun phrases from response
                    try:
                        noun_phrases = self.__extract_list_from_response(response_text)
                        self.__th_ollama_np_collection.update(noun_phrases)
                        logging.debug(f"Ollama NPs for cell '{cell}': {noun_phrases}")
                    except Exception as e:
                        logging.error(f"Error extracting Ollama NPs: {str(e)}")
                        self.sh_set_ai_error(cell, response_text)
                else:
                    logging.error(f"Ollama API error: {response.status_code} - {response.text}")
                    self.sh_set_ai_error(cell, f"API Error: {response.status_code}")
                    
            except Exception as e:
                logging.error(f"Error calling Ollama service: {str(e)}")
                self.sh_set_ai_error(cell, str(e))
                
        execution_time = time.time() - start_time
        logging.info(f"Ollama NP recognition completed in {execution_time} seconds")
        logging.debug(f"Total Ollama NPs: {self.__th_ollama_np_collection}")

    def th_np_translation_en(self, np: str) -> str:
        """
        Translate a noun phrase to English using the Ollama service.
        
        This method translates a given noun phrase to English using the Ollama service.
        It prepares the request payload and sends it to the Ollama service for translation.
        """
        print("\n\n th_np_translation_en: ", np, "\n\n")

    def th_replace_except_braces(self, text: str, old: str, new: str) -> str:
        """
        Replace characters in text while preserving content within braces.
        
        This method performs text replacement while protecting content within
        curly braces from being modified. This is useful for preserving
        annotation markers during text processing.
        
        Args:
            text (str): The input text to process
            old (str): The character to replace
            new (str): The replacement character

        Returns:
            str: The processed text with replacements applied outside of braces
            
        Example:
            >>> helper = TextHelper()
            >>> text = "metal oxide {'metal oxide': {...}}"
            >>> result = helper.th_replace_except_braces(text, "e", "X")
            >>> print(result)
            "mXtal oxidX {'metal oxide': {...}}"
        """
        segments = re.split(r'(\{[^}]*\})', text)

        for i in range(len(segments)):
            if not segments[i].startswith('{') and not segments[i].endswith('}'):
                segments[i] = segments[i].replace(old, new)

        return ''.join(segments)

    def __extract_list_from_response(self, input_string: str) -> Set[str]:
        """
        Extract a list of noun phrases from an AI service response.
        
        This method parses AI service responses to extract noun phrases
        that are formatted as lists in square brackets. It handles various
        formatting issues and returns a clean set of noun phrases.
        
        Args:
            input_string (str): The raw response string from the AI service containing
                               lists in the format [item1, item2, ...]

        Returns:
            Set[str]: A set of cleaned noun phrases
            
        Example:
            >>> helper = TextHelper()
            >>> response = "Here are the noun phrases: [metal oxide, carbon dioxide, water]"
            >>> result = helper.__extract_list_from_response(response)
            >>> print(result)
            {'metal oxide', 'carbon dioxide', 'water'}
        """
        result_set = set()
        
        # Find all lists in square brackets
        list_pattern = r'\[(.*?)\]'
        matches = re.findall(list_pattern, input_string)
        
        for match in matches:
            # Split at commas and clean each item
            items = [item.strip().strip("'\"") for item in match.split(',')]
            # Add non-empty items to result set
            result_set.update(item for item in items if item)

        return result_set
    
    def __remove_think_tags(self, text: str) -> str:
        """
        Remove <think> tags and their content from the beginning of a text.
        
        This method removes thinking/reflection tags that some AI models
        include in their responses, keeping only the actual content.
        
        Args:
            text (str): The input text to process
            
        Returns:
            str: Text with <think> section removed
            
        Example:
            >>> helper = TextHelper()
            >>> text = "<think>Some thoughts from the AI model</think>Actual content"
            >>> result = helper.__remove_think_tags(text)
            >>> print(result)
            'Actual content'
        """
        # Look for <think> tags at the start of the text
        pattern = r'^\s*<think>.*?</think>'
        return re.sub(pattern, '', text, flags=re.DOTALL).strip()

