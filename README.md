# FAIRenrich
A comprehensive system for text processing and terminology annotation using multiple AI services and the TIB terminology service. The tool supports both batch processing of CSV files and interactive web-based annotation.

## Features

- Multi-language text processing (English and German support)
- Multiple AI services support:
  - spaCy for NLP tasks
  - Ollama for remote or local AI processing
  - GPT4All (both local and service-based)
- Terminology matching using TIB terminology service
- Thread-safe caching system for improved performance
- Configurable validation and statistics collection
- Interactive web interface for real-time annotation
- Batch processing of CSV files
- Support for multiple terminology sources and collections

##### Configuration

### Main Configuration (config.json)

- `version` (float): Configuration version (current: 0.4)
  *Don't change this manually.*

- `annotation`:
  - `input_file` (str): Path to input CSV file
  - `output_file` (str): Path for annotated output CSV
  - `perform_export` (bool): Enable/disable export of annotated file
  - `perform_validation` (bool): Enable/disable validation of annotations
  - `ts_sources`: Terminology source configuration
    - `explicit_terminologies` (array/bool): List of specific terminologies or "False"
    - `collection` (str/bool): BITS TS collection name or "False"
  - `relevant_fields` (array): Columns to process for annotations
  - `ignore_cell_value` (array): Values to ignore during processing
  - `max_iterations` (int): Maximum number of rows to process

- `ai_use`: Enable/disable AI services
  - `spacy` (bool): Enable spaCy for NLP tasks
  - `ollama` (bool): Enable Ollama for local AI processing
  - `gpt4all` (bool): Enable GPT4All service
  - `gpt4all_local` (bool): Enable local GPT4All

- `web_ui`: Web interface configuration
  - `enabled` (bool): Enable/disable web interface
  - `port` (int): Port number for web server (default: 5000)
  - `open_browser` (bool): Automatically open browser when starting

- `persist_cache` (bool): Enable caching of terminology service results (1 week validity)
- `persist_statistics` (bool): Enable collection of processing statistics
- `max_threads` (int): Maximum number of concurrent threads

### AI Service Configurations

Each enabled AI service requires its own configuration file:

- `config_ollama.json`: Ollama service configuration
- `config_gpt4all.json`: GPT4All service configuration
- `config_gpt4all_local.json`: Local GPT4All configuration

Sample configuration files are provided with the `_sample` suffix.

## Installation

Requires Python 3.8+

Depending on your system use `python` or `python3`, `pip` or `pip3`

```bash
# Install required packages
pip install pandas requests spacy gpt4all flask
# or
sudo apt install python3-pandas python3-requests python3-spacy python3-flask

# Install spaCy language models
python -m spacy download en_core_web_lg
python -m spacy download de_core_news_lg
```

Note: Use `--break-system-packages` on Linux only if needed.

### AI Service Dependencies

- For Ollama: Follow installation instructions at [Ollama's website](https://ollama.ai)
- For GPT4All: See [GPT4All Documentation](https://docs.gpt4all.io/index.html)
- For Web Interface: Flask is required for the web server functionality

## Usage

1. Configure your settings in `config.json`
2. Set up AI service configurations if enabled
3. Run the application:
   ```bash
   python main.py
   ```
4. If web UI is enabled:
   - Access the web interface at `http://localhost:<port>` (default: http://localhost:5000)
   - Choose between CSV annotation or interactive annotation modes
   - Process your content and view results in real-time

### Web Interface Features

The web UI provides two main modes:

1. CSV Annotation:
   - Process CSV files
   - View and edit (in later development state) annotations
   - View results

2. Interactive Annotation:
   - Real-time text input and processing
   - Immediate terminology matching
   - Interactive annotation editing
   - View processing statistics

### Output Files

When configured, the system generates:

- Annotated output file (specified in config.json)
- `cache.json`: Cached terminology service results
- `statistics.json`: Processing statistics including:
  - Identified noun phrases and annotations
  - Missed/declined annotations
  - Cache performance metrics
  - Validation results

## Performance Tips

- Thread Count:
  - On Mac: Set `max_threads` to match performance core count
  - Other systems: Use fewer threads than physical cores
  - Excessive threads can increase overhead and reduce performance

- Cache Usage:
  - Enable `persist_cache` for repeated runs with similar terminology sources
  - Cache entries expire after one week

## Development Status

Current as of 2025-03-20. Features and configurations may change in future updates.
