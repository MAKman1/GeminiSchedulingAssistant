#!/bin/bash

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Error: .env file not found. Please create one from .env.example."
    exit 1
fi

# Check if venv directory exists, if not create it
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating one..."
    python3 -m venv venv
fi

# Check if virtual environment is already activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "Virtual environment already activated."
fi

# Install dependencies
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

# Run the application
echo "Starting the Flask application..."
flask run
