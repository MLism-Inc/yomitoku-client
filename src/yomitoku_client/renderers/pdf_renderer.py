"""
PDF Renderer - For converting document data to searchable PDF format
"""

import os
from typing import Optional, List, Any
import numpy as np

from .base import BaseRenderer
from ..parsers.sagemaker_parser import DocumentResult
from ..exceptions import FormatConversionError
from ..pdf_generator import SearchablePDFGenerator
from ..font_manager import FontManager


class PDFRenderer(BaseRenderer):
    """PDF format renderer for creating searchable PDFs"""
    
    def __init__(self,
                 font_path: Optional[str] = None,
                 **kwargs):
        """
        Initialize PDF renderer
        Args:
            font_path: Path to font file. If None, uses built-in font
            **kwargs: Additional options
        """
        super().__init__(**kwargs)
        # Use FontManager to get appropriate font path
        self.font_path = FontManager.get_font_path(font_path)
        self.generator = SearchablePDFGenerator(font_path=self.font_path)
    
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
    
    def save(self, data: DocumentResult, output_path: str, img: Optional[np.ndarray] = None, **kwargs) -> None:
        """
        Save rendered content to PDF file
        
        Args:
            data: Document result to render
            output_path: Path to save the PDF file
            img: Optional image array for PDF generation
            **kwargs: Additional rendering options
        """
        if img is None:
            raise FormatConversionError("Image is required for PDF generation")
        
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
            
            # Generate PDF
            self.generator.create_searchable_pdf(
                images=[img],
                ocr_results=[ocr_result],
                output_path=output_path,
                **kwargs
            )
            
        except Exception as e:
            raise FormatConversionError(f"Failed to save PDF file: {e}")
    
    def get_supported_formats(self) -> list:
        """Get supported formats"""
        return ["pdf"]
