"""
Utility functions for Yomitoku Client
"""

import os
import re
from typing import Optional, List, Any
import numpy as np


def escape_markdown_special_chars(text: str) -> str:
    """
    Escape markdown special characters
    
    Args:
        text: Text to escape
        
    Returns:
        str: Escaped text
    """
    special_chars = r"([`*{}[\]()#+!~|-])"
    return re.sub(special_chars, r"\\\1", text)


def remove_dot_prefix(contents: str) -> str:
    """
    Remove the leading dot or hyphen from the contents
    
    Args:
        contents: Text content
        
    Returns:
        str: Content without dot prefix
    """
    return re.sub(r"^[·\-●·・]\s*", "", contents, count=1).strip()


def save_image(img: np.ndarray, path: str) -> None:
    """
    Save image to file
    
    Args:
        img: Image array to save
        path: Path to save the image
        
    Raises:
        ImportError: If cv2 is not installed
        ValueError: If failed to encode image
    """
    try:
        import cv2
    except ImportError:
        raise ImportError("OpenCV is required for image saving. Install with: pip install opencv-python")
    
    basedir = os.path.dirname(path)
    if basedir:
        os.makedirs(basedir, exist_ok=True)
    
    success, buffer = cv2.imencode(".png", img)
    
    if not success:
        raise ValueError("Failed to encode image")
    
    with open(path, "wb") as f:
        f.write(buffer.tobytes())


def save_figure(
    figures: List[Any],
    img: Optional[np.ndarray],
    out_path: str,
    figure_dir: str = "figures"
) -> List[str]:
    """
    Save figures from document to separate files
    
    Args:
        figures: List of figure objects
        img: Source image array
        out_path: Output path for the main file
        figure_dir: Directory name for saving figures
        
    Returns:
        List[str]: Paths of saved figure files
    """
    if img is None:
        return []
    
    saved_paths = []
    
    for i, figure in enumerate(figures):
        x1, y1, x2, y2 = map(int, figure.box)
        figure_img = img[y1:y2, x1:x2, :]
        
        save_dir = os.path.dirname(out_path)
        save_dir = os.path.join(save_dir, figure_dir)
        os.makedirs(save_dir, exist_ok=True)
        
        filename = os.path.splitext(os.path.basename(out_path))[0]
        figure_name = f"{filename}_figure_{i}.png"
        figure_path = os.path.join(save_dir, figure_name)
        
        save_image(figure_img, figure_path)
        saved_paths.append(os.path.join(figure_dir, figure_name))
    
    return saved_paths


def is_numeric_list_item(contents: str) -> bool:
    """
    Check if the contents start with a number followed by a dot or parentheses
    
    Args:
        contents: Text content
        
    Returns:
        bool: True if it's a numeric list item
    """
    return re.match(r"^[\(]?\d+[\.\)]?\s*", contents) is not None


def is_dot_list_item(contents: str) -> bool:
    """
    Check if the contents start with a dot
    
    Args:
        contents: Text content
        
    Returns:
        bool: True if it's a dot list item
    """
    return re.match(r"^[·\-●·・]", contents) is not None


def remove_numeric_prefix(contents: str) -> str:
    """
    Remove the leading number and dot or parentheses from the contents
    
    Args:
        contents: Text content
        
    Returns:
        str: Content without numeric prefix
    """
    return re.sub(r"^[\(]?\d+[\.\)]?\s*", "", contents, count=1).strip()


def convert_text_to_html(text: str) -> str:
    """
    Convert text to HTML, escaping special characters
    
    Args:
        text: Text to convert
        
    Returns:
        str: HTML-escaped text
    """
    from html import escape
    
    # URL regex pattern
    url_regex = re.compile(r"https?://[^\s<>]+")
    
    def replace_url(match):
        url = match.group(0)
        return escape(url)
    
    return url_regex.sub(replace_url, escape(text))