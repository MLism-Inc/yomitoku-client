"""
Document visualizer for layout analysis and OCR results
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, features
from typing import Any, Dict, List, Optional, Tuple, Union
import logging

from .base import BaseVisualizer


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
                # 安全获取box属性
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
                    
                    # 处理figures中的paragraphs
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
