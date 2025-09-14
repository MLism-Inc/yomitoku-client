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

```bash
# Install from PyPI (includes PDF support by default)
pip install yomitoku-client

# Install from GitHub (latest features)
pip install git+https://github.com/MLism-Inc/yomitoku-client.git@main
```

## Quick Start

### Step 1: Get OCR Results from Yomitoku Pro

First, you need to deploy Yomitoku Pro and get OCR results. See the `yomitoku-pro-document-analyzer.ipynb` notebook for detailed instructions on:

1. **Deploying Yomitoku Pro** using CloudFormation or SageMaker Console
2. **Creating endpoints** and configuring permissions
3. **Running OCR analysis** on your documents
4. **Getting structured results** in JSON format

### Step 2: Process Results with Yomitoku Client

Once you have OCR results from Yomitoku Pro, use Yomitoku Client to process and convert them:

```python
from yomitoku_client import YomitokuClient

# Initialize client
client = YomitokuClient()

# Parse SageMaker output (from Yomitoku Pro)
data = client.parse_file('sagemaker_output.json')

# Convert to different formats
csv_result = client.convert_to_format(data, 'csv')
html_result = client.convert_to_format(data, 'html')
markdown_result = client.convert_to_format(data, 'markdown')

# Save to files
client.convert_to_format(data, 'csv', 'output.csv')
client.convert_to_format(data, 'html', 'output.html')
```

### Step 3: Advanced Processing and Visualization

```python
# Enhanced document visualization
from yomitoku_client.visualizers import DocumentVisualizer

doc_viz = DocumentVisualizer()

# Element relationships visualization
rel_img = doc_viz.visualize_element_relationships(
    image, results, 
    show_overlaps=True, 
    show_distances=True
)

# Element hierarchy visualization
hierarchy_img = doc_viz.visualize_element_hierarchy(
    image, results, 
    show_containment=True
)

# Confidence scores visualization
confidence_img = doc_viz.visualize_confidence_scores(
    image, ocr_results, 
    show_ocr_confidence=True
)
```

### Step 4: Searchable PDF Generation

```python
from yomitoku_client.pdf_generator import SearchablePDFGenerator

# Create searchable PDF from images and OCR results
pdf_generator = SearchablePDFGenerator()
pdf_generator.create_searchable_pdf(images, ocr_results, 'output.pdf')
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

MIT License - see LICENSE file for details.

## Contact

For questions and support: support-aws-marketplace@mlism.com
