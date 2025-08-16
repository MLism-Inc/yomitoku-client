#!/bin/bash

# Setup script for Yomitoku Client Notebook Environment

echo "Setting up Yomitoku Client Notebook Environment..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed. Please install uv first."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "notebooks-env" ]; then
    echo "Creating virtual environment..."
    uv venv --python 3.9 notebooks-env
fi

# Activate virtual environment
echo "Activating virtual environment..."
source notebooks-env/bin/activate

# Install dependencies
echo "Installing dependencies..."
uv pip install -r notebooks-requirements.txt

# Install the yomitoku-client package in development mode
echo "Installing yomitoku-client in development mode..."
uv pip install -e .

# Create Jupyter kernel
echo "Creating Jupyter kernel..."
python -m ipykernel install --user --name=yomitoku-notebook --display-name="Yomitoku Client"

echo "Notebook environment setup complete!"
echo ""
echo "To activate the environment:"
echo "  source notebooks-env/bin/activate"
echo ""
echo "To start Jupyter:"
echo "  jupyter notebook"
echo "  or"
echo "  jupyter lab"
echo ""
echo "The kernel 'Yomitoku Client' will be available in your notebooks."
