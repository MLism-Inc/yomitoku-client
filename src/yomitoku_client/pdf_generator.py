"""
Searchable PDF Generator - Create searchable PDFs from images and OCR results
"""

import os
from typing import List, Optional, Union, Any
import numpy as np
from io import BytesIO

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None

try:
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.pdfmetrics import stringWidth
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    canvas = None
    TTFont = None
    pdfmetrics = None
    stringWidth = None

try:
    import jaconv
    JACONV_AVAILABLE = True
except ImportError:
    JACONV_AVAILABLE = False
    jaconv = None

from .exceptions import FormatConversionError
from .font_manager import get_font_path


class SearchablePDFGenerator:
    """Generator for creating searchable PDFs from images and OCR results"""
    
    def __init__(self, font_path: Optional[str] = None):
        """
        Initialize PDF generator

        Args:
            font_path: Path to font file. If None, uses built-in font
        """
        if not PIL_AVAILABLE:
            raise ImportError("PIL is required for PDF generation. Install with: pip install Pillow")

        if not REPORTLAB_AVAILABLE:
            raise ImportError(
                "ReportLab is required for PDF generation. Install with: pip install reportlab\n"
                "Or in Jupyter notebook, run: !pip install reportlab jaconv"
            )

        # Use get_font_path function to get appropriate font path
        self.font_path = get_font_path(font_path)
        self._register_font()
    
    def _register_font(self) -> None:
        """Register font for PDF generation"""
        try:
            # Always try to register the font (either custom or built-in)
            pdfmetrics.registerFont(TTFont("CustomFont", self.font_path))
            self.font_name = "CustomFont"
        except Exception as e:
            # Fall back to Helvetica if registration fails
            print(f"Warning: Failed to register font, falling back to Helvetica: {e}")
            self.font_name = "Helvetica"
    
    def create_searchable_pdf(
        self,
        images: List[np.ndarray],
        ocr_results: List[Any],
        output_path: str,
        **kwargs
    ) -> None:
        """
        Create a searchable PDF from images and OCR results
        
        Args:
            images: List of images as numpy arrays
            ocr_results: List of OCR results corresponding to the images
            output_path: Path to save the output PDF
            **kwargs: Additional options
            
        Raises:
            FormatConversionError: If PDF generation fails
        """
        try:
            packet = BytesIO()
            c = canvas.Canvas(packet)
            
            for i, (image, ocr_result) in enumerate(zip(images, ocr_results)):
                # Convert BGR to RGB if needed
                if len(image.shape) == 3 and image.shape[2] == 3:
                    image_rgb = image[:, :, ::-1]
                else:
                    image_rgb = image
                
                # Convert to PIL Image
                pil_image = Image.fromarray(image_rgb)
                w, h = pil_image.size
                
                # Set page size
                c.setPageSize((w, h))
                
                # Save temporary image and draw it
                temp_path = f"temp_image_{i}.png"
                pil_image.save(temp_path)
                c.drawImage(temp_path, 0, 0, width=w, height=h)
                os.remove(temp_path)  # Clean up
                
                # Add OCR text
                self._add_ocr_text(c, ocr_result, w, h)
                
                c.showPage()
            
            c.save()
            
            # Write to file
            with open(output_path, "wb") as f:
                f.write(packet.getvalue())
                
        except Exception as e:
            raise FormatConversionError(f"Failed to create searchable PDF: {e}")
    
    def _add_ocr_text(self, canvas_obj, ocr_result: Any, page_width: int, page_height: int) -> None:
        """
        Add OCR text to PDF canvas
        
        Args:
            canvas_obj: ReportLab canvas object
            ocr_result: OCR result object
            page_width: Page width
            page_height: Page height
        """
        for word in ocr_result.words:
            text = word.content
            bbox = self._poly_to_rect(word.points)
            direction = getattr(word, 'direction', 'horizontal')
            
            x1, y1, x2, y2 = bbox
            bbox_height = y2 - y1
            bbox_width = x2 - x1
            
            # Convert to full-width characters for vertical text
            if direction == "vertical" and JACONV_AVAILABLE:
                text = self._to_full_width(text)
            
            # Calculate font size
            if direction == "horizontal":
                font_size = self._calc_font_size(text, bbox_height, bbox_width)
            else:
                font_size = self._calc_font_size(text, bbox_width, bbox_height)
            
            # Set font and color
            canvas_obj.setFont(self.font_name, font_size)
            canvas_obj.setFillColorRGB(1, 1, 1, alpha=0)  # Transparent
            
            # Draw text
            if direction == "vertical":
                self._draw_vertical_text(canvas_obj, text, x1, y1, y2, font_size, page_height)
            else:
                self._draw_horizontal_text(canvas_obj, text, x1, y1, y2, bbox_height, font_size, page_height)
    
    def _poly_to_rect(self, points: List[List[float]]) -> List[int]:
        """
        Convert polygon to bounding rectangle
        
        Args:
            points: Polygon points [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
            
        Returns:
            List[int]: Bounding rectangle [x1, y1, x2, y2]
        """
        points = np.array(points, dtype=int)
        x_min = points[:, 0].min()
        x_max = points[:, 0].max()
        y_min = points[:, 1].min()
        y_max = points[:, 1].max()
        
        return [x_min, y_min, x_max, y_max]
    
    def _calc_font_size(self, content: str, bbox_height: float, bbox_width: float) -> float:
        """
        Calculate optimal font size for text to fit in bounding box
        
        Args:
            content: Text content
            bbox_height: Bounding box height
            bbox_width: Bounding box width
            
        Returns:
            float: Optimal font size
        """
        rates = np.arange(0.5, 1.0, 0.01)
        
        min_diff = np.inf
        best_font_size = None
        
        for rate in rates:
            font_size = bbox_height * rate
            try:
                text_w = stringWidth(content, self.font_name, font_size)
                diff = abs(text_w - bbox_width)
                if diff < min_diff:
                    min_diff = diff
                    best_font_size = font_size
            except:
                # If stringWidth fails, use a default size
                best_font_size = bbox_height * 0.8
                break
        
        return best_font_size or bbox_height * 0.8
    
    def _to_full_width(self, text: str) -> str:
        """
        Convert text to full-width characters
        
        Args:
            text: Input text
            
        Returns:
            str: Full-width text
        """
        if not JACONV_AVAILABLE:
            return text
        
        # Character mapping for full-width conversion
        fw_map = {
            "\u00a5": "\uffe5",  # ¥ → ￥
            "\u00b7": "\u30fb",  # · → ・
            " ": "\u3000",       # Half-width space → Full-width space
        }
        
        to_fullwidth = str.maketrans(fw_map)
        
        # Convert using jaconv
        jaconv_text = jaconv.h2z(text, kana=True, ascii=True, digit=True)
        jaconv_text = jaconv_text.translate(to_fullwidth)
        
        return jaconv_text
    
    def _draw_horizontal_text(
        self,
        canvas_obj,
        text: str,
        x1: float,
        y1: float,
        y2: float,
        bbox_height: float,
        font_size: float,
        page_height: int
    ) -> None:
        """
        Draw horizontal text on canvas
        
        Args:
            canvas_obj: ReportLab canvas object
            text: Text to draw
            x1: X coordinate
            y1: Y coordinate (top)
            y2: Y coordinate (bottom)
            bbox_height: Bounding box height
            font_size: Font size
            page_height: Page height
        """
        base_y = page_height - y2 + (bbox_height - font_size) * 0.5
        canvas_obj.drawString(x1, base_y, text)
    
    def _draw_vertical_text(
        self,
        canvas_obj,
        text: str,
        x1: float,
        y1: float,
        y2: float,
        font_size: float,
        page_height: int
    ) -> None:
        """
        Draw vertical text on canvas
        
        Args:
            canvas_obj: ReportLab canvas object
            text: Text to draw
            x1: X coordinate
            y1: Y coordinate (top)
            y2: Y coordinate (bottom)
            font_size: Font size
            page_height: Page height
        """
        bbox_height = y2 - y1
        base_y = page_height - y2 + (bbox_height - font_size)
        
        for j, ch in enumerate(text):
            canvas_obj.saveState()
            canvas_obj.translate(x1 + font_size * 0.5, base_y - (j - 1) * font_size)
            canvas_obj.rotate(-90)
            canvas_obj.drawString(0, 0, ch)
            canvas_obj.restoreState()


def create_searchable_pdf(
    images: List[np.ndarray],
    ocr_results: List[Any],
    output_path: str,
    font_path: Optional[str] = None,
    **kwargs
) -> None:
    """
    Convenience function to create a searchable PDF
    
    Args:
        images: List of images as numpy arrays
        ocr_results: List of OCR results corresponding to the images
        output_path: Path to save the output PDF
        font_path: Path to font file (optional)
        **kwargs: Additional options
    """
    generator = SearchablePDFGenerator(font_path=font_path)
    generator.create_searchable_pdf(images, ocr_results, output_path, **kwargs)
