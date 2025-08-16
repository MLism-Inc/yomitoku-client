"""
Markdown Renderer - For converting document data to Markdown format
"""

import re
from typing import List, Dict, Any

from .base import BaseRenderer
from ..parsers.sagemaker_parser import DocumentResult, Table, Paragraph
from ..exceptions import FormatConversionError


class MarkdownRenderer(BaseRenderer):
    """Markdown format renderer"""
    
    def __init__(self, ignore_line_break: bool = False, **kwargs):
        """
        Initialize Markdown renderer
        
        Args:
            ignore_line_break: Whether to ignore line breaks in text
            **kwargs: Additional options
        """
        super().__init__(**kwargs)
        self.ignore_line_break = ignore_line_break
    
    def render(self, data: DocumentResult, **kwargs) -> str:
        """
        Render document data to Markdown format
        
        Args:
            data: Document result to render
            **kwargs: Additional rendering options
            
        Returns:
            str: Markdown formatted string
        """
        elements = []
        
        # Process tables
        for table in data.tables:
            table_md = self._table_to_markdown(table)
            elements.append({
                "type": "table",
                "box": table.box,
                "element": table_md,
                "order": table.order,
            })
        
        # Process paragraphs
        for paragraph in data.paragraphs:
            md_content = self._paragraph_to_markdown(paragraph)
            elements.append({
                "type": "paragraph",
                "box": paragraph.box,
                "element": md_content,
                "order": paragraph.order,
            })
        
        # Sort by order
        elements.sort(key=lambda x: x["order"])
        
        # Convert to markdown string
        return self._elements_to_markdown_string(elements)
    
    def save(self, data: DocumentResult, output_path: str, **kwargs) -> None:
        """
        Save rendered content to Markdown file
        
        Args:
            data: Document result to render
            output_path: Path to save the Markdown file
            **kwargs: Additional rendering options
        """
        md_content = self.render(data, **kwargs)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
        except Exception as e:
            raise FormatConversionError(f"Failed to save Markdown file: {e}")
    
    def _paragraph_to_markdown(self, paragraph: Paragraph) -> str:
        """
        Convert paragraph to Markdown
        
        Args:
            paragraph: Paragraph data
            
        Returns:
            str: Markdown formatted paragraph
        """
        contents = paragraph.contents
        indent = paragraph.indent_level or 0
        
        if self.ignore_line_break:
            contents = contents.replace("\n", "")
        else:
            contents = contents.replace("\n", "<br>")
        
        # Handle different paragraph roles
        if paragraph.role == "section_headings":
            contents = self._escape_markdown(contents)
            contents = "# " + contents
        elif paragraph.role == "list_item":
            contents = self._build_list_item_markdown(contents)
            contents = " " * ((indent - 1) * 4) + contents
        else:
            contents = self._escape_markdown(contents)
        
        return contents + "\n"
    
    def _table_to_markdown(self, table: Table) -> str:
        """
        Convert table to Markdown table
        
        Args:
            table: Table data
            
        Returns:
            str: Markdown formatted table
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
            
            contents = self._escape_markdown(contents)
            if self.ignore_line_break:
                contents = contents.replace("\n", "")
            else:
                contents = contents.replace("\n", "<br>")
            
            for i in range(row, row + row_span):
                for j in range(col, col + col_span):
                    if i == row and j == col:
                        table_array[i][j] = contents
        
        # Build markdown table
        md_table = ""
        
        # Add caption if available
        if table.caption:
            caption_text = table.caption.get("contents", "")
            md_table += f"**{self._escape_markdown(caption_text)}**\n\n"
        
        # Add table header
        for row in table_array:
            md_table += "| " + " | ".join(cell for cell in row) + " |\n"
            
            # Add separator line after first row
            if table_array.index(row) == 0:
                md_table += "| " + " | ".join("---" for _ in row) + " |\n"
        
        return md_table + "\n"
    
    def _build_list_item_markdown(self, contents: str) -> str:
        """
        Build list item markdown
        
        Args:
            contents: List item content
            
        Returns:
            str: Formatted list item
        """
        if self._is_dot_list_item(contents):
            contents = self._escape_markdown(contents)
            contents = self._remove_dot_prefix(contents)
            return f"- {contents}\n"
        else:
            contents = self._escape_markdown(contents)
            return f"- {contents}\n"
    
    def _is_dot_list_item(self, contents: str) -> bool:
        """Check if content is a dot list item"""
        return re.match(r"^[·-●·・]", contents) is not None
    
    def _remove_dot_prefix(self, contents: str) -> str:
        """Remove dot prefix from content"""
        return re.sub(r"^[·-●·・]\s*", "", contents, count=1).strip()
    
    def _escape_markdown(self, text: str) -> str:
        """
        Escape markdown special characters
        
        Args:
            text: Text to escape
            
        Returns:
            str: Escaped text
        """
        # Escape markdown special characters
        special_chars = ['*', '_', '`', '#', '+', '-', '.', '!', '[', ']', '(', ')', '|']
        for char in special_chars:
            text = text.replace(char, f"\\{char}")
        return text
    
    def _elements_to_markdown_string(self, elements: List[Dict[str, Any]]) -> str:
        """
        Convert elements to markdown string
        
        Args:
            elements: List of document elements
            
        Returns:
            str: Markdown formatted string
        """
        output = []
        
        for element in elements:
            if element["type"] == "table":
                output.append(element["element"])
            elif element["type"] == "paragraph":
                output.append(element["element"])
        
        return "".join(output)
    
    def get_supported_formats(self) -> list:
        """Get supported formats"""
        return ["markdown", "md"]
