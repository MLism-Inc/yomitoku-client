"""
JSON Renderer - For converting document data to JSON format
"""

from ..models import DocumentResult
from .base import BaseRenderer


class JSONRenderer(BaseRenderer):
    """JSON format renderer"""

    def __init__(
        self,
        ignore_line_break: bool = False,
        export_figure: bool = False,
        figure_dir: str = "figures",
        **kwargs,
    ):
        """
        Initialize JSON renderer

        Args:
            ignore_line_break: Whether to ignore line breaks in text
            export_figure: Whether to export figures
            figure_dir: Directory to save figures
            **kwargs: Additional options
        """
        super().__init__(**kwargs)
        self.ignore_line_break = ignore_line_break
        self.export_figure = export_figure
        self.figure_dir = figure_dir

    def render(
        self,
        data: DocumentResult,
    ) -> str:
        """Render document data to JSON format"""
        # Convert to dict for processing
        data_dict = data.model_dump()

        # Process ignore_line_break if needed
        if self.ignore_line_break:
            # Process tables
            for table in data_dict.get("tables", []):
                for cell in table.get("cells", []):
                    if "contents" in cell:
                        cell["contents"] = cell["contents"].replace("\n", "")

            # Process paragraphs
            for paragraph in data_dict.get("paragraphs", []):
                if "contents" in paragraph:
                    paragraph["contents"] = paragraph["contents"].replace("\n", "")

        # Format JSON with proper settings (matching original)
        return data_dict
