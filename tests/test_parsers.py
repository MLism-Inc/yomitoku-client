"""
Tests for Parsers
"""

import pytest

from yomitoku_client.exceptions import DocumentAnalysisError, ValidationError
from yomitoku_client.parser import (
    DocumentResult,
    Figure,
    Paragraph,
    parse_pydantic_model,
    Table,
    TableCell,
    Word,
)


class TestDocumentResult:
    """Test cases for DocumentResult model"""

    def test_document_result_creation(self):
        """Test creating DocumentResult"""
        doc = DocumentResult(
            paragraphs=[], tables=[], figures=[], words=[], preprocess={}
        )
        assert doc is not None
        assert doc.paragraphs == []
        assert doc.tables == []
        assert doc.figures == []
        assert doc.words == []
        assert doc.preprocess == {}

    def test_document_result_with_data(self):
        """Test DocumentResult with actual data"""
        paragraph = Paragraph(
            contents="Test paragraph", box=[10, 10, 100, 30], order=1, role="paragraph"
        )

        word = Word(
            content="test",
            points=[[10, 10], [40, 10], [40, 20], [10, 20]],
            direction="horizontal",
            det_score=0.95,
            rec_score=0.90,
        )

        doc = DocumentResult(
            paragraphs=[paragraph],
            tables=[],
            figures=[],
            words=[word],
            preprocess={"test": "value"},
        )

        assert len(doc.paragraphs) == 1
        assert len(doc.words) == 1
        assert doc.preprocess["test"] == "value"


class TestParagraph:
    """Test cases for Paragraph model"""

    def test_paragraph_creation(self):
        """Test creating Paragraph"""
        para = Paragraph(
            contents="Sample text", box=[10, 10, 100, 30], order=1, role="paragraph"
        )

        assert para.contents == "Sample text"
        assert para.box == [10, 10, 100, 30]
        assert para.order == 1
        assert para.role == "paragraph"

    def test_paragraph_with_optional_fields(self):
        """Test Paragraph with optional fields"""
        para = Paragraph(
            contents="Sample text",
            box=[10, 10, 100, 30],
            order=1,
            role="section_headings",
            indent_level=2,
        )

        assert para.indent_level == 2


class TestTable:
    """Test cases for Table model"""

    def test_table_creation(self):
        """Test creating Table"""
        cell = TableCell(
            contents="Cell content",
            box=[10, 10, 50, 30],
            row=1,
            col=1,
            row_span=1,
            col_span=1,
        )

        table = Table(
            cells=[cell],
            box=[10, 10, 100, 50],
            order=1,
            n_row=2,
            n_col=2,
            cols=[{"col": 1}, {"col": 2}],
            rows=[{"row": 1}, {"row": 2}],
        )

        assert len(table.cells) == 1
        assert table.n_row == 2
        assert table.n_col == 2
        assert table.box == [10, 10, 100, 50]

    def test_table_with_caption(self):
        """Test Table with caption"""
        cell = TableCell(
            contents="Cell content",
            box=[10, 10, 50, 30],
            row=1,
            col=1,
            row_span=1,
            col_span=1,
        )

        caption = {
            "contents": "Table caption",
            "box": [10, 50, 100, 70],
            "order": 1,
            "role": "caption",
        }

        table = Table(
            cells=[cell],
            box=[10, 10, 100, 50],
            order=1,
            n_row=2,
            n_col=2,
            cols=[{"col": 1}, {"col": 2}],
            rows=[{"row": 1}, {"row": 2}],
            caption=caption,
        )

        assert table.caption is not None
        assert table.caption["contents"] == "Table caption"


class TestFigure:
    """Test cases for Figure model"""

    def test_figure_creation(self):
        """Test creating Figure"""
        figure = Figure(box=[10, 10, 100, 50], order=1, paragraphs=[])

        assert figure.box == [10, 10, 100, 50]
        assert figure.order == 1

    def test_figure_with_caption(self):
        """Test Figure with caption"""
        caption = {
            "contents": "Figure caption",
            "box": [10, 50, 100, 70],
            "order": 1,
            "role": "caption",
        }

        figure = Figure(box=[10, 10, 100, 50], order=1, paragraphs=[], caption=caption)

        assert figure.caption is not None
        assert figure.caption["contents"] == "Figure caption"


class TestWord:
    """Test cases for Word model"""

    def test_word_creation(self):
        """Test creating Word"""
        word = Word(
            content="sample",
            points=[[10, 10], [50, 10], [50, 20], [10, 20]],
            direction="horizontal",
            det_score=0.95,
            rec_score=0.90,
        )

        assert word.content == "sample"
        assert word.points == [[10, 10], [50, 10], [50, 20], [10, 20]]
        assert word.direction == "horizontal"
        assert word.det_score == 0.95
        assert word.rec_score == 0.90

    def test_word_vertical_direction(self):
        """Test Word with vertical direction"""
        word = Word(
            content="vertical",
            points=[[10, 10], [20, 10], [20, 50], [10, 50]],
            direction="vertical",
            det_score=0.95,
            rec_score=0.90,
        )

        assert word.direction == "vertical"


class TestTableCell:
    """Test cases for TableCell model"""

    def test_cell_creation(self):
        """Test creating TableCell"""
        cell = TableCell(
            contents="Cell content",
            box=[10, 10, 50, 30],
            row=1,
            col=1,
            row_span=1,
            col_span=1,
        )

        assert cell.contents == "Cell content"
        assert cell.box == [10, 10, 50, 30]
        assert cell.row == 1
        assert cell.col == 1
        assert cell.row_span == 1
        assert cell.col_span == 1

    def test_cell_with_spans(self):
        """Test TableCell with row and column spans"""
        cell = TableCell(
            contents="Spanned cell",
            box=[10, 10, 100, 50],
            row=1,
            col=1,
            row_span=2,
            col_span=3,
        )

        assert cell.row_span == 2
        assert cell.col_span == 3


if __name__ == "__main__":
    pytest.main([__file__])
