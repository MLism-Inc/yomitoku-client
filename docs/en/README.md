# Yomitoku Client

## Overview

Yomitoku Client is a Python library for processing SageMaker Yomitoku API outputs with comprehensive format conversion and visualization capabilities. It bridges the gap between Yomitoku Pro's OCR analysis and practical data processing workflows.

## Key Features

- **SageMaker Integration**: Seamlessly process Yomitoku Pro OCR results
- **Multiple Format Support**: Convert to CSV, Markdown, HTML, JSON, and PDF formats
- **Searchable PDF Generation**: Create searchable PDFs with OCR text overlay
- **Advanced Visualization**: Document layout analysis, element relationships, and confidence scores
- **Utility Functions**: Rectangle calculations, text processing, and image manipulation
- **Jupyter Notebook Support**: Ready-to-use examples and workflows

## Installation

### Using pip
```bash
# Install directly from GitHub
pip install git+https://github.com/MLism-Inc/yomitoku-client.git@main
```

### Using uv (Recommended)
```bash
# Install directly from GitHub
uv add git+https://github.com/MLism-Inc/yomitoku-client.git@main
```

> **Note**: If you don't have uv installed, you can install it with:
> ```bash
> curl -LsSf https://astral.sh/uv/install.sh | sh
> ```

## Quick Start

### Step 1: Connect to SageMaker Endpoint

```python
import boto3
import json
from yomitoku_client.parsers.sagemaker_parser import SageMakerParser

# Initialize SageMaker runtime client
sagemaker_runtime = boto3.client('sagemaker-runtime')
ENDPOINT_NAME = 'your-yomitoku-endpoint'

# Initialize parser
parser = SageMakerParser()

# Call SageMaker endpoint with your document
with open('document.pdf', 'rb') as f:
    response = sagemaker_runtime.invoke_endpoint(
        EndpointName=ENDPOINT_NAME,
        ContentType='application/pdf',  # or 'image/png', 'image/jpeg'
        Body=f.read(),
    )

# Parse the response
body_bytes = response['Body'].read()
sagemaker_result = json.loads(body_bytes)

# Convert to structured data
data = parser.parse_dict(sagemaker_result)

print(f"Found {len(data.pages)} pages")
print(f"Page 1 has {len(data.pages[0].paragraphs)} paragraphs")
print(f"Page 1 has {len(data.pages[0].tables)} tables")

# Access specific page (page_index: 0=first page)
page_index = 0  # First page
print(f"Specified page has {len(data.pages[page_index].paragraphs)} paragraphs")
```

### Step 2: Convert Data to Different Formats

#### Single Page Documents (Images)

```python
# Convert to different formats (page_index: 0=first page)
data.to_csv('output.csv', page_index=0)
data.to_html('output.html', page_index=0)
data.to_markdown('output.md', page_index=0)
data.to_json('output.json', page_index=0)

# Create searchable PDF from image
data.to_pdf(output_path='searchable.pdf', img='document.png')
```

#### Multi-page Documents (PDFs)

```python
# Convert all pages (creates folder structure)
data.to_csv_folder('csv_output/')
data.to_html_folder('html_output/')
data.to_markdown_folder('markdown_output/')
data.to_json_folder('json_output/')

# Create searchable PDF (enhances existing PDF with searchable text)
data.to_pdf(output_path='enhanced.pdf', pdf='original.pdf')

# Or convert individual pages (page_index: 0=first page, 1=second page)
data.to_csv('page1.csv', page_index=0)  # First page
data.to_html('page2.html', page_index=1)  # Second page
```

#### Table Data Extraction

```python
# Export tables in various formats (page_index: 0=first page)
data.export_tables(
    output_folder='tables/',
    output_format='csv',    # or 'html', 'json', 'text'
    page_index=0
)

# For multi-page documents
data.export_tables(
    output_folder='all_tables/',
    output_format='csv'
)

# Export tables from specific page only
data.export_tables(
    output_folder='page1_tables/',
    output_format='csv',
    page_index=0  # First page
)

# For multi-page documents
data.visualize_tables(
    output_folder='all_tables/',
    output_format='csv'
)
```

### Step 3: Visualize Results

#### Single Image Visualization

```python
# OCR text visualization
result_img = data.pages[0].visualize(
    image_path='document.png',
    viz_type='ocr',
    output_path='ocr_visualization.png'
)

# Layout detail visualization (text, tables, figures)
result_img = data.pages[0].visualize(
    image_path='document.png',
    viz_type='layout_detail',
    output_path='layout_visualization.png'
)
```

#### Batch Image Visualization

```python
# Batch visualize OCR results for all pages (saved as 0.png, 1.png, 2.png...)
data.export_viz_images(
    image_path='document.pdf',
    folder_path='ocr_results/',
    viz_type='ocr'
)

# Batch visualize layout details for all pages
data.export_viz_images(
    image_path='document.pdf',
    folder_path='layout_results/',
    viz_type='layout_detail'
)

# Visualize specific page only
data.export_viz_images(
    image_path='document.pdf',
    folder_path='page1_results/',
    viz_type='layout_detail',
    page_index=0  # First page only
)
```

#### PDF Visualization

```python
# Visualize specific PDF page
result_img = data.pages[0].visualize(
    image_path='document.pdf',
    viz_type='layout_detail',
    output_path='pdf_visualization.png',
    page_index=0  # Specify which page to visualize
)
```

## Notebook Examples

### 1. Yomitoku Pro Document Analyzer (`yomitoku-pro-document-analyzer.ipynb`)

This notebook shows how to:
- Deploy Yomitoku Pro service
- Configure SageMaker endpoints
- Run OCR analysis on documents
- Get structured JSON results

**Key sections:**
- Service deployment (CloudFormation/SageMaker Console)
- Endpoint configuration
- Document processing workflow
- Result extraction and validation

### 2. Yomitoku Client Examples (`yomitoku-client-example.ipynb`)

This notebook demonstrates:
- Parsing SageMaker outputs
- Format conversion (CSV, HTML, Markdown, JSON)
- Document visualization
- Advanced processing workflows

**Key sections:**
- Client initialization and setup
- Sample data processing
- Multi-format conversion
- Visualization techniques
- Utility function usage

## Data Transformation and Visualization

### Format Conversion

Yomitoku Client provides comprehensive format conversion capabilities:

```python
# Single page conversion
data.pages[0].to_csv('output.csv')
data.pages[0].to_html('output.html')
data.pages[0].to_markdown('output.md')
data.pages[0].to_json('output.json')

# Multi-page document conversion (creates folder structure)
data.to_csv_folder('csv_output/')
data.to_html_folder('html_output/')
data.to_markdown_folder('markdown_output/')
data.to_json_folder('json_output/')
```

### Searchable PDF Generation

Create searchable PDFs with OCR text overlay:

```python
# From image
data.to_pdf(output_path='searchable.pdf', img='document.png')

# From PDF (enhances existing PDF with searchable text)
data.to_pdf(output_path='enhanced.pdf', pdf='original.pdf')
```

### Visualization

Visualize OCR results with bounding boxes and layout analysis:

```python
# OCR text visualization
result_img = data.pages[0].visualize(
    image_path='document.png',
    viz_type='ocr',
    output_path='ocr_visualization.png'
)

# Layout detail visualization (text, tables, figures)
result_img = data.pages[0].visualize(
    image_path='document.png',
    viz_type='layout_detail',
    output_path='layout_visualization.png'
)

# PDF visualization (specify page index)
result_img = data.pages[0].visualize(
    image_path='document.pdf',
    viz_type='layout_detail',
    output_path='pdf_visualization.png',
    page_index=0
)
```

### Table Processing

Extract and visualize table data in multiple formats:

```python
# Export tables in various formats
data.pages[0].visualize_tables(
    output_folder='tables/',
    output_format='csv'    # or 'html', 'json', 'text'
)

# For multi-page documents
data.visualize_tables(
    output_folder='all_tables/',
    output_format='csv'
)
```

## Supported Formats

- **CSV**: Tabular data export with proper cell handling
- **Markdown**: Structured document format with tables and headings
- **HTML**: Web-ready format with proper styling
- **JSON**: Structured data export with full document structure
- **PDF**: Searchable PDF generation with OCR text overlay

## Command Line Interface

```bash
# Convert to different formats
yomitoku-client sagemaker_output.json --format csv --output result.csv
yomitoku-client sagemaker_output.json --format html --output result.html
yomitoku-client sagemaker_output.json --format markdown --output result.md
```

## Architecture

The library uses several design patterns:
- **Factory Pattern**: `RendererFactory` manages different format renderers
- **Strategy Pattern**: Different conversion strategies for each format
- **Adapter Pattern**: Handles different input formats from SageMaker

## Development

```bash
# Clone repository
git clone https://github.com/MLism-Inc/yomitoku-client
cd yomitoku-client

# Install dependencies
uv sync

# Run tests
uv run pytest
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

Apache License 2.0 - see LICENSE file for details.

## Contact

For questions and support: support-aws-marketplace@mlism.com
