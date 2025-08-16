"""
Yomitoku Client - Main client class for processing SageMaker outputs
"""

from typing import Optional, Dict, Any, Union
from pathlib import Path

from .parsers.sagemaker_parser import SageMakerParser, DocumentResult
from .renderers.factory import RendererFactory
from .exceptions import YomitokuError, DocumentAnalysisError, FormatConversionError


class YomitokuClient:
    """Main client for processing SageMaker Yomitoku API outputs"""
    
    def __init__(self):
        """Initialize the client"""
        self.parser = SageMakerParser()
    
    def parse_json(self, json_data: str) -> DocumentResult:
        """
        Parse JSON data from SageMaker output
        
        Args:
            json_data: JSON string from SageMaker
            
        Returns:
            DocumentResult: Parsed document result
        """
        return self.parser.parse_json(json_data)
    
    def parse_file(self, file_path: str) -> DocumentResult:
        """
        Parse JSON file from SageMaker output
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            DocumentResult: Parsed document result
        """
        return self.parser.parse_file(file_path)
    
    def convert_to_format(
        self, 
        data: Union[DocumentResult, str], 
        format_type: str, 
        output_path: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Convert document data to specified format
        
        Args:
            data: Document result to convert (DocumentResult or JSON string)
            format_type: Target format (csv, markdown, html, json)
            output_path: Optional path to save the output
            **kwargs: Additional rendering options
            
        Returns:
            str: Converted content
            
        Raises:
            FormatConversionError: If format is not supported or conversion fails
        """
        try:
            # Parse data if it's a string
            if isinstance(data, str):
                data = self.parse_json(data)
            
            # Create renderer using factory
            renderer = RendererFactory.create_renderer(format_type, **kwargs)
            
            # Render content
            content = renderer.render(data, **kwargs)
            
            # Save to file if output path is provided
            if output_path:
                renderer.save(data, output_path, **kwargs)
            
            return content
            
        except Exception as e:
            raise FormatConversionError(f"Failed to convert to {format_type}: {e}")
    
    def get_supported_formats(self) -> list:
        """
        Get list of supported output formats
        
        Returns:
            list: List of supported format names
        """
        return RendererFactory.get_supported_formats()
    
    def process_file(
        self, 
        input_path: str, 
        output_format: str, 
        output_path: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Process a SageMaker output file and convert to specified format
        
        Args:
            input_path: Path to input JSON file
            output_format: Target format
            output_path: Optional output path (auto-generated if not provided)
            **kwargs: Additional options
            
        Returns:
            str: Converted content
        """
        # Parse input file
        data = self.parse_file(input_path)
        
        # Generate output path if not provided
        if not output_path:
            input_file = Path(input_path)
            output_path = input_file.with_suffix(f".{output_format}")
        
        # Convert to target format
        return self.convert_to_format(data, output_format, output_path, **kwargs)
    
    def validate_data(self, data: DocumentResult) -> bool:
        """
        Validate parsed document data
        
        Args:
            data: Document result to validate
            
        Returns:
            bool: True if data is valid
        """
        return self.parser.validate_result(data)
