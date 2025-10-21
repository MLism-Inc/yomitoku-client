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
    image_path=target_file,
    mode='layout',
    page_index=None,
    output_directory="demo",
)
```

## Batch Processing

**YomiTokuClient** also supports batch processing, enabling safe and efficient analysis of a large number of documents.

### Key Features

* **Folder-level batch analysis**: Automatically detects PDF and image files in the specified directory and performs parallel processing.
* **Intermediate log output (`process_log.jsonl`)**: Records processing results, success/failure status, elapsed time, and errors for each file as JSON Lines.
  The log file can be reused for post-processing or reruns.
* **Overwrite control**: Skips already processed files when `overwrite=False`, improving efficiency.
* **File name collision prevention**: Files with the same name but different extensions are saved as `_pdf.json`, `_png.json`, etc., to avoid overwriting.
* **Rerun support**: Failed files can be easily reprocessed based on the log records.
* **Post-processing via logs**: By reading `process_log.jsonl`, you can automatically export Markdown files or visualize results only for successful items.

### Example

```python
import asyncio
import json
import os

from yomitoku_client import YomitokuClient
from yomitoku_client.parsers.sagemaker_parser import parse_pydantic_model

# Input / output settings
target_dir = "notebooks/sample"
outdir = "output"

# SageMaker endpoint settings
ENDPOINT_NAME = "my-endpoint"
AWS_REGION = "ap-northeast-1"

async def main():
    # Run batch analysis
    async with YomitokuClient(
        endpoint=ENDPOINT_NAME,
        region=AWS_REGION,
    ) as client:
        await client.analyze_batch_async(
            input_dir=target_dir,
            output_dir=outdir,
        )

    # Process successful files based on logs
    with open(os.path.join(outdir, "process_log.jsonl"), "r", encoding="utf-8") as f:
        logs = [json.loads(line) for line in f if line.strip()]

    out_markdown = os.path.join(outdir, "markdown")
    out_visualize = os.path.join(outdir, "visualization")
    os.makedirs(out_markdown, exist_ok=True)
    os.makedirs(out_visualize, exist_ok=True)

    for log in logs:
        if not log.get("success"):
            continue

        # Load the analysis result
        with open(log["output_path"], "r", encoding="utf-8") as rf:
            result = json.load(rf)

        doc = parse_pydantic_model(result)

        # Export as Markdown
        base = os.path.splitext(os.path.basename(log["file_path"]))[0]
        doc.to_markdown(output_path=os.path.join(out_markdown, f"{base}.md"))

        # Visualize OCR results
        doc.visualize(
            image_path=log["file_path"],
            mode="ocr",
            output_directory=out_visualize,
            dpi=log.get("dpi", 200),
        )

if __name__ == "__main__":
    asyncio.run(main())
```

> 💡 *Tip:*
> The batch mode is ideal for large-scale offline document processing.
> The `process_log.jsonl` file provides a complete record of the batch run and can be reused for monitoring, recovery, or post-processing.


## License

Licensed under the **Apache License 2.0**.
See the [LICENSE](LICENSE) file for details.



## Contact

For questions or support, please contact:
📧 **[support-aws-marketplace@mlism.com](mailto:support-aws-marketplace@mlism.com)**
