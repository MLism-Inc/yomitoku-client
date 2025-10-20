# Yomitoku Client

<div align="center">

[![Language](https://img.shields.io/badge/🌐_English-blue?style=for-the-badge\&logo=github)](docs/en/README.md) [![Language](https://img.shields.io/badge/🌐_Japanese-red?style=for-the-badge\&logo=github)](README.md)

</div>

---

## Quick Links

* 📓 **[Sample Notebook: Using AWS SageMaker](notebooks/yomitoku-pro-document-analyzer.ipynb)** – Tutorial on connecting to an AWS SageMaker endpoint and performing document analysis
* 📓 **[Sample Notebook: Result Conversion & Visualization](notebooks/yomitoku-client-parser.ipynb)** – Tutorial on parsing, converting, and visualizing SageMaker results

**Yomitoku Client** is a Python library that processes the output from the **SageMaker Yomitoku API**, providing comprehensive format conversion and visualization tools.
It bridges the gap between **Yomitoku Pro OCR analysis** and practical data-processing workflows.

---

## Key Features

* **SageMaker Integration**: Seamless processing of Yomitoku Pro OCR results
* **Multi-Format Conversion**: Export results as CSV, Markdown, HTML, JSON, or PDF
* **Searchable PDF Generation**: Create searchable PDFs with OCR text overlays
* **Visualization Tools**: Render document layouts and OCR recognition results
* **Jupyter Notebook Support**: Ready-to-use sample code and workflows

---

## Supported Conversion Formats

* **CSV**: Export structured tabular data with accurate cell mapping
* **Markdown**: Structured document format including tables and headings
* **HTML**: Web-ready output with styling
* **JSON**: Full document structure in structured data form
* **PDF**: Generate searchable PDFs with OCR text overlays

---

## Installation

### Using pip

```bash
pip install yomitoku-client
```

### Using uv (recommended)

```bash
uv add yomitoku-client
```

> **Note:**
> If you don’t have **uv** installed, you can install it as follows:
>
> ```bash
> curl -LsSf https://astral.sh/uv/install.sh | sh
> ```

---

## Quick Start

### Step 1: Connect to the SageMaker Endpoint

```python
import boto3
import json

# Initialize the SageMaker runtime client
sagemaker_runtime = boto3.client('sagemaker-runtime')
ENDPOINT_NAME = 'your-yomitoku-endpoint'

# Initialize the parser
parser = SageMakerParser()

# Invoke the SageMaker endpoint with a document
with open('document.pdf', 'rb') as f:
    response = sagemaker_runtime.invoke_endpoint(
        EndpointName=ENDPOINT_NAME,
        ContentType='image/png',
        Body=f.read(),
    )

# Parse the response
body_bytes = response['Body'].read()
sagemaker_result = json.loads(body_bytes)
```

---

### Step 2: Convert Data into Different Formats

#### For Single-Page Documents (Images)

```python
from yomitoku_client.parsers import parse_pydantic_model

# Convert to structured data
data = parse_pydantic_model(sagemaker_result)

# Export to various formats
data.to_csv(output_path='output.csv')
data.to_html(output_path='output.html')
data.to_markdown(output_path='output.md')
data.to_json(output_path='output.json')
```

---

### Step 3: Visualize the Results

#### Visualizing a Single Image

```python
# Visualize OCR text
data.visualize(
    image_path='document.png',
    mode='ocr',
    page_index=None,
    output_directory='demo'
)

# Visualize layout details (text, tables, figures)
data.visualize(
    image_path='document.png',
    viz_type='layout',
    page_index=None,
    output_directory='demo'
)
```

---

#### Batch Visualization for Multi-Page PDFs

```python
# Visualize OCR results for all pages
data.visualize(
    image_path="sample/image.pdf",
    mode='ocr',
    page_index=None,
    output_directory="demo",
    dpi=200
)

# Visualize layout analysis for all pages
data.visualize(
    image_path="sample/image.pdf",
    mode='layout',
    page_index=None,
    output_directory="demo",
    dpi=200
)

# Visualize specific pages only
data.visualize(
    image_path="sample/image.pdf",
    mode='ocr',
    page_index=[0, 1],
    output_directory="demo",
    dpi=200
)
```

---

## License

Licensed under the **Apache License 2.0**.
See the [LICENSE](LICENSE) file for details.

---

## Contact

For questions or support:
📧 **[support-aws-marketplace@mlism.com](mailto:support-aws-marketplace@mlism.com)**