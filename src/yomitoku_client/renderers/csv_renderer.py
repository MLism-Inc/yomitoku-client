"""
CSV Renderer - For converting document data to CSV format
"""

import csv
import os
from typing import List, Dict, Any

from .base import BaseRenderer
from ..parsers.sagemaker_parser import DocumentResult, Table, Paragraph
from ..exceptions import FormatConversionError


class CSVRenderer(BaseRenderer):
    """CSV format renderer"""
    
    def __init__(self, ignore_line_break: bool = True, **kwargs):
        """
        Initialize CSV renderer
        
        Args:
            ignore_line_break: Whether to ignore line breaks in text
            **kwargs: Additional options
        """
        super().__init__(**kwargs)
        self.ignore_line_break = ignore_line_break
    
    def render(self, data: DocumentResult, **kwargs) -> str:
        """
        Render document data to CSV format
        
        Args:
            data: Document result to render
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
        
        # Sort by order
        elements.sort(key=lambda x: x["order"])
        
        # Convert to CSV string
        return self._elements_to_csv_string(elements)
    
    def save(self, data: DocumentResult, output_path: str, **kwargs) -> None:
        """
        Save rendered content to CSV file
        
        Args:
            data: Document result to render
            output_path: Path to save the CSV file
            **kwargs: Additional rendering options
        """
        csv_content = self.render(data, **kwargs)
        
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                f.write(csv_content)
        except Exception as e:
            raise FormatConversionError(f"Failed to save CSV file: {e}")
    
    def _table_to_csv(self, table: Table) -> List[List[str]]:
        """
        Convert table to CSV array
        
        Args:
            table: Table data
            
        Returns:
            List[List[str]]: 2D array representing table
        """
        num_rows = table.n_row
        num_cols = table.n_col
        
        table_array = [["" for _ in range(num_cols)] for _ in range(num_rows)]
        
        for cell in table.cells:
            row = cell.row - 1
            col = cell.col - 1
            row_span = cell.row_span
            col_span = cell.col_span
            contents = cell.contents
            
            if self.ignore_line_break:
                contents = contents.replace("\n", "")
            
            for i in range(row, row + row_span):
                for j in range(col, col + col_span):
                    if i == row and j == col:
                        table_array[i][j] = contents
        
        return table_array
    
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
        Convert elements to CSV string
        
        Args:
            elements: List of document elements
            
        Returns:
            str: CSV formatted string
        """
        output = []
        
        for element in elements:
            if element["type"] == "table":
                # Add table as CSV
                table_data = element["element"]
                for row in table_data:
                    output.append(",".join(f'"{cell}"' for cell in row))
                output.append("")  # Empty line between tables
            elif element["type"] == "paragraph":
                # Add paragraph as single row
                content = element["element"]
                output.append(f'"{content}"')
        
        return "\n".join(output)
    
    def get_supported_formats(self) -> list:
        """Get supported formats"""
        return ["csv"]
