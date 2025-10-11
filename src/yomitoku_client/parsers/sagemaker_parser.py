"""
SageMaker Parser - For parsing SageMaker Yomitoku API outputs
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple
from pydantic import BaseModel, Field

from ..exceptions import ValidationError, DocumentAnalysisError


class Paragraph(BaseModel):
    """Paragraph data model"""
    box: List[int] = Field(description="Bounding box coordinates [x1, y1, x2, y2]")
    contents: str = Field(description="Text content")
    direction: str = Field(default="horizontal", description="Text direction")
    indent_level: Optional[int] = Field(default=None, description="Indentation level")
    order: int = Field(description="Reading order")
    role: Optional[str] = Field(default=None, description="Paragraph role")


class TableCell(BaseModel):
    """Table cell data model"""
    box: List[int] = Field(description="Bounding box coordinates")
    contents: str = Field(description="Cell content")
    col: int = Field(description="Column index")
    row: int = Field(description="Row index")
    col_span: int = Field(description="Column span")
    row_span: int = Field(description="Row span")


class Table(BaseModel):
    """Table data model"""
    box: List[int] = Field(description="Table bounding box")
    caption: Optional[Dict[str, Any]] = Field(default=None, description="Table caption")
    cells: List[TableCell] = Field(description="Table cells")
    cols: List[Dict[str, Any]] = Field(description="Column information")
    n_col: int = Field(description="Number of columns")
    n_row: int = Field(description="Number of rows")
    order: int = Field(description="Reading order")
    rows: List[Dict[str, Any]] = Field(description="Row information")
    spans: List[Any] = Field(default_factory=list, description="Cell spans")


class Figure(BaseModel):
    """Figure data model"""
    box: List[int] = Field(description="Bounding box coordinates")
    caption: Optional[Dict[str, Any]] = Field(default=None, description="Figure caption")
    decode: Optional[str] = Field(default=None, description="Decoded content")
    direction: str = Field(default="horizontal", description="Text direction")
    order: int = Field(description="Reading order")
    paragraphs: List[Paragraph] = Field(description="Figure paragraphs")
    role: Optional[str] = Field(default=None, description="Figure role")


class Word(BaseModel):
    """Word data model"""
    content: str = Field(description="Word content")
    det_score: float = Field(description="Detection score")
    direction: str = Field(description="Text direction")
    points: List[List[int]] = Field(description="Word polygon points")
    rec_score: float = Field(description="Recognition score")


class DocumentResult(BaseModel):
    """Document analysis result model"""
    figures: List[Figure] = Field(description="Detected figures")
    paragraphs: List[Paragraph] = Field(description="Detected paragraphs")
    preprocess: Dict[str, Any] = Field(description="Preprocessing information")
    tables: List[Table] = Field(description="Detected tables")
    words: List[Word] = Field(description="Detected words")
    
    def to_markdown(self, 
                   ignore_line_break: bool = False,
                   export_figure: bool = False,
                   export_figure_letter: bool = False,
                   table_format: str = "html",
                   output_path: Optional[str] = None
                   ) -> str:
        """
        Convert document result to Markdown format text
        
        Args:
            ignore_line_break: Whether to ignore line breaks in text
            export_figure: Whether to export figures
            export_figure_letter: Whether to export figure letters/text
            table_format: Table format ("html" or "md")
            output_path: Path to save the Markdown file
            
        Returns:
            str: Markdown formatted text
        """
        # Dynamic import to avoid circular imports
        from ..renderers.markdown_renderer import MarkdownRenderer
        
        # Create MarkdownRenderer instance
        renderer = MarkdownRenderer(
            ignore_line_break=ignore_line_break,
            export_figure=export_figure,
            export_figure_letter=export_figure_letter,
            table_format=table_format
        )
        if output_path is not None:
            renderer.save(self, output_path)
        return renderer.render(self)
    
    def to_html(self, 
                ignore_line_break: bool = False,
                export_figure: bool = True,
                export_figure_letter: bool = False,
                figure_width: int = 200,
                figure_dir: str = "figures",
                output_path: Optional[str] = None) -> str:
        """
        Convert document result to HTML format text
        
        Args:
            ignore_line_break: Whether to ignore line breaks in text
            export_figure: Whether to export figures
            export_figure_letter: Whether to export figure letters/text
            figure_width: Width of figures in pixels
            figure_dir: Directory to save figures
            output_path: Path to save the HTML file

        Returns:
            str: HTML formatted text
        """
        # Dynamic import to avoid circular imports
        from ..renderers.html_renderer import HTMLRenderer
        
        # Create HTMLRenderer instance
        renderer = HTMLRenderer(
            ignore_line_break=ignore_line_break,
            export_figure=export_figure,
            export_figure_letter=export_figure_letter,
            figure_width=figure_width,
            figure_dir=figure_dir
        )
        
        if output_path is not None:
            renderer.save(self, output_path)
        return renderer.render(self)
    
    def to_csv(self, 
               ignore_line_break: bool = False,
               export_figure: bool = True,
               export_figure_letter: bool = False,
               figure_dir: str = "figures",
               output_path: Optional[str] = None) -> str:
        """
        Convert document result to CSV format text
        
        Args:
            ignore_line_break: Whether to ignore line breaks in text
            export_figure: Whether to export figures
            export_figure_letter: Whether to export figure letters/text
            figure_dir: Directory to save figures
            output_path: Path to save the CSV file
        Returns:
            str: CSV formatted text
        """
        # Dynamic import to avoid circular imports
        from ..renderers.csv_renderer import CSVRenderer
        
        # Create CSVRenderer instance
        renderer = CSVRenderer(
            ignore_line_break=ignore_line_break,
            export_figure=export_figure,
            export_figure_letter=export_figure_letter,
            figure_dir=figure_dir
        )
        
        if output_path is not None:
            renderer.save(self, output_path)
        return renderer.render(self)
    
    def to_json(self, 
                ignore_line_break: bool = False,
                export_figure: bool = False,
                figure_dir: str = "figures",
                output_path: Optional[str] = None) -> str:
        """
        Convert document result to JSON format text
        
        Args:
            ignore_line_break: Whether to ignore line breaks in text
            export_figure: Whether to export figures
            figure_dir: Directory to save figures
            
        Returns:
            str: JSON formatted text
        """
        # Dynamic import to avoid circular imports
        from ..renderers.json_renderer import JSONRenderer
        
        # Create JSONRenderer instance
        renderer = JSONRenderer(
            ignore_line_break=ignore_line_break,
            export_figure=export_figure,
            figure_dir=figure_dir
        )
        
        if output_path is not None:
            renderer.save(self, output_path)
        return renderer.render(self)
    
    def to_pdf(self, 
               font_path: Optional[str] = None,
               output_path: Optional[str] = None,
               img: Optional[Any] = None,
               pdf: Optional[Any] = None) -> str:
        """
        Convert document result to PDF format (returns path to generated PDF)
        
        Args:
            font_path: Path to font file. If None, uses default MPLUS1p-Medium.ttf from resource
            output_path: Path to save the PDF file. If None, uses default name
            img: Optional image array, PIL Image, or image path for PDF generation
            pdf: Optional PDF path for PDF generation (alternative to img)

        Returns:
            str: Path to generated PDF file
        """
        # Dynamic import to avoid circular imports
        from ..renderers.pdf_renderer import PDFRenderer
        
        # Create PDFRenderer instance
        renderer = PDFRenderer(font_path=font_path)
        if output_path is not None:
            renderer.save(self, output_path, img=img, pdf=pdf)
        return renderer.render(self)
    
    def visualize(self, image_path: str, viz_type: str = 'layout_detail', output_path: Optional[str] = None, 
                  page_index: Optional[int] = None, dpi: int = 200, target_size: Optional[Tuple[int, int]] = None, **kwargs) -> Any:
        """
        Visualize document layout with bounding boxes
        
        Args:
            image_path: Path to the source image file or PDF file (string or pathlib.Path)
            viz_type: Type of visualization:
                - 'layout_detail': Detailed layout with all elements
                - 'layout_rough': Rough layout overview
                - 'reading_order': Show reading order arrows
                - 'ocr': OCR text visualization
                - 'detection': Detection bounding boxes
                - 'recognition': Recognition results
                - 'relationships': Element relationships
                - 'hierarchy': Element hierarchy
                - 'confidence': Confidence scores
                - 'captions': Caption visualization
            output_path: Optional path to save the visualization image
            page_index: Page index for PDF files (0-based, default: 0)
            dpi: DPI for PDF to image conversion (default: 200)
            target_size: Manual target size (width, height) for PDF conversion to ensure alignment
            **kwargs: Additional parameters for specific visualization types
            
        Returns:
            Any: Visualized image with bounding boxes drawn
        """
        # Dynamic import to avoid circular imports
        from ..visualizers.document_visualizer import DocumentVisualizer
        
        # Convert pathlib.Path to string if needed
        if hasattr(image_path, '__fspath__'):
            image_path = str(image_path)
        
        # Create DocumentVisualizer instance
        visualizer = DocumentVisualizer()
        
        # Visualize the document layout
        # Use types.SimpleNamespace for a cleaner approach
        from types import SimpleNamespace
        
        doc_data = SimpleNamespace(
            paragraphs=self.paragraphs,
            tables=self.tables,
            figures=self.figures,
            words=self.words
        )
        
        # Call the appropriate visualization method with PDF support
        result_img = visualizer.visualize(
            (image_path, doc_data), 
            type=viz_type, 
            page_index=page_index,
            dpi=dpi,
            target_size=target_size,
            **kwargs
        )
        
        # Save if output path is provided
        if output_path is not None:
            import cv2
            # Ensure output path has a valid image extension
            if not any(output_path.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']):
                output_path += '.png'  # Default to PNG if no extension
            cv2.imwrite(output_path, result_img)
        
        return result_img

    def export_viz_image(self, folder_path: str,output_filename: str = "0.png", viz_type: str = 'layout_detail', dpi: int = 200, target_size: Optional[Tuple[int, int]] = None, **kwargs) -> str:
        """
        Export visualized image to a folder with numbered filename
        
        Args:
            folder_path: Path to the folder to save image
            viz_type: Type of visualization ('layout_detail', 'ocr', etc.)
            dpi: DPI for PDF to image conversion
            target_size: Manual target size for PDF conversion
            **kwargs: Additional parameters for visualization
            
        Returns:
            str: Path to generated image file
        """
        import os
        
        # Create folder if it doesn't exist
        os.makedirs(folder_path, exist_ok=True)
        
        # Use filename "0.png" for single page
        output_path = os.path.join(folder_path, output_filename)
        
        # Visualize the page
        result_img = self.visualize(
            image_path=kwargs.get('image_path', ''),
            viz_type=viz_type,
            output_path=output_path,
            dpi=dpi,
            target_size=target_size,
            **{k: v for k, v in kwargs.items() if k != 'image_path'}
        )
        
        return output_path

    def export_tables(self, output_folder: Optional[str] = None, 
                        output_format: str = 'text') -> List[str]:
        """
        Extract table structures using TableExtractor
        
        Args:
            output_folder: Optional folder path to save all tables
            output_format: Output format ('text', 'html', 'json', 'csv')
            
        Returns:
            List[str]: List of paths to generated table files
        """
        import os
        
        # Dynamic import to avoid circular imports
        from ..visualizers.table_exporter import TableExtractor
        
        # Create TableExtractor instance
        table_viz = TableExtractor()
        
        # Ensure output folder exists if provided
        if output_folder is not None:
            os.makedirs(output_folder, exist_ok=True)
        
        # Process each table
        results = []
        output_paths = []
        
        for i, table in enumerate(self.tables):
            # Convert table to DataFrame for visualization
            import pandas as pd
            
            # Create a matrix to hold table data
            max_row = max(cell.row for cell in table.cells)
            max_col = max(cell.col for cell in table.cells)
            
            table_array = [[""] * max_col for _ in range(max_row)]
            for cell in table.cells:
                table_array[cell.row - 1][cell.col - 1] = cell.contents
            
            # Convert to DataFrame
            df = pd.DataFrame(table_array, columns=[f"Column_{i+1}" for i in range(max_col)])
            
            # Extract the table with specified format
            result = table_viz.visualize(df, format=output_format)
            results.append(result)
            
            # Save individual table if output folder is provided
            if output_folder is not None:
                # Generate output filename with appropriate extension
                if output_format == 'text':
                    ext = 'txt'
                elif output_format == 'html':
                    ext = 'html'
                elif output_format == 'json':
                    ext = 'json'
                elif output_format == 'csv':
                    ext = 'csv'
                else:
                    ext = 'txt'
                
                output_filename = f"table_{i+1}.{ext}"
                output_path = os.path.join(output_folder, output_filename)
                
                # Save the table
                if output_format == 'json':
                    import json
                    with open(output_path, 'w', encoding='utf-8') as f:
                        json.dump(result, f, ensure_ascii=False, indent=2)
                else:
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(str(result))
                
                output_paths.append(output_path)
        
        # Combine results based on format
        if output_format == 'json':
            # For JSON, combine as a list of objects
            combined_result = results if results else []
        else:
            # For text, html, csv, combine as strings
            separator = "\n\n" if output_format in ['text', 'html'] else "\n"
            combined_result = separator.join(str(result) for result in results) if results else "No tables found"
        
        return output_paths if output_folder is not None else combined_result
    

class MultiPageDocumentResult(BaseModel):
    """Multi-page document result model"""
    pages: List[DocumentResult] = Field(description="Pages of the document")
    
    def to_pdf(self, font_path: Optional[str] = None, output_path: Optional[str] = None, 
                img: Optional[Any] = None, pdf: Optional[Any] = None, create_text_pdf: bool = True) -> str:
        """
        Convert multi-page document result to PDF format (returns path to generated PDF)
        
        Args:
            font_path: Path to font file. If None, uses default MPLUS1p-Medium.ttf from resource
            output_path: Path to save the PDF file
            img: Optional image array for PDF generation (required for searchable PDF)
            pdf: Optional PDF array for PDF generation (required for searchable PDF)
            create_text_pdf: If True, creates a simple text-based PDF when image is not available
            
        Returns:
            str: Path to generated PDF file
        """
        import os
        
        # Generate default output path if not provided
        if output_path is None:
            output_path = "multipage_document.pdf"
        
        # Ensure output path has .pdf extension
        if not output_path.endswith('.pdf'):
            output_path += '.pdf'
        
        if img is not None or pdf is not None:
            # Use the existing PDFRenderer for searchable PDF generation
            from ..renderers.pdf_renderer import PDFRenderer
            renderer = PDFRenderer(font_path=font_path)
            
            if len(self.pages) == 1:
                # Single page - use the existing PDFRenderer
                renderer.save(self.pages[0], output_path, img=img, pdf=pdf)
            else:
                # Multiple pages - create individual PDFs and combine them
                import tempfile
                temp_files = []
                
                try:
                    # Create temporary directory for individual page PDFs
                    with tempfile.TemporaryDirectory() as temp_dir:
                        # Generate PDF for each page
                        for i, page in enumerate(self.pages, 1):
                            temp_pdf_path = os.path.join(temp_dir, f"page_{i}.pdf")
                            # Pass page index (0-based) for PDF processing
                            page_index = i - 1 if pdf is not None else None
                            renderer.save(page, temp_pdf_path, img=img, pdf=pdf, page_index=page_index)
                            temp_files.append(temp_pdf_path)
                        
                        # Combine all PDFs into one
                        self._combine_pdfs(temp_files, output_path)
                        
                except Exception as e:
                    # If combining fails, try to save as individual pages
                    print(f"Warning: Could not combine PDFs into single file: {e}")
                    print("Saving as individual page PDFs instead...")
                    
                    # Save each page as separate PDF
                    base_name = os.path.splitext(output_path)[0]
                    for i, page in enumerate(self.pages, 1):
                        page_output_path = f"{base_name}_page_{i}.pdf"
                        # Pass page index (0-based) for PDF processing
                        page_index = i - 1 if pdf is not None else None
                        renderer.save(page, page_output_path, img=img, pdf=pdf, page_index=page_index)
        else:
            # No image provided - create a simple text-based PDF
            if create_text_pdf:
                self._create_text_pdf(output_path, font_path)
            else:
                raise ValueError("Image is required for searchable PDF generation. Set create_text_pdf=True for simple text PDF.")
        
        return output_path
    
    def to_csv(self, output_path: str, page_index: Optional[int] = None) -> None:
        """
        Convert multi-page document result to CSV format
        
        Args:
            output_path: Path to save the CSV file
            page_index: Page index to convert
        """
        if page_index is None:
            page_index = 0
        self.pages[page_index].to_csv(output_path=output_path)
    
    def to_html(self, output_path: str, page_index: Optional[int] = None) -> None:
        """
        Convert multi-page document result to HTML format
        
        Args:
            output_path: Path to save the HTML file
            page_index: Page index to convert
        """
        if page_index is None:
            page_index = 0
        self.pages[page_index].to_html(output_path=output_path)

    def to_markdown(self, output_path: str, page_index: Optional[int] = None) -> None:
        """
        Convert multi-page document result to Markdown format
        
        Args:
            output_path: Path to save the Markdown file
            page_index: Page index to convert
        """
        if page_index is None:
            page_index = 0
        self.pages[page_index].to_markdown(output_path=output_path)
    
    def to_json(self, output_path: str, page_index: Optional[int] = None) -> None:
        """
        Convert multi-page document result to JSON format
        
        Args:
            output_path: Path to save the JSON file
            page_index: Page index to convert
        """
        if page_index is None:
            page_index = 0
        self.pages[page_index].to_json(output_path=output_path)

    def export_tables(self, output_folder: str = 'table_visualizations', 
                        output_format: str = 'text',page_index: Optional[int] = None) -> List[str]:
        """
        Export table structures for multi-page document using TableExtractor
        
        Args:
            output_folder: Folder to save all table extraction files
            output_format: Output format ('text', 'html', 'json', 'csv')
            page_index: Page index to convert
            
        Returns:
            List[str]: List of paths to generated table extraction files
        """
        import os
        os.makedirs(output_folder, exist_ok=True)
        if page_index is None:
            # Count total tables across all pages
            total_tables = sum(len(page.tables) for page in self.pages)
            print(f"Found {total_tables} tables across {len(self.pages)} pages")
            
            all_output_paths = []
            table_counter = 1
            
            # Process each page
            for i, page in enumerate(self.pages):
                # Print table count for this page
                page_table_count = len(page.tables)
                if page_table_count > 0:
                    print(f"Page {i+1}: {page_table_count} tables")
                
                # Process each table in this page
                for j, table in enumerate(page.tables):
                    # Convert table to DataFrame for extraction
                    import pandas as pd
                    from ..visualizers.table_exporter import TableExtractor
                    
                    # Create TableExtractor instance
                    table_viz = TableExtractor()
                    
                    # Create a matrix to hold table data
                    max_row = max(cell.row for cell in table.cells)
                    max_col = max(cell.col for cell in table.cells)
                    
                    table_array = [[""] * max_col for _ in range(max_row)]
                    for cell in table.cells:
                        table_array[cell.row - 1][cell.col - 1] = cell.contents
                    
                    # Convert to DataFrame
                    df = pd.DataFrame(table_array, columns=[f"Column_{k+1}" for k in range(max_col)])
                    
                    # Extract the table with specified format
                    result = table_viz.visualize(df, format=output_format)
                    
                    # Generate output filename with global table numbering
                    if output_format == 'text':
                        ext = 'txt'
                    elif output_format == 'html':
                        ext = 'html'
                    elif output_format == 'json':
                        ext = 'json'
                    elif output_format == 'csv':
                        ext = 'csv'
                    else:
                        ext = 'txt'
                    
                    output_filename = f"table_{table_counter}.{ext}"
                    output_path = os.path.join(output_folder, output_filename)
                    
                    # Save the table
                    if output_format == 'json':
                        import json
                        with open(output_path, 'w', encoding='utf-8') as f:
                            json.dump(result, f, ensure_ascii=False, indent=2)
                    else:
                        with open(output_path, 'w', encoding='utf-8') as f:
                            f.write(str(result))
                    
                    all_output_paths.append(output_path)
                    table_counter += 1
            
            return all_output_paths
        else:
            return self.pages[page_index].export_tables(output_folder=output_folder,output_format=output_format)
 
    def _create_text_pdf(self, output_path: str, font_path: Optional[str] = None) -> None:
        """
        Create a simple text-based PDF from document content
        
        Args:
            output_path: Path to save the PDF file
            font_path: Path to font file
        """
        try:
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.lib import colors
            
            # Create PDF document
            doc = SimpleDocTemplate(output_path, pagesize=A4)
            styles = getSampleStyleSheet()
            story = []
            
            # Create custom style for content
            content_style = ParagraphStyle(
                'CustomContent',
                parent=styles['Normal'],
                fontSize=12,
                spaceAfter=12,
            )
            
            # Process each page
            for page_num, page in enumerate(self.pages, 1):
                if page_num > 1:
                    story.append(Spacer(1, 0.5*inch))
                
                # Add page header
                story.append(Paragraph(f"<b>Page {page_num}</b>", styles['Heading2']))
                story.append(Spacer(1, 0.2*inch))
                
                # Add paragraphs
                for paragraph in page.paragraphs:
                    if paragraph.role == "section_headings":
                        story.append(Paragraph(f"<b>{paragraph.contents}</b>", styles['Heading3']))
                    else:
                        story.append(Paragraph(paragraph.contents, content_style))
                    story.append(Spacer(1, 0.1*inch))
                
                # Add tables
                for table in page.tables:
                    if table.cells:
                        # Create table data
                        table_data = []
                        max_row = max(cell.row for cell in table.cells)
                        max_col = max(cell.col for cell in table.cells)
                        
                        # Initialize table structure
                        for row in range(1, max_row + 1):
                            table_row = []
                            for col in range(1, max_col + 1):
                                table_row.append("")
                            table_data.append(table_row)
                        
                        # Fill table data
                        for cell in table.cells:
                            if cell.row <= max_row and cell.col <= max_col:
                                table_data[cell.row - 1][cell.col - 1] = cell.contents
                        
                        # Create table
                        if table_data:
                            pdf_table = Table(table_data)
                            pdf_table.setStyle(TableStyle([
                                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                ('FONTSIZE', (0, 0), (-1, 0), 14),
                                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                                ('GRID', (0, 0), (-1, -1), 1, colors.black)
                            ]))
                            story.append(pdf_table)
                            story.append(Spacer(1, 0.2*inch))
            
            # Build PDF
            doc.build(story)
            
        except ImportError:
            raise ImportError(
                "Text PDF generation requires reportlab library. "
                "Please install it: pip install reportlab"
            )
    
    def _combine_pdfs(self, pdf_files: List[str], output_path: str) -> None:
        """
        Combine multiple PDF files into a single PDF
        
        Args:
            pdf_files: List of paths to PDF files to combine
            output_path: Path for the combined PDF file
        """
        try:
            # Try to use PyPDF2 if available
            from PyPDF2 import PdfMerger
            
            merger = PdfMerger()
            for pdf_file in pdf_files:
                if os.path.exists(pdf_file):
                    merger.append(pdf_file)
            
            with open(output_path, 'wb') as output_file:
                merger.write(output_file)
            merger.close()
            
        except ImportError:
            # Fallback: try to use pypdf if PyPDF2 is not available
            try:
                import pypdf
                
                merger = pypdf.PdfMerger()
                for pdf_file in pdf_files:
                    if os.path.exists(pdf_file):
                        merger.append(pdf_file)
                
                with open(output_path, 'wb') as output_file:
                    merger.write(output_file)
                merger.close()
                
            except ImportError:
                # If neither library is available, raise an error
                raise ImportError(
                    "PDF combining requires either PyPDF2 or pypdf library. "
                    "Please install one of them: pip install PyPDF2 or pip install pypdf"
                )
    
    def to_csv_folder(self, folder_path: str, 
                      ignore_line_break: bool = False,
                      export_figure: bool = True,
                      export_figure_letter: bool = False,
                      figure_dir: str = "figures") -> List[str]:
        """
        Convert multi-page document result to CSV files in a folder
        
        Args:
            folder_path: Path to the folder to save CSV files
            ignore_line_break: Whether to ignore line breaks in text
            export_figure: Whether to export figures
            export_figure_letter: Whether to export figure letters/text
            figure_dir: Directory to save figures
            
        Returns:
            List[str]: List of paths to generated CSV files
        """
        import os
        
        # Create folder if it doesn't exist
        os.makedirs(folder_path, exist_ok=True)
        
        csv_files = []
        
        for i, page in enumerate(self.pages, 1):
            # Generate CSV content for this page
            csv_content = page.to_csv(
                ignore_line_break=ignore_line_break,
                export_figure=export_figure,
                export_figure_letter=export_figure_letter,
                figure_dir=figure_dir
            )
            
            # Save to file
            csv_filename = f"page{i}.csv"
            csv_path = os.path.join(folder_path, csv_filename)
            
            with open(csv_path, 'w', encoding='utf-8') as f:
                f.write(csv_content)
            
            csv_files.append(csv_path)
        
        return csv_files
    
    def to_html_folder(self, folder_path: str,
                       ignore_line_break: bool = False,
                       export_figure: bool = True,
                       export_figure_letter: bool = False,
                       figure_width: int = 200,
                       figure_dir: str = "figures") -> List[str]:
        """
        Convert multi-page document result to HTML files in a folder
        
        Args:
            folder_path: Path to the folder to save HTML files
            ignore_line_break: Whether to ignore line breaks in text
            export_figure: Whether to export figures
            export_figure_letter: Whether to export figure letters/text
            figure_width: Width of figures in pixels
            figure_dir: Directory to save figures
            
        Returns:
            List[str]: List of paths to generated HTML files
        """
        import os
        
        # Create folder if it doesn't exist
        os.makedirs(folder_path, exist_ok=True)
        
        html_files = []
        
        for i, page in enumerate(self.pages, 1):
            # Generate HTML content for this page
            html_content = page.to_html(
                ignore_line_break=ignore_line_break,
                export_figure=export_figure,
                export_figure_letter=export_figure_letter,
                figure_width=figure_width,
                figure_dir=figure_dir
            )
            
            # Save to file
            html_filename = f"page{i}.html"
            html_path = os.path.join(folder_path, html_filename)
            
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            html_files.append(html_path)
        
        return html_files
    
    def to_markdown_folder(self, folder_path: str,
                           ignore_line_break: bool = False,
                           export_figure: bool = False,
                           export_figure_letter: bool = False,
                           table_format: str = "html") -> List[str]:
        """
        Convert multi-page document result to Markdown files in a folder
        
        Args:
            folder_path: Path to the folder to save Markdown files
            ignore_line_break: Whether to ignore line breaks in text
            export_figure: Whether to export figures
            export_figure_letter: Whether to export figure letters/text
            table_format: Table format ("html" or "md")
            
        Returns:
            List[str]: List of paths to generated Markdown files
        """
        import os
        
        # Create folder if it doesn't exist
        os.makedirs(folder_path, exist_ok=True)
        
        markdown_files = []
        
        for i, page in enumerate(self.pages, 1):
            # Generate Markdown content for this page
            markdown_content = page.to_markdown(
                ignore_line_break=ignore_line_break,
                export_figure=export_figure,
                export_figure_letter=export_figure_letter,
                table_format=table_format
            )
            
            # Save to file
            markdown_filename = f"page{i}.md"
            markdown_path = os.path.join(folder_path, markdown_filename)
            
            with open(markdown_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            markdown_files.append(markdown_path)
        
        return markdown_files
    
    def to_json_folder(self, folder_path: str,
                       ignore_line_break: bool = False,
                       export_figure: bool = False,
                       figure_dir: str = "figures") -> List[str]:
        """
        Convert multi-page document result to JSON files in a folder
        
        Args:
            folder_path: Path to the folder to save JSON files
            ignore_line_break: Whether to ignore line breaks in text
            export_figure: Whether to export figures
            figure_dir: Directory to save figures
            
        Returns:
            List[str]: List of paths to generated JSON files
        """
        import os
        
        # Create folder if it doesn't exist
        os.makedirs(folder_path, exist_ok=True)
        
        json_files = []
        
        for i, page in enumerate(self.pages, 1):
            # Generate JSON content for this page
            json_content = page.to_json(
                ignore_line_break=ignore_line_break,
                export_figure=export_figure,
                figure_dir=figure_dir
            )
            
            # Save to file
            json_filename = f"page{i}.json"
            json_path = os.path.join(folder_path, json_filename)
            
            with open(json_path, 'w', encoding='utf-8') as f:
                f.write(json_content)
            
            json_files.append(json_path)
        
        return json_files

    def visualize(self, image_path: str, viz_type: str = 'layout_detail', output_path: Optional[str] = None, 
                  page_index: Optional[int] = None, dpi: int = 200, target_size: Optional[Tuple[int, int]] = None, **kwargs) -> Any:
        """
        Visualize the document result
        """
        
        return self.pages[page_index].visualize(image_path=image_path, viz_type=viz_type, output_path=output_path, page_index=page_index, dpi=dpi, target_size=target_size, **kwargs)
    
    def export_viz_images(self, image_path: str,folder_path: str, viz_type: str = 'layout_detail', page_index: Optional[int] = None, dpi: int = 200, target_size: Optional[Tuple[int, int]] = None, **kwargs) -> List[str]:
        """
        Export visualized images to a folder with numbered filenames
        
        Args:
            folder_path: Path to the folder to save images
            viz_type: Type of visualization ('layout_detail', 'ocr', etc.)
            page_index: Specific page index to visualize (None for all pages)
            dpi: DPI for PDF to image conversion
            target_size: Manual target size for PDF conversion
            **kwargs: Additional parameters for visualization
            
        Returns:
            List[str]: List of paths to generated image files
        """
        import os
        
        # Create folder if it doesn't exist
        os.makedirs(folder_path, exist_ok=True)
        
        output_paths = []
        
        if page_index is not None:
            # Visualize specific page
            output_filename = f"{page_index}.png"
            
            # Get the page data
            page_data = self.pages[page_index]
            
            # Use export_viz_image method
            output_path = page_data.export_viz_image(
                image_path=image_path,
                folder_path=folder_path,
                viz_type=viz_type,
                dpi=dpi,
                target_size=target_size,
                **kwargs
            )
            
            output_paths.append(output_path)
        else:
            # Visualize all pages
            for i, page_data in enumerate(self.pages):
                output_filename = f"{i}.png"
                # Use export_viz_image method
                output_path = page_data.export_viz_image(
                    image_path=image_path,
                    output_filename = f"{i}.png",
                    folder_path=folder_path,
                    viz_type=viz_type,
                    page_index=i,
                    dpi=dpi,
                    target_size=target_size,                    
                    **kwargs
                )
                
                output_paths.append(output_path)
        
        return output_paths
    
class SageMakerParser:
    """Parser for SageMaker Yomitoku API outputs"""
    
    def __init__(self):
        """Initialize the parser"""
        pass
    
    def parse_dict(self, data: Dict[str, Any]) -> MultiPageDocumentResult:
        """
        Parse dictionary data from SageMaker output
        
        Args:
            data: Dictionary from SageMaker
            
        Returns:
            MultiPageDocumentResult: Multi-page document result containing all pages
            
        Raises:
            ValidationError: If data format is invalid
            DocumentAnalysisError: If parsing fails
        """
        try:
            if "result" not in data or not data["result"]:
                raise ValidationError("Invalid SageMaker output format: missing 'result' field")

            # Handle both single result and multiple results
            if isinstance(data["result"], list):
                if len(data["result"]) == 0:
                    raise ValidationError("Empty result list")
                # Create pages from all results
                pages = [DocumentResult(**result_data) for result_data in data["result"]]
            else:
                # Single result, create single page
                pages = [DocumentResult(**data["result"])]
            
            return MultiPageDocumentResult(pages=pages)
        except Exception as e:
            raise DocumentAnalysisError(f"Failed to parse document: {e}")
    
    def parse_json(self, json_data: str) -> MultiPageDocumentResult:
        """
        Parse JSON data from SageMaker output
        
        Args:
            json_data: JSON string from SageMaker
            
        Returns:
            MultiPageDocumentResult: Multi-page document result containing all pages
            
        Raises:
            ValidationError: If JSON format is invalid
            DocumentAnalysisError: If parsing fails
        """
        try:
            data = json.loads(json_data)
            return self.parse_dict(data)
            
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON format: {e}")
        except Exception as e:
            raise DocumentAnalysisError(f"Failed to parse document: {e}")
    
    def parse_file(self, file_path: str) -> MultiPageDocumentResult:
        """
        Parse JSON file from SageMaker output
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            MultiPageDocumentResult: Multi-page document result containing all pages
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json_data = f.read()
            return self.parse_json(json_data)
        except FileNotFoundError:
            raise DocumentAnalysisError(f"File not found: {file_path}")
        except Exception as e:
            raise DocumentAnalysisError(f"Failed to read file: {e}")
    
    def validate_result(self, result: DocumentResult) -> bool:
        """
        Validate parsed result
        
        Args:
            result: Parsed document result
            
        Returns:
            bool: True if valid
        """
        # Basic validation checks
        if not result.paragraphs and not result.tables and not result.figures:
            return False
        
        # Validate paragraph orders
        if result.paragraphs:
            orders = [p.order for p in result.paragraphs]
            if len(orders) != len(set(orders)):
                return False
        
        return True
