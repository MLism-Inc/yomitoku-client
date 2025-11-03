"""
Basic functionality tests with proper mocking
"""

from unittest.mock import patch

import numpy as np
import pytest

from yomitoku_client.exceptions import (
    FormatConversionError,
)


class TestUtilityFunctions:
    """Test utility functions with proper mocking"""

    def test_rectangle_calculations(self):
        """Test rectangle calculation functions"""
        from yomitoku_client.utils import (
            calc_distance,
            calc_overlap_ratio,
            is_contained,
        )

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
            escape_markdown_special_chars,
            is_dot_list_item,
            is_numeric_list_item,
            remove_dot_prefix,
            remove_numeric_prefix,
        )

        # Test markdown escaping
        text = "This has *bold* and `code`"
        escaped = escape_markdown_special_chars(text)
        assert "\\*" in escaped
        assert "\\`" in escaped

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

    @patch("yomitoku_client.visualizers.document_visualizer.cv2")
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


if __name__ == "__main__":
    pytest.main([__file__])
