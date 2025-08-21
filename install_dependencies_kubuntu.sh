#!/bin/bash

# BITS Project - Dependency Installation Script
# This script installs all required Python packages and dependencies

echo "=== BITS Project - Installing Dependencies ==="
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "Python version: $PYTHON_VERSION"

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "Error: pip3 is not installed. Please install pip3 first."
    exit 1
fi

echo ""
echo "Installing Python packages via apt..."

# Install core Python packages via apt
echo "Installing pandas..."
sudo apt install -y python3-pandas

echo "Installing requests..."
sudo apt install -y python3-requests

echo "Installing spacy..."
echo "Note: python3-spacy not available via apt, installing via pip..."
pip3 install spacy --break-system-packages

echo "Installing flask..."
sudo apt install -y python3-flask

echo "Installing python-Levenshtein..."
sudo apt install -y python3-levenshtein

echo ""
echo "Installing packages that may not be available via apt..."

# Install packages that may not be available via apt
echo "Installing gpt4all..."
pip3 install gpt4all --break-system-packages

echo ""
echo "Installing spaCy language models..."

# Install spaCy language models
echo "Installing English language model (en_core_web_lg)..."
python3 -m spacy download en_core_web_lg --break-system-packages

echo "Installing German language model (de_core_news_lg)..."
python3 -m spacy download de_core_news_lg --break-system-packages

echo ""
echo "=== Installation Complete ==="
echo ""
echo "All required dependencies have been installed:"
echo "- pandas: For CSV file handling"
echo "- requests: For HTTP requests to TIB terminology service"
echo "- spacy: For NLP tasks and noun phrase extraction"
echo "- gpt4all: For local AI processing"
echo "- flask: For web interface"
echo "- python-Levenshtein: For string similarity matching"
echo "- spaCy language models: en_core_web_lg and de_core_news_lg"
echo ""
echo "Optional dependencies (if you plan to use them):"
echo "- Ollama: Follow installation instructions at https://ollama.ai"
echo ""
echo "You can now run the BITS project with: python3 main.py"
