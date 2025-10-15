#!/bin/bash
# Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
# Setup script for PCB Design Agent System

# Create virtual environment
echo "Creating virtual environment..."
python -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create output directory
echo "Creating output directory..."
mkdir -p output

echo "Setup complete!"
echo "To use the system, run:"
echo "source venv/bin/activate"
echo "python pcb_design_system.py --requirements-text 'Your PCB requirements here'"
echo ""
echo "For more options, run:"
echo "python pcb_design_system.py --help"