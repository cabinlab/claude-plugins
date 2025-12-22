"""
Constraint and dimension-related handlers
"""
import adsk.core
import adsk.fusion
from handlers.base import BaseHandler
from core.errors import ValidationError, FusionAPIError


class AddConstraintsHandler(BaseHandler):
    """Handler for add_constraints action"""
    
    def validate(self, args: dict) -> dict:
        """Validate add constraints arguments"""
        self.validators.validate_required_fields(args, ["sketch", "type", "refs"])
        
        sketch_name = self.validators.validate_non_empty_string(args["sketch"], "sketch")
        constraint_type = args["type"]
        refs = args["refs"]
        
        # Validate constraint type
        self.validators.validate_constraint_type(constraint_type)
        
        # Validate refs
        if not isinstance(refs, list) or len(refs) == 0:
            raise ValidationError("refs must be a non-empty array")
        
        return {
            "sketch": sketch_name,
            "type": constraint_type,
            "refs": refs
        }
    
    def execute(self, args: dict) -> dict:
        """Execute add constraints action"""
        # Find the sketch
        target_sketch = self.resolver.resolve_sketch(args["sketch"])
        
        # Use feature detection for constraints collection
        # Prefer geometricConstraints if present; otherwise sketchConstraints
        if hasattr(target_sketch, 'geometricConstraints'):
            gc = target_sketch.geometricConstraints
        elif hasattr(target_sketch, 'sketchConstraints'):
            gc = target_sketch.sketchConstraints
        else:
            raise FusionAPIError("No constraints collection found on sketch")
        
        # Helper to resolve an entityRef into a sketch entity
        def resolve_entity(ref: dict):
            if not isinstance(ref, dict):
                raise ValidationError("Each ref must be an object")
            for k in ("sketch", "type", "index"):
                if k not in ref:
                    raise ValidationError(f"ref missing required field: {k}")
            if ref["sketch"] != args["sketch"]:
                raise ValidationError("ref.sketch must match target sketch")
            
            etype = ref["type"]
            try:
                idx = int(ref["index"])
                if idx < 0:
                    raise ValueError()
            except Exception:
                raise ValidationError("ref.index must be a non-negative integer")
            
            if etype == "line":
                coll = target_sketch.sketchCurves.sketchLines
            elif etype == "arc":
                coll = target_sketch.sketchCurves.sketchArcs
            elif etype == "circle":
                coll = target_sketch.sketchCurves.sketchCircles
            else:
                raise ValidationError("Unsupported entityRef.type for constraints")
            
            if idx >= coll.count:
                raise ValidationError(f"ref.index {idx} out of range for {etype}s (0-{coll.count-1})")
            return coll.item(idx)
        
        applied = False
        constraint_type = args["type"]
        refs = args["refs"]
        
        if constraint_type in ("horizontal", "vertical"):
            # Expect 1 line ref
            if len(refs) != 1:
                raise ValidationError(f"{constraint_type} constraint requires exactly 1 line ref")
            entity = resolve_entity(refs[0])
            # Ensure it's a line
            if not hasattr(entity, 'geometry'):
                raise ValidationError("Constraint requires a line entity")
            if constraint_type == "horizontal":
                gc.addHorizontal(entity)
            else:
                gc.addVertical(entity)
            applied = True
        elif constraint_type in ("parallel", "perpendicular"):
            # Expect 2 line refs
            if len(refs) != 2:
                raise ValidationError(f"{constraint_type} constraint requires exactly 2 line refs")
            a = resolve_entity(refs[0])
            b = resolve_entity(refs[1])
            if constraint_type == "parallel":
                gc.addParallel(a, b)
            else:
                gc.addPerpendicular(a, b)
            applied = True
        elif constraint_type == "tangent":
            # Expect 2 refs: circle/arc with line/arc/circle
            if len(refs) != 2:
                raise ValidationError("tangent constraint requires exactly 2 refs")
            a = resolve_entity(refs[0])
            b = resolve_entity(refs[1])
            gc.addTangent(a, b)
            applied = True
        elif constraint_type == "coincident":
            # Not fully supported in v0 (requires point refs). Return E_BAD_ARGS for now
            raise ValidationError("coincident constraint for point refs not yet supported in v0")
        
        return {"applied": applied}


class AddDimensionDistanceHandler(BaseHandler):
    """Handler for add_dimension_distance action"""
    
    def validate(self, args: dict) -> dict:
        """Validate add dimension distance arguments"""
        self.validators.validate_required_fields(args, ["sketch", "a", "b", "orientation", "expression"])
        
        sketch_name = self.validators.validate_non_empty_string(args["sketch"], "sketch")
        a = args["a"]
        b = args["b"]
        orientation = args["orientation"]
        expression = str(args["expression"]) if args["expression"] is not None else ""
        
        # Validate orientation
        self.validators.validate_orientation(orientation)
        
        # Validate a and b
        if not isinstance(a, dict) or not isinstance(b, dict):
            raise ValidationError("a and b must be objects")
        
        return {
            "sketch": sketch_name,
            "a": a,
            "b": b,
            "orientation": orientation,
            "expression": expression
        }
    
    def execute(self, args: dict) -> dict:
        """Execute add dimension distance action"""
        # Find the sketch
        target_sketch = self.resolver.resolve_sketch(args["sketch"])
        
        # For v0 implement only point-point distances with explicit coordinates
        def to_point3d(obj):
            if "type" in obj and obj["type"] == "point" and isinstance(obj.get("ref"), dict):
                ref = obj["ref"]
                if "x" in ref and "y" in ref:
                    try:
                        x = float(ref["x"])
                        y = float(ref["y"])
                        z = 0.0
                        return adsk.core.Point3D.create(x, y, z)
                    except Exception:
                        raise ValidationError("point ref coordinates must be numeric")
            raise ValidationError("Only point-point with {type:'point', ref:{x,y}} supported in v0")
        
        p1 = to_point3d(args["a"])
        p2 = to_point3d(args["b"])
        
        # Create sketch points so we can dimension between them
        sp1 = target_sketch.sketchPoints.add(p1)
        sp2 = target_sketch.sketchPoints.add(p2)
        
        dim_orient_map = {
            "horizontal": adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation,
            "vertical": adsk.fusion.DimensionOrientations.VerticalDimensionOrientation,
            "aligned": adsk.fusion.DimensionOrientations.AlignedDimensionOrientation
        }
        
        dim = target_sketch.sketchDimensions.addDistanceDimension(
            sp1, sp2, dim_orient_map[args["orientation"]],
            adsk.core.Point3D.create((p1.x+p2.x)/2.0, (p1.y+p2.y)/2.0, 0.0)
        )
        
        # Set expression (may reference parameters); Fusion will error if invalid
        try:
            dim.parameter.expression = args["expression"]
        except Exception as e:
            # If expression invalid, surface as runtime error
            raise FusionAPIError(f"Failed to set dimension expression: {str(e)}")
        
        dim_name = None
        try:
            dim_name = dim.parameter.name
        except Exception:
            pass
        
        return {"dimensionName": dim_name or "dimension"}