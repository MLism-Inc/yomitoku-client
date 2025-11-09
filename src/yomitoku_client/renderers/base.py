"""
Base renderer class - Defines the interface for all renderers
"""

from abc import ABC, abstractmethod

from ..parser import DocumentResult


class BaseRenderer(ABC):
    """Base class for all renderers"""

    def __init__(self, **kwargs):
        """Initialize renderer with options"""
        self.options = kwargs

    @abstractmethod
    def render(self, data: DocumentResult, **kwargs) -> str:
        """
        Render document data to string format

        Args:
            data: Document result to render
            **kwargs: Additional rendering options

        Returns:
            str: Rendered content
        """

    def get_supported_formats(self) -> list:
        """
        Get list of supported output formats

        Returns:
            list: List of supported format strings
        """
        return []

    def validate_options(self) -> bool:
        """
        Validate renderer options

        Args:
            **kwargs: Options to validate

        Returns:
            bool: True if options are valid
        """
        return True
