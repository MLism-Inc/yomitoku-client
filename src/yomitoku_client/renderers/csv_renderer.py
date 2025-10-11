"""
CSV Renderer - For converting document data to CSV format
"""

import csv
import os
from typing import List, Dict, Any, Optional
import numpy as np

from .base import BaseRenderer
from ..parsers.sagemaker_parser import DocumentResult, Table, Paragraph, Figure
from ..exceptions import FormatConversionError
from ..utils import save_figure, table_to_csv


class CSVRenderer(BaseRenderer):
    """CSV format renderer"""
    
    def __init__(self, 
                 ignore_line_break: bool = False,
                 export_figure: bool = True,
                 export_figure_letter: bool = False,
                 figure_dir: str = "figures",
                 **kwargs):
        """
        Initialize CSV renderer
        
        Args:
            ignore_line_break: Whether to ignore line breaks in text
            export_figure: Whether to export figures
            export_figure_letter: Whether to export figure letters/text
            figure_dir: Directory to save figures
            **kwargs: Additional options
        """
        super().__init__(**kwargs)
        self.ignore_line_break = ignore_line_break
        self.export_figure = export_figure
        self.export_figure_letter = export_figure_letter
        self.figure_dir = figure_dir
    
    def render(self, data: DocumentResult, img: Optional[np.ndarray] = None, **kwargs) -> str:
        """
        Render document data to CSV format
        
        Args:
            data: Document result to render
            img: Optional image array for figure extraction
            **kwargs: Additional rendering options
            
        Returns:
            str: CSV formatted string
        """
        elements = []
        
        # Process tables
        for table in data.tables:
            table_csv = self._table_to_csv(table)
            elements.append({
                "type": "table",
                "box": table.box,
                "element": table_csv,
                "order": table.order,
            })
        
        # Process paragraphs
        for paragraph in data.paragraphs:
            contents = self._paragraph_to_csv(paragraph)
            elements.append({
                "type": "paragraph",
                "box": paragraph.box,
                "element": contents,
                "order": paragraph.order,
            })
        
        # Process figure letters if requested
        if self.export_figure_letter and hasattr(data, 'figures'):
            for figure in data.figures:
                if hasattr(figure, 'paragraphs'):
                    for paragraph in sorted(figure.paragraphs, key=lambda x: x.order):
                        contents = self._paragraph_to_csv(paragraph)
                        elements.append({
                            "type": "paragraph",
                            "box": paragraph.box,
                            "element": contents,
                            "order": figure.order,
                        })
        
        # Sort by order
        elements.sort(key=lambda x: x["order"])
        
        # Convert to CSV string
        return self._elements_to_csv_string(elements)
    
    def save(self, data: DocumentResult, output_path: str, img: Optional[np.ndarray] = None, **kwargs) -> None:
        """
        Save rendered content to CSV file
        
        Args:
            data: Document result to render
            output_path: Path to save the CSV file
            img: Optional image array for figure extraction
            **kwargs: Additional rendering options
        """
        # Save figures if requested
        if self.export_figure and img is not None and hasattr(data, 'figures'):
            save_figure(data.figures, img, output_path, self.figure_dir)
        
        # Render and save CSV
        csv_content = self.render(data, img=img, **kwargs)
        
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                f.write(csv_content)
        except Exception as e:
            raise FormatConversionError(f"Failed to save CSV file: {e}")
    
    def _table_to_csv(self, table: Table) -> str:
        """
        Convert table to CSV string
        
        Args:
            table: Table data
            
        Returns:
            str: CSV formatted table
        """
        # Use the utility function for better table handling
        return table_to_csv(table, padding=False, drop_empty=False)
    
    def _paragraph_to_csv(self, paragraph: Paragraph) -> str:
        """
        Convert paragraph to CSV string
        
        Args:
            paragraph: Paragraph data
            
        Returns:
            str: CSV formatted paragraph content
        """
        contents = paragraph.contents
        
        if self.ignore_line_break:
            contents = contents.replace("\n", "")
        
        return contents
    
    def _elements_to_csv_string(self, elements: List[Dict[str, Any]]) -> str:
        """
        Convert elements to CSV string using proper CSV writer
        
        Args:
            elements: List of document elements
            
        Returns:
            str: CSV formatted string
        """
        import io
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
        
        for element in elements:
            if element["type"] == "table":
                # Add table as CSV string
                table_csv = element["element"]
                # Split CSV string into lines and write each line
                for line in table_csv.split('\n'):
                    if line.strip():  # Skip empty lines
                        writer.writerow([line])
                writer.writerow([])  # Empty row between tables
            elif element["type"] == "paragraph":
                # Add paragraph as single row
                writer.writerow([element["element"]])
            
            writer.writerow([])  # Empty row after each element
        
        return output.getvalue()
    
    def get_supported_formats(self) -> list:
        """Get supported formats"""
        return ["csv"]
