"""
Document visualizer for layout analysis and OCR results
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, features
from typing import Any, Dict, List, Optional, Tuple, Union
import logging

from .base import BaseVisualizer
from ..utils import calc_overlap_ratio, calc_distance, is_contained


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
        self.palette = self.DEFAULT_PALETTE
        
    def visualize(self, data: Any, **kwargs) -> np.ndarray:
        """
        Main visualization method
        
        Args:
            data: Document analysis results or image with results
            **kwargs: Visualization parameters
            
        Returns:
            Visualized image as numpy array
        """
        if isinstance(data, tuple) and len(data) == 2:
            img, results = data
        else:
            img = data
            results = kwargs.get('results')
            
        # Handle image input - convert string path to numpy array
        if isinstance(img, str):
            try:
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
                            if k not in ['type']}
            return self.visualize_reading_order(img, results, **reading_kwargs)
        elif visualization_type == 'layout_detail':
            return self.visualize_layout_detail(img, results)
        elif visualization_type == 'layout_rough':
            return self.visualize_layout_rough(img, results)
        elif visualization_type == 'ocr':
            # Filter out non-ocr parameters
            ocr_kwargs = {k: v for k, v in kwargs.items() 
                         if k not in ['type']}
            return self.visualize_ocr(img, results, **ocr_kwargs)
        elif visualization_type == 'detection':
            # Filter out non-detection parameters
            detection_kwargs = {k: v for k, v in kwargs.items() 
                              if k not in ['type']}
            return self.visualize_detection(img, results, **detection_kwargs)
        elif visualization_type == 'recognition':
            # Filter out non-recognition parameters
            recognition_kwargs = {k: v for k, v in kwargs.items() 
                                if k not in ['type']}
            return self.visualize_recognition(img, results, **recognition_kwargs)
        elif visualization_type == 'relationships':
            # Filter out non-relationships parameters
            relationships_kwargs = {k: v for k, v in kwargs.items() 
                                  if k not in ['type', 'results']}
            return self.visualize_element_relationships(img, results, **relationships_kwargs)
        elif visualization_type == 'hierarchy':
            # Filter out non-hierarchy parameters
            hierarchy_kwargs = {k: v for k, v in kwargs.items() 
                              if k not in ['type', 'results']}
            return self.visualize_element_hierarchy(img, results, **hierarchy_kwargs)
        elif visualization_type == 'confidence':
            # Filter out non-confidence parameters
            confidence_kwargs = {k: v for k, v in kwargs.items()
                               if k not in ['type', 'results']}
            return self.visualize_confidence_scores(img, results, **confidence_kwargs)
        elif visualization_type == 'captions':
            # Filter out non-caption parameters
            caption_kwargs = {k: v for k, v in kwargs.items()
                            if k not in ['type', 'results']}
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
            elements = results.paragraphs + results.tables + results.figures
            elements = sorted(elements, key=lambda x: x.order)
            
            out = self._draw_reading_order_arrows(img, elements, line_color, tip_size)
            
            if visualize_figure_letter:
                for figure in results.figures:
                    out = self._draw_reading_order_arrows(
                        out, figure.paragraphs, line_color=(0, 255, 0), tip_size=5
                    )
                    
            return out
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
            out = img.copy()
            out = self._visualize_element(out, "paragraphs", results.paragraphs)
            out = self._visualize_element(out, "tables", results.tables)
            out = self._visualize_element(out, "figures", results.figures)
            
            for table in results.tables:
                out = self._visualize_table(out, table)
                
            return out
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
            out = img.copy()
            results_dict = results.dict()
            
            for id, (category, preds) in enumerate(results_dict.items()):
                for element in preds:
                    box = element["box"]
                    role = element.get("role")
                    
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
        except Exception as e:
            self.logger.error(f"Error in layout rough visualization: {e}")
            return img
    
    def visualize_ocr(self, img: np.ndarray, words: List[Any], 
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
            words: OCR word results
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
            out = img.copy()
            
            if vis_heatmap and det_score is not None:
                w, h = img.shape[1], img.shape[0]
                det_score = (det_score * 255).astype(np.uint8)
                det_score = cv2.resize(det_score, (w, h), interpolation=cv2.INTER_LINEAR)
                heatmap = cv2.applyColorMap(det_score, cv2.COLORMAP_JET)
                out = cv2.addWeighted(out, 0.5, heatmap, 0.5, 0)
            
            if font_path:
                pillow_img = Image.fromarray(out)
                draw = ImageDraw.Draw(pillow_img)
                font = ImageFont.truetype(font_path, font_size)
                
                has_raqm = features.check_feature(feature="raqm")
                if not has_raqm:
                    self.logger.warning(
                        "libraqm is not installed. Vertical text rendering is not supported."
                    )
                
                for word in words:
                    poly = word.points
                    text = word.content
                    direction = getattr(word, 'direction', 'horizontal')
                    
                    poly_line = [tuple(point) for point in poly]
                    draw.polygon(poly_line, outline=line_color, fill=None)
                    
                    if direction == "horizontal" or not has_raqm:
                        x_offset = 0
                        y_offset = -font_size
                        pos_x = poly[0][0] + x_offset
                        pos_y = poly[0][1] + y_offset
                        draw.text((pos_x, pos_y), text, font=font, fill=font_color)
                    else:
                        x_offset = -font_size
                        y_offset = 0
                        pos_x = poly[0][0] + x_offset
                        pos_y = poly[0][1] + y_offset
                        draw.text(
                            (pos_x, pos_y),
                            text,
                            font=font,
                            fill=font_color,
                            direction="ttb",
                        )
                
                out = np.array(pillow_img)
            
            return out
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
            out = img.copy()
            h, w = out.shape[:2]
            
            if vis_heatmap and preds is not None:
                preds_binary = preds["binary"][0]
                binary = preds_binary.detach().cpu().numpy()
                binary = binary.squeeze(0)
                binary = (binary * 255).astype(np.uint8)
                binary = cv2.resize(binary, (w, h), interpolation=cv2.INTER_LINEAR)
                heatmap = cv2.applyColorMap(binary, cv2.COLORMAP_JET)
                out = cv2.addWeighted(out, 0.5, heatmap, 0.5, 0)
            
            for quad in quads:
                quad = np.array(quad).astype(np.int32)
                out = cv2.polylines(out, [quad], True, line_color, 1)
                
            return out
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
                
            out = img.copy()
            pillow_img = Image.fromarray(out)
            draw = ImageDraw.Draw(pillow_img)
            
            has_raqm = features.check_feature(feature="raqm")
            if not has_raqm:
                self.logger.warning(
                    "libraqm is not installed. Vertical text rendering is not supported."
                )
            
            for pred, quad, direction, score in zip(
                outputs.contents, outputs.points, outputs.directions, outputs.scores
            ):
                quad = np.array(quad).astype(np.int32)
                font = ImageFont.truetype(font_path, font_size)
                
                pred_text = f"{pred} ({score:.3f})"
                
                if direction == "horizontal" or not has_raqm:
                    x_offset = 0
                    y_offset = -font_size
                    pos_x = quad[0][0] + x_offset
                    pos_y = quad[0][1] + y_offset
                    draw.text((pos_x, pos_y), pred_text, font=font, fill=font_color)
                else:
                    x_offset = -font_size
                    y_offset = 0
                    pos_x = quad[0][0] + x_offset
                    pos_y = quad[0][1] + y_offset
                    draw.text(
                        (pos_x, pos_y),
                        pred_text,
                        font=font,
                        fill=font_color,
                        direction="ttb",
                    )
            
            out = np.array(pillow_img)
            return out
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
        """Visualize specific element category"""
        out = img.copy()
        categories = [
            "paragraphs", "tables", "figures", "section_headings", "page_header",
            "page_footer", "picture", "logo", "code", "seal", "list_item",
            "caption", "inline_formula", "display_formula", "index",
        ]
        
        for element in elements:
            try:
                if hasattr(element, 'box'):
                    box = element.box
                elif isinstance(element, dict) and 'box' in element:
                    box = element['box']
                else:
                    self.logger.warning(f"Element has no box attribute: {type(element)}")
                    continue
                
                role = None
                
                if category != "tables":
                    if hasattr(element, 'role'):
                        role = element.role
                    elif isinstance(element, dict) and 'role' in element:
                        role = element['role']
                
                color_index = categories.index(category)
                if role is None:
                    role = ""
                else:
                    try:
                        color_index = categories.index(role)
                    except ValueError:
                        # If role is not in categories, use default category index
                        pass
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
                    # 处理caption
                    caption = None
                    if hasattr(element, 'caption'):
                        caption = element.caption
                    elif isinstance(element, dict) and 'caption' in element:
                        caption = element['caption']

                    if caption is not None:
                        caption_box = None

                        # Extract caption box
                        if hasattr(caption, 'box'):
                            caption_box = caption.box
                        elif isinstance(caption, dict) and 'box' in caption:
                            caption_box = caption['box']

                        if caption_box is not None:
                            color_index = categories.index("caption")
                            color = self.palette[color_index % len(self.palette)]
                            x1, y1, x2, y2 = tuple(map(int, caption_box))
                            out = cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)

                            # Just display "caption" label for consistency
                            out = cv2.putText(
                                out,
                                "caption",
                                (x1, y1 - 5),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.4,
                                color,
                                1,
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
            except Exception as e:
                self.logger.warning(f"Error processing element in {category}: {e}")
                continue
        
        return out
    
    def _visualize_table(self, img: np.ndarray, table: Any) -> np.ndarray:
        """Visualize table structure"""
        out = img.copy()
        
        if hasattr(table, 'cells'):
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
