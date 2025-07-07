import re
import time
import logging
import json
import requests
from threading import Lock
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

import spacy
from gpt4all import GPT4All


class TextHelper:
    """A helper class for text processing and noun phrase (NP) recognition using multiple AI services.

    This class provides functionality to:
    - Process text using SpaCy for English and German language models
    - Extract noun phrases using local GPT4All models
    - Support for additional AI services (GPT4All online and Ollama)

    Attributes:
        SIMILARITY_ACK (float): Similarity acknowledgment threshold (0.95)
        SPACY_HANDLER (dict): SpaCy language models for English and German
        th_cells (list): Storage for input text cells
        TextHelper.th_np_collection (set): Collection of noun phrases from all services    
    """

    SIMILARITY_ACK = 0.75
    th_cells = list()

    # SpaCy
    SPACY_HANDLER:dict = {"en": spacy.load(
        'en_core_web_lg'), "ger": spacy.load('de_core_news_lg')}
    # Currently we use a list of cells to have the same order as the input file for later use
    __th_spacy_cells:list = list()
    # Split string to improve the NP recognition for SpaCy preprocessing
    __TH_SGN_SPLIT_SENTENCE:list = [":", ",", ".", "(", ")", "[", "]", "="]
    __TH_REPLACE_SIGN:str = " . "
    __TH_MIN_NP_LENGTH:int = 2

    # In the future steps we annotate the cells independently from the language
    __th_spacy_np_collection:set = set()
    # Here we go a better performance using threads. In this case we have a lock for the collection
    __th_spacy_np_collection_lock:Lock = Lock()

    # Other AI services
    # Here we dont need a Lock() for the collection because service performance is the bottleneck
    __th_gpt4all_local_np_collection:set = set()
    __th_gpt4all_service_np_collection:set = set()
    __th_ollama_np_collection:set = set()

    th_np_collection:set = set()

    def __init__(self, config:dict = None) -> None:
        if config is not None:
            self.__load_manual_config(config) # This is necessary for sub objekts that are not initialized in the main.py

    def __load_manual_config(self, config:dict) -> None:
        """
        This method loads configuration for AI services and other settings from the provided config dictionary.
        This is necessary for sub objekts that are not initialized in the main.py
        """

        for key, value in config.items():
            setattr(self, key, value)

    def th_np_recognition(self) -> None:
        """Perform noun phrase recognition using configured AI services in parallel.

        This method orchestrates the NP recognition process through multiple steps running concurrently:
        1. SpaCy processing (always active)
        2. Local GPT4All (if configured)
        3. GPT4All online service (if configured)
        4. Ollama service (if configured)
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

        TextHelper.th_np_collection = {item for item in self.__th_spacy_np_collection if len(item) >= self.__TH_MIN_NP_LENGTH} | {
            item for item in self.__th_gpt4all_local_np_collection if len(item) >= self.__TH_MIN_NP_LENGTH} | {
            item for item in self.__th_gpt4all_service_np_collection if len(item) >= self.__TH_MIN_NP_LENGTH} | {
            item for item in self.__th_ollama_np_collection if len(item) >= self.__TH_MIN_NP_LENGTH}

    def th_np_recognition_collect_cells(self, cell) -> None:
        """Collect and preprocess text cells for NP recognition.

        Args:
            cell: The text cell to process and store
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

    # Spacy preprocessings and NP recognition
    def __np_recognition_spacy_single_cell_threader(self) -> None:

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

    def __np_recognition_spacy_single_cell(self, language, cell) -> None:
        """Process a single cell using SpaCy for noun phrase recognition.

        Args:
            language: The language model to use ('en' or 'ger')
            cell: The text cell to process
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

    def __prepare_spacy_cell(self, cell):
        # Use smaller text chunks for SpaCy
        for split_sign in self.__TH_SGN_SPLIT_SENTENCE:
            cell = cell.replace(
                split_sign, self.__TH_REPLACE_SIGN)

        # Fix for a better NP recognition
        if cell[-1] != ".":
            cell += self.__TH_REPLACE_SIGN

        return cell

    # GPT4All local instance NP recognition
    def __np_recognition_gpt4all_local(self) -> None:
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
        """Process text using Ollama service for noun phrase recognition.
        
        Uses the Ollama API to extract noun phrases based on the configuration
        in config_ollama.json. Processes each cell and updates the ollama 
        noun phrase collection.
        """
        logging.debug("Start Ollama service NP recognition")
        start_time = time.time()
        
        self.__th_ollama_np_collection = set()  # Reset collection
        
        # Prepare API parameters
        headers = {'Content-Type': 'application/json'}
        if self.ai_config["ollama"]["api_key"]:
            headers['Authorization'] = f'Bearer {self.ai_config["ollama"]["api_key"]}'
            
        for cell in self.th_cells:
            try:
                # Prepare request payload
                payload = {
                    "model": self.ai_config["ollama"]["model"],
                    "prompt": cell,
                    "system": self.ai_config["ollama"]["system"],
                    "temperature": self.ai_config["ollama"]["temperature"],
                    "reasoning_effort": self.ai_config["ollama"]["reasoning_effort"],
                    "top_k": self.ai_config["ollama"]["top_k"],
                    "top_p": self.ai_config["ollama"]["top_p"],
                    "context_length": self.ai_config["ollama"]["context_length"],
                    "stream": self.ai_config["ollama"]["stream"],
                }
                
                # Make API request
                response = requests.post(
                    f"{self.ai_config['ollama']['link_port']}/api/generate",
                    headers=headers,
                    json=payload,
                    timeout=self.ai_config['ollama']["timeout"]
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

    # Other helper methods
    def th_replace_except_braces(self, text, old, new) -> str:
        """Replace characters in text while preserving content within braces.

        Args:
            text: The input text to process
            old: The character to replace
            new: The replacement character

        Returns:
            str: The processed text with replacements
        """

        segments = re.split(r'(\{[^}]*\})', text)

        for i in range(len(segments)):
            if not segments[i].startswith('{') and not segments[i].endswith('}'):
                segments[i] = segments[i].replace(old, new)

        return ''.join(segments)

    def __extract_list_from_response(self, input_string) -> set:
        """Extract a list of noun phrases from an AI service response.

        Args:
            input_string: The raw response string from the AI service containing
                         lists in the format [item1, item2, ...]

        Returns:
            set: A set of cleaned noun phrases
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
        """Remove <think> tags and their content from the beginning of a text.
        
        Args:
            text: The input text to process
            
        Returns:
            str: Text with <think> section removed
            
        Example:
            >>> text = "<think>Some thoughts from the AI model</think>Actual content"
            >>> __remove_think_tags(text)
            'Actual content'
        """
        # Look for <think> tags at the start of the text
        pattern = r'^\s*<think>.*?</think>'
        return re.sub(pattern, '', text, flags=re.DOTALL).strip()
