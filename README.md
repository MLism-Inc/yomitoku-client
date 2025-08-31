# Yomitoku Client

A Python client library for processing SageMaker Yomitoku API outputs with format conversion and visualization capabilities.

## Features

- **SageMaker Output Processing**: Parse and validate SageMaker Yomitoku API JSON outputs
- **Multiple Format Support**: Convert to CSV, Markdown, HTML, and JSON formats
- **Factory Pattern Design**: Extensible renderer system using factory pattern
- **Strategy Pattern**: Flexible format conversion strategies
- **CLI Interface**: Command-line tool for quick conversions
- **Type Safety**: Full type hints and Pydantic models for data validation

## Installation

```bash
# Using pip
pip install yomitoku-client

# Using uv (recommended)
uv add yomitoku-client
```

## Quick Start

### Basic Usage

```python
from yomitoku_client import YomitokuClient

# Initialize client
client = YomitokuClient()

# Parse SageMaker output
data = client.parse_file('sagemaker_output.json')

# Convert to different formats
csv_result = client.convert_to_format(data, 'csv')
md_result = client.convert_to_format(data, 'markdown')

# Save to files
client.convert_to_format(data, 'csv', 'output.csv')
client.convert_to_format(data, 'markdown', 'output.md')
```

### Command Line Interface

```bash
# Convert to CSV
yomitoku-client sagemaker_output.json --format csv --output result.csv

# Convert to Markdown
yomitoku-client sagemaker_output.json --format markdown --output result.md

# Ignore line breaks
yomitoku-client sagemaker_output.json --format csv --ignore-line-break
```

## Supported Formats

- **CSV**: Tabular data export with proper cell handling
- **Markdown**: Structured document format with tables and headings
- **HTML**: Web-ready format (basic implementation)
- **JSON**: Structured data export

## Architecture

The library uses several design patterns:

- **Factory Pattern**: `RendererFactory` manages different format renderers
- **Strategy Pattern**: Different conversion strategies for each format
- **Adapter Pattern**: Handles different input formats from SageMaker

## Development

### Setup

```bash
# Clone repository
git clone <repository-url>
cd yomitoku-client

# Install dependencies with uv
uv sync

# Run tests
uv run pytest
```

### Project Structure

```
yomitoku-client/
├── src/yomitoku_client/     # Source code
│   ├── parsers/            # SageMaker output parsers
│   ├── renderers/          # Format renderers (factory pattern)
│   ├── formatters/         # Format converters (strategy pattern)
│   ├── visualizers/        # Data visualization
│   └── client.py          # Main client class
├── tests/                  # Test suite
├── examples/              # Usage examples
└── pyproject.toml         # Project configuration
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Contact

For questions and support, please contact: support-aws-marketplace@mlism.com
