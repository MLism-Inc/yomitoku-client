"""
SageMaker Parser - For parsing SageMaker Yomitoku API outputs
"""

from typing import Any, Dict

from .exceptions import DocumentAnalysisError, ValidationError
from .models import DocumentResult, MultiPageDocumentResult


def parse_pydantic_model(data: Dict[str, Any]) -> MultiPageDocumentResult:
    """
    Parse dictionary data from SageMaker output

    Args:
        data: Dictionary from SageMaker

    Returns:
        MultiPageDocumentResult: Multi-page document result containing all pages

    Raises:
        ValidationError: If data format is invalid
        DocumentAnalysisError: If parsing fails
    """
    try:
        if "result" not in data or not data["result"]:
            raise ValidationError(
                "Invalid SageMaker output format: missing 'result' field"
            )

        # Handle both single result and multiple results
        if isinstance(data["result"], list):
            if len(data["result"]) == 0:
                raise ValidationError("Empty result list")
            # Create pages from all results
            pages = [
                DocumentResult(**result_data, num_page=i)
                for i, result_data in enumerate(data["result"])
            ]
        else:
            # Single result, create single page
            pages = [DocumentResult(**data["result"], num_page=0)]

        return MultiPageDocumentResult(pages=pages)
    except Exception as e:
        raise DocumentAnalysisError(f"Failed to parse document: {e}")
