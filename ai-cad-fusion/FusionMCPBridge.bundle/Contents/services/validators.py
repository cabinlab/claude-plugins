"""
Centralized validation utilities matching bridge determinism rules
"""
from typing import Any, List
from core.errors import ValidationError


class ValidationService:
    """Centralized validation utilities matching bridge determinism rules"""
    
    # Allowlists from existing implementation and API_BRIDGE.md
    ALLOWED_UNITS = ["", "mm", "cm", "m", "in", "ft", "deg"]
    ALLOWED_PLANES = ["XY", "YZ", "XZ"]
    ALLOWED_OPERATIONS = ["new_body", "join", "cut", "intersect"]
    ALLOWED_DIRECTIONS = ["positive", "negative", "symmetric"]
    ALLOWED_ORIENTATIONS = ["horizontal", "vertical", "aligned"]
    ALLOWED_CONSTRAINT_TYPES = ["horizontal", "vertical", "parallel", "perpendicular", "tangent", "coincident"]
    
    def validate_required_fields(self, args: dict, required: List[str]) -> None:
        """Validate required fields are present"""
        missing = [f for f in required if f not in args]
        if missing:
            # Match existing error format
            if len(missing) == 1:
                raise ValidationError(f"Missing required field: {missing[0]}")
            else:
                raise ValidationError(f"Missing required fields: {', '.join(missing)}")
    
    def validate_unit(self, unit: str) -> None:
        """Validate unit is allowed"""
        if not isinstance(unit, str):
            raise ValidationError(f"Invalid unit type: {type(unit)}")
        if unit not in self.ALLOWED_UNITS:
            raise ValidationError(f"Invalid unit '{unit}'. Allowed units: {', '.join(repr(u) for u in self.ALLOWED_UNITS)}")
    
    def validate_plane(self, plane: str) -> str:
        """Validate and normalize plane name"""
        plane_upper = plane.upper()
        if plane_upper not in self.ALLOWED_PLANES:
            raise ValidationError(f"Invalid plane '{plane}'. Allowed planes: {', '.join(self.ALLOWED_PLANES)}")
        return plane_upper
    
    def validate_positive_number(self, value: Any, field_name: str) -> float:
        """Validate and convert to positive float"""
        try:
            num = float(value)
            if num <= 0:
                raise ValidationError(f"{field_name} must be a positive number")
            return num
        except (TypeError, ValueError):
            raise ValidationError(f"{field_name} must be a positive number")
    
    def validate_non_negative_int(self, value: Any, field_name: str) -> int:
        """Validate and convert to non-negative integer"""
        try:
            num = int(value)
            if num < 0:
                raise ValidationError(f"{field_name} must be a non-negative integer")
            return num
        except (TypeError, ValueError):
            raise ValidationError(f"{field_name} must be a non-negative integer")
    
    def validate_angle(self, value: Any, field_name: str) -> float:
        """Validate angle - can be negative or zero"""
        try:
            return float(value)
        except (TypeError, ValueError):
            raise ValidationError(f"{field_name} must be a number")
    
    def validate_non_empty_string(self, value: Any, field_name: str) -> str:
        """Validate and normalize string field"""
        if not isinstance(value, str) or not value.strip():
            raise ValidationError(f"{field_name} must be a non-empty string")
        return value.strip()
    
    def check_parameter_name_collision(self, name: str, design: Any) -> None:
        """Check if parameter name already exists (determinism requirement)"""
        if design.userParameters:
            for param in design.userParameters:
                if param.name == name:
                    raise ValidationError(f"Parameter '{name}' already exists")
    
    def check_sketch_name_collision(self, name: str, root_comp: Any) -> None:
        """Check if sketch name already exists (determinism requirement)"""
        for sketch in root_comp.sketches:
            if sketch.name == name:
                raise ValidationError(f"Sketch '{name}' already exists")
    
    def validate_operation(self, operation: str) -> None:
        """Validate operation type"""
        if operation not in self.ALLOWED_OPERATIONS:
            raise ValidationError(f"Operation must be one of: {', '.join(self.ALLOWED_OPERATIONS)}")
    
    def validate_direction(self, direction: str) -> None:
        """Validate extrusion direction"""
        if direction not in self.ALLOWED_DIRECTIONS:
            raise ValidationError(f"Direction must be one of: {', '.join(self.ALLOWED_DIRECTIONS)}")
    
    def validate_orientation(self, orientation: str) -> None:
        """Validate dimension orientation"""
        if orientation not in self.ALLOWED_ORIENTATIONS:
            raise ValidationError(f"Orientation must be one of: {', '.join(self.ALLOWED_ORIENTATIONS)}")
    
    def validate_constraint_type(self, constraint_type: str) -> None:
        """Validate constraint type"""
        if constraint_type not in self.ALLOWED_CONSTRAINT_TYPES:
            raise ValidationError(f"Constraint type must be one of: {', '.join(self.ALLOWED_CONSTRAINT_TYPES)}")
