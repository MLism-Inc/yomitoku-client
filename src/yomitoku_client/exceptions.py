"""
Yomitoku Client Custom Exception Classes
"""


class YomitokuError(Exception):
    """Base exception for Yomitoku API"""
    pass


class DocumentAnalysisError(YomitokuError):
    """Document analysis error"""
    pass


class APIError(YomitokuError):
    """API call error"""
    pass


class FormatConversionError(YomitokuError):
    """Format conversion error"""
    pass


class ValidationError(YomitokuError):
    """Data validation error"""
    pass
