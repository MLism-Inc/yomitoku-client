"""
JSON Renderer - For converting document data to JSON format
"""

import json
from .base import BaseRenderer
from ..parsers.sagemaker_parser import DocumentResult
from ..exceptions import FormatConversionError


class JSONRenderer(BaseRenderer):
    """JSON format renderer"""
    
    def render(self, data: DocumentResult, **kwargs) -> str:
        """Render document data to JSON format"""
        return json.dumps(data.model_dump(), ensure_ascii=False, indent=2)
    
    def save(self, data: DocumentResult, output_path: str, **kwargs) -> None:
        """Save rendered content to JSON file"""
        json_content = self.render(data, **kwargs)
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(json_content)
        except Exception as e:
            raise FormatConversionError(f"Failed to save JSON file: {e}")
    
    def get_supported_formats(self) -> list:
        """Get supported formats"""
        return ["json"]
