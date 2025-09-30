# Yomitoku Client

<div align="center">

[![Language](https://img.shields.io/badge/🌐_English-blue?style=for-the-badge&logo=github)](docs/en/README.md) [![Language](https://img.shields.io/badge/🌐_日本語-red?style=for-the-badge&logo=github)](docs/ja/README.md)

**Click the buttons above to view documentation in your preferred language**

</div>

---

## Quick Links

- 📖 **[English Documentation](docs/en/README.md)** - Complete guide in English
- 📖 **[日本語ドキュメント](docs/ja/README.md)** - 日本語での完全ガイド
- 📓 **[Notebook Guide (English)](docs/en/NOTEBOOK_GUIDE.md)** - Step-by-step notebook tutorials
- 📓 **[ノートブックガイド (日本語)](docs/ja/NOTEBOOK_GUIDE.md)** - ステップバイステップのノートブックチュートリアル

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
pip install yomitoku-client
```

### Using uv (Recommended)
```bash
uv add yomitoku-client
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
```

### Step 2: Convert Data to Different Formats

#### Single Page Documents (Images)

```python
# Convert to different formats
data.pages[0].to_csv('output.csv')
data.pages[0].to_html('output.html')
data.pages[0].to_markdown('output.md')
data.pages[0].to_json('output.json')

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

# Or convert individual pages
data.pages[0].to_csv('page1.csv')
data.pages[1].to_html('page2.html')
```

#### Table Data Extraction

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

### Step 3: Visualize Results

#### OCR Text Visualization

```python
# Show detected text with bounding boxes
result_img = data.pages[0].visualize(
    image_path='document.png',
    viz_type='ocr',
    output_path='ocr_visualization.png'
)
```

#### Layout Analysis Visualization

```python
# Show document structure (text, tables, figures)
result_img = data.pages[0].visualize(
    image_path='document.png',
    viz_type='layout_detail',
    output_path='layout_visualization.png'
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

## Supported Formats

- **CSV**: Tabular data export with proper cell handling
- **Markdown**: Structured document format with tables and headings
- **HTML**: Web-ready format with proper styling
- **JSON**: Structured data export with full document structure
- **PDF**: Searchable PDF generation with OCR text overlay

## License

MIT License - see LICENSE file for details.

## Contact

For questions and support: support-aws-marketplace@mlism.com