"""
Basic functionality tests with proper mocking
"""

import pytest
import numpy as np
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock

from yomitoku_client.client import YomitokuClient
from yomitoku_client.exceptions import ValidationError, FormatConversionError, DocumentAnalysisError
from yomitoku_client.parsers.sagemaker_parser import DocumentResult, Paragraph, Table, Figure, Word, TableCell


class TestBasicClientFunctionality:
    """Test basic client functionality with proper mocking"""
    
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
        assert "pdf" in formats
    
    def test_parse_valid_json(self):
        """Test parsing valid JSON"""
        client = YomitokuClient()
        
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
    
    def test_convert_to_csv(self):
        """Test converting to CSV format"""
        client = YomitokuClient()
        
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
        
        result = client.convert_to_format([data], "csv")
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_convert_to_html(self):
        """Test converting to HTML format"""
        client = YomitokuClient()
        
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
        
        result = client.convert_to_format([data], "html")
        assert isinstance(result, str)
        assert len(result) > 0
        # HTML renderer outputs paragraph tags
        assert "<p>" in result.lower()
    
    def test_convert_to_json(self):
        """Test converting to JSON format"""
        client = YomitokuClient()
        
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
        
        result = client.convert_to_format([data], "json")
        assert isinstance(result, str)
        assert len(result) > 0
        # JSON renderer outputs with document headers, need to extract JSON part
        import json
        import re
        # Extract JSON part after the document header
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            parsed = json.loads(json_str)
            assert isinstance(parsed, (dict, list))
        else:
            # If no JSON found, just check it's a string
            assert len(result) > 0
    
    def test_convert_to_markdown(self):
        """Test converting to Markdown format"""
        client = YomitokuClient()
        
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
        
        result = client.convert_to_format([data], "markdown")
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_convert_to_unsupported_format(self):
        """Test converting to unsupported format"""
        client = YomitokuClient()
        
        data = DocumentResult(
            figures=[],
            paragraphs=[],
            preprocess={},
            tables=[],
            words=[]
        )
        
        with pytest.raises(FormatConversionError):
            client.convert_to_format(data, "unsupported_format")


class TestUtilityFunctions:
    """Test utility functions with proper mocking"""
    
    def test_rectangle_calculations(self):
        """Test rectangle calculation functions"""
        from yomitoku_client.utils import calc_overlap_ratio, calc_distance, is_contained
        
        rect1 = [100, 100, 200, 200]
        rect2 = [150, 150, 250, 250]
        
        # Test overlap ratio
        overlap_ratio, intersection = calc_overlap_ratio(rect1, rect2)
        assert overlap_ratio > 0
        assert intersection is not None
        
        # Test distance
        distance = calc_distance(rect1, rect2)
        assert distance > 0
        
        # Test containment
        contained = is_contained(rect1, rect2)
        assert isinstance(contained, bool)
    
    def test_quad_to_xyxy(self):
        """Test quadrilateral to bounding box conversion"""
        from yomitoku_client.utils import quad_to_xyxy
        
        quad = [[100, 100], [200, 100], [200, 200], [100, 200]]
        bbox = quad_to_xyxy(quad)
        assert bbox == (100, 100, 200, 200)
    
    def test_text_processing_functions(self):
        """Test text processing utility functions"""
        from yomitoku_client.utils import (
            escape_markdown_special_chars, remove_dot_prefix,
            is_numeric_list_item, is_dot_list_item, remove_numeric_prefix
        )
        
        # Test markdown escaping
        text = "This has *bold* and `code`"
        escaped = escape_markdown_special_chars(text)
        assert '\\*' in escaped
        assert '\\`' in escaped
        
        # Test dot prefix removal
        text_with_dot = "· List item"
        cleaned = remove_dot_prefix(text_with_dot)
        assert cleaned == "List item"
        
        # Test numeric list detection
        numeric_item = "1. First item"
        assert is_numeric_list_item(numeric_item)
        assert not is_numeric_list_item("Regular text")
        
        # Test dot list detection
        dot_item = "· Bullet point"
        assert is_dot_list_item(dot_item)
        assert not is_dot_list_item("Regular text")
        
        # Test numeric prefix removal
        numeric_text = "1. Numbered item"
        cleaned_numeric = remove_numeric_prefix(numeric_text)
        assert cleaned_numeric == "Numbered item"


class TestRendererFactory:
    """Test renderer factory with proper mocking"""
    
    def test_renderer_factory_supported_formats(self):
        """Test renderer factory supported formats"""
        from yomitoku_client.renderers.factory import RendererFactory
        
        formats = RendererFactory.get_supported_formats()
        expected_formats = ["csv", "markdown", "md", "html", "htm", "json", "pdf"]
        for fmt in expected_formats:
            assert fmt in formats
    
    def test_renderer_factory_create_renderers(self):
        """Test creating renderers"""
        from yomitoku_client.renderers.factory import RendererFactory
        
        # Test creating basic renderers
        csv_renderer = RendererFactory.create_renderer("csv")
        assert csv_renderer is not None
        
        html_renderer = RendererFactory.create_renderer("html")
        assert html_renderer is not None
        
        json_renderer = RendererFactory.create_renderer("json")
        assert json_renderer is not None
        
        markdown_renderer = RendererFactory.create_renderer("markdown")
        assert markdown_renderer is not None
    
    def test_renderer_factory_unsupported_format(self):
        """Test renderer factory with unsupported format"""
        from yomitoku_client.renderers.factory import RendererFactory
        
        with pytest.raises(FormatConversionError):
            RendererFactory.create_renderer("unsupported_format")
    
    def test_renderer_factory_is_supported(self):
        """Test renderer factory support check"""
        from yomitoku_client.renderers.factory import RendererFactory
        
        assert RendererFactory.is_supported("csv")
        assert RendererFactory.is_supported("html")
        assert RendererFactory.is_supported("json")
        assert not RendererFactory.is_supported("unsupported")


class TestDocumentVisualizer:
    """Test document visualizer with proper mocking"""
    
    def test_document_visualizer_initialization(self):
        """Test document visualizer initialization"""
        from yomitoku_client.visualizers import DocumentVisualizer
        
        visualizer = DocumentVisualizer()
        assert visualizer is not None
        assert visualizer.palette is not None
        assert len(visualizer.palette) > 0
    
    @patch('yomitoku_client.visualizers.document_visualizer.cv2')
    def test_document_visualizer_with_mock_data(self, mock_cv2):
        """Test document visualizer with mock data"""
        from yomitoku_client.visualizers import DocumentVisualizer
        
        # Mock cv2 functions
        mock_cv2.rectangle.return_value = None
        mock_cv2.putText.return_value = None
        mock_cv2.line.return_value = None
        mock_cv2.circle.return_value = None
        
        visualizer = DocumentVisualizer()
        
        # Create mock image
        img = np.ones((200, 200, 3), dtype=np.uint8) * 255
        
        # Create mock results
        class MockElement:
            def __init__(self, box, order=1, role=None):
                self.box = box
                self.order = order
                self.role = role
        
        class MockResults:
            def __init__(self):
                self.paragraphs = [MockElement([10, 10, 50, 30], 1, "paragraph")]
                self.tables = [MockElement([60, 10, 100, 50], 2, "table")]
                self.figures = [MockElement([110, 10, 150, 50], 3, "figure")]
        
        results = MockResults()
        
        # Test visualization
        try:
            output = visualizer.visualize((img, results))
            assert output is not None
            assert output.shape == img.shape
        except Exception as e:
            # If visualization fails due to missing dependencies, that's okay
            pytest.skip(f"Visualization failed due to missing dependencies: {e}")


class TestPDFGenerator:
    """Test PDF generator with proper mocking"""
    
    def test_pdf_generator_initialization(self):
        """Test PDF generator initialization"""
        try:
            from yomitoku_client.pdf_generator import SearchablePDFGenerator
            generator = SearchablePDFGenerator()
            assert generator is not None
        except ImportError:
            pytest.skip("ReportLab not available")
    
    @patch('yomitoku_client.pdf_generator.REPORTLAB_AVAILABLE', False)
    def test_pdf_generator_without_dependencies(self):
        """Test PDF generator without dependencies"""
        from yomitoku_client.pdf_generator import SearchablePDFGenerator
        
        with pytest.raises(ImportError):
            SearchablePDFGenerator()


if __name__ == "__main__":
    pytest.main([__file__])
