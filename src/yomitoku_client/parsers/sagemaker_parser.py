"""
SageMaker Parser - For parsing SageMaker Yomitoku API outputs
"""

import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from ..exceptions import ValidationError, DocumentAnalysisError


class Paragraph(BaseModel):
    """Paragraph data model"""
    box: List[int] = Field(description="Bounding box coordinates [x1, y1, x2, y2]")
    contents: str = Field(description="Text content")
    direction: str = Field(default="horizontal", description="Text direction")
    indent_level: Optional[int] = Field(default=None, description="Indentation level")
    order: int = Field(description="Reading order")
    role: Optional[str] = Field(default=None, description="Paragraph role")


class TableCell(BaseModel):
    """Table cell data model"""
    box: List[int] = Field(description="Bounding box coordinates")
    contents: str = Field(description="Cell content")
    col: int = Field(description="Column index")
    row: int = Field(description="Row index")
    col_span: int = Field(description="Column span")
    row_span: int = Field(description="Row span")


class Table(BaseModel):
    """Table data model"""
    box: List[int] = Field(description="Table bounding box")
    caption: Optional[Dict[str, Any]] = Field(default=None, description="Table caption")
    cells: List[TableCell] = Field(description="Table cells")
    cols: List[Dict[str, Any]] = Field(description="Column information")
    n_col: int = Field(description="Number of columns")
    n_row: int = Field(description="Number of rows")
    order: int = Field(description="Reading order")
    rows: List[Dict[str, Any]] = Field(description="Row information")
    spans: List[Any] = Field(default_factory=list, description="Cell spans")


class Figure(BaseModel):
    """Figure data model"""
    box: List[int] = Field(description="Bounding box coordinates")
    caption: Optional[Dict[str, Any]] = Field(default=None, description="Figure caption")
    decode: Optional[str] = Field(default=None, description="Decoded content")
    direction: str = Field(default="horizontal", description="Text direction")
    order: int = Field(description="Reading order")
    paragraphs: List[Paragraph] = Field(description="Figure paragraphs")
    role: Optional[str] = Field(default=None, description="Figure role")


class Word(BaseModel):
    """Word data model"""
    content: str = Field(description="Word content")
    det_score: float = Field(description="Detection score")
    direction: str = Field(description="Text direction")
    points: List[List[int]] = Field(description="Word polygon points")
    rec_score: float = Field(description="Recognition score")


class DocumentResult(BaseModel):
    """Document analysis result model"""
    figures: List[Figure] = Field(description="Detected figures")
    paragraphs: List[Paragraph] = Field(description="Detected paragraphs")
    preprocess: Dict[str, Any] = Field(description="Preprocessing information")
    tables: List[Table] = Field(description="Detected tables")
    words: List[Word] = Field(description="Detected words")


class SageMakerParser:
    """Parser for SageMaker Yomitoku API outputs"""
    
    def __init__(self):
        """Initialize the parser"""
        pass
    
    def parse_json(self, json_data: str) -> DocumentResult:
        """
        Parse JSON data from SageMaker output
        
        Args:
            json_data: JSON string from SageMaker
            
        Returns:
            DocumentResult: Parsed document result
            
        Raises:
            ValidationError: If JSON format is invalid
            DocumentAnalysisError: If parsing fails
        """
        try:
            data = json.loads(json_data)
            
            if "result" not in data or not data["result"]:
                raise ValidationError("Invalid SageMaker output format: missing 'result' field")
            
            # Take the first result if multiple
            result_data = data["result"][0] if isinstance(data["result"], list) else data["result"]
            
            return DocumentResult(**result_data)
            
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON format: {e}")
        except Exception as e:
            raise DocumentAnalysisError(f"Failed to parse document: {e}")
    
    def parse_file(self, file_path: str) -> DocumentResult:
        """
        Parse JSON file from SageMaker output
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            DocumentResult: Parsed document result
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json_data = f.read()
            return self.parse_json(json_data)
        except FileNotFoundError:
            raise DocumentAnalysisError(f"File not found: {file_path}")
        except Exception as e:
            raise DocumentAnalysisError(f"Failed to read file: {e}")
    
    def validate_result(self, result: DocumentResult) -> bool:
        """
        Validate parsed result
        
        Args:
            result: Parsed document result
            
        Returns:
            bool: True if valid
        """
        # Basic validation checks
        if not result.paragraphs and not result.tables and not result.figures:
            return False
        
        # Validate paragraph orders
        if result.paragraphs:
            orders = [p.order for p in result.paragraphs]
            if len(orders) != len(set(orders)):
                return False
        
        return True
