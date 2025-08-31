"""
Chart visualizer for data visualization
"""

import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional, Union, Tuple
import logging

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None
    Figure = None

try:
    import seaborn as sns
    SEABORN_AVAILABLE = True
except ImportError:
    SEABORN_AVAILABLE = False
    sns = None

from .base import BaseVisualizer


class ChartVisualizer(BaseVisualizer):
    """Chart data visualization"""
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        if not MATPLOTLIB_AVAILABLE:
            self.logger.warning("matplotlib is not available. Chart visualization will be limited.")
        
    def visualize(self, data: Any, **kwargs) -> Union[Figure, str]:
        """
        Main visualization method for chart data
        
        Args:
            data: Data to visualize
            **kwargs: Visualization parameters
            
        Returns:
            Matplotlib figure or error message
        """
        if not self._validate_input(data):
            return "No data to visualize"
            
        if not MATPLOTLIB_AVAILABLE:
            return "matplotlib is required for chart visualization"
            
        chart_type = kwargs.get('type', 'auto')
        
        if chart_type == 'auto':
            chart_type = self._detect_chart_type(data)
            
        if chart_type == 'line':
            return self._create_line_chart(data, **kwargs)
        elif chart_type == 'bar':
            return self._create_bar_chart(data, **kwargs)
        elif chart_type == 'scatter':
            return self._create_scatter_chart(data, **kwargs)
        elif chart_type == 'histogram':
            return self._create_histogram(data, **kwargs)
        elif chart_type == 'pie':
            return self._create_pie_chart(data, **kwargs)
        elif chart_type == 'box':
            return self._create_box_plot(data, **kwargs)
        else:
            return self._create_line_chart(data, **kwargs)
    
    def _validate_input(self, data: Any) -> bool:
        """Validate chart input data"""
        if data is None:
            return False
            
        if isinstance(data, (pd.DataFrame, pd.Series, list, dict, np.ndarray)):
            return True
            
        return False
    
    def _detect_chart_type(self, data: Any) -> str:
        """Auto-detect appropriate chart type based on data"""
        try:
            if isinstance(data, pd.DataFrame):
                if len(data.columns) >= 2:
                    # Check if data looks like time series
                    if len(data) > 10:
                        return 'line'
                    else:
                        return 'bar'
                else:
                    return 'histogram'
            elif isinstance(data, pd.Series):
                if data.dtype in ['int64', 'float64']:
                    return 'histogram'
                else:
                    return 'bar'
            elif isinstance(data, list):
                if len(data) > 10:
                    return 'line'
                else:
                    return 'bar'
            elif isinstance(data, dict):
                return 'bar'
            else:
                return 'line'
        except Exception:
            return 'line'
    
    def _create_line_chart(self, data: Any, **kwargs) -> Figure:
        """Create line chart"""
        try:
            fig, ax = plt.subplots(figsize=kwargs.get('figsize', (10, 6)))
            
            # Filter out non-line chart parameters
            line_kwargs = {k: v for k, v in kwargs.items() 
                          if k not in ['type', 'figsize', 'title', 'grid', 'x', 'y']}
            
            if isinstance(data, pd.DataFrame):
                if len(data.columns) >= 2:
                    x_col = kwargs.get('x', data.columns[0])
                    y_col = kwargs.get('y', data.columns[1])
                    ax.plot(data[x_col], data[y_col], **line_kwargs)
                    ax.set_xlabel(x_col)
                    ax.set_ylabel(y_col)
                else:
                    ax.plot(data.index, data.iloc[:, 0], **line_kwargs)
            elif isinstance(data, pd.Series):
                ax.plot(data.index, data.values, **line_kwargs)
            elif isinstance(data, list):
                ax.plot(range(len(data)), data, **line_kwargs)
            elif isinstance(data, dict):
                ax.plot(list(data.keys()), list(data.values()), **line_kwargs)
            
            ax.set_title(kwargs.get('title', 'Line Chart'))
            ax.grid(kwargs.get('grid', True))
            
            return fig
        except Exception as e:
            self.logger.error(f"Error in line chart creation: {e}")
            return self._create_error_figure(str(e))
    
    def _create_bar_chart(self, data: Any, **kwargs) -> Figure:
        """Create bar chart"""
        try:
            fig, ax = plt.subplots(figsize=kwargs.get('figsize', (10, 6)))
            
            # Filter out non-bar chart parameters
            bar_kwargs = {k: v for k, v in kwargs.items() 
                         if k not in ['type', 'figsize', 'title', 'rotate_labels', 'x', 'y']}
            
            if isinstance(data, pd.DataFrame):
                if len(data.columns) >= 2:
                    x_col = kwargs.get('x', data.columns[0])
                    y_col = kwargs.get('y', data.columns[1])
                    ax.bar(data[x_col], data[y_col], **bar_kwargs)
                    ax.set_xlabel(x_col)
                    ax.set_ylabel(y_col)
                else:
                    ax.bar(range(len(data)), data.iloc[:, 0], **bar_kwargs)
            elif isinstance(data, pd.Series):
                ax.bar(range(len(data)), data.values, **bar_kwargs)
            elif isinstance(data, list):
                ax.bar(range(len(data)), data, **bar_kwargs)
            elif isinstance(data, dict):
                ax.bar(list(data.keys()), list(data.values()), **bar_kwargs)
            
            ax.set_title(kwargs.get('title', 'Bar Chart'))
            
            # Rotate x-axis labels if needed
            if kwargs.get('rotate_labels', False):
                plt.xticks(rotation=45)
            
            return fig
        except Exception as e:
            self.logger.error(f"Error in bar chart creation: {e}")
            return self._create_error_figure(str(e))
    
    def _create_scatter_chart(self, data: Any, **kwargs) -> Figure:
        """Create scatter plot"""
        try:
            fig, ax = plt.subplots(figsize=kwargs.get('figsize', (10, 6)))
            
            if isinstance(data, pd.DataFrame):
                if len(data.columns) >= 2:
                    x_col = kwargs.get('x', data.columns[0])
                    y_col = kwargs.get('y', data.columns[1])
                    ax.scatter(data[x_col], data[y_col], **kwargs)
                    ax.set_xlabel(x_col)
                    ax.set_ylabel(y_col)
                else:
                    return self._create_error_figure("Need at least 2 columns for scatter plot")
            elif isinstance(data, list) and len(data) >= 2:
                if isinstance(data[0], (list, tuple)) and len(data[0]) >= 2:
                    x = [point[0] for point in data]
                    y = [point[1] for point in data]
                    ax.scatter(x, y, **kwargs)
                else:
                    return self._create_error_figure("Invalid data format for scatter plot")
            else:
                return self._create_error_figure("Invalid data format for scatter plot")
            
            ax.set_title(kwargs.get('title', 'Scatter Plot'))
            ax.grid(kwargs.get('grid', True))
            
            return fig
        except Exception as e:
            self.logger.error(f"Error in scatter chart creation: {e}")
            return self._create_error_figure(str(e))
    
    def _create_histogram(self, data: Any, **kwargs) -> Figure:
        """Create histogram"""
        try:
            fig, ax = plt.subplots(figsize=kwargs.get('figsize', (10, 6)))
            
            if isinstance(data, pd.DataFrame):
                if len(data.columns) >= 1:
                    col = kwargs.get('column', data.columns[0])
                    ax.hist(data[col], bins=kwargs.get('bins', 30), **kwargs)
                    ax.set_xlabel(col)
                else:
                    return self._create_error_figure("No columns in DataFrame")
            elif isinstance(data, pd.Series):
                ax.hist(data.values, bins=kwargs.get('bins', 30), **kwargs)
                ax.set_xlabel(data.name or 'Value')
            elif isinstance(data, list):
                ax.hist(data, bins=kwargs.get('bins', 30), **kwargs)
                ax.set_xlabel('Value')
            elif isinstance(data, dict):
                ax.hist(list(data.values()), bins=kwargs.get('bins', 30), **kwargs)
                ax.set_xlabel('Value')
            else:
                return self._create_error_figure("Invalid data format for histogram")
            
            ax.set_title(kwargs.get('title', 'Histogram'))
            ax.set_ylabel('Frequency')
            
            return fig
        except Exception as e:
            self.logger.error(f"Error in histogram creation: {e}")
            return self._create_error_figure(str(e))
    
    def _create_pie_chart(self, data: Any, **kwargs) -> Figure:
        """Create pie chart"""
        try:
            fig, ax = plt.subplots(figsize=kwargs.get('figsize', (8, 8)))
            
            if isinstance(data, pd.Series):
                ax.pie(data.values, labels=data.index, **kwargs)
            elif isinstance(data, dict):
                ax.pie(list(data.values()), labels=list(data.keys()), **kwargs)
            elif isinstance(data, list):
                labels = kwargs.get('labels', [f'Item {i}' for i in range(len(data))])
                ax.pie(data, labels=labels, **kwargs)
            else:
                return self._create_error_figure("Invalid data format for pie chart")
            
            ax.set_title(kwargs.get('title', 'Pie Chart'))
            
            return fig
        except Exception as e:
            self.logger.error(f"Error in pie chart creation: {e}")
            return self._create_error_figure(str(e))
    
    def _create_box_plot(self, data: Any, **kwargs) -> Figure:
        """Create box plot"""
        try:
            fig, ax = plt.subplots(figsize=kwargs.get('figsize', (10, 6)))
            
            if isinstance(data, pd.DataFrame):
                if SEABORN_AVAILABLE:
                    sns.boxplot(data=data, ax=ax, **kwargs)
                else:
                    ax.boxplot([data[col] for col in data.columns], labels=data.columns, **kwargs)
            elif isinstance(data, pd.Series):
                ax.boxplot(data.values, **kwargs)
                ax.set_ylabel(data.name or 'Value')
            elif isinstance(data, list):
                ax.boxplot(data, **kwargs)
                ax.set_ylabel('Value')
            else:
                return self._create_error_figure("Invalid data format for box plot")
            
            ax.set_title(kwargs.get('title', 'Box Plot'))
            
            return fig
        except Exception as e:
            self.logger.error(f"Error in box plot creation: {e}")
            return self._create_error_figure(str(e))
    
    def _create_error_figure(self, error_message: str) -> Figure:
        """Create error figure with message"""
        if not MATPLOTLIB_AVAILABLE:
            return None
            
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.text(0.5, 0.5, f'Error: {error_message}', 
                ha='center', va='center', transform=ax.transAxes,
                fontsize=12, color='red')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        return fig
    
    def save_chart(self, fig: Figure, filename: str, **kwargs) -> bool:
        """
        Save chart to file
        
        Args:
            fig: Matplotlib figure
            filename: Output filename
            **kwargs: Save parameters
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if fig is not None:
                fig.savefig(filename, **kwargs)
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error saving chart: {e}")
            return False
    
    def get_chart_data_summary(self, data: Any) -> Dict:
        """
        Get summary of chart data
        
        Args:
            data: Chart data
            
        Returns:
            Data summary as dict
        """
        try:
            if isinstance(data, pd.DataFrame):
                summary = {
                    "type": "DataFrame",
                    "shape": data.shape,
                    "columns": list(data.columns),
                    "dtypes": data.dtypes.to_dict(),
                    "null_counts": data.isnull().sum().to_dict()
                }
                
                # Add numeric statistics
                numeric_cols = data.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    summary["numeric_stats"] = data[numeric_cols].describe().to_dict()
                    
            elif isinstance(data, pd.Series):
                summary = {
                    "type": "Series",
                    "length": len(data),
                    "dtype": str(data.dtype),
                    "null_count": data.isnull().sum()
                }
                
                if data.dtype in ['int64', 'float64']:
                    summary["stats"] = data.describe().to_dict()
                    
            elif isinstance(data, list):
                summary = {
                    "type": "list",
                    "length": len(data),
                    "data_type": type(data[0]).__name__ if data else "empty"
                }
                
            elif isinstance(data, dict):
                summary = {
                    "type": "dict",
                    "keys": list(data.keys()),
                    "key_count": len(data)
                }
                
            else:
                summary = {
                    "type": str(type(data)),
                    "message": "Unknown data type"
                }
                
            return summary
        except Exception as e:
            self.logger.error(f"Error in chart data summary: {e}")
            return {"error": str(e)}
