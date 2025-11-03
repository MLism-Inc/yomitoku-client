"""
PDF Renderer - For converting document data to searchable PDF format
"""

import numpy as np

from ..models import DocumentResult
from .base import BaseRenderer
from .searchable_pdf import create_searchable_pdf


class PDFRenderer(BaseRenderer):
    """PDF format renderer for creating searchable PDFs"""

    def __init__(self, font_path: str | None = None, **kwargs):
        """
        Initialize PDF renderer
        Args:
            font_path: Path to font file. If None, uses default MPLUS1p-Medium.ttf from resource directory
            **kwargs: Additional options
        """
        super().__init__(**kwargs)
        # Store font path (will use default from resource if None)
        self.font_path = font_path

    def render(
        self,
        data: DocumentResult,
        img: np.ndarray | None = None,
    ) -> str:
        """
        Render document data to PDF format (returns path to generated PDF)

        Args:
            data: Document result to render
            img: Optional image array for PDF generation
            **kwargs: Additional rendering options

        Returns:
            str: Path to generated PDF file
        """
        # PDF renderer doesn't return content directly, but saves to file
        # This method is mainly for interface compatibility
        return create_searchable_pdf(
            images=[img],
            docs=[data],
            font_path=self.font_path,
        )

    def save(self, data: DocumentResult, output_path: str, **kwargs) -> None:
        pass
