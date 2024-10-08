#!/bin/bash

# Ensure Python 3 and pip are installed
echo "Checking if Python 3 and pip are installed..."
if ! command -v python3 &>/dev/null || ! command -v pip3 &>/dev/null; then
    echo "Python3 or pip3 is not installed. Please install them before proceeding."
    exit 1
fi

# Create virtual environment (optional but recommended)
echo "Creating a virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies from requirements.txt
echo "Installing dependencies..."
pip install -r requirements.txt

# Inform the user about activating the virtual environment
echo "Setup complete! To activate the virtual environment, use:"
echo "source venv/bin/activate"
