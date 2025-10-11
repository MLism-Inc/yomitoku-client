"""
Tests for Enhanced Features - PDF Generator, Visualizers, Utils, and Renderers
"""

import pytest
import numpy as np
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from yomitoku_client.pdf_generator import SearchablePDFGenerator, create_searchable_pdf
from yomitoku_client.visualizers import DocumentVisualizer, TableExtractor, ChartVisualizer
from yomitoku_client.renderers import RendererFactory
from yomitoku_client.utils import (
    calc_overlap_ratio, calc_distance, is_contained, calc_intersection,
    is_intersected_horizontal, is_intersected_vertical, quad_to_xyxy,
    convert_table_array, table_to_csv, convert_table_array_to_dict,
    escape_markdown_special_chars, remove_dot_prefix, save_image,
    is_numeric_list_item, is_dot_list_item, remove_numeric_prefix
)
from yomitoku_client.exceptions import FormatConversionError


class TestPDFGenerator:
    """Test cases for PDF Generator"""
    
    def test_pdf_generator_initialization(self):
        """Test PDF generator initialization"""
        try:
            generator = SearchablePDFGenerator()
            assert generator is not None
            assert generator.font_name is not None
        except ImportError:
            pytest.skip("ReportLab not available")
    
    def test_pdf_generator_with_custom_font(self):
        """Test PDF generator with custom font"""
        try:
            # Test with non-existent font (should fall back to default)
            generator = SearchablePDFGenerator(font_path="non_existent_font.ttf")
            assert generator is not None
        except ImportError:
            pytest.skip("ReportLab not available")
    
    def test_create_searchable_pdf_function(self):
        """Test convenience function for PDF creation"""
        try:
            # Mock data
            images = [np.ones((100, 100, 3), dtype=np.uint8) * 255]
            
            class MockWord:
                def __init__(self):
                    self.content = "test"
                    self.points = [[10, 10], [50, 10], [50, 30], [10, 30]]
                    self.direction = "horizontal"
            
            class MockOCRResult:
                def __init__(self):
                    self.words = [MockWord()]
            
            ocr_results = [MockOCRResult()]
            
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                output_path = tmp.name
            
            try:
                create_searchable_pdf(images, ocr_results, output_path)
                assert os.path.exists(output_path)
                assert os.path.getsize(output_path) > 0
            finally:
                if os.path.exists(output_path):
                    os.unlink(output_path)
        except ImportError:
            pytest.skip("ReportLab not available")


class TestVisualizers:
    """Test cases for Visualizers"""
    
    def test_document_visualizer_initialization(self):
        """Test document visualizer initialization"""
        visualizer = DocumentVisualizer()
        assert visualizer is not None
        assert visualizer.palette is not None
        assert len(visualizer.palette) > 0
    
    def test_document_visualizer_with_mock_data(self):
        """Test document visualizer with mock data"""
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
        
        # Test different visualization types
        try:
            # Layout detail
            output = visualizer.visualize((img, results), type='layout_detail')
            assert output is not None
            assert output.shape == img.shape
            
            # Reading order
            output = visualizer.visualize((img, results), type='reading_order')
            assert output is not None
            
            # Element relationships
            output = visualizer.visualize_element_relationships(
                img, results, show_overlaps=True, show_distances=True
            )
            assert output is not None
            
            # Element hierarchy
            output = visualizer.visualize_element_hierarchy(
                img, results, show_containment=True
            )
            assert output is not None
            
        except Exception as e:
            pytest.fail(f"Visualization failed: {e}")
    
    def test_table_extractor(self):
        """Test table extractor"""
        visualizer = TableExtractor()
        
        # Test with DataFrame
        import pandas as pd
        df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
        
        result = visualizer.visualize(df, format='text')
        assert isinstance(result, str)
        assert 'A' in result
        assert 'B' in result
        
        # Test with list
        data = [['Header1', 'Header2'], ['Data1', 'Data2']]
        result = visualizer.visualize(data, format='html')
        assert isinstance(result, str)
        assert '<table' in result
    
    def test_chart_visualizer(self):
        """Test chart visualizer"""
        visualizer = ChartVisualizer()
        
        # Test with list data
        data = [1, 2, 3, 4, 5]
        try:
            result = visualizer.visualize(data, type='line')
            assert result is not None
        except ImportError:
            pytest.skip("matplotlib not available")


class TestUtils:
    """Test cases for Utility Functions"""
    
    def test_rectangle_calculations(self):
        """Test rectangle calculation functions"""
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
        
        # Test intersection
        intersection_result = calc_intersection(rect1, rect2)
        assert intersection_result is not None
    
    def test_intersection_functions(self):
        """Test intersection detection functions"""
        rect1 = [100, 100, 200, 200]
        rect2 = [150, 150, 250, 250]
        
        # Test horizontal intersection
        h_intersect = is_intersected_horizontal(rect1, rect2)
        assert isinstance(h_intersect, bool)
        
        # Test vertical intersection
        v_intersect = is_intersected_vertical(rect1, rect2)
        assert isinstance(v_intersect, bool)
    
    def test_quad_to_xyxy(self):
        """Test quadrilateral to bounding box conversion"""
        quad = [[100, 100], [200, 100], [200, 200], [100, 200]]
        bbox = quad_to_xyxy(quad)
        assert bbox == (100, 100, 200, 200)
    
    def test_text_processing_functions(self):
        """Test text processing utility functions"""
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
    
    def test_table_processing_functions(self):
        """Test table processing functions"""
        # Mock table object
        class MockCell:
            def __init__(self, contents, row, col, row_span=1, col_span=1):
                self.contents = contents
                self.row = row
                self.col = col
                self.row_span = row_span
                self.col_span = col_span
        
        class MockTable:
            def __init__(self):
                self.n_row = 2
                self.n_col = 2
                self.cells = [
                    MockCell("Header1", 1, 1),
                    MockCell("Header2", 1, 2),
                    MockCell("Data1", 2, 1),
                    MockCell("Data2", 2, 2)
                ]
        
        table = MockTable()
        
        # Test table array conversion
        table_array = convert_table_array(table)
        assert len(table_array) == 2
        assert len(table_array[0]) == 2
        
        # Test table to CSV
        csv_result = table_to_csv(table)
        assert isinstance(csv_result, str)
        assert "Header1" in csv_result
        
        # Test table array to dict
        table_dict = convert_table_array_to_dict(table_array, header_row=1)
        assert isinstance(table_dict, list)
        assert len(table_dict) == 1  # Only data row after header


class TestRenderers:
    """Test cases for Renderers"""
    
    def test_renderer_factory(self):
        """Test renderer factory"""
        # Test getting supported formats
        formats = RendererFactory.get_supported_formats()
        expected_formats = ["csv", "markdown", "md", "html", "htm", "json", "pdf"]
        for fmt in expected_formats:
            assert fmt in formats
        
        # Test creating renderers
        csv_renderer = RendererFactory.create_renderer("csv")
        assert csv_renderer is not None
        
        html_renderer = RendererFactory.create_renderer("html")
        assert html_renderer is not None
        
        json_renderer = RendererFactory.create_renderer("json")
        assert json_renderer is not None
        
        markdown_renderer = RendererFactory.create_renderer("markdown")
        assert markdown_renderer is not None
        
        # Test PDF renderer (if available)
        try:
            pdf_renderer = RendererFactory.create_renderer("pdf")
            assert pdf_renderer is not None
        except ImportError:
            pytest.skip("PDF dependencies not available")
    
    def test_renderer_factory_unsupported_format(self):
        """Test renderer factory with unsupported format"""
        with pytest.raises(FormatConversionError):
            RendererFactory.create_renderer("unsupported_format")
    
    def test_renderer_factory_is_supported(self):
        """Test renderer factory support check"""
        assert RendererFactory.is_supported("csv")
        assert RendererFactory.is_supported("html")
        assert RendererFactory.is_supported("json")
        assert not RendererFactory.is_supported("unsupported")


class TestImageProcessing:
    """Test cases for Image Processing"""
    
    def test_save_image(self):
        """Test image saving functionality"""
        # Create a test image
        img = np.ones((100, 100, 3), dtype=np.uint8) * 255
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            output_path = tmp.name
        
        try:
            save_image(img, output_path)
            assert os.path.exists(output_path)
            assert os.path.getsize(output_path) > 0
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)


class TestIntegration:
    """Integration tests"""
    
    def test_full_workflow(self):
        """Test complete workflow from parsing to rendering"""
        from yomitoku_client.client import YomitokuClient
        from yomitoku_client.parsers.sagemaker_parser import DocumentResult, Paragraph, Table, Figure, Word
        
        # Create mock document result
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
        
        document_result = DocumentResult(
            paragraphs=[paragraph],
            tables=[],
            figures=[],
            words=[word],
            preprocess={}
        )
        
        # Test client workflow
        client = YomitokuClient()
        
        # Test format conversion
        csv_result = client.convert_to_format([document_result], "csv")
        assert isinstance(csv_result, str)
        
        html_result = client.convert_to_format([document_result], "html")
        assert isinstance(html_result, str)
        
        json_result = client.convert_to_format([document_result], "json")
        assert isinstance(json_result, str)
        
        markdown_result = client.convert_to_format([document_result], "markdown")
        assert isinstance(markdown_result, str)
    
    def test_visualization_workflow(self):
        """Test visualization workflow"""
        visualizer = DocumentVisualizer()
        
        # Create test image and results
        img = np.ones((200, 200, 3), dtype=np.uint8) * 255
        
        class MockElement:
            def __init__(self, box, order=1, role=None):
                self.box = box
                self.order = order
                self.role = role
        
        class MockResults:
            def __init__(self):
                self.paragraphs = [MockElement([10, 10, 50, 30], 1, "paragraph")]
                self.tables = []
                self.figures = []
        
        results = MockResults()
        
        # Test visualization
        output = visualizer.visualize((img, results))
        assert output is not None
        assert output.shape == img.shape


if __name__ == "__main__":
    pytest.main([__file__])
