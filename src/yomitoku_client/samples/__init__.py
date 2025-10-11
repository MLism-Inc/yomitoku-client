"""Sample data for Yomitoku client examples and tests."""

import json
from pathlib import Path
from typing import Any, Dict

_SAMPLES_DIR = Path(__file__).parent


def load_pdf_sample(json_file_path: str = "pdf_sample.json") -> Dict[str, Any]:
    """Load the PDF sample data from JSON file.

    Returns:
        Dict containing the PDF analysis result
    """
    with open(_SAMPLES_DIR / json_file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_image_sample(json_file_path: str = "image_sample.json") -> Dict[str, Any]:
    """Load the image sample data from JSON file.

    Returns:
        Dict containing the image analysis result
    """
    with open(_SAMPLES_DIR / json_file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_pdf_sample_path(pdf_file_path: str = "pdf_sample.pdf") -> Path:
    """Get the path to the PDF sample file.

    Returns:
        Path to pdf_sample.pdf
    """
    return _SAMPLES_DIR / pdf_file_path


def get_image_sample_path(image_file_path: str = "image_sample.png") -> Path:
    """Get the path to the image sample file.

    Returns:
        Path to image_sample.png
    """
    return _SAMPLES_DIR / image_file_path


def load_image_file(image_file_path: str = "image_sample.png"):
    """Load the actual image file using PIL.

    Returns:
        PIL.Image object
    """
    from PIL import Image
    return Image.open(get_image_sample_path(image_file_path))


def load_pdf_file_bytes(pdf_file_path: str = "pdf_sample.pdf") -> bytes:
    """Load the PDF file as bytes.

    Returns:
        bytes: PDF file content
    """
    with open(get_pdf_sample_path(pdf_file_path), "rb") as f:
        return f.read()


# Convenience exports
__all__ = [
    "load_pdf_sample",
    "load_image_sample",
    "get_pdf_sample_path",
    "get_image_sample_path",
    "load_image_file",
    "load_pdf_file_bytes",
]