"""
Tests for Yomitoku Client
"""

import pytest
import tempfile
import os
from pathlib import Path

from yomitoku_client.client import YomitokuClient
from yomitoku_client.exceptions import ValidationError, FormatConversionError, DocumentAnalysisError
from yomitoku_client.parsers.sagemaker_parser import DocumentResult, Paragraph, Table, Figure, Word


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
        data = DocumentResult(
            figures=[],
            paragraphs=[],
            preprocess={},
            tables=[],
            words=[]
        )
        
        with pytest.raises(FormatConversionError):
            client.convert_to_format(data, "unsupported_format")
    
    def test_parse_valid_json(self):
        """Test parsing valid JSON"""
        client = YomitokuClient()
        
        # Create a valid JSON structure
        valid_json = '''
        {
            "result": [
                {
                    "paragraphs": [
                        {
                            "contents": "Sample paragraph",
                            "box": [10, 10, 100, 30],
                            "order": 1,
                            "role": "paragraph"
                        }
                    ],
                    "tables": [],
                    "figures": [],
                    "words": [],
                    "preprocess": {}
                }
            ]
        }
        '''
        
        result = client.parse_json(valid_json)
        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], DocumentResult)
    
    def test_parse_dict(self):
        """Test parsing dictionary data"""
        client = YomitokuClient()
        
        # Create valid dictionary structure
        valid_dict = {
            "result": [
                {
                    "paragraphs": [
                        {
                            "contents": "Sample paragraph",
                            "box": [10, 10, 100, 30],
                            "order": 1,
                            "role": "paragraph"
                        }
                    ],
                    "tables": [],
                    "figures": [],
                    "words": [],
                    "preprocess": {}
                }
            ]
        }
        
        result = client.parse_dict(valid_dict)
        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], DocumentResult)
    
    def test_convert_to_all_supported_formats(self):
        """Test converting to all supported formats"""
        client = YomitokuClient()
        
        # Create test data
        paragraph = Paragraph(
            contents="Sample paragraph",
            box=[10, 10, 100, 30],
            order=1,
            role="paragraph"
        )
        
        word = Word(
            content="sample",
            points=[[10, 10], [50, 10], [50, 20], [10, 20]],
            direction="horizontal",
            det_score=0.95,
            rec_score=0.90
        )
        
        data = DocumentResult(
            paragraphs=[paragraph],
            tables=[],
            figures=[],
            words=[word],
            preprocess={}
        )
        
        # Test all supported formats
        formats = client.get_supported_formats()
        for format_type in formats:
            if format_type == "pdf":
                # Skip PDF test as it requires image data
                continue
            
            result = client.convert_to_format([data], format_type)
            assert isinstance(result, str)
            assert len(result) > 0
    
    def test_convert_to_format_with_output_path(self):
        """Test converting to format with output path"""
        client = YomitokuClient()
        
        # Create test data
        paragraph = Paragraph(
            contents="Sample paragraph",
            box=[10, 10, 100, 30],
            order=1,
            role="paragraph"
        )
        
        data = DocumentResult(
            paragraphs=[paragraph],
            tables=[],
            figures=[],
            words=[],
            preprocess={}
        )
        
        # Test with temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            output_path = tmp.name
        
        try:
            result = client.convert_to_format([data], "csv", output_path=output_path)
            assert os.path.exists(output_path)
            assert os.path.getsize(output_path) > 0
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_convert_to_format_with_kwargs(self):
        """Test converting to format with additional kwargs"""
        client = YomitokuClient()
        
        # Create test data
        paragraph = Paragraph(
            contents="Sample paragraph",
            box=[10, 10, 100, 30],
            order=1,
            role="paragraph"
        )
        
        data = DocumentResult(
            paragraphs=[paragraph],
            tables=[],
            figures=[],
            words=[],
            preprocess={}
        )
        
        # Test with additional parameters
        result = client.convert_to_format(
            [data], 
            "html", 
            ignore_line_break=True,
            export_figure=False
        )
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_get_supported_formats_includes_pdf(self):
        """Test that PDF format is included in supported formats"""
        client = YomitokuClient()
        formats = client.get_supported_formats()
        assert "pdf" in formats
    
    def test_client_with_complex_data(self):
        """Test client with complex document data"""
        client = YomitokuClient()
        
        # Create complex test data
        paragraph1 = Paragraph(
            contents="First paragraph",
            box=[10, 10, 100, 30],
            order=1,
            role="paragraph"
        )
        
        paragraph2 = Paragraph(
            contents="Second paragraph",
            box=[10, 40, 100, 60],
            order=2,
            role="section_headings"
        )
        
        word1 = Word(
            content="first",
            points=[[10, 10], [40, 10], [40, 20], [10, 20]],
            direction="horizontal",
            det_score=0.95,
            rec_score=0.90
        )
        
        word2 = Word(
            content="second",
            points=[[10, 40], [50, 40], [50, 50], [10, 50]],
            direction="horizontal",
            det_score=0.95,
            rec_score=0.90
        )
        
        data = DocumentResult(
            paragraphs=[paragraph1, paragraph2],
            tables=[],
            figures=[],
            words=[word1, word2],
            preprocess={}
        )
        
        # Test conversion
        result = client.convert_to_format([data], "json")
        assert isinstance(result, str)
        assert "First paragraph" in result
        assert "Second paragraph" in result
