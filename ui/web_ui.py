from flask import Flask, render_template, request, jsonify, redirect, url_for
from typing import Optional, Any
import logging
import threading
import webbrowser


class WebUI():
    """
    Flask-based web interface for annotation visualization and in later steps interactive text processing and annotation.
    Provides functionality for displaying and updating content.
    """

    def __init__(self, TH) -> None:
        """
        Initialize the Text Helper object
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

    def run_server(self):
        """
        Start the Flask server if initialized
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

    #Routing
    def __show_csv_annotation(self):
        """
        Show the CSV annotation page.
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
        """
        return render_template('about.html')

    def __show_interactive_annotation(self) -> str:
        """
        Show the interactive annotation page.
        """
        return render_template('interactive_annotation.html')


    # User text annotation
    def __handle_annotation(self):
        """
        Handle the POST request for text annotation
        """
        try:
            content = request.json.get('text', '')
            result, np_collection = self.__annotate_user_text_content(content)
            return jsonify({'content': result, 'np_collection': np_collection})
        except Exception as e:
            logging.error(f"Error in annotation handler: {str(e)}")
            return jsonify({'error': str(e)}), 500

    def __annotate_user_text_content(self, content: str):
        """
        Annotate the user text content.
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

    # User text annotation, terminology handling
    def __get_terminologies(self):
        """
        API endpoint that returns available terminologies
        """
        try:
            terminologies = self.bh_request_terminology_names()
            return jsonify({'terminologies': terminologies})
        except Exception as e:
            logging.error(f"Error fetching terminologies: {str(e)}")
            return jsonify({'error': str(e)}), 500

    def __update_terminologies(self):
        """
        API endpoint to update selected terminologies
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

    # CSV annotation    
    def __get_csv_data(self):
        """
        API endpoint that returns the current data as JSON
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

    # Helper functions
    def __update_explicit_terminologies(self, explicit_terminologies):
        """
        Update the global explicit terminologies.
        """
        self.explicit_terminologies = explicit_terminologies
        logging.debug(f"ContentHandler, explicit_terminologies: {self.explicit_terminologies}")