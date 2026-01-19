"""
Base class for all action handlers
"""
from abc import ABC, abstractmethod
from typing import Any, Dict
from core.errors import ValidationError, FusionAPIError
from services.fusion_context import FusionContext
from services.entity_resolver import EntityResolver
from services.validators import ValidationService


class BaseHandler(ABC):
    """Base class for all action handlers"""
    
    def __init__(self, context: FusionContext, resolver: EntityResolver, validators: ValidationService):
        self.context = context
        self.resolver = resolver
        self.validators = validators
        
    @abstractmethod
    def validate(self, args: dict) -> dict:
        """Validate and normalize input arguments"""
        pass
    
    @abstractmethod
    def execute(self, args: dict) -> dict:
        """Execute the action and return result"""
        pass
    
    def handle(self, args: dict) -> dict:
        """Main entry point with error handling"""
        try:
            validated_args = self.validate(args)
            return self.execute(validated_args)
        except ValidationError:
            raise  # Re-raise validation errors
        except Exception as e:
            raise FusionAPIError(f"Operation failed: {str(e)}")
