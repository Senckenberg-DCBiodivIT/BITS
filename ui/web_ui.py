"""
WebUI Module

This module provides a Flask-based web interface for annotation visualization
and interactive text processing. It offers functionality for displaying and
updating content through a web browser with real-time processing capabilities.

The module includes comprehensive web interface features:
- CSV annotation visualization
- Interactive text annotation with real-time processing
- Terminology selection and management
- Real-time annotation processing and results display
- API endpoints for data exchange

The web interface runs in a separate thread to avoid blocking
the main annotation workflow, providing a responsive user experience
while maintaining system performance.

Classes:
    WebUI: Main class for Flask-based web interface
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
from typing import Optional, Any, Dict, List
import logging
import threading
import webbrowser


class WebUI:
    """
    Flask-based web interface for annotation visualization and interactive text processing.
    
    This class provides a comprehensive web interface for the BITS annotation system,
    including CSV annotation visualization, interactive text processing, and
    terminology management. It runs as a separate thread to avoid blocking
    the main application while providing a responsive user experience.
    
    The interface supports comprehensive annotation workflows:
    - CSV annotation display
    - Interactive text input and processing with immediate results
    - Terminology selection and management with dynamic updates
    - Real-time annotation results with detailed statistics
    - API endpoints for data exchange
    
    The web interface is designed to be user-friendly while providing
    powerful annotation capabilities for both batch processing and
    interactive text analysis.
    
    Attributes:
        TH_WEBUI: TextHelper instance for text processing
        selected_terminologies (List[str]): List of selected terminologies for annotation
        __ui (Flask): Flask application instance
        server_thread (threading.Thread): Thread running the Flask server
    """

    def __init__(self, TH) -> None:
        """
        Initialize the WebUI with Flask app and routes.
        
        This method sets up the Flask application, configures routes,
        and starts the web server in a separate thread. It also
        initializes the TextHelper for text processing.
        
        Args:
            TH: TextHelper instance for text processing functionality
        """
        self.TH_WEBUI = TH
        self.selected_terminologies = []  # Initialize empty list for selected terminologies
        
        TH_config = {"ai_use": {"spacy": True, # TODO: Use the config from the main.py after the refactoring
                                "ollama": False,
                                "gpt4all": False,
                                "gpt4all_local": False},
                     "max_threads": self.config["max_threads"],
                     "ignore_cell_value": ""
                     }
        self.TH_WEBUI.__init__(TH_config)

        """
        Initialize the WebUI with Flask app and routes
        """
        self.__ui = Flask(__name__,
                          template_folder='templates',
                          static_folder='static')

        # Register routes
        self.__ui.add_url_rule('/', 'index', self.__show_csv_annotation)
        self.__ui.add_url_rule('/about', 'about', self.__show_about)
        self.__ui.add_url_rule('/interactive', 'interactive',
                               self.__show_interactive_annotation)
        self.__ui.add_url_rule('/api/get_csv_data',
                               'get_csv_data', self.__get_csv_data)
        self.__ui.add_url_rule('/annotate', 'annotate',
                               self.__handle_annotation, methods=['POST'])
        # Add new routes for terminology handling
        self.__ui.add_url_rule('/api/get_terminologies',
                               'get_terminologies', self.__get_terminologies)
        self.__ui.add_url_rule('/api/update_terminologies',
                               'update_terminologies', self.__update_terminologies, methods=['POST'])

        logging.debug("Flask app defined successfully")

        # Start server in separate thread
        self.server_thread = threading.Thread(target=self.run_server)
        self.server_thread.daemon = True
        self.server_thread.start()

        # Open browser automatically if configured
        if self.config["web_ui"].get("open_browser", True):
            port = self.config["web_ui"]["port"]
            webbrowser.open(f'http://localhost:{port}')

    def run_server(self) -> None:
        """
        Start the Flask server if initialized.
        
        This method runs the Flask development server with appropriate
        settings for production use. It includes error handling for
        server startup issues.
        
        The server runs on localhost with the configured port and
        supports threaded requests for better performance.
        """
        if self.__ui:
            try:
                self.__ui.run(
                    debug=False,  # Set to False to avoid the reloader thread
                    port=self.config["web_ui"]["port"],
                    use_reloader=False,
                    host='localhost',  # Changed from 0.0.0.0 to localhost for security
                    threaded=True
                )
            except Exception as e:
                logging.error(f"Failed to start Flask server: {e}")
        else:
            logging.error("Flask app not initialized!")

    def __show_csv_annotation(self) -> str:
        """
        Show the CSV annotation page.
        
        This route displays the main CSV annotation interface with
        noun phrases, annotated results, and performed annotations.
        It provides a comprehensive view of the annotation process
        and results.
        
        Returns:
            str: Rendered HTML template for CSV annotation page
            
        Raises:
            Exception: If template rendering fails
        """
        try:
            return render_template('csv_annotation.html',
                                   noun_groups=self.th_np_collection,
                                   annotated_noun_groups=self.bh_request_results,
                                   performed_annotation=self.load_json_loads)
        except Exception as e:
            logging.error(f"Error in function __show_csv_annotation: {str(e)}")
            return f"Error in function __show_csv_annotation: {str(e)}"

    def __show_about(self) -> str:
        """
        Show the about page.
        
        Returns:
            str: Rendered HTML template for about page
        """
        return render_template('about.html')

    def __show_interactive_annotation(self) -> str:
        """
        Show the interactive annotation page.
        
        This route displays the interactive annotation interface where
        users can input text and see real-time annotation results.
        
        Returns:
            str: Rendered HTML template for interactive annotation page
        """
        return render_template('interactive_annotation.html')

    def __handle_annotation(self) -> jsonify:
        """
        Handle the POST request for text annotation.
        
        This API endpoint processes text annotation requests from the
        web interface. It takes user input text, performs noun phrase
        recognition, and returns annotated results.
        
        Returns:
            jsonify: JSON response containing annotated content and noun phrases
            
        Raises:
            Exception: If annotation processing fails
        """
        try:
            content = request.json.get('text', '')
            result, np_collection = self.__annotate_user_text_content(content)
            return jsonify({'content': result, 'np_collection': np_collection})
        except Exception as e:
            logging.error(f"Error in annotation handler: {str(e)}")
            return jsonify({'error': str(e)}), 500

    def __annotate_user_text_content(self, content: str) -> tuple[str, str]:
        """
        Annotate the user text content.
        
        This method processes user-provided text through the annotation
        pipeline: noun phrase recognition, terminology matching, and
        annotation application.
        
        Args:
            content (str): The text content to annotate
            
        Returns:
            tuple[str, str]: Tuple containing (annotated_content, noun_phrases)
                where noun_phrases is a string representation of the set
                
        Raises:
            Exception: If annotation processing fails
        """
        try:
            # Collect sentences from the content
            self.TH_WEBUI.th_cells = content.replace("\n", " ").split(".")
            self.TH_WEBUI.th_cells = [
                cell.strip() for cell in self.TH_WEBUI.th_cells if cell.strip()]

            logging.debug(f"self.TH_WEBUI.th_cells: {self.TH_WEBUI.th_cells}")

            # Detect NP
            self.TH_WEBUI.th_np_recognition()

            # Only proceed with annotation if terminologies are selected
            if not self.selected_terminologies:
                return "Please select at least one terminology before annotation.", str([])

            # Annotate NP in a threaded process
            annotation_done = self.bh_request_explicit_terminologies(
                self.TH_WEBUI.th_np_collection)

            # Perform Annotation
            annotated_content = self.ah_annotate_cell(content)
            logging.debug(f"annotated_content: {annotated_content}")

            # Finish
            return annotated_content, str(self.TH_WEBUI.th_np_collection)
        except Exception as e:
            logging.error(f"Error in annotation: {str(e)}")
            return f"Error during annotation: {str(e)}", str([])

    def __get_terminologies(self) -> jsonify:
        """
        API endpoint that returns available terminologies.
        
        This endpoint queries the TIB API to retrieve a list of all
        available terminologies that can be used for annotation.
        
        Returns:
            jsonify: JSON response containing list of available terminologies
            
        Raises:
            Exception: If terminology retrieval fails
        """
        try:
            terminologies = self.bh_request_terminology_names()
            return jsonify({'terminologies': terminologies})
        except Exception as e:
            logging.error(f"Error fetching terminologies: {str(e)}")
            return jsonify({'error': str(e)}), 500

    def __update_terminologies(self) -> jsonify:
        """
        API endpoint to update selected terminologies.
        
        This endpoint receives the list of selected terminologies from
        the web interface and updates the internal state for use in
        annotation processing.
        
        Returns:
            jsonify: JSON response indicating success or failure
            
        Raises:
            Exception: If terminology update fails
        """
        try:
            selected = request.json.get('selected', [])
            self.selected_terminologies = selected
            # Update the explicit terminologies in TH_WEBUI
            self.__update_explicit_terminologies(selected)

            return jsonify({'status': 'success'})
        except Exception as e:
            logging.error(f"Error updating terminologies: {str(e)}")
            return jsonify({'error': str(e)}), 500

    def __get_csv_data(self) -> jsonify:
        """
        API endpoint that returns the current data as JSON.
        
        This endpoint provides the current annotation data to the web
        interface, including noun phrases, annotated results, and
        performed annotations.
        
        Returns:
            jsonify: JSON response containing current annotation data
            
        Raises:
            Exception: If data retrieval fails
        """
        try:
            data = {
                # Convert Set to List
                'noun_groups': list(self.th_np_collection),
                'annotated_noun_groups': self.bh_request_results,  # Remains Dictionary
                'performed_annotation': self.load_json_loads  # Add performed_annotation
            }
            return jsonify(data)
        except Exception as e:
            logging.error(f"Error in __get_csv_data: {str(e)}")
            return jsonify({'error': str(e)}), 500

    def __update_explicit_terminologies(self, selected_terminologies: List[str]) -> None:
        """
        Update the explicit terminologies in the TextHelper instance.
        
        This method updates the explicit_terminologies configuration
        in the TextHelper instance to match the user's selection
        from the web interface.
        
        Args:
            selected_terminologies (List[str]): List of selected terminology names
        """
        # Update the explicit terminologies in TH_WEBUI
        self.TH_WEBUI.explicit_terminologies = selected_terminologies