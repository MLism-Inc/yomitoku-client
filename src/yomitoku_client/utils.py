"""
Utility functions for Yomitoku Client
"""

import os
import re
from typing import Optional, List, Any, Tuple, Union
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


def load_charset(charset_path: str) -> str:
    """
    Load character set from file
    
    Args:
        charset_path: Path to charset file
        
    Returns:
        str: Character set content
    """
    with open(charset_path, "r", encoding="utf-8") as f:
        charset = f.read()
    return charset


def filter_by_flag(elements: List[Any], flags: List[bool]) -> List[Any]:
    """
    Filter elements by boolean flags
    
    Args:
        elements: List of elements to filter
        flags: List of boolean flags
        
    Returns:
        List[Any]: Filtered elements
        
    Raises:
        AssertionError: If lengths don't match
    """
    assert len(elements) == len(flags), "Elements and flags must have the same length"
    return [element for element, flag in zip(elements, flags) if flag]


def calc_overlap_ratio(rect_a: List[float], rect_b: List[float]) -> Tuple[float, Optional[List[int]]]:
    """
    Calculate overlap ratio between two rectangles
    
    Args:
        rect_a: First rectangle [x1, y1, x2, y2]
        rect_b: Second rectangle [x1, y1, x2, y2]
        
    Returns:
        Tuple[float, Optional[List[int]]]: (overlap_ratio, intersection_rect)
    """
    intersection = calc_intersection(rect_a, rect_b)
    if intersection is None:
        return 0, None

    ix1, iy1, ix2, iy2 = intersection
    overlap_width = ix2 - ix1
    overlap_height = iy2 - iy1
    bx1, by1, bx2, by2 = rect_b

    b_area = (bx2 - bx1) * (by2 - by1)
    overlap_area = overlap_width * overlap_height
    overlap_ratio = overlap_area / b_area
    
    return overlap_ratio, intersection


def calc_distance(rect_a: List[float], rect_b: List[float]) -> float:
    """
    Calculate distance between centers of two rectangles
    
    Args:
        rect_a: First rectangle [x1, y1, x2, y2]
        rect_b: Second rectangle [x1, y1, x2, y2]
        
    Returns:
        float: Distance between centers
    """
    ax1, ay1, ax2, ay2 = map(int, rect_a)
    bx1, by1, bx2, by2 = map(int, rect_b)

    # Center coordinates of rectangle A
    center_a_x = (ax1 + ax2) / 2
    center_a_y = (ay1 + ay2) / 2

    # Center coordinates of rectangle B
    center_b_x = (bx1 + bx2) / 2
    center_b_y = (by1 + by2) / 2

    # Calculate distance between centers
    distance = ((center_a_x - center_b_x) ** 2 + (center_a_y - center_b_y) ** 2) ** 0.5

    return distance


def is_contained(rect_a: List[float], rect_b: List[float], threshold: float = 0.8) -> bool:
    """
    Check if rectangle B is contained in rectangle A
    
    Args:
        rect_a: Container rectangle [x1, y1, x2, y2]
        rect_b: Contained rectangle [x1, y1, x2, y2]
        threshold: Overlap threshold for containment
        
    Returns:
        bool: True if rect_b is contained in rect_a
    """
    overlap_ratio, _ = calc_overlap_ratio(rect_a, rect_b)
    return overlap_ratio > threshold


def calc_intersection(rect_a: List[float], rect_b: List[float]) -> Optional[List[int]]:
    """
    Calculate intersection of two rectangles
    
    Args:
        rect_a: First rectangle [x1, y1, x2, y2]
        rect_b: Second rectangle [x1, y1, x2, y2]
        
    Returns:
        Optional[List[int]]: Intersection rectangle or None if no intersection
    """
    ax1, ay1, ax2, ay2 = map(int, rect_a)
    bx1, by1, bx2, by2 = map(int, rect_b)

    # Intersection coordinates
    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)

    overlap_width = max(0, ix2 - ix1)
    overlap_height = max(0, iy2 - iy1)

    if overlap_width == 0 or overlap_height == 0:
        return None

    return [ix1, iy1, ix2, iy2]


def is_intersected_horizontal(rect_a: List[float], rect_b: List[float], threshold: float = 0.5) -> bool:
    """
    Check if two rectangles intersect horizontally
    
    Args:
        rect_a: First rectangle [x1, y1, x2, y2]
        rect_b: Second rectangle [x1, y1, x2, y2]
        threshold: Intersection threshold
        
    Returns:
        bool: True if horizontally intersected
    """
    _, ay1, _, ay2 = map(int, rect_a)
    _, by1, _, by2 = map(int, rect_b)

    # Intersection coordinates
    iy1 = max(ay1, by1)
    iy2 = min(ay2, by2)

    min_height = min(ay2 - ay1, by2 - by1)
    overlap_height = max(0, iy2 - iy1)

    return (overlap_height / min_height) >= threshold


def is_intersected_vertical(rect_a: List[float], rect_b: List[float]) -> bool:
    """
    Check if two rectangles intersect vertically
    
    Args:
        rect_a: First rectangle [x1, y1, x2, y2]
        rect_b: Second rectangle [x1, y1, x2, y2]
        
    Returns:
        bool: True if vertically intersected
    """
    ax1, _, ax2, _ = map(int, rect_a)
    bx1, _, bx2, _ = map(int, rect_b)

    # Intersection coordinates
    ix1 = max(ax1, bx1)
    ix2 = min(ax2, bx2)

    overlap_width = max(0, ix2 - ix1)
    return overlap_width > 0


def quad_to_xyxy(quad: List[List[float]]) -> Tuple[float, float, float, float]:
    """
    Convert quadrilateral to bounding box rectangle
    
    Args:
        quad: Quadrilateral points [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
        
    Returns:
        Tuple[float, float, float, float]: Bounding box (x1, y1, x2, y2)
    """
    x1 = min([x for x, _ in quad])
    y1 = min([y for _, y in quad])
    x2 = max([x for x, _ in quad])
    y2 = max([y for _, y in quad])

    return x1, y1, x2, y2


def convert_table_array(table: Any, padding: bool = False, drop_empty: bool = False) -> List[List[str]]:
    """
    Convert table object to 2D array
    
    Args:
        table: Table object with cells, n_row, n_col attributes
        padding: Whether to pad span cells with same contents
        drop_empty: Whether to drop empty rows and columns
        
    Returns:
        List[List[str]]: 2D array representing table
    """
    n_rows = table.n_row
    n_cols = table.n_col

    table_array = [["" for _ in range(n_cols)] for _ in range(n_rows)]

    for cell in table.cells:
        row = cell.row - 1
        col = cell.col - 1
        row_span = cell.row_span
        col_span = cell.col_span
        contents = cell.contents

        table_array[row][col] = contents
        if padding:
            for r in range(row_span):
                for c in range(col_span):
                    if row + r + 1 < n_rows and col + c + 1 < n_cols:
                        table_array[row + r + 1][col + c + 1] = contents

    if drop_empty:
        # Drop empty rows
        table_array = [row for row in table_array if any(cell != "" for cell in row)]

        # Drop empty columns
        if table_array:
            keep = [
                j
                for j in range(len(table_array[0]))
                if any(row[j] != "" for row in table_array)
            ]
            table_array = [[row[j] for j in keep] for row in table_array]

    return table_array


def table_to_csv(table: Any, padding: bool = False, drop_empty: bool = False) -> str:
    """
    Convert table object to CSV string
    
    Args:
        table: Table object to convert
        padding: Whether to pad span cells with same contents
        drop_empty: Whether to drop empty rows and columns
        
    Returns:
        str: CSV string representation of the table
    """
    table_array = convert_table_array(table, padding=padding, drop_empty=drop_empty)
    csv_lines = []

    for row in table_array:
        csv_lines.append(",".join(f'"{cell}"' for cell in row))

    return "\n".join(csv_lines)


def convert_table_array_to_dict(table_array: List[List[str]], header_row: int = 1) -> List[dict]:
    """
    Convert table array to list of dictionaries
    
    Args:
        table_array: 2D table array
        header_row: Number of header rows
        
    Returns:
        List[dict]: List of dictionaries with header keys
    """
    n_cols = len(table_array[0])
    n_rows = len(table_array)

    header_cols = []
    for i in range(n_cols):
        header = []
        for j in range(header_row):
            header.append(table_array[j][i])

        if len(header) > 0:
            header_cols.append("_".join(header))
        else:
            header_cols.append(f"col_{i}")

    table_dict = []
    for i in range(header_row, n_rows):
        row_dict = {}
        for j in range(n_cols):
            row_dict[header_cols[j]] = table_array[i][j]
        table_dict.append(row_dict)

    return table_dict