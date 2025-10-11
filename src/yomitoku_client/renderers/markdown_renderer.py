"""
Markdown Renderer - For converting document data to Markdown format
"""

import os
import re
from typing import List, Dict, Any, Optional
import numpy as np

from .base import BaseRenderer
from ..parsers.sagemaker_parser import DocumentResult, Table, Paragraph, Figure
from ..exceptions import FormatConversionError
from ..utils import escape_markdown_special_chars, remove_dot_prefix, save_image


class MarkdownRenderer(BaseRenderer):
    """Markdown format renderer"""
    
    def __init__(self, 
                 ignore_line_break: bool = False,
                 export_figure: bool = True,
                 export_figure_letter: bool = False,
                 figure_width: int = 200,
                 figure_dir: str = "figures",
                 table_format: str = "html",
                 **kwargs):
        """
        Initialize Markdown renderer
        
        Args:
            ignore_line_break: Whether to ignore line breaks in text
            export_figure: Whether to export figures
            export_figure_letter: Whether to export figure letters/text
            figure_width: Width of figures in pixels
            figure_dir: Directory to save figures
            table_format: Table format ("html" or "md")
            **kwargs: Additional options
        """
        super().__init__(**kwargs)
        self.ignore_line_break = ignore_line_break
        self.export_figure = export_figure
        self.export_figure_letter = export_figure_letter
        self.figure_width = figure_width
        self.figure_dir = figure_dir
        self.table_format = table_format
    
    def render(self, data: DocumentResult, img: Optional[np.ndarray] = None, output_path: Optional[str] = None, **kwargs) -> str:
        """
        Render document data to Markdown format
        
        Args:
            data: Document result to render
            img: Optional image array for figure extraction
            output_path: Output path (needed for figure references)
            **kwargs: Additional rendering options
            
        Returns:
            str: Markdown formatted string
        """
        elements = []
        
        # Process tables
        for table in data.tables:
            if self.table_format == "html":
                table_md = self._table_to_html(table)
            else:
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
        
        # Process figures if requested
        if self.export_figure and img is not None and output_path and hasattr(data, 'figures'):
            figure_elements = self._figures_to_markdown(data.figures, img, output_path)
            elements.extend(figure_elements)
        
        # Sort by order
        elements.sort(key=lambda x: x["order"])
        
        # Convert to markdown string
        return self._elements_to_markdown_string(elements)
    
    def save(self, data: DocumentResult, output_path: str, img: Optional[np.ndarray] = None, **kwargs) -> None:
        """
        Save rendered content to Markdown file
        
        Args:
            data: Document result to render
            output_path: Path to save the Markdown file
            img: Optional image array for figure extraction
            **kwargs: Additional rendering options
        """
        md_content = self.render(data, img=img, output_path=output_path, **kwargs)
        
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
            contents = escape_markdown_special_chars(contents)
            contents = "# " + contents
        elif paragraph.role == "list_item":
            contents = self._build_list_item_markdown(contents)
            if indent > 0:
                contents = " " * ((indent - 1) * 4) + contents
        else:
            contents = escape_markdown_special_chars(contents)
        
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
            
            contents = escape_markdown_special_chars(contents)
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
            # Handle caption as object or dict
            if hasattr(table.caption, 'contents'):
                caption_text = table.caption.contents
            elif isinstance(table.caption, dict):
                caption_text = table.caption.get("contents", "")
            else:
                caption_text = str(table.caption)
            md_table += f"**{escape_markdown_special_chars(caption_text)}**\n\n"
        
        # Add table header
        for row in table_array:
            md_table += "| " + " | ".join(cell for cell in row) + " |\n"
            
            # Add separator line after first row
            if table_array.index(row) == 0:
                md_table += "| " + " | ".join("---" for _ in row) + " |\n"
        
        return md_table + "\n"
    
    def _table_to_html(self, table: Table) -> str:
        """
        Convert table to HTML format for Markdown
        
        Args:
            table: Table data
            
        Returns:
            str: HTML formatted table
        """
        from ..utils import convert_text_to_html
        
        html = '<table border="1" style="border-collapse: collapse">\n'
        
        # Add caption if available
        if table.caption:
            if hasattr(table.caption, 'contents'):
                caption_text = table.caption.contents
            elif isinstance(table.caption, dict):
                caption_text = table.caption.get("contents", "")
            else:
                caption_text = str(table.caption)
            html += f"<caption>{convert_text_to_html(caption_text)}</caption>\n"
        
        html += "<tbody>\n"
        
        # Build table rows
        pre_row = 1
        rows = []
        row = []
        for cell in table.cells:
            row_span = cell.row_span
            col_span = cell.col_span
            contents = cell.contents
            
            if contents is None:
                contents = ""
            
            if self.ignore_line_break:
                contents = contents.replace("\n", "")
            else:
                contents = contents.replace("\n", "<br>")
            
            if cell.row != pre_row:
                rows.append(self._add_tr_tag("".join(row)))
                row = []
            
            row.append(self._add_td_tag(contents, row_span, col_span))
            pre_row = cell.row
        else:
            rows.append(self._add_tr_tag("".join(row)))
        
        html += "".join(rows)
        html += "</tbody>\n</table>\n"
        
        return html
    
    def _add_td_tag(self, contents: str, row_span: int = 1, col_span: int = 1) -> str:
        """Add TD tag with optional span attributes"""
        row_span_attr = f' rowspan="{row_span}"' if row_span > 1 else ""
        col_span_attr = f' colspan="{col_span}"' if col_span > 1 else ""
        return f"<td{row_span_attr}{col_span_attr}>{contents}</td>\n"
    
    def _add_tr_tag(self, contents: str) -> str:
        """Add TR tag"""
        return f"<tr>\n{contents}</tr>\n"
    
    def _build_list_item_markdown(self, contents: str) -> str:
        """
        Build list item markdown
        
        Args:
            contents: List item content
            
        Returns:
            str: Formatted list item
        """
        if self._is_dot_list_item(contents):
            contents = escape_markdown_special_chars(contents)
            contents = remove_dot_prefix(contents)
            return f"- {contents}"
        else:
            contents = escape_markdown_special_chars(contents)
            return f"- {contents}"
    
    def _is_dot_list_item(self, contents: str) -> bool:
        """Check if content is a dot list item"""
        return re.match(r"^[·\-●·・]", contents) is not None
    
    def _figures_to_markdown(self, figures: List[Figure], img: np.ndarray, output_path: str) -> List[Dict[str, Any]]:
        """
        Convert figures to Markdown with image files
        
        Args:
            figures: List of figure objects
            img: Source image array  
            output_path: Output path for references
            
        Returns:
            List of figure elements
        """
        elements = []
        
        for i, figure in enumerate(figures):
            # Extract and save figure image
            x1, y1, x2, y2 = map(int, figure.box)
            figure_img = img[y1:y2, x1:x2, :]
            
            save_dir = os.path.dirname(output_path)
            save_dir = os.path.join(save_dir, self.figure_dir)
            os.makedirs(save_dir, exist_ok=True)
            
            filename = os.path.splitext(os.path.basename(output_path))[0]
            figure_name = f"{filename}_figure_{i}.png"
            figure_path = os.path.join(save_dir, figure_name)
            save_image(figure_img, figure_path)
            
            relative_path = os.path.join(self.figure_dir, figure_name)
            
            # Create HTML figure tag
            fig_html = f'<figure>\n'
            fig_html += f'\t<img src="{relative_path}" width="{self.figure_width}px">\n'
            
            # Add caption if available
            if figure.caption:
                if hasattr(figure.caption, 'contents'):
                    caption_text = figure.caption.contents
                elif isinstance(figure.caption, dict):
                    caption_text = figure.caption.get("contents", "")
                else:
                    caption_text = str(figure.caption)
                fig_html += f'\t<figcaption>{caption_text}</figcaption>\n'
            
            fig_html += '</figure>\n'
            
            elements.append({
                "type": "figure",
                "element": fig_html,
                "order": figure.order
            })
            
            # Process figure letters if requested
            if self.export_figure_letter and hasattr(figure, 'paragraphs'):
                for paragraph in sorted(figure.paragraphs, key=lambda x: x.order):
                    md_content = self._paragraph_to_markdown(paragraph)
                    elements.append({
                        "type": "paragraph",
                        "element": md_content,
                        "order": figure.order
                    })
        
        return elements
    
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
            elif element["type"] == "figure":
                output.append(element["element"])
        
        return "".join(output)
    
    def get_supported_formats(self) -> list:
        """Get supported formats"""
        return ["markdown", "md"]