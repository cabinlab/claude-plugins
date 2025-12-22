"""
Inspection and measurement-related handlers
"""
import adsk.core
import adsk.fusion
from handlers.base import BaseHandler
from core.errors import ValidationError, FusionAPIError


class MeasureGeometryHandler(BaseHandler):
    """Handler for measure_geometry action"""
    
    def validate(self, args: dict) -> dict:
        """Validate measure geometry arguments"""
        self.validators.validate_required_fields(args, ["refs"])
        
        refs = args["refs"]
        if not isinstance(refs, list):
            raise ValidationError("Refs must be an array")
        
        return {
            "refs": refs
        }
    
    def execute(self, args: dict) -> dict:
        """Execute measure geometry action"""
        root_comp = self.context.root_component
        measurements = []
        
        for ref in args["refs"]:
            if not isinstance(ref, dict):
                raise ValidationError("Each ref must be an object")
            
            measurement = {"ref": ref}
            
            # For Phase 1, support basic body measurements
            if ref.get("type") == "body" and "body" in ref and "component" in ref:
                body_name = ref["body"]
                component_name = ref["component"]
                
                # Find the body (simplified - assume root component for v0)
                if component_name == root_comp.name:
                    try:
                        for body in root_comp.bRepBodies:
                            if body.name == body_name:
                                if hasattr(body, 'physicalProperties'):
                                    measurement["volume"] = body.physicalProperties.volume
                                break
                    except:
                        pass
            
            measurements.append(measurement)
        
        return {
            "measurements": measurements
        }