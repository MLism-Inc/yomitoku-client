"""
Yomitoku Client - Main client class for processing SageMaker outputs
"""

from typing import Optional, Dict, Any, List
from pathlib import Path

from .parsers.sagemaker_parser import SageMakerParser, DocumentResult
from .renderers.factory import RendererFactory
from .exceptions import YomitokuError, DocumentAnalysisError, FormatConversionError


class YomitokuClient:
    """Main client for processing SageMaker Yomitoku API outputs"""
    
    def __init__(self):
        """Initialize the client"""
        self.parser = SageMakerParser()
    
    def parse_json(self, json_data: str) -> List[DocumentResult]:
        """
        Parse JSON data from SageMaker output
        
        Args:
            json_data: JSON string from SageMaker
            
        Returns:
            List[DocumentResult]: List of all parsed document results
        """
        return self.parser.parse_json(json_data)
    
    def parse_dict(self, data: Dict[str, Any]) -> List[DocumentResult]:
        """
        Parse dictionary data from SageMaker output
        
        Args:
            data: Dictionary from SageMaker
            
        Returns:
            List[DocumentResult]: List of all parsed document results
        """
        return self.parser.parse_dict(data)
    
    def parse_file(self, file_path: str) -> List[DocumentResult]:
        """
        Parse JSON file from SageMaker output
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            List[DocumentResult]: List of all parsed document results
        """
        return self.parser.parse_file(file_path)
    
    def convert_to_format(
        self, 
        data: List[DocumentResult], 
        format_type: str, 
        output_path: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Convert document data to specified format
        
        Args:
            data: List of document results to convert
            format_type: Target format (csv, markdown, html, json)
            output_path: Optional path to save the output
            **kwargs: Additional rendering options
            
        Returns:
            str: Converted content
            
        Raises:
            FormatConversionError: If format is not supported or conversion fails
        """
        try:
            # Create renderer using factory
            renderer = RendererFactory.create_renderer(format_type, **kwargs)
            
            # For now, we'll combine all results into one
            # This is a simple approach - you might want to customize this based on your needs
            combined_content = []
            
            for i, doc_data in enumerate(data):
                # Add separator between documents
                if i > 0:
                    combined_content.append(f"\n--- Document {i+1} ---\n")
                else:
                    combined_content.append(f"--- Document {i+1} ---\n")
                
                # Render individual document
                content = renderer.render(doc_data, **kwargs)
                combined_content.append(content)
            
            final_content = "".join(combined_content)
            
            # Save to file if output path is provided
            if output_path:
                # For multiple documents, we might want to save them separately
                # For now, we'll save the combined content
                try:
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(final_content)
                except Exception as e:
                    raise FormatConversionError(f"Failed to save file: {e}")
            
            return final_content
            
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
