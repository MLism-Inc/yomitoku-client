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

# Install core dependencies first
echo "Installing core dependencies..."
uv pip install -r notebooks-requirements.txt

# Install the yomitoku-client package in development mode (without streamlit)
echo "Installing yomitoku-client core package..."
uv pip install --no-deps -e .

# Install only the core dependencies that don't require compilation
echo "Installing core yomitoku-client dependencies..."
uv pip install pydantic requests python-dotenv click

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
echo ""
echo "Note: This environment includes core functionality without streamlit/pyarrow dependencies."
