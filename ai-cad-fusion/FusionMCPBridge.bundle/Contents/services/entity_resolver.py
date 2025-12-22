"""
Entity resolution without object caching (safer for Fusion's environment)
"""
import adsk.core
import adsk.fusion
from core.errors import ValidationError, FusionAPIError
from services.fusion_context import FusionContext


class EntityResolver:
    """Entity resolution without object caching (safer for Fusion's environment)"""
    
    def __init__(self, fusion_context: FusionContext):
        self._context = fusion_context
        
    def resolve_body_ref(self, ref: dict):
        """Resolve bodyRef to Fusion body - always fresh lookup"""
        # Note: We don't cache BRepBody objects as they can become stale
        # after geometry changes. The lookup is fast enough.
        
        # Validation
        if not isinstance(ref, dict):
            raise ValidationError("bodyRef must be an object")
        
        comp_name = ref.get("component")
        body_name = ref.get("body")
        
        if not comp_name or not body_name:
            raise ValidationError("bodyRef requires 'component' and 'body'")
        
        # v0 scope: only root component supported
        root_comp = self._context.root_component
        if comp_name != root_comp.name:
            raise ValidationError("Only bodies in the root component are supported in v0")
        
        # Linear search is fine - body lists are typically small
        for body in root_comp.bRepBodies:
            if body.name == body_name:
                return body
                
        raise ValidationError(f"Body '{body_name}' not found in component '{comp_name}'")
    
    def resolve_sketch(self, name: str):
        """Resolve sketch by name - always fresh lookup"""
        root_comp = self._context.root_component
        for sketch in root_comp.sketches:
            if sketch.name == name:
                return sketch
        raise ValidationError(f"Sketch '{name}' not found")
    
    def resolve_face_ref(self, ref: dict):
        """Resolve faceRef to Fusion face - v0 scope"""
        if not isinstance(ref, dict):
            raise ValidationError("faceRef must be an object")
        
        comp_name = ref.get("component")
        body_name = ref.get("body")
        face_index = ref.get("faceIndex")
        
        if comp_name is None or body_name is None or face_index is None:
            raise ValidationError("faceRef requires component, body, and faceIndex")
        
        # First resolve the body
        body = self.resolve_body_ref({"component": comp_name, "body": body_name})
        
        # Then get the face by index
        try:
            idx = int(face_index)
            if idx < 0 or idx >= body.faces.count:
                raise ValidationError(f"faceIndex {idx} out of range (0-{body.faces.count-1})")
            return body.faces.item(idx)
        except (TypeError, ValueError):
            raise ValidationError("faceIndex must be a non-negative integer")

    def resolve_edge_ref(self, ref: dict):
        """Resolve edgeRef to Fusion edge - v0 scope"""
        if not isinstance(ref, dict):
            raise ValidationError("edgeRef must be an object")

        comp_name = ref.get("component")
        body_name = ref.get("body")
        edge_index = ref.get("edgeIndex")

        if comp_name is None or body_name is None or edge_index is None:
            raise ValidationError("edgeRef requires component, body, and edgeIndex")

        # First resolve the body
        body = self.resolve_body_ref({"component": comp_name, "body": body_name})

        # Then get the edge by index
        try:
            idx = int(edge_index)
            if idx < 0 or idx >= body.edges.count:
                raise ValidationError(f"edgeIndex {idx} out of range (0-{body.edges.count-1})")
            return body.edges.item(idx)
        except (TypeError, ValueError):
            raise ValidationError("edgeIndex must be a non-negative integer")
