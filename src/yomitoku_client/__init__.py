"""
Yomitoku Client - A Python library for processing SageMaker Yomitoku API outputs
"""

__version__ = "0.1.0"
__author__ = "Yomitoku Team"
__email__ = "support-aws-marketplace@mlism.com"

# Import main classes for easy access
from .parsers.sagemaker_parser import DocumentResult, MultiPageDocumentResult, SageMakerParser
from .client import YomitokuClient

# Import renderers
from .renderers.markdown_renderer import MarkdownRenderer
from .renderers.html_renderer import HTMLRenderer
from .renderers.csv_renderer import CSVRenderer
from .renderers.json_renderer import JSONRenderer
from .renderers.pdf_renderer import PDFRenderer

# Import visualizers
from .visualizers.document_visualizer import DocumentVisualizer
from .visualizers.table_exporter import TableExtractor

# Import font manager and PDF functions
from .font_manager import FontManager, get_font_path
from .renderers.searchable_pdf import create_searchable_pdf, create_searchable_pdf_from_pdf

__all__ = [
    "DocumentResult",
    "MultiPageDocumentResult", 
    "SageMakerParser",
    "YomitokuClient",
    "MarkdownRenderer",
    "HTMLRenderer",
    "CSVRenderer",
    "JSONRenderer",
    "PDFRenderer",
    "DocumentVisualizer",
    "TableExtractor",
    "FontManager",
    "create_searchable_pdf",
    "create_searchable_pdf_from_pdf",
]

# Post-installation hook to ensure font is available
def _ensure_font_available():
    """Ensure MPLUS1p-Medium font is available from resource directory"""
    try:
        import os
        # Check if the default font exists in resource directory
        module_dir = os.path.dirname(os.path.abspath(__file__))
        font_path = os.path.join(module_dir, "resource", "MPLUS1p-Medium.ttf")
        if os.path.exists(font_path):
            return font_path
        else:
            return None
    except Exception:
        # Font not available, but don't fail the import
        return None

# Check font availability on import
_font_path = _ensure_font_available()
if _font_path is None:
    import warnings
    warnings.warn(
        "MPLUS1p-Medium font not found in resource directory. PDF generation may not work properly. "
        "Please ensure the font file is present in src/yomitoku_client/resource/",
        UserWarning
    )