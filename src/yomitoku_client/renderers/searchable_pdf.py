"""
Searchable PDF Generator - Create searchable PDFs from images and OCR results
"""

import os
from typing import List, Optional, Any
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

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    fitz = None

# Get the directory where this module is located
# Since we're in renderers/, we need to go up one level to find resource/
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_PATH = ROOT_DIR + "/resource/MPLUS1p-Medium.ttf"


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
    """
    Calculate optimal font size for text to fit in bounding box
    """
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
    """
    Convert text to full-width characters
    """
    if not JACONV_AVAILABLE:
        return text
    
    fw_map = {
        "\u00a5": "\uffe5",  # ¥ → ￥
        "\u00b7": "\u30fb",  # · → ・
        " ": "\u3000",  # Half-width space → Full-width space
    }

    TO_FULLWIDTH = str.maketrans(fw_map)

    jaconv_text = jaconv.h2z(text, kana=True, ascii=True, digit=True)
    jaconv_text = jaconv_text.translate(TO_FULLWIDTH)

    return jaconv_text


def _detect_pdf_dpi(pdf_path):
    """
    Detect the DPI of the original PDF by analyzing embedded images
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        int: Detected DPI of the PDF
    """
    if not PYMUPDF_AVAILABLE:
        raise ImportError("PyMuPDF is required for PDF processing. Install with: pip install PyMuPDF")
    
    doc = fitz.open(pdf_path)
    page = doc[0]  # Use first page for DPI detection
    
    # Try to find embedded images to analyze their DPI
    image_list = page.get_images()
    
    if image_list:
        # If there are embedded images, analyze the first one
        try:
            img_index = image_list[0][0]
            img = doc.extract_image(img_index)
            img_bytes = img["image"]
            
            # Get image dimensions
            from PIL import Image
            from io import BytesIO
            pil_img = Image.open(BytesIO(img_bytes))
            img_width, img_height = pil_img.size
            
            # Get image display dimensions from PDF
            img_rects = page.get_image_rects(img_index)
            if img_rects:
                img_rect = img_rects[0]
                display_width_pt = img_rect.width
                display_height_pt = img_rect.height
                
                # Calculate DPI based on image dimensions
                dpi_x = (img_width * 72) / display_width_pt
                dpi_y = (img_height * 72) / display_height_pt
                detected_dpi = round((dpi_x + dpi_y) / 2)
                
                # Round to common DPI values
                common_dpis = [72, 96, 150, 200, 300, 600]
                closest_dpi = min(common_dpis, key=lambda x: abs(x - detected_dpi))
                
                doc.close()
                return closest_dpi
        except Exception as e:
            print(f"Warning: Could not analyze embedded image: {e}")
    
    # No embedded images or analysis failed, use default high DPI
    doc.close()
    return 300


def _pdf_to_images_pypdfium2(pdf_path, dpi=200):
    """
    Convert PDF pages to images using pypdfium2
    
    Args:
        pdf_path (str): Path to the PDF file
        dpi (int): Resolution for image conversion (default 200)
        
    Returns:
        tuple: (list of PIL Images, list of original page dimensions, DPI)
    """
    try:
        import pypdfium2
    except ImportError:
        raise ImportError("pypdfium2 is required for PDF processing. Install with: pip install pypdfium2")
    
    images = []
    page_dimensions = []
    doc = pypdfium2.PdfDocument(pdf_path)
    
    
    renderer = doc.render(
        pypdfium2.PdfBitmap.to_pil,
        scale=dpi / 72,  
    )
    images = list(renderer)
    
    # Get page dimensions for each page
    for page_num in range(len(doc)):
        page = doc[page_num]
        original_width = page.get_width()
        original_height = page.get_height()
        page_dimensions.append((original_width, original_height))
    
    doc.close()
    return images, page_dimensions, dpi


def _pdf_to_images(pdf_path, dpi=None):
    """
    Convert PDF pages to images using PyMuPDF with detected or specified DPI
    
    Args:
        pdf_path (str): Path to the PDF file
        dpi (int, optional): Resolution for image conversion. If None, detects original DPI.
        
    Returns:
        tuple: (list of PIL Images, list of original page dimensions, detected DPI)
    """
    if not PYMUPDF_AVAILABLE:
        raise ImportError("PyMuPDF is required for PDF processing. Install with: pip install PyMuPDF")
    
    # Detect original DPI if not specified
    if dpi is None:
        dpi = _detect_pdf_dpi(pdf_path)
    
    images = []
    page_dimensions = []
    doc = fitz.open(pdf_path)
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        
        # Get original page dimensions (in points)
        page_rect = page.rect
        original_width = page_rect.width
        original_height = page_rect.height
        page_dimensions.append((original_width, original_height))
        
        # Calculate matrix to maintain aspect ratio and use detected/specified DPI
        zoom = dpi / 72.0  # 72 is default DPI
        mat = fitz.Matrix(zoom, zoom)
        
        # Create pixmap with high quality settings
        pix = page.get_pixmap(matrix=mat, alpha=False)
        
        # Convert to high-quality image data
        img_data = pix.tobytes("png")
        
        # Convert to PIL Image
        from io import BytesIO
        img = Image.open(BytesIO(img_data))
        
        images.append(img)
    
    doc.close()
    return images, page_dimensions, dpi


def create_searchable_pdf_from_pdf(pdf_path, ocr_results, output_path, font_path=None, dpi=200, page_index=None, use_pypdfium2=True):
    """
    Create a searchable PDF by directly modifying the original PDF content.
    This preserves the original quality and clarity.

    Args:
        pdf_path (str): Path to the input PDF file.
        ocr_results (list): List of OCR results corresponding to the PDF pages.
        output_path (str): Path to save the output PDF.
        font_path (str, optional): Path to the font file. Defaults to MPLUS1p-Medium.ttf from resource.
        dpi (int, optional): DPI for image conversion (default 200).
        page_index (int, optional): Specific page index to process (0-based). If None, processes all pages.
        use_pypdfium2 (bool, optional): Whether to use pypdfium2 or PyMuPDF.
    """
    if use_pypdfium2:
        try:
            import pypdfium2
        except ImportError:
            raise ImportError("pypdfium2 is required for PDF processing. Install with: pip install pypdfium2")
        
        # Use the pypdfium2-based PDF processing
        images, page_dimensions, actual_dpi = _pdf_to_images_pypdfium2(pdf_path, dpi)
        
        # Create searchable PDF using the images
        create_searchable_pdf(images, ocr_results, output_path, font_path, page_dimensions)
        return
    
    # Fallback to PyMuPDF approach
    if not PYMUPDF_AVAILABLE:
        raise ImportError("PyMuPDF is required for PDF processing. Install with: pip install PyMuPDF")
    
    # Use default font if not specified
    if font_path is None:
        font_path = FONT_PATH
    
    # Register font
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    
    try:
        pdfmetrics.registerFont(TTFont("MPLUS1p-Medium", font_path))
        font_name = "MPLUS1p-Medium"
    except Exception as e:
        print(f"Warning: Could not register font {font_path}: {e}")
        font_name = "Helvetica"
    
    # Open the original PDF
    doc = fitz.open(pdf_path)
    
    # Determine which pages to process
    if page_index is not None:
        pages_to_process = [page_index] if page_index < len(doc) else []
    else:
        pages_to_process = list(range(len(doc)))
    
    # Process each page
    for i, page_num in enumerate(pages_to_process):
        page = doc[page_num]
        
        # Get corresponding OCR result
        if i < len(ocr_results):
            ocr_result = ocr_results[i]
        else:
            ocr_result = ocr_results[0] if ocr_results else None
        
        if ocr_result is None:
            continue
        
        # Remove existing text content (optional - comment out if you want to keep original text)
        # This creates a clean slate for the new text
        page.clean_contents()
        
        # Add OCR text as invisible text layer
        for word in ocr_result.words:
            if hasattr(word, 'content') and word.content.strip():
                # Get word position
                if hasattr(word, 'points') and word.points:
                    # Calculate bounding box
                    x_coords = [p[0] for p in word.points]
                    y_coords = [p[1] for p in word.points]
                    x1, x2 = min(x_coords), max(x_coords)
                    y1, y2 = min(y_coords), max(y_coords)
                    
                    # Add invisible text
                    try:
                        # Use PyMuPDF's text insertion with invisible color
                        page.insert_text(
                            (x1, y1), 
                            word.content,
                            fontsize=8,  # Small font size for searchability
                            color=(1, 1, 1),  # White color (invisible on white background)
                            overlay=False
                        )
                    except Exception as e:
                        print(f"Warning: Could not insert text '{word.content}': {e}")
    
    # Save the modified PDF
    doc.save(output_path)
    doc.close()


def create_searchable_pdf(images, ocr_results, output_path, font_path=None, page_dimensions=None):
    """
    Create a searchable PDF from images and OCR results.

    Args:
        images (list): List of images as numpy arrays, PIL Images, file paths, or PDF paths.
        ocr_results (list): List of OCR results corresponding to the images.
        output_path (str): Path to save the output PDF.
        font_path (str, optional): Path to the font file. Defaults to MPLUS1p-Medium.ttf from resource.
        page_dimensions (list, optional): List of original page dimensions (width, height) in points.
    """
    if not PIL_AVAILABLE:
        raise ImportError("PIL is required for PDF generation. Install with: pip install Pillow")

    if not REPORTLAB_AVAILABLE:
        raise ImportError("ReportLab is required for PDF generation. Install with: pip install reportlab")

    # Use default MPLUS1p-Medium font from resource
    if font_path is None:
        font_path = FONT_PATH

    # Register font
    pdfmetrics.registerFont(TTFont("MPLUS1p-Medium", font_path))

    packet = BytesIO()
    c = canvas.Canvas(packet)

    for i, (image, ocr_result) in enumerate(zip(images, ocr_results)):
        # Handle different image input types
        if hasattr(image, '__fspath__'):  # pathlib.Path or similar
            # Load image from file path
            image = Image.open(str(image))
        elif isinstance(image, str):
            # Load image from string path
            image = Image.open(image)
        elif hasattr(image, 'shape'):  # numpy array
            # Convert BGR to RGB
            image = Image.fromarray(image[:, :, ::-1])
        else:
            # Assume it's already a PIL Image
            pass
            
        image_path = f"tmp_{i}.png"
        # Save with high quality settings to maintain clarity
        image.save(image_path, "PNG", optimize=False, compress_level=0)
        
        # Use original page dimensions if available, otherwise use image dimensions
        if page_dimensions and i < len(page_dimensions):
            w, h = page_dimensions[i]
        else:
            w, h = image.size

        # Set page size to match the original dimensions exactly
        c.setPageSize((w, h))
        # Draw image with exact dimensions to maintain quality
        c.drawImage(image_path, 0, 0, width=w, height=h, preserveAspectRatio=True)
        os.remove(image_path)  # Clean up temporary image file

        # Add OCR text
        for word in ocr_result.words:
            text = word.content
            bbox = _poly2rect(word.points)
            direction = word.direction

            x1, y1, x2, y2 = bbox
            bbox_height = y2 - y1
            bbox_width = x2 - x1

            if direction == "vertical":
                text = to_full_width(text)

            if direction == "horizontal":
                font_size = _calc_font_size(text, bbox_height, bbox_width)
            else:
                font_size = _calc_font_size(text, bbox_width, bbox_height)

            c.setFont("MPLUS1p-Medium", font_size)
            c.setFillColorRGB(1, 1, 1, alpha=0)  # 透明
            # c.setFillColorRGB(0, 0, 0)
            if direction == "vertical":
                base_y = h - y2 + (bbox_height - font_size)
                for j, ch in enumerate(text):
                    c.saveState()
                    c.translate(x1 + font_size * 0.5, base_y - (j - 1) * font_size)
                    c.rotate(-90)
                    c.drawString(0, 0, ch)
                    c.restoreState()
            else:
                base_y = h - y2 + (bbox_height - font_size) * 0.5
                c.drawString(x1, base_y, text)
        c.showPage()

    c.save()

    # Write to file
    with open(output_path, "wb") as f:
        f.write(packet.getvalue())
