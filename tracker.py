#!/bin/bash

# Ensure Python 3, pip, and git are installed
echo "Checking if Python 3, pip, and git are installed..."
if ! command -v python3 &>/dev/null || ! command -v pip3 &>/dev/null || ! command -v git &>/dev/null; then
    echo "Python3, pip3, or git is not installed. Please install them before proceeding."
    exit 1
fi

# Install SQLite if not already installed
echo "Checking for SQLite installation..."
if ! command -v sqlite3 &>/dev/null; then
    echo "SQLite is not installed. Installing SQLite..."
    sudo apt-get update
    sudo apt-get install sqlite3 -y
else
    echo "SQLite is already installed."
fi

# Clone the program from GitHub
echo "Cloning program from GitHub..."
if [ -d "DRGTracker" ]; then
    echo "Directory 'DRGTracker' already exists. Pulling latest changes..."
    cd DRGTracker && git pull
else
    git clone https://github.com/Manayethas/DRGTracker.git
    cd DRGTracker
fi

# Create a virtual environment (optional but recommended)
echo "Creating a virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies from requirements.txt
echo "Installing dependencies..."
pip install -r requirements.txt

# Inform the user about activating the virtual environment
echo "Setup complete! To activate the virtual environment, use:"
echo "source venv/bin/activate"
