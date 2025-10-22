# Yomitoku Client

<div align="center">

[![Language](https://img.shields.io/badge/🌐_English-blue?style=for-the-badge\&logo=github)](README.en.md) [![Language](https://img.shields.io/badge/🌐_日本語-red?style=for-the-badge\&logo=github)](README.md)

</div>

**Yomitoku Client** is a Python client library for handling outputs from the **Yomitoku Pro API** on **AWS SageMaker**. It converts OCR results into structured data and makes it easy to save and visualize them in formats such as CSV, JSON, Markdown, and PDF.
It serves as a “bridge” between Yomitoku Pro’s high-accuracy OCR and your business applications.

## Key Features

* **Automatic content-type detection**: Automatically recognizes PDF / TIFF / PNG / JPEG and processes them with optimal settings.
* **Page splitting & async parallelization**: Automatically splits multi-page PDF/TIFF and runs inference on each page in parallel.
* **Timeouts & retries**: `connect_timeout`, `read_timeout`, and `total_timeout` safely control network/overall processing. Temporary failures are retried with exponential backoff.
* **Circuit breaker**: Pauses requests after consecutive failures to protect the endpoint.
* **Robust error handling**: Centralized handling for AWS communication errors, JSON decode errors, timeouts, and more.
* **MFA-enabled AWS authentication**: Secure endpoint access via temporary session tokens.
* **Simple interface**: `client("document.pdf")` performs page splitting, inference, and result aggregation automatically.
* **Multiple output formats**: Convert to CSV / JSON / Markdown / HTML / PDF.
* **Searchable PDF generation**: Produce searchable PDFs with OCR text overlays.
* **Visualization**: Render document layout analysis and OCR reading results.
* **Jupyter Notebook support**: Quick-start sample code and workflows included.

## Quick Links

* 📓 **[Sample Notebook](notebooks/yomitoku-pro-document-analyzer.ipynb)** — Tutorial on connecting to an AWS SageMaker endpoint and analyzing documents

## What is YomiToku-Pro Document Analyzer?

**YomiToku-Pro Document Analyzer** is a SageMaker endpoint offered on the AWS Marketplace.

* Performs fast and accurate text recognition and document layout analysis for Japanese documents.
* Models are trained specifically for Japanese document images, supporting recognition of over 7,000 Japanese characters. They can also handle handwriting, vertical writing, and other Japanese-specific layouts. (English documents are also supported.)
* With layout analysis, table structure analysis, and reading-order estimation, it extracts information while preserving the semantic layout of documents.
* **Page rotation correction**: Estimates page rotation and automatically corrects orientation before analysis.
* A dedicated SageMaker endpoint is created within each customer’s AWS account, and data is processed entirely within the AWS region. Nothing is sent to external servers or third parties, enabling highly secure and compliant document analysis.

## Installation

### Using pip

```bash
pip install yomitoku-client
```

### Using uv (recommended)

```bash
uv add yomitoku-client
```

> **Note**: If `uv` is not installed:
>
> ```bash
> curl -LsSf https://astral.sh/uv/install.sh | sh
> ```

## Quick Start

### Calling a SageMaker Endpoint

```python
from yomitoku_client import YomitokuClient

ENDPOINT_NAME = "my-endpoint"
AWS_REGION = "ap-northeast-1"
MFA_SERIAL = None
MFA_TOKEN = input("MFA Token: ") if MFA_SERIAL is not None else None

target_file = "notebooks/sample/image.pdf"

async def main():
    async with YomitokuClient(
        endpoint=ENDPOINT_NAME,
        region=AWS_REGION,
        mfa_serial=MFA_SERIAL,
        mfa_token=MFA_TOKEN,
    ) as client:
        result = await client.analyze_async(target_file)
```

### Converting OCR Results

```python
from yomitoku_client import parse_pydantic_model

model = parse_pydantic_model(result)

model.to_csv(output_path="output.csv")  # Save as CSV
model.to_markdown(output_path="output.md", image_path=target_file)  # Save as Markdown
model.to_json(output_path="output.json", mode="separate")  # Save per page (mode="separate")
model.to_html(output_path="output.html", image_path=target_file, page_index=[0, 2])  # Output subset of pages
model.to_pdf(output_path="output.pdf", image_path=target_file)  # Output as Searchable PDF
```

### Visualizing Analysis Results

```python
# Save visualization of OCR results
model.visualize(
    image_path=target_file,
    mode='ocr',
    page_index=None,
    output_directory="demo",
)

# Save visualization of layout analysis
model.visualize(
    image_path=target_file,
    mode='layout',
    page_index=None,
    output_directory="demo",
)
```

## Batch Processing

**YomitokuClient** also supports batch processing, enabling safe and efficient analysis of large document sets.

### Highlights

* **Bulk analysis by folder**: Automatically discovers PDF/image files in a target directory and processes them in parallel.
* **Intermediate log output (`process_log.jsonl`)**: Records per-file status, success/failure, processing time, and error details as JSON Lines, which is useful for post-processing and reruns.
* **Overwrite control**: Skip already-processed files with `overwrite=False` for efficiency.
* **Reruns**: Easily re-analyze only failed files based on the log.
* **Log-driven post-processing**: Load `process_log.jsonl` to automatically export Markdown or visualizations for successful files.

### Sample Code

```python
import asyncio
import json
import os

from yomitoku_client import YomitokuClient
from yomitoku_client import parse_pydantic_model

# I/O settings
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

    # Post-process only successful files from the log
    with open(os.path.join(outdir, "process_log.jsonl"), "r", encoding="utf-8") as f:
        logs = [json.loads(line) for line in f if line.strip()]

    out_markdown = os.path.join(outdir, "markdown")
    out_visualize = os.path.join(outdir, "visualization")

    os.makedirs(out_markdown, exist_ok=True)
    os.makedirs(out_visualize, exist_ok=True)

    for log in logs:
        if not log.get("success"):
            continue

        # Load the JSON result produced during batch analysis
        with open(log["output_path"], "r", encoding="utf-8") as rf:
            result = json.load(rf)

        doc = parse_pydantic_model(result)

        # Export as Markdown
        base = os.path.splitext(os.path.basename(log["file_path"]))[0]
        doc.to_markdown(output_path=os.path.join(out_markdown, f"{base}.md"))

        # Save OCR visualization
        doc.visualize(
            image_path=log["file_path"],
            mode="ocr",
            output_directory=out_visualize,
            dpi=log.get("dpi", 200),
        )

if __name__ == "__main__":
    asyncio.run(main())
```

## License

Apache License 2.0 — see the `LICENSE` file for details.

## Contact

For questions or support, feel free to reach out:
📧 **[support-aws-marketplace@mlism.com](mailto:support-aws-marketplace@mlism.com)**