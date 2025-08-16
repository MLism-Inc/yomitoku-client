# Yomitoku Client - Notebook Environment

This directory contains Jupyter notebooks for demonstrating and experimenting with the Yomitoku Client library.

## Setup

### Option 1: Using the Setup Script (Recommended)

1. Run the setup script:
   ```bash
   ./setup-notebook-env.sh
   ```

2. Activate the environment:
   ```bash
   source notebooks-env/bin/activate
   ```

3. Start Jupyter:
   ```bash
   jupyter notebook
   # or
   jupyter lab
   ```

### Option 2: Manual Setup

1. Create a virtual environment:
   ```bash
   uv venv --python 3.9 notebooks-env
   ```

2. Activate the environment:
   ```bash
   source notebooks-env/bin/activate
   ```

3. Install dependencies:
   ```bash
   uv pip install -r notebooks-requirements.txt
   ```

4. Install the package in development mode:
   ```bash
   uv pip install -e .
   ```

5. Create Jupyter kernel:
   ```bash
   python -m ipykernel install --user --name=yomitoku-notebook --display-name="Yomitoku Client"
   ```

## Available Notebooks

### `yomitoku-client-example.ipynb`
A comprehensive example demonstrating:
- How to parse SageMaker Yomitoku API outputs
- Converting to different formats (CSV, Markdown, JSON)
- Data analysis and visualization
- Error handling
- Advanced usage examples

### `yomitoku-pro-document-analyzer.ipynb`
Original notebook from the reference implementation.

### `eda.ipynb`
Exploratory data analysis notebook.

## Environment Features

The notebook environment includes:

- **Core Dependencies**: pandas, numpy, matplotlib, plotly, pydantic
- **Jupyter Tools**: jupyter, ipykernel, notebook, jupyterlab
- **Visualization**: seaborn, plotly-express, bokeh
- **Document Processing**: python-docx, PyPDF2, openpyxl
- **Development Tools**: black, ruff

## Usage

1. Make sure you're in the notebook environment:
   ```bash
   source notebooks-env/bin/activate
   ```

2. Start Jupyter:
   ```bash
   jupyter notebook
   ```

3. Open any notebook and select the "Yomitoku Client" kernel

4. Run the cells to see the Yomitoku Client in action!

## Troubleshooting

### Kernel Not Found
If the "Yomitoku Client" kernel is not available:
```bash
source notebooks-env/bin/activate
python -m ipykernel install --user --name=yomitoku-notebook --display-name="Yomitoku Client"
```

### Import Errors
Make sure the package is installed in development mode:
```bash
source notebooks-env/bin/activate
uv pip install -e .
```

### Environment Issues
If you encounter environment issues, recreate the environment:
```bash
rm -rf notebooks-env
./setup-notebook-env.sh
```

## Examples

### Basic Usage
```python
from yomitoku_client import YomitokuClient

# Create client
client = YomitokuClient()

# Parse SageMaker output
data = client.parse_file('sagemaker_output.json')

# Convert to CSV
csv_result = client.convert_to_format(data, 'csv')

# Save to file
client.convert_to_format(data, 'markdown', 'output.md')
```

### CLI Usage
```bash
# Convert to CSV
yomitoku sagemaker_output.json --format csv --output result.csv

# Convert to Markdown
yomitoku sagemaker_output.json --format markdown --output result.md
```

## Contributing

When adding new notebooks:
1. Use the "Yomitoku Client" kernel
2. Include clear documentation and examples
3. Test all cells before committing
4. Add any new dependencies to `notebooks-requirements.txt`
