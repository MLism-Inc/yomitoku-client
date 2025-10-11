"""
Table extractor for table data extraction and formatting
"""

import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional, Union
import logging

from .base import BaseVisualizer


class TableExtractor(BaseVisualizer):
    """Table data extraction and formatting"""
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
    def visualize(self, data: Any, **kwargs) -> Union[str, Dict]:
        """
        Main visualization method (calls extract for table data)
        
        Args:
            data: Table data (DataFrame, list of lists, or dict)
            **kwargs: Extraction parameters
            
        Returns:
            Extracted table as string or dict
        """
        return self.extract(data, **kwargs)
    
    def extract(self, data: Any, **kwargs) -> Union[str, Dict]:
        """
        Main extraction method for table data
        
        Args:
            data: Table data (DataFrame, list of lists, or dict)
            **kwargs: Extraction parameters
            
        Returns:
            Extracted table as string or dict
        """
        if not self._validate_input(data):
            return "No data to extract"
            
        output_format = kwargs.get('format', 'text')
        
        if output_format == 'text':
            return self._extract_as_text(data, **kwargs)
        elif output_format == 'html':
            return self._extract_as_html(data, **kwargs)
        elif output_format == 'json':
            return self._extract_as_json(data, **kwargs)
        else:
            return self._extract_as_text(data, **kwargs)
    
    def _validate_input(self, data: Any) -> bool:
        """Validate table input data"""
        if data is None:
            return False
            
        if isinstance(data, (pd.DataFrame, list, dict)):
            return True
            
        return False
    
    def _extract_as_text(self, data: Any, **kwargs) -> str:
        """Extract table as formatted text"""
        try:
            if isinstance(data, pd.DataFrame):
                # Remove format parameter from kwargs
                text_kwargs = {k: v for k, v in kwargs.items() if k != 'format'}
                return data.to_string(**text_kwargs)
            elif isinstance(data, list):
                if not data:
                    return "Empty table"
                    
                # Convert to DataFrame for better formatting
                df = pd.DataFrame(data)
                if kwargs.get('headers'):
                    df.columns = kwargs['headers']
                # Remove format and headers parameters from kwargs
                text_kwargs = {k: v for k, v in kwargs.items() 
                              if k not in ['format', 'headers']}
                return df.to_string(**text_kwargs)
            elif isinstance(data, dict):
                # Handle dict of lists or nested dict
                if all(isinstance(v, list) for v in data.values()):
                    df = pd.DataFrame(data)
                    # Remove format parameter from kwargs
                    text_kwargs = {k: v for k, v in kwargs.items() if k != 'format'}
                    return df.to_string(**text_kwargs)
                else:
                    return str(data)
            else:
                return str(data)
        except Exception as e:
            self.logger.error(f"Error in text extraction: {e}")
            return str(data)
    
    def _extract_as_html(self, data: Any, **kwargs) -> str:
        """Extract table as HTML"""
        try:
            if isinstance(data, pd.DataFrame):
                # Only pass valid parameters to to_html()
                valid_html_params = ['buf', 'columns', 'col_space', 'header', 'index', 'na_rep', 
                                   'formatters', 'float_format', 'sparsify', 'index_names', 
                                   'justify', 'max_rows', 'max_cols', 'show_dimensions', 
                                   'decimal', 'table_id', 'render_links', 'escape', 'classes']
                html_kwargs = {k: v for k, v in kwargs.items() if k in valid_html_params}
                html_output = data.to_html(**html_kwargs)
                # Convert \n to <br> tags for proper HTML line breaks
                html_output = html_output.replace('\\n', '<br>')
                return html_output
            elif isinstance(data, list):
                if not data:
                    return "<table><tr><td>Empty table</td></tr></table>"
                    
                df = pd.DataFrame(data)
                if kwargs.get('headers'):
                    df.columns = kwargs['headers']
                # Only pass valid parameters to to_html()
                valid_html_params = ['buf', 'columns', 'col_space', 'header', 'index', 'na_rep', 
                                   'formatters', 'float_format', 'sparsify', 'index_names', 
                                   'justify', 'max_rows', 'max_cols', 'show_dimensions', 
                                   'decimal', 'table_id', 'render_links', 'escape', 'classes']
                html_kwargs = {k: v for k, v in kwargs.items() if k in valid_html_params}
                return df.to_html(**html_kwargs)
            elif isinstance(data, dict):
                if all(isinstance(v, list) for v in data.values()):
                    df = pd.DataFrame(data)
                    # Only pass valid parameters to to_html()
                    valid_html_params = ['buf', 'columns', 'col_space', 'header', 'index', 'na_rep', 
                                       'formatters', 'float_format', 'sparsify', 'index_names', 
                                       'justify', 'max_rows', 'max_cols', 'show_dimensions', 
                                       'decimal', 'table_id', 'render_links', 'escape', 'classes']
                    html_kwargs = {k: v for k, v in kwargs.items() if k in valid_html_params}
                    return df.to_html(**html_kwargs)
                else:
                    # Convert dict to HTML table
                    html = "<table border='1'>\n"
                    for key, value in data.items():
                        html += f"<tr><td>{key}</td><td>{value}</td></tr>\n"
                    html += "</table>"
                    return html
            else:
                return f"<table><tr><td>{data}</td></tr></table>"
        except Exception as e:
            self.logger.error(f"Error in HTML extraction: {e}")
            return f"<table><tr><td>Error: {e}</td></tr></table>"
    
    def _extract_as_json(self, data: Any, **kwargs) -> Dict:
        """Extract table as JSON structure"""
        try:
            if isinstance(data, pd.DataFrame):
                # Remove 'format' and 'index' from kwargs as they're not valid for to_dict()
                # Handle 'index' parameter separately
                include_index = kwargs.get('index', True)
                json_kwargs = {k: v for k, v in kwargs.items()
                              if k not in ['format', 'index']}

                # Use 'records' orient if index=False is specified
                if not include_index and 'orient' not in json_kwargs:
                    json_kwargs['orient'] = 'records'

                # Ensure we don't pass any invalid parameters to to_dict()
                valid_params = ['orient', 'into', 'date_format', 'date_unit', 'default_handler']
                json_kwargs = {k: v for k, v in json_kwargs.items() if k in valid_params}

                return data.to_dict(**json_kwargs)
            elif isinstance(data, list):
                if not data:
                    return {"table": [], "message": "Empty table"}
                    
                # Convert to dict format
                if kwargs.get('headers'):
                    headers = kwargs['headers']
                    result = {}
                    for i, header in enumerate(headers):
                        if i < len(data[0]):
                            result[header] = [row[i] for row in data]
                    return result
                else:
                    return {"table": data}
            elif isinstance(data, dict):
                return data
            else:
                return {"data": str(data)}
        except Exception as e:
            error_msg = f"Error in JSON extraction: {e}"
            self.logger.error(error_msg)
            # Return a list format if DataFrame.to_dict() fails
            if isinstance(data, pd.DataFrame):
                try:
                    # Fallback to records format
                    return data.to_dict(orient='records')
                except:
                    # Last resort: convert to list
                    return {"data": data.values.tolist(), "columns": data.columns.tolist()}
            return {"error": str(e)}
    
    def extract_table_structure(self, table_data: Any, **kwargs) -> str:
        """
        Extract table structure information
        
        Args:
            table_data: Table data
            **kwargs: Additional parameters
            
        Returns:
            Table structure information as string
        """
        try:
            if isinstance(table_data, pd.DataFrame):
                info = {
                    "shape": table_data.shape,
                    "columns": list(table_data.columns),
                    "dtypes": table_data.dtypes.to_dict(),
                    "memory_usage": table_data.memory_usage(deep=True).sum(),
                    "null_counts": table_data.isnull().sum().to_dict()
                }
            elif isinstance(table_data, list):
                if not table_data:
                    return "Empty table"
                    
                info = {
                    "rows": len(table_data),
                    "columns": len(table_data[0]) if table_data else 0,
                    "data_type": "list"
                }
            elif isinstance(table_data, dict):
                info = {
                    "keys": list(table_data.keys()),
                    "key_count": len(table_data),
                    "data_type": "dict"
                }
            else:
                return f"Unknown data type: {type(table_data)}"
            
            # Format the info
            result = "Table Structure:\n"
            for key, value in info.items():
                result += f"  {key}: {value}\n"
                
            return result
        except Exception as e:
            self.logger.error(f"Error in table structure extraction: {e}")
            return f"Error analyzing table structure: {e}"
    
    def get_table_summary(self, data: Any, **kwargs) -> Dict:
        """
        Get summary statistics for table data
        
        Args:
            data: Table data
            **kwargs: Additional parameters
            
        Returns:
            Summary statistics as dict
        """
        try:
            if isinstance(data, pd.DataFrame):
                summary = {
                    "shape": data.shape,
                    "columns": list(data.columns),
                    "dtypes": data.dtypes.to_dict(),
                    "null_counts": data.isnull().sum().to_dict(),
                    "numeric_columns": data.select_dtypes(include=[np.number]).columns.tolist(),
                    "categorical_columns": data.select_dtypes(include=['object']).columns.tolist()
                }
                
                # Add numeric statistics if available
                if len(summary["numeric_columns"]) > 0:
                    summary["numeric_stats"] = data[summary["numeric_columns"]].describe().to_dict()
                    
                return summary
            else:
                return {"message": "Summary not available for non-DataFrame data"}
        except Exception as e:
            self.logger.error(f"Error in table summary: {e}")
            return {"error": str(e)}
