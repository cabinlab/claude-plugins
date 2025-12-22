"""
Centralized Fusion 360 API context management - no caching of Fusion objects
"""
import adsk.core
import adsk.fusion
from core.errors import FusionAPIError


class FusionContext:
    """Centralized Fusion 360 API context management - no caching of Fusion objects"""
    
    def __init__(self):
        self._app = None
        
    @property
    def app(self):
        """Lazy initialization of Fusion app"""
        if self._app is None:
            self._app = adsk.core.Application.get()
        return self._app
    
    @property
    def design(self):
        """Get active design - always fresh, never cached"""
        design = self.app.activeProduct
        if not design or not hasattr(design, 'rootComponent'):
            raise FusionAPIError("No active design document")
        return design
    
    @property
    def root_component(self):
        """Get root component - always fresh, never cached"""
        return self.design.rootComponent
