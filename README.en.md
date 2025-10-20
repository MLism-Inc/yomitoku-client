# Yomitoku Client

<div align="center">

[![Language](https://img.shields.io/badge/🌐_English-blue?style=for-the-badge\&logo=github)](README.en.md) [![Language](https://img.shields.io/badge/🌐_Japanese-red?style=for-the-badge\&logo=github)](README.md)

</div>

---

## Quick Links

* 📓 **[Sample Notebook](notebooks/yomitoku-pro-document-analyzer.ipynb)** – Tutorial on connecting to an AWS SageMaker endpoint and performing document analysis

**Yomitoku Client** is a Python library that processes the output from the **SageMaker Yomitoku API**, providing comprehensive format conversion and visualization capabilities.
It bridges **Yomitoku Pro OCR analysis** with practical data-processing workflows.

---

## Key Features

* **Automatic Content-Type Detection**: Automatically recognizes PDF, TIFF, PNG, and JPEG and processes them in the optimal format.
* **Page Splitting & Asynchronous Parallel Processing**: Automatically splits multi-page PDF/TIFF files and runs inference for each page in parallel.
* **Timeout Control**: Safely manages communication and total processing time with `connect_timeout`, `read_timeout`, and `total_timeout`.
* **Retry & Circuit-Breaker Mechanism**: Automatically retries transient failures and temporarily pauses requests after consecutive failures to protect the endpoint.
* **Robust Error Handling**: Unified handling of AWS communication errors, JSON decoding issues, and timeouts.
* **Secure AWS Authentication with MFA**: Supports temporary session tokens for secure endpoint connections.
* **Simple Interface**: Execute `client("document.pdf")` to automatically perform page splitting, inference, and result aggregation.
* **Multi-Format Conversion**: Export results to CSV, Markdown, HTML, JSON, or PDF.
* **Searchable PDF Generation**: Create searchable PDFs with OCR text overlays.
* **Visualization Tools**: Render document layouts and OCR reading results.
* **Jupyter Notebook Support**: Ready-to-use sample code and workflows for rapid prototyping.

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
> If `uv` is not installed, you can install it as follows:
>
> ```bash
> curl -LsSf https://astral.sh/uv/install.sh | sh
> ```

---

## Quick Start

### Calling a SageMaker Endpoint

```python
from yomitoku_client import YomitokuClient

target_file = TARGET_FILE

with YomitokuClient(
    endpoint=ENDPOINT_NAME,
    region=AWS_REGION,
    mfa_serial=MFA_SERIAL,
    mfa_token=MFA_TOKEN,
) as client:
    result = client(target_file)
```

---

### Converting OCR Results to Various Formats

```python
result.to_markdown(output_path="output.md")
result.to_csv(output_path="output.csv")
result.to_json(output_path="output.json")
result.to_html(output_path="output.html")
```

---

### Visualizing Analysis Results

```python
result.visualize(
    image_path=target_file,
    mode='ocr',
    page_index=None,
    output_directory="demo",
)

data.visualize(
    image_path="sample/image.pdf",
    mode='layout',
    page_index=None,
    output_directory="demo",
)
```

---

## License

Licensed under the **Apache License 2.0**.
See the [LICENSE](LICENSE) file for details.

---

## Contact

For questions or support, please contact:
📧 **[support-aws-marketplace@mlism.com](mailto:support-aws-marketplace@mlism.com)**
