"""
HTML Renderer - For converting document data to HTML format
"""

from .base import BaseRenderer
from ..parsers.sagemaker_parser import DocumentResult
from ..exceptions import FormatConversionError


class HTMLRenderer(BaseRenderer):
    """HTML format renderer"""
    
    def render(self, data: DocumentResult, **kwargs) -> str:
        """Render document data to HTML format"""
        # TODO: Implement HTML rendering
        return f"<html><body><h1>Document Content</h1><p>Tables: {len(data.tables)}, Paragraphs: {len(data.paragraphs)}</p></body></html>"
    
    def save(self, data: DocumentResult, output_path: str, **kwargs) -> None:
        """Save rendered content to HTML file"""
        html_content = self.render(data, **kwargs)
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
        except Exception as e:
            raise FormatConversionError(f"Failed to save HTML file: {e}")
    
    def get_supported_formats(self) -> list:
        """Get supported formats"""
        return ["html"]
