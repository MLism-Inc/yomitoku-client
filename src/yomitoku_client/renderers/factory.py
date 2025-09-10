"""
Renderer factory - Factory pattern for managing different renderers
"""

from typing import Dict, Type, Optional

from .base import BaseRenderer
from .csv_renderer import CSVRenderer
from .markdown_renderer import MarkdownRenderer
from .html_renderer import HTMLRenderer
from .json_renderer import JSONRenderer
from .pdf_renderer import PDFRenderer

from ..exceptions import FormatConversionError


class RendererFactory:
    """Factory class for creating renderers"""
    
    _renderers: Dict[str, Type[BaseRenderer]] = {
        "csv": CSVRenderer,
        "markdown": MarkdownRenderer,
        "md": MarkdownRenderer,
        "html": HTMLRenderer,
        "htm": HTMLRenderer,
        "json": JSONRenderer,
        "pdf": PDFRenderer,
    }
    
    @classmethod
    def register_renderer(cls, format_name: str, renderer_class: Type[BaseRenderer]) -> None:
        """
        Register a new renderer
        
        Args:
            format_name: Format identifier
            renderer_class: Renderer class to register
        """
        cls._renderers[format_name.lower()] = renderer_class
    
    @classmethod
    def get_supported_formats(cls) -> list:
        """
        Get list of supported formats
        
        Returns:
            list: List of supported format names
        """
        return list(cls._renderers.keys())
    
    @classmethod
    def create_renderer(cls, format_type: str, **kwargs) -> BaseRenderer:
        """
        Create a renderer instance
        
        Args:
            format_type: Format type (csv, markdown, html, json)
            **kwargs: Renderer initialization options
            
        Returns:
            BaseRenderer: Renderer instance
            
        Raises:
            FormatConversionError: If format is not supported
        """
        format_type = format_type.lower()
        
        if format_type not in cls._renderers:
            supported = ", ".join(cls.get_supported_formats())
            raise FormatConversionError(
                f"Unsupported format: {format_type}. Supported formats: {supported}"
            )
        
        renderer_class = cls._renderers[format_type]
        return renderer_class(**kwargs)
    
    @classmethod
    def is_supported(cls, format_type: str) -> bool:
        """
        Check if format is supported
        
        Args:
            format_type: Format type to check
            
        Returns:
            bool: True if format is supported
        """
        return format_type.lower() in cls._renderers
