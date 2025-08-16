"""
Tests for Yomitoku Client
"""

import pytest
from pathlib import Path

from src.yomitoku_client.client import YomitokuClient
from src.yomitoku_client.exceptions import ValidationError, FormatConversionError, DocumentAnalysisError


class TestYomitokuClient:
    """Test cases for YomitokuClient"""
    
    def test_client_initialization(self):
        """Test client initialization"""
        client = YomitokuClient()
        assert client is not None
        assert client.parser is not None
    
    def test_get_supported_formats(self):
        """Test getting supported formats"""
        client = YomitokuClient()
        formats = client.get_supported_formats()
        assert "csv" in formats
        assert "markdown" in formats
        assert "html" in formats
        assert "json" in formats
    
    def test_parse_invalid_json(self):
        """Test parsing invalid JSON"""
        client = YomitokuClient()
        with pytest.raises(ValidationError):
            client.parse_json("invalid json")
    
    def test_parse_empty_result(self):
        """Test parsing empty result"""
        client = YomitokuClient()
        with pytest.raises(DocumentAnalysisError):
            client.parse_json('{"result": []}')
    
    def test_convert_to_unsupported_format(self):
        """Test converting to unsupported format"""
        client = YomitokuClient()
        # Create a minimal valid document result
        from src.yomitoku_client.parsers.sagemaker_parser import DocumentResult
        data = DocumentResult(
            figures=[],
            paragraphs=[],
            preprocess={},
            tables=[],
            words=[]
        )
        
        with pytest.raises(FormatConversionError):
            client.convert_to_format(data, "unsupported_format")
