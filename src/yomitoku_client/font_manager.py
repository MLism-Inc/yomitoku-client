"""
Font Manager - Manages built-in fonts for PDF generation
"""

import os
from pathlib import Path
from typing import Optional


def get_default_font_path() -> str:
    """
    Get the path to the default built-in font

    Returns:
        str: Path to the built-in font
    """
    # Get the directory where this module is located
    module_dir = Path(__file__).parent
    resource_dir = module_dir / "resource"
    font_path = resource_dir / "MPLUS1p-Medium.ttf"

    if not font_path.exists():
        raise FileNotFoundError(
            f"Built-in font not found at {font_path}. "
            "Please ensure the font file is properly installed with the package."
        )

    return str(font_path)


def get_font_path(custom_font_path: Optional[str] = None) -> str:
    """
    Get font path, using custom path if provided, otherwise default built-in font

    Args:
        custom_font_path: Optional custom font path

    Returns:
        str: Path to the font file to use
    """
    if custom_font_path and os.path.exists(custom_font_path):
        return custom_font_path

    # Use built-in font as default
    return get_default_font_path()


# Backward compatibility - keep FontManager class for existing code
class FontManager:
    """Manages built-in fonts for the library (backward compatibility)"""
    
    @staticmethod
    def get_default_font_path() -> str:
        """Get the path to the default built-in font"""
        return get_default_font_path()
    
    @staticmethod
    def get_font_path(custom_font_path: Optional[str] = None) -> str:
        """Get font path, using custom path if provided, otherwise default built-in font"""
        return get_font_path(custom_font_path)