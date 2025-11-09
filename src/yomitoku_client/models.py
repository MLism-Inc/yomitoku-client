import json
import os
from pathlib import Path
from typing import Any

import cv2
import pypdfium2 as pdfium
from PIL import Image
from pydantic import BaseModel, Field

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

    box: list[int] = Field(description="Bounding box coordinates [x1, y1, x2, y2]")
    contents: str = Field(description="Text content")
    direction: str = Field(default="horizontal", description="Text direction")
    indent_level: int | None = Field(default=None, description="Indentation level")
    order: int = Field(description="Reading order")
    role: str | None = Field(default=None, description="Paragraph role")


class TableCell(BaseModel):
    """Table cell data model"""

    box: list[int] = Field(description="Bounding box coordinates")
    contents: str = Field(description="Cell content")
    col: int = Field(description="Column index")
    row: int = Field(description="Row index")
    col_span: int = Field(description="Column span")
    row_span: int = Field(description="Row span")


class Table(BaseModel):
    """Table data model"""

    box: list[int] = Field(description="Table bounding box")
    caption: Paragraph | None = Field(
        default=None,
        description="Table caption",
    )
    cells: list[TableCell] = Field(description="Table cells")
    cols: list[dict[str, Any]] = Field(description="Column information")
    n_col: int = Field(description="Number of columns")
    n_row: int = Field(description="Number of rows")
    order: int = Field(description="Reading order")
    rows: list[dict[str, Any]] = Field(description="Row information")
    spans: list[Any] = Field(default_factory=list, description="Cell spans")


class Figure(BaseModel):
    """Figure data model"""

    box: list[int] = Field(description="Bounding box coordinates")
    caption: Paragraph | None = Field(
        default=None,
        description="Table caption",
    )
    decode: str | None = Field(default=None, description="Decoded content")
    direction: str = Field(default="horizontal", description="Text direction")
    order: int = Field(description="Reading order")
    paragraphs: list[Paragraph] = Field(description="Figure paragraphs")
    role: str | None = Field(default=None, description="Figure role")


class Word(BaseModel):
    """Word data model"""

    content: str = Field(description="Word content")
    det_score: float = Field(description="Detection score")
    direction: str = Field(description="Text direction")
    points: list[list[int]] = Field(description="Word polygon points")
    rec_score: float = Field(description="Recognition score")


class DocumentResult(BaseModel):
    """Document analysis result model"""

    num_page: int = Field(description="Page index in the original document")
    figures: list[Figure] = Field(description="Detected figures")
    paragraphs: list[Paragraph] = Field(description="Detected paragraphs")
    preprocess: dict[str, Any] = Field(description="Preprocessing information")
    tables: list[Table] = Field(description="Detected tables")
    words: list[Word] = Field(description="Detected words")

    def to_markdown(
        self,
        img=None,
        output_path: str | Path | None = None,
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
            table_format: Format for tables ('html' or 'markdown')
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
        img: str | Path | None = None,
        output_path: str | Path | None = None,
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
            figure_width: Width of exported figures
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
        output_path: str | None = None,
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

        return renderer.render(self)

    def to_pdf(
        self,
        font_path: str | None = None,
        img: Any | None = None,
    ) -> str:
        """
        Convert document result to PDF format (returns PDF byte stream)

        Args:
            font_path: Path to font file. If None, uses default MPLUS1p-Medium.ttf from resource
            img: Optional image array for PDF generation (required for searchable PDF)
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
            img: Image array to draw bounding boxes on
            mode: Type of visualization:
                - 'layout_detail': Detailed layout with all elements
                - 'ocr': OCR text visualization
        Returns:
            np.ndarray: Image array with visualizations
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


class MultiPageDocumentResult(BaseModel):
    """Multi-page document result model"""

    pages: dict[int, DocumentResult] = Field(
        description="Dictionary of page index to DocumentResult",
    )

    def to_pdf(
        self,
        image_path: str | Path,
        output_path,
        page_index: list = None,
        font_path: str | None = None,
        dpi: int = 200,
        mode="combine",
    ) -> str:
        """
        Convert multi-page document result to PDF format

        Args:
            output_path: Path to save the PDF file
            page_index: Page index to convert
            font_path: Path to font file. If None, uses default MPLUS1p-Medium.ttf from resource
            image_path: Path to the original image/PDF file for searchable PDF generation
            dpi: DPI for loading PDF pages as images
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
                self.pages[idx].to_pdf(
                    img=Image.fromarray(corrected_img[:, :, ::-1]),
                    font_path=font_path,
                ),
            )

        base_name, ext = os.path.splitext(output_path)
        if mode == "combine":
            merge_pdf_packets_to_file(
                results,
                out_path=output_path,
            )
        elif mode == "separate":
            for i, content in zip(page_index, results, strict=True):
                page_output_path = f"{base_name}_page_{i}{ext}"
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
        """
        Export results to file based on mode

        Args:
            results: List of results for each page
            output_path: Path to save the file
            mode: 'combine' or 'separate'
            encoding: File encoding
            page_index: List of page indices
        """

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
            for i, content in zip(page_index, results, strict=True):
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
            output_path: Path to save the CSV file
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
        image_path: str | Path | None = None,
        dpi: int = 200,
        **kwargs,
    ) -> None:
        """
        Convert multi-page document result to HTML format

        Args:
            output_path: Path to save the Markdown file
            encoding: File encoding
            mode: 'combine' to combine all pages into one file, 'separate' to save each page separately
            page_index: List of page indices to process
            image_path: Path to the original image/PDF file for image extraction
            dpi: DPI for loading PDF pages as images
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
                ),
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
        image_path: str | Path | None = None,
        dpi: int = 200,
        **kwargs,
    ) -> None:
        """
        Convert multi-page document result to Markdown format

        Args:
            output_path: Path to save the Markdown file
            encoding: File encoding
            mode: 'combine' to combine all pages into one file, 'separate' to save each page separately
            page_index: List of page indices to process
            image_path: Path to the original image/PDF file for image extraction
            dpi: DPI for loading PDF pages as images
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
                ),
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
        **kwargs,
    ) -> None:
        """
        Convert multi-page document result to JSON format

        Args:
            output_path: Path to save the JSON file
            encoding: File encoding
            mode: 'combine' to combine all pages into one file, 'separate' to save each page separately
            page_index: List of page indices to process
            image_path: Path to the original image/PDF file for image extraction
            dpi: DPI for loading PDF pages as images
        """

        base_dir = os.path.dirname(output_path)
        if base_dir:
            os.makedirs(base_dir, exist_ok=True)

        page_index = make_page_index(page_index, len(self.pages))

        results = []
        for idx in page_index:
            results.append(self.pages[idx].to_json(**kwargs))

        self.export_file(
            results,
            output_path=output_path,
            mode=mode,
            encoding=encoding,
            page_index=page_index,
        )

        return results

    def visualize(
        self,
        image_path: str,
        mode: str = "layout",
        output_directory: str | None = None,
        page_index: list = None,
        dpi: int = 200,
    ) -> Any:
        """
        Visualize the document result

        Args:
            image_path: Path to the original image/PDF file
            mode: Type of visualization ('layout', 'ocr', etc.)
            output_directory: Directory to save visualized images
            page_index: List of page indices to visualize
            dpi: DPI for loading PDF pages as images
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
