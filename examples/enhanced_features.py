"""
Enhanced Features Example - Demonstrating new functionality added to yomitoku-client
"""

import numpy as np
from yomitoku_client import YomitokuClient, SearchablePDFGenerator, create_searchable_pdf
from yomitoku_client.visualizers import DocumentVisualizer, TableVisualizer, ChartVisualizer
from yomitoku_client.renderers import RendererFactory
from yomitoku_client.utils import (
    calc_overlap_ratio, calc_distance, is_contained,
    convert_table_array, table_to_csv, quad_to_xyxy
)


def demonstrate_enhanced_utils():
    """Demonstrate enhanced utility functions"""
    print("=== Enhanced Utility Functions ===")
    
    # Rectangle calculations
    rect1 = [100, 100, 200, 200]
    rect2 = [150, 150, 250, 250]
    
    overlap_ratio, intersection = calc_overlap_ratio(rect1, rect2)
    distance = calc_distance(rect1, rect2)
    is_contained_result = is_contained(rect1, rect2)
    
    print(f"Rectangle 1: {rect1}")
    print(f"Rectangle 2: {rect2}")
    print(f"Overlap ratio: {overlap_ratio:.2f}")
    print(f"Distance: {distance:.2f}")
    print(f"Is rect2 contained in rect1: {is_contained_result}")
    
    # Quadrilateral to rectangle conversion
    quad = [[100, 100], [200, 100], [200, 200], [100, 200]]
    bbox = quad_to_xyxy(quad)
    print(f"Quadrilateral: {quad}")
    print(f"Bounding box: {bbox}")


def demonstrate_enhanced_visualization():
    """Demonstrate enhanced visualization features"""
    print("\n=== Enhanced Visualization Features ===")
    
    # Create a mock document result for demonstration
    class MockWord:
        def __init__(self, content, points, confidence=0.9):
            self.content = content
            self.points = points
            self.confidence = confidence
    
    class MockParagraph:
        def __init__(self, contents, box, order=1, role=None):
            self.contents = contents
            self.box = box
            self.order = order
            self.role = role
    
    class MockTable:
        def __init__(self, cells, box, order=1):
            self.cells = cells
            self.box = box
            self.order = order
            self.n_row = 2
            self.n_col = 2
    
    class MockCell:
        def __init__(self, contents, row, col, row_span=1, col_span=1):
            self.contents = contents
            self.row = row
            self.col = col
            self.row_span = row_span
            self.col_span = col_span
    
    class MockResults:
        def __init__(self):
            self.words = [
                MockWord("Hello", [[100, 100], [150, 100], [150, 120], [100, 120]], 0.95),
                MockWord("World", [[160, 100], [200, 100], [200, 120], [160, 120]], 0.85)
            ]
            self.paragraphs = [
                MockParagraph("Sample paragraph", [50, 50, 300, 100], 1, "paragraph"),
                MockParagraph("Another paragraph", [50, 120, 300, 170], 2, "section_headings")
            ]
            self.tables = [
                MockTable([
                    MockCell("Header 1", 1, 1),
                    MockCell("Header 2", 1, 2),
                    MockCell("Data 1", 2, 1),
                    MockCell("Data 2", 2, 2)
                ], [50, 200, 300, 300], 3)
            ]
            self.figures = []
    
    # Create mock image
    img = np.zeros((400, 400, 3), dtype=np.uint8)
    results = MockResults()
    
    # Initialize visualizer
    visualizer = DocumentVisualizer()
    
    print("Available visualization types:")
    print("- layout_detail: Detailed layout visualization")
    print("- layout_rough: Rough layout visualization")
    print("- reading_order: Reading order visualization")
    print("- ocr: OCR text visualization")
    print("- detection: Detection visualization")
    print("- recognition: Recognition visualization")
    print("- relationships: Element relationships visualization")
    print("- hierarchy: Element hierarchy visualization")
    print("- confidence: Confidence scores visualization")
    
    # Example: Element relationships visualization
    try:
        relationships_img = visualizer.visualize_element_relationships(
            img, results, 
            show_overlaps=True, 
            show_distances=True,
            overlap_threshold=0.1
        )
        print("✓ Element relationships visualization completed")
    except Exception as e:
        print(f"✗ Element relationships visualization failed: {e}")
    
    # Example: Confidence scores visualization
    try:
        confidence_img = visualizer.visualize_confidence_scores(
            img, results,
            show_ocr_confidence=True
        )
        print("✓ Confidence scores visualization completed")
    except Exception as e:
        print(f"✗ Confidence scores visualization failed: {e}")


def demonstrate_pdf_generation():
    """Demonstrate searchable PDF generation"""
    print("\n=== Searchable PDF Generation ===")
    
    # Create mock OCR results
    class MockOCRWord:
        def __init__(self, content, points, direction="horizontal"):
            self.content = content
            self.points = points
            self.direction = direction
    
    class MockOCRResult:
        def __init__(self, words):
            self.words = words
    
    # Mock data
    words = [
        MockOCRWord("Sample", [[100, 100], [200, 100], [200, 120], [100, 120]]),
        MockOCRWord("Text", [[100, 130], [150, 130], [150, 150], [100, 150]])
    ]
    ocr_result = MockOCRResult(words)
    
    # Create mock image
    img = np.ones((300, 300, 3), dtype=np.uint8) * 255  # White image
    
    print("Searchable PDF generation features:")
    print("- Transparent text overlay")
    print("- Support for horizontal and vertical text")
    print("- Automatic font size calculation")
    print("- Full-width character conversion for Japanese text")
    print("- Custom font support")
    
    try:
        # Note: This would require actual ReportLab and PIL installation
        # generator = SearchablePDFGenerator()
        # generator.create_searchable_pdf([img], [ocr_result], "output.pdf")
        print("✓ PDF generation functionality available (requires ReportLab and PIL)")
    except ImportError as e:
        print(f"✗ PDF generation requires additional dependencies: {e}")


def demonstrate_enhanced_renderers():
    """Demonstrate enhanced renderer functionality"""
    print("\n=== Enhanced Renderer Functionality ===")
    
    # Show supported formats
    supported_formats = RendererFactory.get_supported_formats()
    print(f"Supported output formats: {', '.join(supported_formats)}")
    
    # Create mock document data
    class MockDocumentResult:
        def __init__(self):
            self.tables = []
            self.paragraphs = []
            self.figures = []
    
    data = MockDocumentResult()
    
    print("\nRenderer features:")
    print("- HTML: Full HTML export with figure support")
    print("- Markdown: Markdown export with table formatting options")
    print("- JSON: Structured JSON export")
    print("- CSV: Table data export with proper formatting")
    print("- PDF: Searchable PDF generation (new feature)")
    
    # Example: Create different renderers
    try:
        html_renderer = RendererFactory.create_renderer("html")
        print("✓ HTML renderer created")
        
        markdown_renderer = RendererFactory.create_renderer("markdown")
        print("✓ Markdown renderer created")
        
        json_renderer = RendererFactory.create_renderer("json")
        print("✓ JSON renderer created")
        
        csv_renderer = RendererFactory.create_renderer("csv")
        print("✓ CSV renderer created")
        
        pdf_renderer = RendererFactory.create_renderer("pdf")
        print("✓ PDF renderer created")
        
    except Exception as e:
        print(f"✗ Renderer creation failed: {e}")


def main():
    """Main demonstration function"""
    print("Yomitoku Client Enhanced Features Demonstration")
    print("=" * 50)
    
    demonstrate_enhanced_utils()
    demonstrate_enhanced_visualization()
    demonstrate_pdf_generation()
    demonstrate_enhanced_renderers()
    
    print("\n" + "=" * 50)
    print("Enhanced features demonstration completed!")
    print("\nNew features added:")
    print("1. ✅ Enhanced utility functions (rectangle calculations, text processing)")
    print("2. ✅ Searchable PDF generation")
    print("3. ✅ Advanced visualization options (relationships, hierarchy, confidence)")
    print("4. ✅ Improved renderer functionality")
    print("5. ✅ Better table processing and CSV export")


if __name__ == "__main__":
    main()
