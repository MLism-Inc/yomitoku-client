import json
import os
import cv2
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, Field
import pypdfium2 as pdfium

from PIL import Image

from .utils import load_image, load_pdf, make_page_index
from .visualizers.document_visualizer import DocumentVisualizer


def merge_pdf_packets_to_file(packets, out_path):
    """
    packets: List[BytesIO]  （各要素は seek(0) 済みのPDF）
    """
    assert len(packets) >= 1
    # 先頭をベースにする
    packets[0].seek(0)
    doc = pdfium.PdfDocument(packets[0])
    for buf in packets[1:]:
        buf.seek(0)
        src = pdfium.PdfDocument(buf)
        page_count = len(src)
        doc.import_pages(src, list(range(page_count)))  # 全ページ追加
    doc.save(out_path)


def correct_rotation_image(
    img,
    angle: float,
):
    if int(angle) == 90:
        return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
    elif int(angle) == 180:
        return cv2.rotate(img, cv2.ROTATE_180)
    elif int(angle) == -90:
        return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)

    return img


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
    caption: Optional[Union[Paragraph, None]] = Field(
        default=None, description="Table caption"
    )
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
    caption: Optional[Union[Paragraph, None]] = Field(
        default=None, description="Table caption"
    )
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

    num_page: int = Field(description="Page index in the original document")
    figures: List[Figure] = Field(description="Detected figures")
    paragraphs: List[Paragraph] = Field(description="Detected paragraphs")
    preprocess: Dict[str, Any] = Field(description="Preprocessing information")
    tables: List[Table] = Field(description="Detected tables")
    words: List[Word] = Field(description="Detected words")

    def to_markdown(
        self,
        img=None,
        output_path: Optional[Union[str, Path]] = None,
        ignore_line_break: bool = False,
        export_figure: bool = True,
        export_figure_letter: bool = False,
        table_format: str = "html",
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
        from .renderers.markdown_renderer import MarkdownRenderer

        # Create MarkdownRenderer instance
        renderer = MarkdownRenderer(
            ignore_line_break=ignore_line_break,
            export_figure=export_figure,
            export_figure_letter=export_figure_letter,
            table_format=table_format,
        )
        return renderer.render(
            self,
            img=img,
            output_path=output_path,
            page=self.num_page,
        )

    def to_html(
        self,
        img: Optional[Union[str, Path]] = None,
        output_path: Optional[Union[str, Path]] = None,
        ignore_line_break: bool = False,
        export_figure: bool = True,
        export_figure_letter: bool = False,
        figure_width: int = 200,
        figure_dir: str = "figures",
    ) -> str:
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
        from .renderers.html_renderer import HTMLRenderer

        # Create HTMLRenderer instance
        renderer = HTMLRenderer(
            ignore_line_break=ignore_line_break,
            export_figure=export_figure,
            export_figure_letter=export_figure_letter,
            figure_width=figure_width,
            figure_dir=figure_dir,
        )

        # if output_path is not None:
        #    renderer.save(self, output_path)
        return renderer.render(
            self,
            img=img,
            output_path=output_path,
            page=self.num_page,
        )

    def to_csv(
        self,
        ignore_line_break: bool = False,
        export_figure: bool = True,
        export_figure_letter: bool = False,
        figure_dir: str = "figures",
        output_path: Optional[str] = None,
    ) -> str:
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
        from .renderers.csv_renderer import CSVRenderer

        # Create CSVRenderer instance
        renderer = CSVRenderer(
            ignore_line_break=ignore_line_break,
            export_figure=export_figure,
            export_figure_letter=export_figure_letter,
            figure_dir=figure_dir,
        )

        if output_path is not None:
            renderer.save(self, output_path)
        return renderer.render(self)

    def to_json(
        self,
        img=None,
        ignore_line_break: bool = False,
        export_figure: bool = False,
        figure_dir: str = "figures",
    ) -> str:
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
        from .renderers.json_renderer import JSONRenderer

        # Create JSONRenderer instance
        renderer = JSONRenderer(
            ignore_line_break=ignore_line_break,
            export_figure=export_figure,
            figure_dir=figure_dir,
        )

        return renderer.render(self, img=img)

    def to_pdf(
        self,
        font_path: Optional[str] = None,
        img: Optional[Any] = None,
    ) -> str:
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
        from .renderers.pdf_renderer import PDFRenderer

        # Create PDFRenderer instance
        renderer = PDFRenderer(font_path=font_path)
        return renderer.render(
            self,
            img=img,
        )

    def visualize(
        self,
        img,
        mode: str = "layout_detail",
    ) -> Any:
        """
        Visualize document layout with bounding boxes

        Args:
            imag: Path to the source image file or PDF file (string or pathlib.Path)
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
        Returns:
            Any: Visualized image with bounding boxes drawn
        """
        # Create DocumentVisualizer instance
        visualizer = DocumentVisualizer()

        # Visualize the document layout
        # Use types.SimpleNamespace for a cleaner approach
        from types import SimpleNamespace

        results = SimpleNamespace(
            paragraphs=self.paragraphs,
            tables=self.tables,
            figures=self.figures,
            words=self.words,
        )

        # Call the appropriate visualization method with PDF support
        result_img = visualizer.visualize(
            img,
            results,
            mode=mode,
        )

        return result_img

    def export_tables(
        self, output_folder: Optional[str] = None, output_format: str = "text"
    ) -> List[str]:
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
        from .visualizers.table_exporter import TableExtractor

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
            df = pd.DataFrame(
                table_array, columns=[f"Column_{i + 1}" for i in range(max_col)]
            )

            # Extract the table with specified format
            result = table_viz.visualize(df, format=output_format)
            results.append(result)

            # Save individual table if output folder is provided
            if output_folder is not None:
                # Generate output filename with appropriate extension
                if output_format == "text":
                    ext = "txt"
                elif output_format == "html":
                    ext = "html"
                elif output_format == "json":
                    ext = "json"
                elif output_format == "csv":
                    ext = "csv"
                else:
                    ext = "txt"

                output_filename = f"table_{i + 1}.{ext}"
                output_path = os.path.join(output_folder, output_filename)

                # Save the table
                if output_format == "json":
                    import json

                    with open(output_path, "w", encoding="utf-8") as f:
                        json.dump(result, f, ensure_ascii=False, indent=2)
                else:
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(str(result))

                output_paths.append(output_path)

        # Combine results based on format
        if output_format == "json":
            # For JSON, combine as a list of objects
            combined_result = results if results else []
        else:
            # For text, html, csv, combine as strings
            separator = "\n\n" if output_format in ["text", "html"] else "\n"
            combined_result = (
                separator.join(str(result) for result in results)
                if results
                else "No tables found"
            )

        return output_paths if output_folder is not None else combined_result


class MultiPageDocumentResult(BaseModel):
    """Multi-page document result model"""

    pages: Dict[int, DocumentResult] = Field(
        description="Dictionary of page index to DocumentResult"
    )

    def to_pdf(
        self,
        image_path: Union[str, Path],
        output_path,
        page_index: list = None,
        font_path: Optional[str] = None,
        dpi: int = 200,
        mode="combine",
    ) -> str:
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
        page_index = make_page_index(page_index, len(self.pages))

        base_dir = os.path.dirname(output_path)
        if base_dir:
            os.makedirs(base_dir, exist_ok=True)

        if image_path is not None:
            basename, ext = os.path.splitext(os.path.basename(image_path))
            if ext.lower() == ".pdf":
                images = load_pdf(image_path, dpi=dpi)
            else:
                images = load_image(image_path)

        results = []
        for idx in page_index:
            corrected_img = None
            if image_path is not None:
                corrected_img = correct_rotation_image(
                    images[idx],
                    angle=self.pages[idx].preprocess.get("angle", 0),
                )

            results.append(
                self.pages[idx].to_pdf(
                    img=Image.fromarray(corrected_img[:, :, ::-1]),
                )
            )

        base_name, ext = os.path.splitext(output_path)
        if mode == "combine":
            merge_pdf_packets_to_file(
                results,
                out_path=output_path,
            )
        elif mode == "separate":
            for i, content in zip(page_index, results):
                page_output_path = f"{base_name}_page_{i + 1}{ext}"
                with open(page_output_path, "wb") as f:
                    f.write(content.getvalue())

    def export_file(
        self,
        results,
        output_path: str,
        mode: str,
        encoding: str,
        page_index: list,
    ) -> None:
        base_name, ext = os.path.splitext(output_path)
        if mode == "combine":
            if ext == ".json":
                with open(output_path, "w", encoding=encoding) as f:
                    json.dump(
                        results,
                        f,
                        ensure_ascii=False,
                        indent=2,
                    )
            else:
                combined_content = "\n".join(results)
                with open(output_path, "w", encoding=encoding) as f:
                    f.write(combined_content)

        elif mode == "separate":
            for i, content in zip(page_index, results):
                page_output_path = f"{base_name}_page_{i}{ext}"

                if ext == ".json":
                    with open(page_output_path, "w", encoding=encoding) as f:
                        json.dump(
                            content,
                            f,
                            ensure_ascii=False,
                            indent=2,
                        )
                else:
                    with open(page_output_path, "w", encoding=encoding) as f:
                        f.write(content)

    def to_csv(
        self,
        output_path: str,
        encoding: str = "utf-8",
        mode="combine",
        page_index: list = None,
        **kwargs,
    ) -> None:
        """
        Convert multi-page document result to CSV format

        Args:
            output_path: Path to save the Markdown file
            page_index: Page index to convert
            encoding: File encoding
            mode: 'combine' to combine all pages into one file, 'separate' to save each page separately
        """
        page_index = make_page_index(page_index, len(self.pages))

        base_dir = os.path.dirname(output_path)
        if base_dir:
            os.makedirs(base_dir, exist_ok=True)

        results = []
        for idx in page_index:
            results.append(self.pages[idx].to_csv(**kwargs))

        self.export_file(
            results,
            output_path=output_path,
            mode=mode,
            encoding=encoding,
            page_index=page_index,
        )

        return results

    def to_html(
        self,
        output_path: str,
        encoding: str = "utf-8",
        mode="combine",
        page_index: list = None,
        image_path: Optional[Union[str, Path]] = None,
        dpi: int = 200,
        **kwargs,
    ) -> None:
        """
        Convert multi-page document result to HTML format

        Args:
            output_path: Path to save the Markdown file
            page_index: Page index to convert
            encoding: File encoding
            mode: 'combine' to combine all pages into one file, 'separate' to save each page separately
        """
        page_index = make_page_index(page_index, len(self.pages))

        base_dir = os.path.dirname(output_path)
        if base_dir:
            os.makedirs(base_dir, exist_ok=True)

        if image_path is not None:
            basename, ext = os.path.splitext(os.path.basename(image_path))
            if ext.lower() == ".pdf":
                images = load_pdf(image_path, dpi=dpi)
            else:
                images = load_image(image_path)

        results = []
        for idx in page_index:
            if image_path is not None:
                corrected_img = correct_rotation_image(
                    images[idx],
                    angle=self.pages[idx].preprocess.get("angle", 0),
                )
            else:
                corrected_img = None

            results.append(
                self.pages[idx].to_html(
                    **kwargs,
                    img=corrected_img,
                    output_path=output_path,
                )
            )

        self.export_file(
            results,
            output_path=output_path,
            mode=mode,
            encoding=encoding,
            page_index=page_index,
        )

        return results

    def to_markdown(
        self,
        output_path: str,
        encoding: str = "utf-8",
        mode="combine",
        page_index: list = None,
        image_path: Optional[Union[str, Path]] = None,
        dpi: int = 200,
        **kwargs,
    ) -> None:
        """
        Convert multi-page document result to Markdown format

        Args:
            output_path: Path to save the Markdown file
            page_index: Page index to convert
            encoding: File encoding
            mode: 'combine' to combine all pages into one file, 'separate' to save each page separately
        """
        page_index = make_page_index(page_index, len(self.pages))

        base_dir = os.path.dirname(output_path)
        if base_dir:
            os.makedirs(base_dir, exist_ok=True)

        if image_path is not None:
            basename, ext = os.path.splitext(os.path.basename(image_path))
            if ext.lower() == ".pdf":
                images = load_pdf(image_path, dpi=dpi)
            else:
                images = load_image(image_path)

        results = []
        for idx in page_index:
            corrected_img = None
            if image_path is not None:
                corrected_img = correct_rotation_image(
                    images[idx],
                    angle=self.pages[idx].preprocess.get("angle", 0),
                )

            results.append(
                self.pages[idx].to_markdown(
                    img=corrected_img,
                    output_path=output_path,
                    **kwargs,
                )
            )

        self.export_file(
            results,
            output_path=output_path,
            mode=mode,
            encoding=encoding,
            page_index=page_index,
        )

        return results

    def to_json(
        self,
        output_path: str,
        encoding: str = "utf-8",
        mode="combine",
        page_index: list = None,
        image_path: Optional[Union[str, Path]] = None,
        dpi: int = 200,
        **kwargs,
    ) -> None:
        """
        Convert multi-page document result to JSON format

        Args:
            output_path: Path to save the Markdown file
            page_index: Page index to convert
            encoding: File encoding
            mode: 'combine' to combine all pages into one file, 'separate' to save each page separately
        """
        base_dir = os.path.dirname(output_path)
        if base_dir:
            os.makedirs(base_dir, exist_ok=True)

        page_index = make_page_index(page_index, len(self.pages))
        if image_path is not None:
            basename, ext = os.path.splitext(os.path.basename(image_path))
            if ext.lower() == ".pdf":
                images = load_pdf(image_path, dpi=dpi)
            else:
                images = load_image(image_path)

        results = []
        for idx in page_index:
            if image_path is not None:
                corrected_img = correct_rotation_image(
                    images[idx],
                    angle=self.pages[idx].preprocess.get("angle", 0),
                )
            else:
                corrected_img = None

            results.append(self.pages[idx].to_json(**kwargs, img=corrected_img))

        self.export_file(
            results,
            output_path=output_path,
            mode=mode,
            encoding=encoding,
            page_index=page_index,
        )

        return results

    def export_tables(
        self,
        output_folder: str = "table_visualizations",
        output_format: str = "text",
        page_index: Optional[int] = None,
    ) -> List[str]:
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
                    print(f"Page {i + 1}: {page_table_count} tables")

                # Process each table in this page
                for j, table in enumerate(page.tables):
                    # Convert table to DataFrame for extraction
                    import pandas as pd

                    from .visualizers.table_exporter import TableExtractor

                    # Create TableExtractor instance
                    table_viz = TableExtractor()

                    # Create a matrix to hold table data
                    max_row = max(cell.row for cell in table.cells)
                    max_col = max(cell.col for cell in table.cells)

                    table_array = [[""] * max_col for _ in range(max_row)]
                    for cell in table.cells:
                        table_array[cell.row - 1][cell.col - 1] = cell.contents

                    # Convert to DataFrame
                    df = pd.DataFrame(
                        table_array, columns=[f"Column_{k + 1}" for k in range(max_col)]
                    )

                    # Extract the table with specified format
                    result = table_viz.visualize(df, format=output_format)

                    # Generate output filename with global table numbering
                    if output_format == "text":
                        ext = "txt"
                    elif output_format == "html":
                        ext = "html"
                    elif output_format == "json":
                        ext = "json"
                    elif output_format == "csv":
                        ext = "csv"
                    else:
                        ext = "txt"

                    output_filename = f"table_{table_counter}.{ext}"
                    output_path = os.path.join(output_folder, output_filename)

                    # Save the table
                    if output_format == "json":
                        import json

                        with open(output_path, "w", encoding="utf-8") as f:
                            json.dump(result, f, ensure_ascii=False, indent=2)
                    else:
                        with open(output_path, "w", encoding="utf-8") as f:
                            f.write(str(result))

                    all_output_paths.append(output_path)
                    table_counter += 1

            return all_output_paths
        else:
            return self.pages[page_index].export_tables(
                output_folder=output_folder, output_format=output_format
            )

    def visualize(
        self,
        image_path: str,
        mode: str = "layout",
        output_directory: Optional[str] = None,
        page_index: list = None,
        dpi: int = 200,
    ) -> Any:
        """
        Visualize the document result
        """

        page_index = make_page_index(page_index, len(self.pages))

        if output_directory is not None:
            os.makedirs(output_directory, exist_ok=True)

        basename, ext = os.path.splitext(os.path.basename(image_path))
        if ext.lower() == ".pdf":
            images = load_pdf(image_path, dpi=dpi)
        else:
            images = load_image(image_path)

        basename, _ext = os.path.splitext(os.path.basename(image_path))

        visualize_imgs = []
        for index in page_index:
            corrected_img = correct_rotation_image(
                images[index],
                angle=self.pages[index].preprocess.get("angle", 0),
            )

            visualize_img = self.pages[index].visualize(
                corrected_img,
                mode=mode,
            )

            path_output = basename + f"_{mode}_page_{index}.jpg"

            if output_directory is not None:
                path_output = os.path.join(output_directory, path_output)

            cv2.imwrite(path_output, visualize_img)
            visualize_imgs.append(visualize_img)

        return visualize_imgs

    def export_viz_images(
        self,
        image_path: str,
        folder_path: str,
        viz_type: str = "layout_detail",
        page_index: Optional[int] = None,
        dpi: int = 200,
        target_size: Optional[Tuple[int, int]] = None,
        **kwargs,
    ) -> List[str]:
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
                **kwargs,
            )

            output_paths.append(output_path)
        else:
            # Visualize all pages
            for i, page_data in enumerate(self.pages):
                output_filename = f"{i}.png"
                # Use export_viz_image method
                output_path = page_data.export_viz_image(
                    image_path=image_path,
                    output_filename=f"{i}.png",
                    folder_path=folder_path,
                    viz_type=viz_type,
                    page_index=i,
                    dpi=dpi,
                    target_size=target_size,
                    **kwargs,
                )

                output_paths.append(output_path)

        return output_paths
