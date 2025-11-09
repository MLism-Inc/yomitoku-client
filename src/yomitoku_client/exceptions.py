"""
YomiToku-Client Custom Exception Classes
"""


class YomitokuError(Exception):
    """Base exception for YomiToku API"""


class DocumentAnalysisError(YomitokuError):
    """Document analysis error"""


class APIError(YomitokuError):
    """API call error"""


class FormatConversionError(YomitokuError):
    """Format conversion error"""


class ValidationError(YomitokuError):
    """Data validation error"""


class YomitokuInvokeError(YomitokuError):
    pass
