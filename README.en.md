# Yomitoku Client

<div align="center">

[![Language](https://img.shields.io/badge/🌐_English-blue?style=for-the-badge\&logo=github)](README.en.md) [![Language](https://img.shields.io/badge/🌐_日本語-red?style=for-the-badge\&logo=github)](README.md)

</div>

**Yomitoku Client** is a Python library designed to handle the output of the **Yomitoku Pro API** provided on **AWS SageMaker**.
It converts OCR analysis results into structured data, making it easy to save or visualize them in various formats such as **CSV**, **JSON**, **Markdown**, and **PDF**.
This library serves as a “bridge” between Yomitoku Pro’s high-accuracy OCR engine and your business applications.

---

## Key Features

* Simple, secure, and efficient integration with your own AWS SageMaker endpoint.
* Support for multiple output formats: **CSV / JSON / Markdown / HTML / PDF**.
* Built-in visualization to quickly review OCR and layout results.
* Batch processing for efficient large-scale document analysis.

---

## Quick Links

* 📓 **[Sample Notebook](notebooks/yomitoku-pro-document-analyzer.ipynb)** – Tutorial for connecting to an AWS SageMaker endpoint and running document analysis.

---

## Quick Start

A minimal example — analyze a PDF and export the result as Markdown.

```python
import asyncio
from yomitoku_client import YomitokuClient, parse_pydantic_model

ENDPOINT_NAME = "my-endpoint"
AWS_REGION = "ap-northeast-1"
target_file = "notebooks/sample/image.pdf"

async def main():
    async with YomitokuClient(
        endpoint=ENDPOINT_NAME,
        region=AWS_REGION,
    ) as client:
        result = await client.analyze_async(target_file)

    model = parse_pydantic_model(result)
    model.to_markdown(output_path="output.md", image_path=target_file)

if __name__ == "__main__":
    asyncio.run(main())
```

> **Note:**
> When running in Jupyter Notebook, you may need to add:
>
> ```python
> import nest_asyncio; nest_asyncio.apply()
> ```

---

## What is YomiToku-Pro Document Analyzer?

**YomiToku-Pro Document Analyzer** is an AWS Marketplace offering that provides an OCR and layout-analysis endpoint on SageMaker.

* Performs high-speed, high-accuracy recognition and layout analysis for Japanese documents.
* Each model is trained specifically for Japanese document images and supports recognition of over **7,000 characters**, including handwritten and vertical text layouts. (English documents are also supported.)
* Layout analysis, table structure extraction, and reading-order estimation allow information to be extracted without breaking the document’s logical structure.
* **Automatic rotation correction:** Detects page orientation and automatically adjusts before analysis.
* Each user runs their own dedicated SageMaker endpoint within their AWS account, ensuring all data is processed **securely within the AWS region** — never sent to external servers or third parties.

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

> **Note:** If `uv` is not installed, you can install it with:
>
> ```bash
> curl -LsSf https://astral.sh/uv/install.sh | sh
> ```

---

## Single-File Analysis (Detailed Example)

* Automatic page splitting and parallel inference for multi-page documents
* Automatic retries with exponential backoff
* Circuit breaker for endpoint protection
* Unified handling of communication, JSON-decode, and timeout errors

```python
from yomitoku_client import YomitokuClient, parse_pydantic_model

ENDPOINT_NAME = "my-endpoint"
AWS_REGION = "ap-northeast-1"
target_file = "notebooks/sample/image.pdf"

async def main():
    async with YomitokuClient(
        endpoint=ENDPOINT_NAME,
        region=AWS_REGION,
    ) as client:
        result = await client.analyze_async(target_file)

    # Format conversion
    model = parse_pydantic_model(result)
    model.to_csv(output_path="output.csv")     # Save as CSV
    model.to_markdown(output_path="output.md", image_path=target_file)  # Save as Markdown
    model.to_json(output_path="output.json", mode="separate")  # Save per page (mode="separate")
    model.to_html(output_path="output.html", image_path=target_file, page_index=[0, 2])  # Export selected pages
    model.to_pdf(output_path="output.pdf", image_path=target_file)  # Generate searchable PDF

    # Visualization
    model.visualize(
        image_path=target_file,
        mode="ocr",
        page_index=None,
        output_directory="demo",
    )

    model.visualize(
        image_path=target_file,
        mode="layout",
        page_index=None,
        output_directory="demo",
    )

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Batch Processing

`YomitokuClient` also supports robust batch processing for large-scale, automated document analysis.

* **Folder-level batch analysis** – Automatically detects and processes PDFs and images in a given directory using parallel execution.
* **Intermediate logging (`process_log.jsonl`)** – Logs each file’s success/failure status, processing time, and error messages in JSON Lines format, enabling post-processing and re-runs.
* **Overwrite control** – Skip already processed files (`overwrite=False`) for efficiency.
* **Retry support** – Easily reprocess only failed files using the log.
* **Post-processing automation** – Load `process_log.jsonl` to automatically export Markdown and visualization results for successful files.

### Example

```python
import asyncio
import json
import os
from yomitoku_client import YomitokuClient, parse_pydantic_model

target_dir = "notebooks/sample"
outdir = "output"

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

    # Post-process successful results
    with open(os.path.join(outdir, "process_log.jsonl"), "r", encoding="utf-8") as f:
        logs = [json.loads(line) for line in f if line.strip()]

    out_markdown = os.path.join(outdir, "markdown")
    out_visualize = os.path.join(outdir, "visualization")

    os.makedirs(out_markdown, exist_ok=True)
    os.makedirs(out_visualize, exist_ok=True)

    for log in logs:
        if not log.get("success"):
            continue

        with open(log["output_path"], "r", encoding="utf-8") as rf:
            result = json.load(rf)

        doc = parse_pydantic_model(result)

        base = os.path.splitext(os.path.basename(log["file_path"]))[0]
        doc.to_markdown(output_path=os.path.join(out_markdown, f"{base}.md"))

        doc.visualize(
            image_path=log["file_path"],
            mode="ocr",
            output_directory=out_visualize,
            dpi=log.get("dpi", 200),
        )

if __name__ == "__main__":
    asyncio.run(main())
```

---

## License

Apache License 2.0 — See the LICENSE file for details.

---

## Contact

For questions or support inquiries, please feel free to reach out:
📧 **[support-aws-marketplace@mlism.com](mailto:support-aws-marketplace@mlism.com)**