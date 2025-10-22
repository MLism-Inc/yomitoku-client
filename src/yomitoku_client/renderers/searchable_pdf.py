import os
from io import BytesIO

import jaconv
import numpy as np
from PIL import Image
from reportlab.lib.colors import Color
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from ..constants import ROOT_DIR

from ..models import DocumentResult

FONT_PATH = ROOT_DIR + "/resource/MPLUS1p-Medium.ttf"


def calc_overlap_ratio(rect_a, rect_b):
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


def calc_intersection(rect_a, rect_b):
    ax1, ay1, ax2, ay2 = map(int, rect_a)
    bx1, by1, bx2, by2 = map(int, rect_b)

    # 交差領域の左上と右下の座標
    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)

    overlap_width = max(0, ix2 - ix1)
    overlap_height = max(0, iy2 - iy1)

    if overlap_width == 0 or overlap_height == 0:
        return None

    return [ix1, iy1, ix2, iy2]


def calc_overlap_ratio(rect_a, rect_b):
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


def is_contained(rect_a, rect_b, threshold=0.8):
    """二つの矩形A, Bが与えられたとき、矩形Bが矩形Aに含まれるかどうかを判定する。
    ずれを許容するため、重複率求め、thresholdを超える場合にTrueを返す。


    Args:
        rect_a (np.array): x1, y1, x2, y2
        rect_b (np.array): x1, y1, x2, y2
        threshold (float, optional): 判定の閾値. Defaults to 0.9.

    Returns:
        bool: 矩形Bが矩形Aに含まれる場合True
    """

    overlap_ratio, _ = calc_overlap_ratio(rect_a, rect_b)

    if overlap_ratio > threshold:
        return True

    return False


def _poly2rect(points):
    """
    Convert a polygon defined by its corner points to a rectangle.
    The points should be in the format [[x1, y1], [x2, y2], [x3, y3], [x4, y4]].
    """
    points = np.array(points, dtype=int)
    x_min = points[:, 0].min()
    x_max = points[:, 0].max()
    y_min = points[:, 1].min()
    y_max = points[:, 1].max()

    return [x_min, y_min, x_max, y_max]


def _calc_font_size(content, bbox_height, bbox_width):
    rates = np.arange(0.5, 1.0, 0.01)

    min_diff = np.inf
    best_font_size = None
    for rate in rates:
        font_size = bbox_height * rate
        text_w = stringWidth(content, "MPLUS1p-Medium", font_size)
        diff = abs(text_w - bbox_width)
        if diff < min_diff:
            min_diff = diff
            best_font_size = font_size

    return best_font_size


def to_full_width(text):
    fw_map = {
        "\u00a5": "\uffe5",  # ¥ → ￥
        "\u00b7": "\u30fb",  # · → ・
        " ": "\u3000",  # 半角スペース→全角スペース
    }

    TO_FULLWIDTH = str.maketrans(fw_map)

    jaconv_text = jaconv.h2z(text, kana=True, ascii=True, digit=True)
    jaconv_text = jaconv_text.translate(TO_FULLWIDTH)

    return jaconv_text


from typing import List, Optional


def create_searchable_pdf(
    docs: List[DocumentResult],
    images: List[Image.Image],
    font_path: Optional[str] = None,
):
    """
    Create a searchable PDF from an image and OCR results.

    Args:
        images (List[Image.Image]): A list of pillow images.
        docs (List[DocumentAnalyzerSchema]): A list of OCR results.
        output_path (str): Path to the output PDF file.
        font_path (str, optional): Path to the font file. Defaults to None.
    """
    if font_path is None:
        font_path = FONT_PATH

    pdfmetrics.registerFont(TTFont("MPLUS1p-Medium", font_path))

    packet = BytesIO()
    c = canvas.Canvas(packet)

    for i, (image, doc) in enumerate(zip(images, docs)):
        image_path = f"tmp_{i}.png"
        image.save(image_path, format="JPEG", quality=90)
        w, h = image.size

        c.setPageSize((w, h))
        c.drawImage(image_path, 0, 0, width=w, height=h)
        os.remove(image_path)

        # Collect all text containers
        containers = []
        for p in doc.paragraphs:
            containers.append(
                {
                    "box": p.box,
                    "order": p.order,
                    "sub_order": 0,
                    "direction": p.direction,
                    "type": "paragraph",
                }
            )
        for t in doc.tables:
            for cell in t.cells:
                containers.append(
                    {
                        "box": cell.box,
                        "order": t.order,
                        "sub_order": (cell.row, cell.col),
                        "direction": "horizontal",  # Assuming table text is horizontal
                        "type": "table_cell",
                    }
                )

            if t.caption is not None:
                containers.append(
                    {
                        "box": t.caption.box,
                        "order": t.order,
                        "sub_order": (-1, -1),
                        "direction": t.caption.direction,
                        "type": "table_caption",
                    }
                )

        for f in doc.figures:
            for para_idx, p in enumerate(f.paragraphs):
                containers.append(
                    {
                        "box": p.box,
                        "order": f.order,
                        "sub_order": para_idx,
                        "direction": p.direction,
                        "type": "figure_paragraph",
                    }
                )

            if f.caption is not None:
                containers.append(
                    {
                        "box": f.caption.box,
                        "order": f.order,
                        "sub_order": 0,
                        "direction": f.caption.direction,
                        "type": "figure_caption",
                    }
                )

        # Sort containers by reading order
        containers = sorted(containers, key=lambda c: (c["order"], c["sub_order"]))

        all_words = []
        for container in containers:
            container_words = []
            for word in doc.words:
                word_box = _poly2rect(word.points)
                if is_contained(container["box"], word_box, 0.5):
                    container_words.append(word)

            # Sort words within the container
            if container["direction"] == "vertical":
                # Right-to-left column, then top-to-bottom
                container_words.sort(
                    key=lambda w: (
                        -_poly2rect(w.points)[0],
                        _poly2rect(w.points)[1],
                    )
                )
            else:
                # Top-to-bottom, then left-to-right
                container_words.sort(
                    key=lambda w: (
                        _poly2rect(w.points)[1],
                        _poly2rect(w.points)[0],
                    )
                )
            all_words.extend(container_words)

        # Set transparent color for text
        text_color = Color(1, 1, 1, alpha=0)
        c.setFillColor(text_color)

        for word in all_words:
            text = word.content
            bbox = _poly2rect(word.points)
            direction = word.direction

            x1, y1, x2, y2 = bbox
            bbox_height = y2 - y1
            bbox_width = x2 - x1

            if direction == "vertical":
                text = to_full_width(text)
                font_size = _calc_font_size(text, bbox_width, bbox_height)
            else:
                font_size = _calc_font_size(text, bbox_height, bbox_width)

            if not font_size:
                continue

            c.setFont("MPLUS1p-Medium", font_size)

            if direction == "vertical":
                # Adjust for vertical text rendering
                base_y = h - y1
                char_height = bbox_height / len(text) if text else 0

                for j, ch in enumerate(text):
                    char_x = x1 + (bbox_width - font_size) / 2
                    char_y = base_y - (j * char_height) - char_height / 2

                    c.saveState()
                    c.translate(char_x, char_y + font_size / 2)
                    c.rotate(-90)
                    c.drawString(0, 0, ch)
                    c.restoreState()
            else:
                base_y = h - y2 + (bbox_height - font_size) * 0.5
                c.drawString(x1, base_y, text)

        c.showPage()

    c.save()

    return packet
