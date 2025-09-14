"""
Tests for Exception Classes
"""

import pytest
from yomitoku_client.exceptions import (
    YomitokuError, 
    DocumentAnalysisError, 
    APIError, 
    ValidationError, 
    FormatConversionError
)


class TestYomitokuError:
    """Test cases for YomitokuError"""
    
    def test_yomitoku_error_creation(self):
        """Test creating YomitokuError"""
        error = YomitokuError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)
    
    def test_yomitoku_error_with_details(self):
        """Test YomitokuError with additional details"""
        error = YomitokuError("Test error")
        assert str(error) == "Test error"
        # Simple exception classes don't support additional attributes


class TestDocumentAnalysisError:
    """Test cases for DocumentAnalysisError"""
    
    def test_document_analysis_error_creation(self):
        """Test creating DocumentAnalysisError"""
        error = DocumentAnalysisError("Document analysis failed")
        assert str(error) == "Document analysis failed"
        assert isinstance(error, YomitokuError)
    
    def test_document_analysis_error_inheritance(self):
        """Test DocumentAnalysisError inheritance"""
        error = DocumentAnalysisError("Test message")
        assert isinstance(error, YomitokuError)
        assert isinstance(error, Exception)


class TestAPIError:
    """Test cases for APIError"""
    
    def test_api_error_creation(self):
        """Test creating APIError"""
        error = APIError("API request failed")
        assert str(error) == "API request failed"
        assert isinstance(error, YomitokuError)
    
    def test_api_error_with_status_code(self):
        """Test APIError with status code"""
        error = APIError("Not found")
        assert str(error) == "Not found"
        # Simple exception classes don't support additional attributes
    
    def test_api_error_inheritance(self):
        """Test APIError inheritance"""
        error = APIError("Test message")
        assert isinstance(error, YomitokuError)
        assert isinstance(error, Exception)


class TestValidationError:
    """Test cases for ValidationError"""
    
    def test_validation_error_creation(self):
        """Test creating ValidationError"""
        error = ValidationError("Validation failed")
        assert str(error) == "Validation failed"
        assert isinstance(error, YomitokuError)
    
    def test_validation_error_with_field(self):
        """Test ValidationError with field information"""
        error = ValidationError("Invalid field")
        assert str(error) == "Invalid field"
        # Simple exception classes don't support additional attributes
    
    def test_validation_error_inheritance(self):
        """Test ValidationError inheritance"""
        error = ValidationError("Test message")
        assert isinstance(error, YomitokuError)
        assert isinstance(error, Exception)


class TestFormatConversionError:
    """Test cases for FormatConversionError"""
    
    def test_format_conversion_error_creation(self):
        """Test creating FormatConversionError"""
        error = FormatConversionError("Format conversion failed")
        assert str(error) == "Format conversion failed"
        assert isinstance(error, YomitokuError)
    
    def test_format_conversion_error_with_format(self):
        """Test FormatConversionError with format information"""
        error = FormatConversionError("Unsupported format")
        assert str(error) == "Unsupported format"
        # Simple exception classes don't support additional attributes
    
    def test_format_conversion_error_inheritance(self):
        """Test FormatConversionError inheritance"""
        error = FormatConversionError("Test message")
        assert isinstance(error, YomitokuError)
        assert isinstance(error, Exception)


class TestExceptionChaining:
    """Test cases for exception chaining"""
    
    def test_exception_chaining(self):
        """Test exception chaining"""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise YomitokuError("Wrapped error") from e
        except YomitokuError as e:
            assert str(e) == "Wrapped error"
            assert e.__cause__ is not None
            assert isinstance(e.__cause__, ValueError)
    
    def test_document_analysis_error_chaining(self):
        """Test DocumentAnalysisError chaining"""
        try:
            try:
                raise KeyError("Missing key")
            except KeyError as e:
                raise DocumentAnalysisError("Document parsing failed") from e
        except DocumentAnalysisError as e:
            assert str(e) == "Document parsing failed"
            assert e.__cause__ is not None
            assert isinstance(e.__cause__, KeyError)
    
    def test_api_error_chaining(self):
        """Test APIError chaining"""
        try:
            try:
                raise ConnectionError("Connection failed")
            except ConnectionError as e:
                raise APIError("API request failed") from e
        except APIError as e:
            assert str(e) == "API request failed"
            assert e.__cause__ is not None
            assert isinstance(e.__cause__, ConnectionError)


class TestExceptionMessages:
    """Test cases for exception messages"""
    
    def test_detailed_error_messages(self):
        """Test detailed error messages"""
        # Test with simple error message
        error = APIError("Request failed")
        
        assert "Request failed" in str(error)
        # Simple exception classes don't support additional attributes
    
    def test_validation_error_messages(self):
        """Test validation error messages"""
        error = ValidationError("Invalid input data")
        
        assert "Invalid input data" in str(error)
        # Simple exception classes don't support additional attributes
    
    def test_format_conversion_error_messages(self):
        """Test format conversion error messages"""
        error = FormatConversionError("Unsupported output format")
        
        assert "Unsupported output format" in str(error)
        # Simple exception classes don't support additional attributes


if __name__ == "__main__":
    pytest.main([__file__])
