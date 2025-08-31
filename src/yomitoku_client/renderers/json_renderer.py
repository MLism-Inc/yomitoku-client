"""
JSON Renderer - For converting document data to JSON format
"""

import json
from typing import Optional
import numpy as np

from .base import BaseRenderer
from ..parsers.sagemaker_parser import DocumentResult
from ..exceptions import FormatConversionError
from ..utils import save_figure


class JSONRenderer(BaseRenderer):
    """JSON format renderer"""
    
    def __init__(self,
                 ignore_line_break: bool = False,
                 export_figure: bool = False,
                 figure_dir: str = "figures",
                 **kwargs):
        """
        Initialize JSON renderer
        
        Args:
            ignore_line_break: Whether to ignore line breaks in text
            export_figure: Whether to export figures
            figure_dir: Directory to save figures
            **kwargs: Additional options
        """
        super().__init__(**kwargs)
        self.ignore_line_break = ignore_line_break
        self.export_figure = export_figure
        self.figure_dir = figure_dir
    
    def render(self, data: DocumentResult, img: Optional[np.ndarray] = None, **kwargs) -> str:
        """Render document data to JSON format"""
        # Convert to dict for processing
        data_dict = data.model_dump()
        
        # Process ignore_line_break if needed
        if self.ignore_line_break:
            # Process tables
            for table in data_dict.get('tables', []):
                for cell in table.get('cells', []):
                    if 'contents' in cell:
                        cell['contents'] = cell['contents'].replace("\n", "")
            
            # Process paragraphs
            for paragraph in data_dict.get('paragraphs', []):
                if 'contents' in paragraph:
                    paragraph['contents'] = paragraph['contents'].replace("\n", "")
        
        # Format JSON with proper settings (matching original)
        return json.dumps(
            data_dict,
            ensure_ascii=False,
            indent=4,
            sort_keys=True,
            separators=(',', ': ')
        )
    
    def save(self, data: DocumentResult, output_path: str, img: Optional[np.ndarray] = None, **kwargs) -> None:
        """Save rendered content to JSON file"""
        # Save figures if requested
        if self.export_figure and img is not None and hasattr(data, 'figures'):
            save_figure(data.figures, img, output_path, self.figure_dir)
        
        # Render and save JSON
        json_content = self.render(data, img=img, **kwargs)
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(json_content)
        except Exception as e:
            raise FormatConversionError(f"Failed to save JSON file: {e}")
    
    def get_supported_formats(self) -> list:
        """Get supported formats"""
        return ["json"]
