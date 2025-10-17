"""
Parser module - For parsing SageMaker Yomitoku API outputs
"""

from .sagemaker_parser import parse_pydantic_model

__all__ = ["parse_pydantic_model"]
