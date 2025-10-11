"""
Document visualizer for layout analysis and OCR results
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, features
from typing import Any, Dict, List, Optional, Tuple, Union
import logging
import os

from .base import BaseVisualizer
from ..utils import calc_overlap_ratio, calc_distance, is_contained
from ..constants import PALETTE

try:
    import pypdfium2
    PYPDFIUM2_AVAILABLE = True
except ImportError:
    PYPDFIUM2_AVAILABLE = False
    raise ImportError("pypdfium2 is required for PDF processing. Install with: pip install pypdfium2")


class DocumentVisualizer(BaseVisualizer):
    """Document layout and OCR visualization"""
    
    # Default color palette for different element types
    DEFAULT_PALETTE = [
        (255, 0, 0),    # Red
        (0, 255, 0),    # Green  
        (0, 0, 255),    # Blue
        (255, 255, 0),  # Yellow
        (255, 0, 255),  # Magenta
        (0, 255, 255),  # Cyan
        (128, 0, 0),    # Dark Red
        (0, 128, 0),    # Dark Green
        (0, 0, 128),    # Dark Blue
        (128, 128, 0),  # Olive
        (128, 0, 128),  # Purple
        (0, 128, 128),  # Teal
        (192, 192, 192), # Silver
        (128, 128, 128), # Gray
        (255, 165, 0),  # Orange
    ]
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.palette = PALETTE
        
    def _convert_pdf_page_to_image(self, pdf_path: str, page_index: int = 0, dpi: int = 200, target_size: Optional[Tuple[int, int]] = None) -> np.ndarray:
        """
        Convert specified PDF page to image using pypdfium2
        
        Args:
            pdf_path: PDF file path
            page_index: Page index (0-based)
            dpi: Image resolution (default 200)
            target_size: Target image size (width, height) to match original parsing
            
        Returns:
            Converted image as numpy array in BGR format
            
        Raises:
            ImportError: If pypdfium2 is not installed
            ValueError: If PDF file cannot be opened or page index is invalid
        """
        # Import pypdfium2 at the beginning to ensure it's available
        import pypdfium2
        
        try:
            # Open PDF document
            doc = pypdfium2.PdfDocument(pdf_path)
            
            # Check if page index is valid
            if page_index < 0 or page_index >= len(doc):
                doc.close()
                raise ValueError(f"Page index {page_index} is out of range. PDF has {len(doc)} pages.")
            
            if target_size is not None:
                # Use target size to match original parsing dimensions
                target_width, target_height = target_size
                
                # Validate target size (check for None and invalid values)
                if target_width is None or target_height is None or target_width <= 0 or target_height <= 0 or target_width > 20000 or target_height > 20000:
                    self.logger.warning(f"Invalid target size: {target_size}, falling back to DPI-based conversion")
                    target_size = None
                else:
                    # Get specified page
                    page = doc[page_index]
                    
                    # Get original page dimensions
                    original_width = page.get_width()
                    original_height = page.get_height()
                    
                    # Validate original dimensions (check for None and invalid values)
                    if original_width is None or original_height is None or original_width <= 0 or original_height <= 0:
                        self.logger.warning(f"Invalid original page dimensions: {original_width}x{original_height}")
                        target_size = None
                    else:
                        # Calculate scale to match target size exactly
                        # This ensures coordinate alignment between original parsing and visualization
                        scale_x = target_width / original_width
                        scale_y = target_height / original_height
                        
                        # Use uniform scaling to maintain aspect ratio
                        scale = min(scale_x, scale_y)
                        
                        # Validate scale factor
                        if scale <= 0 or scale > 10:  # Reasonable scale range
                            self.logger.warning(f"Invalid scale factor: {scale}, falling back to DPI-based conversion")
                            target_size = None
                        else:
                            try:
                                # Render page with calculated scale 
                                bitmap = page.render(scale=scale)
                                pil_image = bitmap.to_pil()
                                
                                # Calculate the actual size after scaling
                                actual_width = int(original_width * scale)
                                actual_height = int(original_height * scale)
                                
                                # For coordinate alignment, we need to ensure the final image size matches target_size exactly
                                # This is critical for proper bounding box alignment
                                if actual_width != target_width or actual_height != target_height:
                                    # Calculate scaling factors for final adjustment
                                    final_scale_x = target_width / actual_width
                                    final_scale_y = target_height / actual_height
                                    
                                    # Use uniform scaling to maintain aspect ratio
                                    final_scale = min(final_scale_x, final_scale_y)
                                    
                                    # Calculate new size
                                    new_width = int(actual_width * final_scale)
                                    new_height = int(actual_height * final_scale)
                                    
                                    # Resize the image
                                    pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                                    
                                    # If we still don't match exactly, crop or pad as needed
                                    if new_width != target_width or new_height != target_height:
                                        # Create a new image with target size
                                        final_image = Image.new('RGB', (target_width, target_height), (255, 255, 255))
                                        
                                        # Calculate position to center the image
                                        x_offset = (target_width - new_width) // 2
                                        y_offset = (target_height - new_height) // 2
                                        
                                        # Paste the resized image onto the final image
                                        final_image.paste(pil_image, (x_offset, y_offset))
                                        pil_image = final_image
                                
                                # Log the coordinate mapping for debugging
                                self.logger.info(f"PDF coordinate mapping: original({original_width}x{original_height}) -> target({target_width}x{target_height})")
                                self.logger.info(f"Scale factor: {scale:.4f}, Final scale: {final_scale if 'final_scale' in locals() else 1.0:.4f}")
                                self.logger.info(f"Final image size: {pil_image.size}")
                                
                            except Exception as e:
                                self.logger.warning(f"Error in target size conversion: {e}, falling back to DPI-based conversion")
                                target_size = None
            
            # If target_size is None (either not provided or failed), use DPI-based conversion
            if target_size is None:
                
                renderer = doc.render(
                    pypdfium2.PdfBitmap.to_pil,
                    scale=dpi / 72,
                )
                images = list(renderer)
                
                # Get the specific page image
                if page_index >= len(images):
                    doc.close()
                    raise ValueError(f"Page index {page_index} is out of range. PDF has {len(images)} pages.")
                
                pil_image = images[page_index]
            
            img_array = np.array(pil_image.convert("RGB"))
            img_array = img_array[:, :, ::-1]  # RGB to BGR
            
            doc.close()
            return img_array
            
        except Exception as e:
            if 'doc' in locals():
                doc.close()
            raise ValueError(f"Failed to convert PDF page to image: {e}")
    
    
    def _is_pdf_file(self, file_path: str) -> bool:
        """
        Check if file is a PDF file
        
        Args:
            file_path: File path
            
        Returns:
            True if PDF file, False otherwise
        """
        if not os.path.exists(file_path):
            return False
        
        # Check file extension
        _, ext = os.path.splitext(file_path.lower())
        if ext == '.pdf':
            return True
        
        # Check file header (more reliable method)
        try:
            with open(file_path, 'rb') as f:
                header = f.read(4)
                return header == b'%PDF'
        except:
            return False
    
    def _get_original_image_size(self, results: Any) -> Optional[Tuple[int, int]]:
        """
        Extract original image size from parsing results with improved accuracy and stability
        
        Args:
            results: Document analysis results
            
        Returns:
            Tuple of (width, height) if found, None otherwise
        """
        try:
            all_coords = []
            
            # Collect all coordinates from different element types with validation
            # Words (most precise for OCR results)
            if hasattr(results, 'words') and results.words:
                for word in results.words:
                    if hasattr(word, 'points') and word.points:
                        for point in word.points:
                            if len(point) >= 2 and isinstance(point[0], (int, float)) and isinstance(point[1], (int, float)):
                                all_coords.append((float(point[0]), float(point[1])))
                    elif hasattr(word, 'box') and word.box:
                        # Fallback to box coordinates
                        if len(word.box) >= 4:
                            all_coords.extend([
                                (float(word.box[0]), float(word.box[1])),  # x1, y1
                                (float(word.box[2]), float(word.box[3]))   # x2, y2
                            ])
            
            # Paragraphs
            if hasattr(results, 'paragraphs') and results.paragraphs:
                for para in results.paragraphs:
                    if hasattr(para, 'box') and para.box and len(para.box) >= 4:
                        all_coords.extend([
                            (float(para.box[0]), float(para.box[1])),  # x1, y1
                            (float(para.box[2]), float(para.box[3]))   # x2, y2
                        ])
            
            # Tables
            if hasattr(results, 'tables') and results.tables:
                for table in results.tables:
                    if hasattr(table, 'box') and table.box and len(table.box) >= 4:
                        all_coords.extend([
                            (float(table.box[0]), float(table.box[1])),  # x1, y1
                            (float(table.box[2]), float(table.box[3]))   # x2, y2
                        ])
            
            # Figures
            if hasattr(results, 'figures') and results.figures:
                for figure in results.figures:
                    if hasattr(figure, 'box') and figure.box and len(figure.box) >= 4:
                        all_coords.extend([
                            (float(figure.box[0]), float(figure.box[1])),  # x1, y1
                            (float(figure.box[2]), float(figure.box[3]))   # x2, y2
                        ])
            
            if all_coords:
                # Filter out invalid coordinates
                valid_coords = [(x, y) for x, y in all_coords if x >= 0 and y >= 0 and x < 10000 and y < 10000]
                
                if not valid_coords:
                    self.logger.warning("No valid coordinates found")
                    return None
                
                # Find the actual image boundaries
                min_x = min(coord[0] for coord in valid_coords)
                min_y = min(coord[1] for coord in valid_coords)
                max_x = max(coord[0] for coord in valid_coords)
                max_y = max(coord[1] for coord in valid_coords)
                
                # For PDF documents, coordinates are typically absolute pixel coordinates
                # The max coordinates should represent the full image dimensions
                # Add a small margin to ensure we capture the full image
                margin = max(10, (max_x - min_x + max_y - min_y) * 0.01)  # Dynamic margin
                final_width = int(max_x + margin)
                final_height = int(max_y + margin)
                
                # Validate the detected size
                if final_width > 0 and final_height > 0 and final_width < 20000 and final_height < 20000:
                    self.logger.info(f"Detected original image size: {final_width}x{final_height} from coordinates")
                    self.logger.info(f"Coordinate range: x=[{min_x:.1f}, {max_x:.1f}], y=[{min_y:.1f}, {max_y:.1f}]")
                    self.logger.info(f"Valid coordinates: {len(valid_coords)}/{len(all_coords)}")
                    return (final_width, final_height)
                else:
                    self.logger.warning(f"Detected size seems invalid: {final_width}x{final_height}")
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Could not extract original image size from results: {e}")
            return None
        
    def visualize(self, data: Any, **kwargs) -> np.ndarray:
        """
        Main visualization method
        
        Args:
            data: Document analysis results or image with results
            **kwargs: Visualization parameters including:
                - image_path: Path to image or PDF file
                - page_index: Page index for PDF files (0-based, default: 0)
                - dpi: DPI for PDF to image conversion (default: 300)
                - results: Analysis results for visualization
                - type: Visualization type (ocr, layout_detail, etc.)
            
        Returns:
            Visualized image as numpy array
        """
        if isinstance(data, tuple) and len(data) == 2:
            img, results = data
        else:
            img = data
            results = kwargs.get('results')
        
        # Get parameters
        image_path = kwargs.get('image_path')
        page_index = kwargs.get('page_index', 0)
        dpi = kwargs.get('dpi', 200)
        target_size = kwargs.get('target_size')  # Allow manual override
        
        # For PDF visualization, we should NOT try to match original image size
        # The OCR coordinates are already in the correct coordinate system
        if target_size is None and results is not None:
            # Check if we're dealing with a PDF file
            is_pdf = False
            if image_path and self._is_pdf_file(image_path):
                is_pdf = True
            elif isinstance(img, str) and self._is_pdf_file(img):
                is_pdf = True
            
            if is_pdf:
                self.logger.info("PDF file detected, using DPI-based conversion")
                target_size = None
            else:
                # Only try to detect target size for non-PDF images
                try:
                    target_size = self._get_original_image_size(results)
                    if target_size is not None:
                        self.logger.info(f"Using detected target size: {target_size}")
                    else:
                        self.logger.info("Could not detect target size, using DPI-based conversion")
                except Exception as e:
                    self.logger.warning(f"Error detecting target size: {e}, using DPI-based conversion")
                    target_size = None
        
        # Handle image input - convert string path to numpy array
        if isinstance(img, str):
            try:
                # Check if it is a PDF file
                if self._is_pdf_file(img):
                    self.logger.info(f"Detected PDF file: {img}, converting page {page_index} to image")
                    if target_size:
                        self.logger.info(f"Using target size {target_size} to match original parsing dimensions")
                    img = self._convert_pdf_page_to_image(img, page_index, dpi, target_size)
                else:
                    # Normal image file
                    img = cv2.imread(img)
                    if img is None:
                        self.logger.error(f"Failed to load image from path: {img}")
                        return np.zeros((400, 600, 3), dtype=np.uint8)
            except Exception as e:
                self.logger.error(f"Error loading image from path {img}: {e}")
                return np.zeros((400, 600, 3), dtype=np.uint8)
        elif not isinstance(img, np.ndarray):
            self.logger.error(f"Invalid image type: {type(img)}. Expected string path or numpy array.")
            return np.zeros((400, 600, 3), dtype=np.uint8)
        
        # If image_path parameter is provided, also try to process it
        if image_path and isinstance(image_path, str):
            try:
                if self._is_pdf_file(image_path):
                    self.logger.info(f"Processing PDF file from image_path: {image_path}, page {page_index}")
                    if target_size:
                        self.logger.info(f"Using target size {target_size} to match original parsing dimensions")
                    img = self._convert_pdf_page_to_image(image_path, page_index, dpi, target_size)
                else:
                    # If img is not a numpy array, try to load from image_path
                    if not isinstance(img, np.ndarray):
                        img = cv2.imread(image_path)
                        if img is None:
                            self.logger.error(f"Failed to load image from image_path: {image_path}")
                            return np.zeros((400, 600, 3), dtype=np.uint8)
            except Exception as e:
                self.logger.error(f"Error processing image_path {image_path}: {e}")
                return np.zeros((400, 600, 3), dtype=np.uint8)
            
        if results is None:
            return img
        # Handle results - if it's a list, take the first element
        if isinstance(results, list) and len(results) > 0:
            results = results[0]
            self.logger.info("Results is a list, using first element for visualization")
        elif isinstance(results, list) and len(results) == 0:
            self.logger.warning("Results is an empty list, returning original image")
            return img
            
        visualization_type = kwargs.get('type', 'layout_detail')
        
        if visualization_type == 'reading_order':
            # Filter out non-reading order parameters
            reading_kwargs = {k: v for k, v in kwargs.items() 
                            if k not in ['type', 'page_index', 'dpi', 'image_path', 'target_size']}
            return self.visualize_reading_order(img, results, **reading_kwargs)
        elif visualization_type == 'layout_detail':
            return self.visualize_layout_detail(img, results)
        elif visualization_type == 'layout_rough':
            return self.visualize_layout_rough(img, results)
        elif visualization_type == 'ocr':
            # Filter out non-ocr parameters
            ocr_kwargs = {k: v for k, v in kwargs.items() 
                         if k not in ['type', 'page_index', 'dpi', 'image_path', 'target_size']}
            return self.visualize_ocr(img, results, **ocr_kwargs)
        elif visualization_type == 'detection':
            # Filter out non-detection parameters
            detection_kwargs = {k: v for k, v in kwargs.items() 
                              if k not in ['type', 'page_index', 'dpi', 'image_path', 'target_size']}
            return self.visualize_detection(img, results, **detection_kwargs)
        elif visualization_type == 'recognition':
            # Filter out non-recognition parameters
            recognition_kwargs = {k: v for k, v in kwargs.items() 
                                if k not in ['type', 'page_index', 'dpi', 'image_path', 'target_size']}
            return self.visualize_recognition(img, results, **recognition_kwargs)
        elif visualization_type == 'relationships':
            # Filter out non-relationships parameters
            relationships_kwargs = {k: v for k, v in kwargs.items() 
                                  if k not in ['type', 'results', 'page_index', 'dpi', 'image_path', 'target_size']}
            return self.visualize_element_relationships(img, results, **relationships_kwargs)
        elif visualization_type == 'hierarchy':
            # Filter out non-hierarchy parameters
            hierarchy_kwargs = {k: v for k, v in kwargs.items() 
                              if k not in ['type', 'results', 'page_index', 'dpi', 'image_path', 'target_size']}
            return self.visualize_element_hierarchy(img, results, **hierarchy_kwargs)
        elif visualization_type == 'confidence':
            # Filter out non-confidence parameters
            confidence_kwargs = {k: v for k, v in kwargs.items()
                               if k not in ['type', 'results', 'page_index', 'dpi', 'image_path', 'target_size']}
            return self.visualize_confidence_scores(img, results, **confidence_kwargs)
        elif visualization_type == 'captions':
            # Filter out non-caption parameters
            caption_kwargs = {k: v for k, v in kwargs.items()
                            if k not in ['type', 'results', 'page_index', 'dpi', 'image_path', 'target_size']}
            return self.visualize_captions(img, results, **caption_kwargs)
        else:
            return self.visualize_layout_detail(img, results)
    
    def visualize_reading_order(self, img: np.ndarray, results: Any, 
                               line_color: Tuple[int, int, int] = (0, 0, 255),
                               tip_size: int = 10,
                               visualize_figure_letter: bool = False) -> np.ndarray:
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
            return self.reading_order_visualizer(img, results, line_color, tip_size, visualize_figure_letter)
        except Exception as e:
            self.logger.error(f"Error in reading order visualization: {e}")
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
            self.logger.error(f"Error in layout detail visualization: {e}")
            return img
    
    def visualize_layout_rough(self, img: np.ndarray, results: Any) -> np.ndarray:
        """
        Rough layout visualization 
        
        Args:
            img: Input image
            results: Document analysis results
            
        Returns:
            Image with rough layout visualization
        """
        try:
            return self.layout_visualizer_rough(results, img)
        except Exception as e:
            self.logger.error(f"Error in layout rough visualization: {e}")
            return img
    
    def visualize_ocr(self, img: np.ndarray, results: Any, 
                     font_path: str = None,
                     det_score: np.ndarray = None,
                     vis_heatmap: bool = False,
                     font_size: int = 12,
                     font_color: Tuple[int, int, int] = (255, 0, 0),
                     line_color: Tuple[int, int, int] = (0, 255, 0)) -> np.ndarray:
        """
        OCR visualization 
        
        Args:
            img: Input image
            results: Document analysis results containing words
            font_path: Path to font file
            det_score: Detection score heatmap
            vis_heatmap: Whether to visualize heatmap
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
                    self.logger.info(f"Using default font: {font_path}")
                except Exception as e:
                    self.logger.warning(f"No font path provided and default font not available: {e}")
                    return img
            
            # Extract words from results
            words = []
            if hasattr(results, 'words') and results.words:
                words = results.words
            elif hasattr(results, 'texts') and results.texts:
                # If results has texts instead of words, convert them
                words = results.texts
            else:
                self.logger.warning("No words found in results for OCR visualization")
                return img
            
            return self.ocr_visualizer(words, img, font_path, det_score, vis_heatmap, 
                                     font_size, font_color, line_color)
        except Exception as e:
            self.logger.error(f"Error in OCR visualization: {e}")
            return img
    
    def visualize_detection(self, img: np.ndarray, quads: List[List], 
                           preds: Optional[Dict] = None,
                           vis_heatmap: bool = False,
                           line_color: Tuple[int, int, int] = (0, 255, 0)) -> np.ndarray:
        """
        Detection visualization 
        
        Args:
            img: Input image
            quads: Detected quadrangles
            preds: Prediction results
            vis_heatmap: Whether to visualize heatmap
            line_color: Line color
            
        Returns:
            Image with detection visualization
        """
        try:
            return self.det_visualizer(img, quads, preds, vis_heatmap, line_color)
        except Exception as e:
            self.logger.error(f"Error in detection visualization: {e}")
            return img
    
    def visualize_recognition(self, img: np.ndarray, outputs: Any,
                             font_path: str = None,
                             font_size: int = 12,
                             font_color: Tuple[int, int, int] = (255, 0, 0)) -> np.ndarray:
        """
        Recognition visualization 
        
        Args:
            img: Input image
            outputs: Recognition outputs
            font_path: Path to font file
            font_size: Font size
            font_color: Font color
            
        Returns:
            Image with recognition visualization
        """
        try:
            if not font_path:
                return img
            return self.rec_visualizer(img, outputs, font_path, font_size, font_color)
        except Exception as e:
            self.logger.error(f"Error in recognition visualization: {e}")
            return img
    
    def _draw_reading_order_arrows(self, img: np.ndarray, elements: List[Any],
                                  line_color: Tuple[int, int, int],
                                  tip_size: int) -> np.ndarray:
        """Draw reading order arrows between elements"""
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
            
            if arrow_length > 0:
                tip_length = tip_size / arrow_length
            else:
                tip_length = 0
            
            cv2.arrowedLine(
                out,
                (int(prev_center[0]), int(prev_center[1])),
                (int(cur_center[0]), int(cur_center[1])),
                line_color,
                2,
                tipLength=tip_length,
            )
            
        return out
    
    def _visualize_element(self, img: np.ndarray, category: str, elements: List[Any]) -> np.ndarray:
        """Visualize specific element category  visualize_element"""
        out = img.copy()
        categories = [
            "paragraphs", "tables", "figures", "section_headings", "page_header",
            "page_footer", "picture", "logo", "code", "seal", "list_item",
            "caption", "inline_formula", "display_formula", "index",
        ]
        
        for i, element in enumerate(elements):
            try:
                # Extract box - handle both object and dict formats
                if hasattr(element, 'box'):
                    box = element.box
                elif isinstance(element, dict) and 'box' in element:
                    box = element['box']
                else:
                    self.logger.warning(f"Element has no box attribute: {type(element)}")
                    continue
                
                # Extract role - handle both object and dict formats
                role = None
                if category != "tables":
                    if hasattr(element, 'role'):
                        role = element.role
                    elif isinstance(element, dict) and 'role' in element:
                        role = element['role']
                
                # Color selection logic  exactly
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
                
                # Handle captions for tables and figures 
                if category in ["tables", "figures"]:
                    caption = None
                    if hasattr(element, 'caption'):
                        caption = element.caption
                    elif isinstance(element, dict) and 'caption' in element:
                        caption = element['caption']
                    
                    if caption is not None:
                        caption_box = None
                        if hasattr(caption, 'box'):
                            caption_box = caption.box
                        elif isinstance(caption, dict) and 'box' in caption:
                            caption_box = caption['box']
                        
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
                    
                    # Handle figure paragraphs 
                    if category == "figures":
                        paragraphs = None
                        if hasattr(element, 'paragraphs'):
                            paragraphs = element.paragraphs
                        elif isinstance(element, dict) and 'paragraphs' in element:
                            paragraphs = element['paragraphs']
                        
                        if paragraphs is not None:
                            for paragraph in paragraphs:
                                try:
                                    para_box = None
                                    if hasattr(paragraph, 'box'):
                                        para_box = paragraph.box
                                    elif isinstance(paragraph, dict) and 'box' in paragraph:
                                        para_box = paragraph['box']
                                    
                                    if para_box is not None:
                                        color_index = categories.index("paragraphs")
                                        color = self.palette[color_index % len(self.palette)]
                                        x1, y1, x2, y2 = tuple(map(int, para_box))
                                        out = cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
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
                                    self.logger.warning(f"Error processing figure paragraph: {e}")
                                    continue
            except Exception as e:
                self.logger.warning(f"Error processing element in {category}: {e}")
                continue
        
        return out
    
    def _visualize_table(self, img: np.ndarray, table: Any) -> np.ndarray:
        """Visualize table structure  table_visualizer exactly"""
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
    
    def visualize_element_relationships(self, img: np.ndarray, results: Any, 
                                     show_overlaps: bool = True,
                                     show_distances: bool = False,
                                     overlap_threshold: float = 0.1) -> np.ndarray:
        """
        Visualize relationships between document elements
        
        Args:
            img: Input image
            results: Document analysis results
            show_overlaps: Whether to show overlapping elements
            show_distances: Whether to show distances between elements
            overlap_threshold: Threshold for overlap detection
            
        Returns:
            Image with element relationships visualization
        """
        try:
            out = img.copy()
            
            # Get all elements including captions
            all_elements = []
            if hasattr(results, 'paragraphs') and results.paragraphs:
                all_elements.extend([(p, 'paragraph') for p in results.paragraphs])
            if hasattr(results, 'tables') and results.tables:
                all_elements.extend([(t, 'table') for t in results.tables])
                # Add table captions as separate elements
                for table in results.tables:
                    if hasattr(table, 'caption') and table.caption:
                        # Handle caption as dict or object
                        if isinstance(table.caption, dict) and 'box' in table.caption:
                            caption_obj = type('Caption', (), table.caption)()  # Convert dict to object
                            all_elements.append((caption_obj, 'caption'))
                        elif hasattr(table.caption, 'box'):
                            all_elements.append((table.caption, 'caption'))
            if hasattr(results, 'figures') and results.figures:
                all_elements.extend([(f, 'figure') for f in results.figures])
                # Add figure captions as separate elements
                for figure in results.figures:
                    if hasattr(figure, 'caption') and figure.caption:
                        # Handle caption as dict or object
                        if isinstance(figure.caption, dict) and 'box' in figure.caption:
                            caption_obj = type('Caption', (), figure.caption)()  # Convert dict to object
                            all_elements.append((caption_obj, 'caption'))
                        elif hasattr(figure.caption, 'box'):
                            all_elements.append((figure.caption, 'caption'))

            # Visualize all elements including captions
            if len(all_elements) > 0:
                # Draw bounding boxes for all elements with different colors
                color_map = {
                    'paragraph': (255, 0, 0),    # Red
                    'table': (0, 255, 0),         # Green
                    'figure': (0, 0, 255),        # Blue
                    'caption': (255, 128, 0)      # Orange for captions
                }
                for element, elem_type in all_elements:
                    if hasattr(element, 'box'):
                        box = element.box
                        color = color_map.get(elem_type, (128, 128, 128))
                        cv2.rectangle(out, (box[0], box[1]), (box[2], box[3]), color, 2)

                        # Add label - just show element type name for consistency
                        cv2.putText(out, elem_type, (box[0], box[1]-5),
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # Check relationships between elements
            for i, (element1, type1) in enumerate(all_elements):
                for j, (element2, type2) in enumerate(all_elements[i+1:], i+1):
                    if not hasattr(element1, 'box') or not hasattr(element2, 'box'):
                        continue
                    
                    box1 = element1.box
                    box2 = element2.box
                    
                    if show_overlaps:
                        # Check for overlaps
                        overlap_ratio, intersection = calc_overlap_ratio(box1, box2)
                        if overlap_ratio > overlap_threshold:
                            # Draw overlap region
                            if intersection:
                                x1, y1, x2, y2 = intersection
                                cv2.rectangle(out, (x1, y1), (x2, y2), (255, 0, 255), 2)
                                cv2.putText(out, f"Overlap: {overlap_ratio:.2f}", 
                                          (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1)
                    
                    if show_distances:
                        # Calculate and show distance
                        distance = calc_distance(box1, box2)
                        center1 = ((box1[0] + box1[2]) // 2, (box1[1] + box1[3]) // 2)
                        center2 = ((box2[0] + box2[2]) // 2, (box2[1] + box2[3]) // 2)
                        
                        # Draw line between centers
                        cv2.line(out, center1, center2, (0, 255, 255), 1)
                        
                        # Draw distance text
                        mid_point = ((center1[0] + center2[0]) // 2, (center1[1] + center2[1]) // 2)
                        cv2.putText(out, f"{distance:.1f}px", mid_point, 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
            
            return out
        except Exception as e:
            self.logger.error(f"Error in element relationships visualization: {e}")
            return img
    
    def visualize_element_hierarchy(self, img: np.ndarray, results: Any,
                                  show_containment: bool = True,
                                  containment_threshold: float = 0.8) -> np.ndarray:
        """
        Visualize hierarchical relationships between elements
        
        Args:
            img: Input image
            results: Document analysis results
            show_containment: Whether to show containment relationships
            containment_threshold: Threshold for containment detection
            
        Returns:
            Image with element hierarchy visualization
        """
        try:
            out = img.copy()
            
            # Get all elements including captions
            all_elements = []
            if hasattr(results, 'paragraphs') and results.paragraphs:
                all_elements.extend([(p, 'paragraph') for p in results.paragraphs])
            if hasattr(results, 'tables') and results.tables:
                all_elements.extend([(t, 'table') for t in results.tables])
                # Add table captions
                for table in results.tables:
                    if hasattr(table, 'caption') and table.caption:
                        if isinstance(table.caption, dict) and 'box' in table.caption:
                            caption_obj = type('Caption', (), table.caption)()
                            all_elements.append((caption_obj, 'caption'))
                        elif hasattr(table.caption, 'box'):
                            all_elements.append((table.caption, 'caption'))
            if hasattr(results, 'figures') and results.figures:
                all_elements.extend([(f, 'figure') for f in results.figures])
                # Add figure captions
                for figure in results.figures:
                    if hasattr(figure, 'caption') and figure.caption:
                        if isinstance(figure.caption, dict) and 'box' in figure.caption:
                            caption_obj = type('Caption', (), figure.caption)()
                            all_elements.append((caption_obj, 'caption'))
                        elif hasattr(figure.caption, 'box'):
                            all_elements.append((figure.caption, 'caption'))

            # If no high-level elements, visualize what we have
            if not all_elements and hasattr(results, 'texts') and results.texts:
                all_elements.extend([(t, 'text') for t in results.texts[:30]])
            
            if show_containment:
                # Check for containment relationships
                for i, (element1, type1) in enumerate(all_elements):
                    for j, (element2, type2) in enumerate(all_elements):
                        if i == j or not hasattr(element1, 'box') or not hasattr(element2, 'box'):
                            continue
                        
                        box1 = element1.box
                        box2 = element2.box
                        
                        # Check if element2 is contained in element1
                        if is_contained(box1, box2, containment_threshold):
                            # Draw containment indicator
                            x1, y1, x2, y2 = map(int, box2)
                            cv2.rectangle(out, (x1, y1), (x2, y2), (0, 255, 0), 3)
                            cv2.putText(out, f"{type2} in {type1}", 
                                      (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            return out
        except Exception as e:
            self.logger.error(f"Error in element hierarchy visualization: {e}")
            return img
    
    def visualize_captions(self, img: np.ndarray, results: Any,
                         show_text: bool = True,
                         font_size: float = 0.5,
                         box_color: Tuple[int, int, int] = (255, 128, 0),
                         text_color: Tuple[int, int, int] = (255, 128, 0)) -> np.ndarray:
        """
        Visualize captions for tables and figures

        Args:
            img: Input image
            results: Document analysis results
            show_text: Whether to show caption text
            font_size: Font size for caption text
            box_color: Color for caption boxes
            text_color: Color for caption text

        Returns:
            Image with caption visualization
        """
        try:
            out = img.copy()

            # Process table captions
            if hasattr(results, 'tables'):
                for table in results.tables:
                    if hasattr(table, 'caption') and table.caption:
                        out = self._draw_caption(out, table.caption, show_text, font_size, box_color, text_color)

            # Process figure captions
            if hasattr(results, 'figures'):
                for figure in results.figures:
                    if hasattr(figure, 'caption') and figure.caption:
                        out = self._draw_caption(out, figure.caption, show_text, font_size, box_color, text_color)

            return out
        except Exception as e:
            self.logger.error(f"Error in caption visualization: {e}")
            return img

    def _draw_caption(self, img: np.ndarray, caption: Any, show_text: bool,
                     font_size: float, box_color: Tuple[int, int, int],
                     text_color: Tuple[int, int, int]) -> np.ndarray:
        """Draw a single caption"""
        out = img.copy()

        # Extract caption box
        caption_box = None
        if hasattr(caption, 'box'):
            caption_box = caption.box
        elif isinstance(caption, dict) and 'box' in caption:
            caption_box = caption['box']

        # Extract caption text
        caption_text = None
        if hasattr(caption, 'contents'):
            caption_text = caption.contents
        elif isinstance(caption, dict) and 'contents' in caption:
            caption_text = caption.get('contents', '')
        elif isinstance(caption, str):
            caption_text = caption

        if caption_box is not None:
            x1, y1, x2, y2 = tuple(map(int, caption_box))

            # Draw caption box
            cv2.rectangle(out, (x1, y1), (x2, y2), box_color, 2)

            # Draw caption text if requested
            if show_text and caption_text:
                # Split long text into multiple lines
                max_width = x2 - x1
                words = caption_text.split()
                lines = []
                current_line = []

                for word in words:
                    test_line = ' '.join(current_line + [word])
                    text_size = cv2.getTextSize(test_line, cv2.FONT_HERSHEY_SIMPLEX, font_size, 1)[0]

                    if text_size[0] <= max_width or not current_line:
                        current_line.append(word)
                    else:
                        lines.append(' '.join(current_line))
                        current_line = [word]

                if current_line:
                    lines.append(' '.join(current_line))

                # Draw each line
                line_height = int(cv2.getTextSize("Test", cv2.FONT_HERSHEY_SIMPLEX, font_size, 1)[0][1] * 1.5)
                for i, line in enumerate(lines[:3]):  # Limit to 3 lines
                    y_pos = y1 + (i + 1) * line_height
                    if y_pos < y2:
                        cv2.putText(out, line, (x1 + 5, y_pos),
                                  cv2.FONT_HERSHEY_SIMPLEX, font_size, text_color, 1)

        return out

    def visualize_confidence_scores(self, img_or_path: Union[np.ndarray, str], results: Any,
                                  show_ocr_confidence: bool = True,
                                  show_detection_confidence: bool = False) -> np.ndarray:
        """
        Visualize confidence scores for different elements
        
        Args:
            img_or_path: Input image (numpy array) or path to image file
            results: Document analysis results
            show_ocr_confidence: Whether to show OCR confidence scores
            show_detection_confidence: Whether to show detection confidence scores
            
        Returns:
            Image with confidence scores visualization
        """
        try:
            # Handle both image array and image path
            if isinstance(img_or_path, str):
                img = cv2.imread(img_or_path)
                if img is None:
                    raise ValueError(f"Could not load image from path: {img_or_path}")
            else:
                img = img_or_path
            
            out = img.copy()
            
            if hasattr(results, 'words'):
                for word in results.words:
                    if not hasattr(word, 'points'):
                        continue
                        
                    points = word.points
                    # Convert points to bounding box
                    x_coords = [p[0] for p in points]
                    y_coords = [p[1] for p in points]
                    x1, y1 = int(min(x_coords)), int(min(y_coords))
                    x2, y2 = int(max(x_coords)), int(max(y_coords))
                    
                    # Show OCR confidence (rec_score) - Recognition confidence
                    if show_ocr_confidence:
                        rec_confidence = None
                        if hasattr(word, 'rec_score'):
                            rec_confidence = word.rec_score
                        elif hasattr(word, 'confidence'):
                            rec_confidence = word.confidence
                        
                        if rec_confidence is not None:
                            # Color based on OCR confidence
                            if rec_confidence > 0.8:
                                color = (0, 255, 0)  # Green for high confidence
                            elif rec_confidence > 0.6:
                                color = (0, 255, 255)  # Yellow for medium confidence
                            else:
                                color = (0, 0, 255)  # Red for low confidence
                            
                            cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
                            cv2.putText(out, f"OCR:{rec_confidence:.2f}", (x1, y1-5), 
                                      cv2.FONT_HERSHEY_SIMPLEX, 0.3, color, 1)
                    
                    # Show detection confidence (det_score) - Detection confidence
                    if show_detection_confidence:
                        det_confidence = None
                        if hasattr(word, 'det_score'):
                            det_confidence = word.det_score
                        
                        if det_confidence is not None:
                            # Color based on detection confidence (different color scheme)
                            if det_confidence > 0.8:
                                color = (255, 0, 255)  # Magenta for high detection confidence
                            elif det_confidence > 0.6:
                                color = (255, 165, 0)  # Orange for medium detection confidence
                            else:
                                color = (0, 0, 128)  # Dark blue for low detection confidence
                            
                            # Draw detection confidence with different line style
                            cv2.rectangle(out, (x1+2, y1+2), (x2-2, y2-2), color, 1)
                            cv2.putText(out, f"DET:{det_confidence:.2f}", (x1, y2+15), 
                                      cv2.FONT_HERSHEY_SIMPLEX, 0.3, color, 1)
            
            return out
        except Exception as e:
            self.logger.error(f"Error in confidence scores visualization: {e}")
            return img

    # =============================================================================
    # Visualization methods integrated as class methods
    # =============================================================================
    
    def _reading_order_visualizer(self, img, elements, line_color, tip_size):
        """Internal function for drawing reading order arrows """
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
            if arrow_length > 0:
                tip_length = tip_size / arrow_length
            else:
                tip_length = 0  # 長さが0なら矢じりもゼロ

            cv2.arrowedLine(
                out,
                (int(prev_center[0]), int(prev_center[1])),
                (int(cur_center[0]), int(cur_center[1])),
                line_color,
                2,
                tipLength=tip_length,
            )
        return out

    def reading_order_visualizer(self, img, results, line_color=(0, 0, 255), tip_size=10, visualize_figure_letter=False):
        """Visualize reading order of document elements """
        elements = results.paragraphs + results.tables + results.figures
        elements = sorted(elements, key=lambda x: x.order)

        out = self._reading_order_visualizer(img, elements, line_color, tip_size)

        if visualize_figure_letter:
            for figure in results.figures:
                out = self._reading_order_visualizer(
                    out, figure.paragraphs, line_color=(0, 255, 0), tip_size=5
                )

        return out

    def det_visualizer(self, img, quads, preds=None, vis_heatmap=False, line_color=(0, 255, 0)):
        """Detection visualizer """
        out = img.copy()
        h, w = out.shape[:2]
        if vis_heatmap:
            preds = preds["binary"][0]
            binary = preds.detach().cpu().numpy()
            binary = binary.squeeze(0)
            binary = (binary * 255).astype(np.uint8)
            binary = cv2.resize(binary, (w, h), interpolation=cv2.INTER_LINEAR)
            heatmap = cv2.applyColorMap(binary, cv2.COLORMAP_JET)
            out = cv2.addWeighted(out, 0.5, heatmap, 0.5, 0)

        for quad in quads:
            quad = np.array(quad).astype(np.int32)
            out = cv2.polylines(out, [quad], True, line_color, 1)
        return out

    def ocr_visualizer(self, words, img, font_path, det_score=None, vis_heatmap=False, font_size=12, font_color=(255, 0, 0), line_color=(0, 255, 0)):
        """OCR visualizer """
        out = img.copy()
        if vis_heatmap and det_score is not None:
            w, h = img.shape[1], img.shape[0]
            det_score = (det_score * 255).astype(np.uint8)
            det_score = cv2.resize(det_score, (w, h), interpolation=cv2.INTER_LINEAR)
            heatmap = cv2.applyColorMap(det_score, cv2.COLORMAP_JET)
            out = cv2.addWeighted(out, 0.5, heatmap, 0.5, 0)

        pillow_img = Image.fromarray(out)
        draw = ImageDraw.Draw(pillow_img)
        font = ImageFont.truetype(font_path, font_size)

        has_raqm = features.check_feature(feature="raqm")
        if not has_raqm:
            self.logger.warning(
                "libraqm is not installed. Vertical text rendering is not supported. Rendering horizontally instead."
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
        """Visualize elements """
        out = img.copy()
        categories = [
            "paragraphs", "tables", "figures", "section_headings", "page_header",
            "page_footer", "picture", "logo", "code", "seal", "list_item",
            "caption", "inline_formula", "display_formula", "index",
        ]

        for i, element in enumerate(elements):
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
                if hasattr(element, 'caption'):
                    caption = element.caption
                elif isinstance(element, dict) and 'caption' in element:
                    caption = element['caption']
                
                if caption is not None:
                    caption_box = None
                    if hasattr(caption, 'box'):
                        caption_box = caption.box
                    elif isinstance(caption, dict) and 'box' in caption:
                        caption_box = caption['box']
                    
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
                    if hasattr(element, 'paragraphs'):
                        paragraphs = element.paragraphs
                    elif isinstance(element, dict) and 'paragraphs' in element:
                        paragraphs = element['paragraphs']
                    
                    if paragraphs is not None:
                        for paragraph in paragraphs:
                            try:
                                para_box = None
                                if hasattr(paragraph, 'box'):
                                    para_box = paragraph.box
                                elif isinstance(paragraph, dict) and 'box' in paragraph:
                                    para_box = paragraph['box']
                                
                                if para_box is not None:
                                    color_index = categories.index("paragraphs")
                                    color = self.palette[color_index % len(self.palette)]
                                    x1, y1, x2, y2 = tuple(map(int, para_box))
                                    out = cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
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
                                self.logger.warning(f"Error processing figure paragraph: {e}")
                                continue

        return out

    def layout_visualizer_detail(self, results, img):
        """Detailed layout visualizer """
        out = img.copy()
        # results_dict = results.dict()
        out = self.visualize_element(out, "paragraphs", results.paragraphs)
        out = self.visualize_element(out, "tables", results.tables)
        out = self.visualize_element(out, "figures", results.figures)

        for table in results.tables:
            out = self.table_visualizer(out, table)

        return out

    def layout_visualizer_rough(self, results, img):
        """Rough layout visualizer """
        out = img.copy()
        results_dict = results.dict()
        for id, (category, preds) in enumerate(results_dict.items()):
            for element in preds:
                box = element["box"]
                role = element["role"]

                if role is None:
                    role = ""
                else:
                    role = f"({role})"

                color = self.palette[id % len(self.palette)]
                x1, y1, x2, y2 = tuple(map(int, box))
                out = cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
                out = cv2.putText(
                    out,
                    category + role,
                    (x1, y1),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    2,
                )

        return out

    def table_visualizer(self, img, table):
        """Table visualizer """
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

    def rec_visualizer(self, img, outputs, font_path, font_size=12, font_color=(255, 0, 0)):
        """Recognition visualizer """
        out = img.copy()
        pillow_img = Image.fromarray(out)
        draw = ImageDraw.Draw(pillow_img)
        has_raqm = features.check_feature(feature="raqm")
        if not has_raqm:
            self.logger.warning(
                "libraqm is not installed. Vertical text rendering is not supported. Rendering horizontally instead."
            )

        for pred, quad, direction, score in zip(
            outputs.contents, outputs.points, outputs.directions, outputs.scores
        ):
            quad = np.array(quad).astype(np.int32)
            font = ImageFont.truetype(font_path, font_size)

            pred = f"{pred} ({score:.3f})"

            if direction == "horizontal" or not has_raqm:
                x_offset = 0
                y_offset = -font_size

                pos_x = quad[0][0] + x_offset
                pox_y = quad[0][1] + y_offset
                draw.text((pos_x, pox_y), pred, font=font, fill=font_color)
            else:
                x_offset = -font_size
                y_offset = 0

                pos_x = quad[0][0] + x_offset
                pox_y = quad[0][1] + y_offset
                draw.text(
                    (pos_x, pox_y),
                    pred,
                    font=font,
                    fill=font_color,
                    direction="ttb",
                )

        out = np.array(pillow_img)
        return out