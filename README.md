# FAIRenrich - FAIR Enrichment and Curation for ESS and Biodiversity Data

A comprehensive system for automated terminology annotation and enrichment using multiple AI services and the TIB terminology service. The tool supports both batch processing of CSV files and interactive web-based annotation with semantic similarity matching.

## Overview

FAIRenrich (Biodiversity and ESS Terminology Service) is designed to automatically identify and annotate terms in text content using semantic similarity matching against various terminology sources. The system integrates multiple AI services for noun phrase recognition and provides a flexible web interface for interactive annotation.

## Key Features

- **Multi-language Support**: English and German text processing with language-specific models
- **Multiple AI Services**: 
  - spaCy for NLP tasks and noun phrase extraction
  - Ollama for local AI processing
  - GPT4All (both local and service-based)
- **Terminology Matching**: Integration with TIB terminology service for semantic similarity matching
- **Thread-safe Processing**: Multi-threaded architecture for improved performance
- **Caching System**: Persistent caching of terminology service results
- **Web Interface**: Interactive Flask-based web UI for real-time annotation
- **Batch Processing**: CSV file processing with configurable validation
- **Statistics Collection**: Comprehensive processing statistics and performance metrics

## Architecture

The system follows a modular architecture with specialized helper classes:

### Core Modules
- `main.py`: Main entry point and workflow orchestration
- `helper/text_helper.py`: Text processing and noun phrase recognition
- `helper/bits_helper.py`: TIB terminology service integration
- `helper/annotation_helper.py`: Annotation processing and result formatting
- `helper/file_handler.py`: File I/O and configuration management
- `helper/cache.py`: Thread-safe caching system
- `helper/statistics_helper.py`: Statistics collection and reporting
- `helper/validator.py`: Data validation and integrity checking
- `ui/web_ui.py`: Web interface and API endpoints

### Data Flow
1. **Input Processing**: CSV files are loaded and parsed
2. **Text Analysis**: Noun phrases are extracted using AI services
3. **Terminology Matching**: Extracted phrases are matched against terminology sources
4. **Annotation**: Results are applied to the original content
5. **Validation**: Data integrity is verified
6. **Export**: Annotated results are exported to CSV

## Configuration

### Main Configuration (`config.json`)

- `version` (float): Configuration version (current: 0.4)
  *Don't change this manually.*

#### Annotation Settings
- `input_file`: Path to input CSV file
- `output_file`: Path for annotated output CSV
- `perform_export`: Enable/disable export of annotated file
- `perform_validation`: Enable/disable validation of annotations
- `ts_sources`: Terminology source configuration
  - `explicit_terminologies`: List of specific terminologies or "False"
  - `collection`: BITS TS collection name or "False"
- `relevant_fields`: Columns to process for annotations
- `ignore_cell_value`: Values to ignore during processing
- `max_iterations`: Maximum number of rows to process

#### AI Services
- `spacy`: Enable spaCy for NLP tasks
- `ollama`: Enable Ollama for local AI processing
- `gpt4all`: Enable GPT4All service
- `gpt4all_local`: Enable local GPT4All

#### Web Interface
- `enabled`: Enable/disable web interface
- `port`: Port number for web server (default: 5001)
- `open_browser`: Automatically open browser when starting

**Note for macOS users**: Port 5000 is used by AirPlay on macOS. Use port 5001 or another available port.

#### Performance Settings
- `persist_cache`: Enable caching of terminology service results (1 week validity)
- `persist_statistics`: Enable collection of processing statistics
- `max_threads`: Maximum number of concurrent threads

### AI Service Configurations

Each enabled AI service requires its own configuration file:
- `config_ollama.json`: Ollama service configuration
- `config_gpt4all.json`: GPT4All service configuration
- `config_gpt4all_local.json`: Local GPT4All configuration

Sample configuration files are provided with the `_sample` suffix.

## Installation

### Requirements
- Python 3.8+
- Required packages: pandas, requests, spacy, gpt4all, flask

### Setup Instructions

```bash
# Install required packages
pip install pandas requests spacy gpt4all flask

# Install spaCy language models
python -m spacy download en_core_web_lg
python -m spacy download de_core_news_lg
```

### AI Service Dependencies

- **Ollama**: Follow installation instructions at [Ollama's website](https://ollama.ai)
- **GPT4All**: See [GPT4All Documentation](https://docs.gpt4all.io/index.html)
- **Web Interface**: Flask is required for the web server functionality

## Usage

### Command Line Usage

1. Configure your settings in `config.json`
2. Set up AI service configurations if enabled
3. Run the application:
   ```bash
   python main.py
   ```

### Web Interface

If web UI is enabled:
- Access the web interface at `http://localhost:<port>` (default: http://localhost:5001)
- Choose between CSV annotation or interactive annotation modes
- Process your content and view results in real-time

#### Web Interface Features

The web UI provides two main modes:

1. **CSV Annotation**:
   - Process CSV files
   - View and edit (in later development state) annotations
   - Export results

2. **Interactive Annotation**:
   - Real-time text input and processing
   - Immediate terminology matching
   - Interactive annotation editing
   - View processing statistics

## Output Files

When configured, the system generates:

- **Annotated output file**: Specified in config.json
- `cache.json`: Cached terminology service results
- `statistics.json`: Processing statistics including:
  - Identified noun phrases and annotations
  - Missed/declined annotations
  - Cache performance metrics
  - Validation results

## Performance Optimization

### Thread Configuration
- **Mac**: Set `max_threads` to match performance core count
- **Other systems**: Use fewer threads than physical cores
- **Note**: Excessive threads can increase overhead and reduce performance

### Cache Usage
- Enable `persist_cache` for repeated runs with similar terminology sources
- Cache entries expire after one week
- Cache significantly improves performance for repeated queries

### AI Service Selection
- **spaCy**: Fastest for basic noun phrase extraction
- **GPT4All Local**: Good balance of speed and accuracy
- **Ollama**: Flexible local AI processing
- **GPT4All Service**: Highest accuracy but slower

## Development Status

Current version: 0.4 (as of 2025-07-20)

### Recent Updates
- Enhanced web interface with interactive annotation
- Improved caching system with persistence
- Comprehensive statistics collection
- Multi-language support (English/German)
- Thread-safe processing architecture

### Planned Features
- Additional terminology sources
- Enhanced validation capabilities
- Improved web interface functionality
- Extended AI service integrations

## Contributing

When contributing to this project, please ensure:

1. **Documentation**: All new code includes comprehensive docstrings
2. **Type hints**: Use type annotations for all function parameters and return values
3. **Examples**: Include usage examples in docstrings for complex methods
4. **Error handling**: Document exceptions and error conditions
5. **Testing**: Add tests for new functionality

### Documentation Standards

- Use Google-style docstrings
- Include parameter types and descriptions
- Document return values and exceptions
- Provide usage examples for complex methods
- Maintain consistency across all modules

### Code Style

- Follow PEP 8 guidelines
- Use meaningful variable and function names
- Include comprehensive error handling
- Add logging for debugging and monitoring
- Use type hints throughout the codebase

## Support

For issues, questions, or contributions, please refer to the project documentation or contact the development team.
