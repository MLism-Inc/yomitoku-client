"""
Document visualizer for layout analysis and OCR results
"""

import logging
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, features

from ..constants import PALETTE
from .base import BaseVisualizer


class DocumentVisualizer(BaseVisualizer):
    """Document layout and OCR visualization"""

    # Default color palette for different element types
    DEFAULT_PALETTE = [
        (255, 0, 0),  # Red
        (0, 255, 0),  # Green
        (0, 0, 255),  # Blue
        (255, 255, 0),  # Yellow
        (255, 0, 255),  # Magenta
        (0, 255, 255),  # Cyan
        (128, 0, 0),  # Dark Red
        (0, 128, 0),  # Dark Green
        (0, 0, 128),  # Dark Blue
        (128, 128, 0),  # Olive
        (128, 0, 128),  # Purple
        (0, 128, 128),  # Teal
        (192, 192, 192),  # Silver
        (128, 128, 128),  # Gray
        (255, 165, 0),  # Orange
    ]

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.palette = PALETTE

    def visualize(
        self,
        img,
        results,
        mode="ocr",
    ) -> np.ndarray:
        """
        Main visualization method

        Args:
            img: Input image
            data: Document analysis results or image with results
            mode: Visualization mode - "reading_order", "layout_detail", "layout_rough", "ocr", "confidence"
        Returns:
            Visualized image as numpy array
        """
        if mode == "layout":
            out = self.visualize_layout_detail(img, results)
            return self.visualize_reading_order(out, results)
        elif mode == "ocr":
            return self.visualize_ocr(img, results)

    def visualize_reading_order(
        self,
        img: np.ndarray,
        results: Any,
        line_color: tuple[int, int, int] = (0, 0, 255),
        tip_size: int = 10,
        visualize_figure_letter: bool = False,
    ) -> np.ndarray:
        """
        Visualize reading order of document elements

        Args:
            img: Input image
            results: Document analysis results
            line_color: Color for reading order arrows
            tip_size: Size of arrow tips
            visualize_figure_letter: Whether to visualize figure lettering

        Returns:
            Image with reading order visualization
        """
        try:
            return self.reading_order_visualizer(
                img,
                results,
                line_color,
                tip_size,
                visualize_figure_letter,
            )
        except Exception as e:
            self.logger.error(
                "Error in reading order visualization: %s",
                e,
            )
            return img

    def visualize_layout_detail(self, img: np.ndarray, results: Any) -> np.ndarray:
        """
        Detailed layout visualization

        Args:
            img: Input image
            results: Document analysis results

        Returns:
            Image with detailed layout visualization
        """
        try:
            return self.layout_visualizer_detail(results, img)
        except Exception as e:
            self.logger.error(
                "Error in layout detail visualization: %s",
                e,
            )
            return img

    def visualize_ocr(
        self,
        img: np.ndarray,
        results: Any,
        font_path: str = None,
        font_size: int = 12,
        font_color: tuple[int, int, int] = (255, 0, 0),
        line_color: tuple[int, int, int] = (0, 255, 0),
    ) -> np.ndarray:
        """
        OCR visualization

        Args:
            img: Input image
            results: Document analysis results containing words
            font_path: Path to font file
            font_size: Font size
            font_color: Font color
            line_color: Line color for bounding boxes

        Returns:
            Image with OCR visualization
        """
        try:
            # Use default font path if not provided
            if not font_path:
                try:
                    from ..font_manager import get_font_path

                    font_path = get_font_path()
                    self.logger.info("Using default font: %s", font_path)
                except Exception as e:
                    self.logger.warning(
                        "No font path provided and default font not available: %s",
                        e,
                    )
                    return img

            # Extract words from results
            words = []
            if hasattr(results, "words") and results.words:
                words = results.words
            elif hasattr(results, "texts") and results.texts:
                # If results has texts instead of words, convert them
                words = results.texts
            else:
                self.logger.warning("No words found in results for OCR visualization")
                return img

            return self.ocr_visualizer(
                words,
                img,
                font_path,
                font_size,
                font_color,
                line_color,
            )
        except Exception as e:
            self.logger.error(
                "Error in OCR visualization: %s",
                e,
            )
            return img

    def _reading_order_visualizer(self, img, elements, line_color, tip_size):
        """Internal function for drawing reading order arrows"""
        out = img.copy()
        for i, element in enumerate(elements):
            if i == 0:
                continue

            prev_element = elements[i - 1]
            cur_x1, cur_y1, cur_x2, cur_y2 = element.box
            prev_x1, prev_y1, prev_x2, prev_y2 = prev_element.box

            cur_center = (
                cur_x1 + (cur_x2 - cur_x1) / 2,
                cur_y1 + (cur_y2 - cur_y1) / 2,
            )
            prev_center = (
                prev_x1 + (prev_x2 - prev_x1) / 2,
                prev_y1 + (prev_y2 - prev_y1) / 2,
            )

            arrow_length = np.linalg.norm(np.array(cur_center) - np.array(prev_center))

            # tipLength を計算（矢印長さに対する固定サイズの割合）
            tip_length = tip_size / arrow_length if arrow_length > 0 else 0

            cv2.arrowedLine(
                out,
                (int(prev_center[0]), int(prev_center[1])),
                (int(cur_center[0]), int(cur_center[1])),
                line_color,
                2,
                tipLength=tip_length,
            )
        return out

    def reading_order_visualizer(
        self,
        img,
        results,
        line_color=(0, 0, 255),
        tip_size=10,
        visualize_figure_letter=False,
    ):
        """Visualize reading order of document elements"""
        elements = results.paragraphs + results.tables + results.figures
        elements = sorted(elements, key=lambda x: x.order)

        out = self._reading_order_visualizer(img, elements, line_color, tip_size)

        if visualize_figure_letter:
            for figure in results.figures:
                out = self._reading_order_visualizer(
                    out,
                    figure.paragraphs,
                    line_color=(0, 255, 0),
                    tip_size=5,
                )

        return out

    def ocr_visualizer(
        self,
        words,
        img,
        font_path,
        font_size=12,
        font_color=(255, 0, 0),
        line_color=(0, 255, 0),
    ):
        """OCR visualizer"""
        out = img.copy()
        pillow_img = Image.fromarray(out)
        draw = ImageDraw.Draw(pillow_img)
        font = ImageFont.truetype(font_path, font_size)

        has_raqm = features.check_feature(feature="raqm")
        if not has_raqm:
            self.logger.warning(
                "libraqm is not installed. Vertical text rendering is not supported. Rendering horizontally instead.",
            )

        for word in words:
            poly = word.points
            text = word.content
            direction = word.direction

            poly_line = [tuple(point) for point in poly]
            draw.polygon(poly_line, outline=line_color, fill=None)

            if direction == "horizontal" or not has_raqm:
                x_offset = 0
                y_offset = -font_size

                pos_x = poly[0][0] + x_offset
                pox_y = poly[0][1] + y_offset
                draw.text(
                    (pos_x, pox_y),
                    text,
                    font=font,
                    fill=font_color,
                )
            else:
                x_offset = -font_size
                y_offset = 0

                pos_x = poly[0][0] + x_offset
                pox_y = poly[0][1] + y_offset
                draw.text(
                    (pos_x, pox_y),
                    text,
                    font=font,
                    fill=font_color,
                    direction="ttb",
                )

        return np.array(pillow_img)

    def visualize_element(self, img, category, elements):
        """Visualize elements"""
        out = img.copy()
        categories = [
            "paragraphs",
            "tables",
            "figures",
            "section_headings",
            "page_header",
            "page_footer",
            "picture",
            "logo",
            "code",
            "seal",
            "list_item",
            "caption",
            "inline_formula",
            "display_formula",
            "index",
        ]

        for element in elements:
            box = element.box
            role = None

            if category != "tables":
                role = element.role

            color_index = categories.index(category)
            if role is None:
                role = ""
            else:
                color_index = categories.index(role)
                role = f"({role})"

            color = self.palette[color_index % len(self.palette)]
            x1, y1, x2, y2 = tuple(map(int, box))
            out = cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
            out = cv2.putText(
                out,
                category + role,
                (x1, y1),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 0),
                2,
            )

            if category in ["tables", "figures"]:
                caption = None
                if hasattr(element, "caption"):
                    caption = element.caption
                elif isinstance(element, dict) and "caption" in element:
                    caption = element["caption"]

                if caption is not None:
                    caption_box = None
                    if hasattr(caption, "box"):
                        caption_box = caption.box
                    elif isinstance(caption, dict) and "box" in caption:
                        caption_box = caption["box"]

                    if caption_box is not None:
                        color_index = categories.index("caption")
                        color = self.palette[color_index % len(self.palette)]
                        x1, y1, x2, y2 = tuple(map(int, caption_box))
                        out = cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
                        out = cv2.putText(
                            out,
                            "caption",
                            (x1, y1),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5,
                            (0, 0, 0),
                            2,
                        )

                if category == "figures":
                    paragraphs = None
                    if hasattr(element, "paragraphs"):
                        paragraphs = element.paragraphs
                    elif isinstance(element, dict) and "paragraphs" in element:
                        paragraphs = element["paragraphs"]

                    if paragraphs is not None:
                        for paragraph in paragraphs:
                            try:
                                para_box = None
                                if hasattr(paragraph, "box"):
                                    para_box = paragraph.box
                                elif isinstance(paragraph, dict) and "box" in paragraph:
                                    para_box = paragraph["box"]

                                if para_box is not None:
                                    color_index = categories.index("paragraphs")
                                    color = self.palette[
                                        color_index % len(self.palette)
                                    ]
                                    x1, y1, x2, y2 = tuple(map(int, para_box))
                                    out = cv2.rectangle(
                                        out,
                                        (x1, y1),
                                        (x2, y2),
                                        color,
                                        2,
                                    )
                                    out = cv2.putText(
                                        out,
                                        "paragraphs",
                                        (x1, y1),
                                        cv2.FONT_HERSHEY_SIMPLEX,
                                        0.5,
                                        (0, 0, 0),
                                        2,
                                    )
                            except Exception as e:
                                self.logger.warning(
                                    "Error processing figure paragraph: %s",
                                    e,
                                )
                                continue

        return out

    def layout_visualizer_detail(self, results, img):
        """Detailed layout visualizer"""
        out = img.copy()
        # results_dict = results.dict()
        out = self.visualize_element(out, "paragraphs", results.paragraphs)
        out = self.visualize_element(out, "tables", results.tables)
        out = self.visualize_element(out, "figures", results.figures)

        for table in results.tables:
            out = self.table_visualizer(out, table)

        return out

    def table_visualizer(self, img, table):
        """Table visualizer"""
        out = img.copy()
        cells = table.cells
        for cell in cells:
            box = cell.box
            row = cell.row
            col = cell.col
            row_span = cell.row_span
            col_span = cell.col_span

            text = f"[{row}, {col}] ({row_span}x{col_span})"

            x1, y1, x2, y2 = map(int, box)
            out = cv2.rectangle(out, (x1, y1), (x2, y2), (255, 0, 255), 2)
            out = cv2.putText(
                out,
                text,
                (x1, y1),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 0, 0),
                2,
            )

        return out
