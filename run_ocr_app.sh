#!/bin/bash

# Script to run the OCR application

# Change to the smart-invoice-auditor directory
cd "$(dirname "$0")/smart-invoice-auditor" || {
    echo "Error: Cannot find smart-invoice-auditor directory"
    exit 1
}

# Verify Python is available
if ! command -v python &> /dev/null; then
    echo "Error: Python is not installed or not in PATH"
    exit 1
fi

# Run the application
echo "Starting OCR application..."
echo "Once started, open your browser to http://127.0.0.1:7860"
python app.py

# This script will terminate when the application is closed 