"""
HTML Renderer - For converting document data to HTML format
"""

import os
import re
from typing import List, Dict, Any, Optional
import numpy as np
from html import escape

from .base import BaseRenderer
from ..parsers.sagemaker_parser import DocumentResult, Table, Paragraph, Figure
from ..exceptions import FormatConversionError
from ..utils import save_image, remove_dot_prefix


class HTMLRenderer(BaseRenderer):
    """HTML format renderer"""
    
    def __init__(self,
                 ignore_line_break: bool = False,
                 export_figure: bool = True,
                 export_figure_letter: bool = False,
                 figure_width: int = 200,
                 figure_dir: str = "figures",
                 **kwargs):
        """
        Initialize HTML renderer
        
        Args:
            ignore_line_break: Whether to ignore line breaks in text
            export_figure: Whether to export figures
            export_figure_letter: Whether to export figure letters/text
            figure_width: Width of figures in pixels
            figure_dir: Directory to save figures
            **kwargs: Additional options
        """
        super().__init__(**kwargs)
        self.ignore_line_break = ignore_line_break
        self.export_figure = export_figure
        self.export_figure_letter = export_figure_letter
        self.figure_width = figure_width
        self.figure_dir = figure_dir
    
    def render(self, data: DocumentResult, img: Optional[np.ndarray] = None, output_path: Optional[str] = None, **kwargs) -> str:
        """
        Render document data to HTML format
        
        Args:
            data: Document result to render
            img: Optional image array for figure extraction
            output_path: Output path (needed for figure references)
            **kwargs: Additional rendering options
            
        Returns:
            str: HTML formatted string
        """
        elements = []
        
        # Process tables
        for table in data.tables:
            elements.append(self._table_to_html(table))
        
        # Process paragraphs
        for paragraph in data.paragraphs:
            elements.append(self._paragraph_to_html(paragraph))
        
        # Process figures if requested
        if self.export_figure and img is not None and output_path and hasattr(data, 'figures'):
            figure_elements = self._figures_to_html(data.figures, img, output_path)
            elements.extend(figure_elements)
        
        # Sort by order
        elements.sort(key=lambda x: x["order"])
        
        # Build list structure
        self._list_to_html(elements)
        
        # Convert to HTML string
        html_string = "".join([element["html"] for element in elements])
        
        # Format HTML
        formatted_html = self._format_html(html_string)
        
        return formatted_html
    
    def save(self, data: DocumentResult, output_path: str, img: Optional[np.ndarray] = None, **kwargs) -> None:
        """
        Save rendered content to HTML file
        
        Args:
            data: Document result to render
            output_path: Path to save the HTML file
            img: Optional image array for figure extraction
            **kwargs: Additional rendering options
        """
        html_content = self.render(data, img=img, output_path=output_path, **kwargs)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
        except Exception as e:
            raise FormatConversionError(f"Failed to save HTML file: {e}")
    
    def _convert_text_to_html(self, text: str) -> str:
        """
        Convert text to HTML, escaping special characters
        
        Args:
            text: Text to convert
            
        Returns:
            str: HTML-escaped text
        """
        # URL regex pattern
        url_regex = re.compile(r"https?://[^\s<>]+")
        
        def replace_url(match):
            url = match.group(0)
            return escape(url)
        
        return url_regex.sub(replace_url, escape(text))
    
    def _table_to_html(self, table: Table) -> Dict[str, Any]:
        """
        Convert table to HTML
        
        Args:
            table: Table data
            
        Returns:
            dict: HTML element dictionary
        """
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
        
        body = self._add_tbody_tag("".join(rows))
        
        caption = ""
        if table.caption:
            if hasattr(table.caption, 'contents'):
                caption_text = table.caption.contents
            elif isinstance(table.caption, dict):
                caption_text = table.caption.get("contents", "")
            else:
                caption_text = str(table.caption)
            caption = self._add_caption_tag(caption_text)
        
        table_contents = f"{caption}{body}"
        table_html = self._add_table_tag(table_contents)
        
        return {
            "box": table.box,
            "order": table.order,
            "html": table_html,
            "role": None,
        }
    
    def _paragraph_to_html(self, paragraph: Paragraph) -> Dict[str, Any]:
        """
        Convert paragraph to HTML
        
        Args:
            paragraph: Paragraph data
            
        Returns:
            dict: HTML element dictionary
        """
        contents = paragraph.contents
        contents = self._convert_text_to_html(contents)
        
        if self.ignore_line_break:
            contents = contents.replace("\n", "")
        else:
            contents = contents.replace("\n", "<br>")
        
        if paragraph.role == "section_headings":
            contents = self._add_h1_tag(contents)
        elif paragraph.role == "list_item":
            contents = remove_dot_prefix(contents)
            contents = self._add_li_tag(contents)
        else:
            contents = self._add_p_tag(contents)
        
        return {
            "box": paragraph.box,
            "order": paragraph.order,
            "html": contents,
            "indent_level": paragraph.indent_level or 0,
            "role": paragraph.role,
        }
    
    def _figures_to_html(self, figures: List[Figure], img: np.ndarray, output_path: str) -> List[Dict[str, Any]]:
        """
        Convert figures to HTML with image files
        
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
            
            # Create HTML figure
            html = self._figure_to_html(relative_path, self.figure_width, figure.caption)
            
            elements.append({
                "order": figure.order,
                "html": html,
                "role": figure.role if hasattr(figure, 'role') else None,
            })
            
            # Process figure letters if requested
            if self.export_figure_letter and hasattr(figure, 'paragraphs'):
                for paragraph in sorted(figure.paragraphs, key=lambda x: x.order):
                    contents = self._paragraph_to_html(paragraph)
                    elements.append({
                        "order": figure.order,
                        "html": contents["html"],
                        "role": None,
                    })
        
        return elements
    
    def _figure_to_html(self, relative_path: str, width: int, caption=None) -> str:
        """
        Create HTML figure element
        
        Args:
            relative_path: Path to figure image
            width: Width in pixels
            caption: Optional caption
            
        Returns:
            str: HTML figure element
        """
        img_tag = f'\t<img src="{relative_path}" width="{width}px">\n'
        caption_tag = ""
        
        if caption:
            if hasattr(caption, 'contents'):
                caption_text = caption.contents
            elif isinstance(caption, dict):
                caption_text = caption.get("contents", "")
            else:
                caption_text = str(caption)
            caption_tag = f"\t<figcaption>{caption_text}</figcaption>\n"
        
        return f"<figure>\n{img_tag}{caption_tag}</figure>\n"
    
    def _list_to_html(self, elements: List[Dict[str, Any]]) -> None:
        """
        Convert list items to proper HTML list structure
        
        Args:
            elements: List of HTML elements (modified in place)
        """
        pre_indent_level = 0
        has_list_head = False
        
        for element in elements:
            if "role" in element and element.get("role") == "list_item":
                indent_level = element.get("indent_level", 0)
                
                if not has_list_head:
                    element["html"] = "<ul>\n" + element["html"]
                    has_list_head = True
                elif pre_indent_level < indent_level:
                    element["html"] = "<ul>\n" + element["html"]
                elif pre_indent_level > indent_level:
                    element["html"] = "</ul>\n" + element["html"]
                
                pre_indent_level = indent_level
            
            if has_list_head and element.get("role") != "list_item":
                close_tag = "</ul>\n" * pre_indent_level
                element["html"] = close_tag + element["html"]
                has_list_head = False
                pre_indent_level = 0
    
    def _format_html(self, html_string: str) -> str:
        """
        Format HTML string for pretty output
        
        Args:
            html_string: Raw HTML string
            
        Returns:
            str: Formatted HTML string
        """
        if not html_string:
            return ""
        
        try:
            from lxml import html, etree
            parsed_html = html.fromstring(html_string)
            return etree.tostring(parsed_html, pretty_print=True, encoding="unicode")
        except ImportError:
            # If lxml is not available, return the raw HTML
            return html_string
    
    # HTML tag helper methods
    def _add_td_tag(self, contents: str, row_span: int = 1, col_span: int = 1) -> str:
        row_span_attr = f' rowspan="{row_span}"' if row_span > 1 else ""
        col_span_attr = f' colspan="{col_span}"' if col_span > 1 else ""
        return f"<td{row_span_attr}{col_span_attr}>{contents}</td>\n"
    
    def _add_table_tag(self, contents: str) -> str:
        return f'<table border="1" style="border-collapse: collapse">\n{contents}</table>\n'
    
    def _add_caption_tag(self, contents: str) -> str:
        return f"<caption>{contents}</caption>"
    
    def _add_tr_tag(self, contents: str) -> str:
        return f"<tr>\n{contents}</tr>\n"
    
    def _add_p_tag(self, contents: str) -> str:
        return f"<p>{contents}</p>\n"
    
    def _add_h1_tag(self, contents: str) -> str:
        return f"<h1>{contents}</h1>\n"
    
    def _add_tbody_tag(self, contents: str) -> str:
        return f"<tbody>\n{contents}</tbody>\n"
    
    def _add_li_tag(self, contents: str) -> str:
        return f"<li>{contents}</li>\n"
    
    def get_supported_formats(self) -> list:
        """Get supported formats"""
        return ["html", "htm"]