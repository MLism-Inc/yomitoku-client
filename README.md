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
# Install from PyPI (includes PDF support by default)
pip install yomitoku-client

# Install from GitHub (latest features)
pip install git+https://github.com/MLism-Inc/yomitoku-client.git@main
```

### Using uv (Recommended)
```bash
# Install from PyPI using uv
uv add yomitoku-client

# Install from GitHub using uv
uv add git+https://github.com/MLism-Inc/yomitoku-client.git@main

# For development (includes dev dependencies)
uv sync --dev

# Run with uv
uv run python your_script.py
```

> **Note**: If you don't have uv installed, you can install it with:
> ```bash
> curl -LsSf https://astral.sh/uv/install.sh | sh
> ```

## Quick Start

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