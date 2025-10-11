"""
Base visualizer class for document visualization
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
import numpy as np
from PIL import Image


class BaseVisualizer(ABC):
    """Base class for all visualizers"""
    
    def __init__(self):
        self.logger = None
    
    @abstractmethod
    def visualize(self, data: Any, **kwargs) -> Union[np.ndarray, Image.Image]:
        """
        Main visualization method
        
        Args:
            data: Input data to visualize
            **kwargs: Additional visualization parameters
            
        Returns:
            Visualized image as numpy array or PIL Image
        """
        pass
    
    def _validate_input(self, data: Any) -> bool:
        """
        Validate input data
        
        Args:
            data: Input data to validate
            
        Returns:
            True if valid, False otherwise
        """
        return data is not None
