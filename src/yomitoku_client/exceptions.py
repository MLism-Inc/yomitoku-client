"""
Yomitoku-Client Custom Exception Classes
"""


class YomitokuError(Exception):
    """Base exception for Yomitoku API"""


class DocumentAnalysisError(YomitokuError):
    """Document analysis error"""


class APIError(YomitokuError):
    """API call error"""


class FormatConversionError(YomitokuError):
    """Format conversion error"""


class ValidationError(YomitokuError):
    """Data validation error"""
