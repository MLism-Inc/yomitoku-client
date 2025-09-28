"""
PDF Renderer - For converting document data to searchable PDF format
"""

import os
from typing import Optional, List, Any
import numpy as np

from .base import BaseRenderer
from ..parsers.sagemaker_parser import DocumentResult
from ..exceptions import FormatConversionError
from .searchable_pdf import create_searchable_pdf


class PDFRenderer(BaseRenderer):
    """PDF format renderer for creating searchable PDFs"""
    
    def __init__(self,
                 font_path: Optional[str] = None,
                 **kwargs):
        """
        Initialize PDF renderer
        Args:
            font_path: Path to font file. If None, uses default MPLUS1p-Medium.ttf from resource directory
            **kwargs: Additional options
        """
        super().__init__(**kwargs)
        # Store font path (will use default from resource if None)
        self.font_path = font_path
    
    def render(self, data: DocumentResult, img: Optional[np.ndarray] = None, **kwargs) -> str:
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
        return "PDF file will be saved to specified path"
    
    def save(self, data: DocumentResult, output_path: str, img: Optional[Any] = None, pdf: Optional[Any] = None, page_index: Optional[int] = None, **kwargs) -> None:
        """
        Save rendered content to PDF file
        
        Args:
            data: Document result to render
            output_path: Path to save the PDF file
            img: Optional image array, PIL Image, or image path for PDF generation
            pdf: Optional PDF path for PDF generation (alternative to img)
            page_index: Optional page index for PDF processing (0-based)
            **kwargs: Additional rendering options
        """
        if img is None and pdf is None:
            raise FormatConversionError("Either image or PDF is required for PDF generation")
        
        try:
            # For PDF generation, we need OCR results
            # This is a simplified implementation - in practice, you'd need actual OCR results
            if not hasattr(data, 'words') or not data.words:
                raise FormatConversionError("OCR results (words) are required for searchable PDF generation")
            
            # Create mock OCR results structure
            class OCRResult:
                def __init__(self, words):
                    self.words = words
            
            # Convert document words to OCR format
            ocr_words = []
            for word in data.words:
                ocr_words.append(word)
            
            ocr_result = OCRResult(ocr_words)
            
            # Generate PDF using create_searchable_pdf function
            if pdf is not None:
                # Use PDF input
                from .searchable_pdf import create_searchable_pdf_from_pdf
                create_searchable_pdf_from_pdf(
                    pdf_path=str(pdf),
                    ocr_results=[ocr_result],
                    output_path=output_path,
                    font_path=self.font_path,
                    page_index=page_index
                )
            else:
                # Use image input
                create_searchable_pdf(
                    images=[img],
                    ocr_results=[ocr_result],
                    output_path=output_path,
                    font_path=self.font_path
                )
            
        except Exception as e:
            raise FormatConversionError(f"Failed to save PDF file: {e}")
    
    def get_supported_formats(self) -> list:
        """Get supported formats"""
        return ["pdf"]
