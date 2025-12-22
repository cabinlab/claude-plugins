"""
Sketch-related handlers
"""
import adsk.core
import adsk.fusion
from handlers.base import BaseHandler
from core.errors import ValidationError, FusionAPIError


class CreateSketchHandler(BaseHandler):
    """Handler for create_sketch action"""
    
    def validate(self, args: dict) -> dict:
        """Validate sketch creation arguments"""
        self.validators.validate_required_fields(args, ["plane", "name"])
        
        # Validate and normalize plane
        plane = self.validators.validate_plane(args["plane"])
        
        # Validate name
        name = self.validators.validate_non_empty_string(args["name"], "name")
        
        # Check for name collision (determinism requirement)
        self.validators.check_sketch_name_collision(name, self.context.root_component)
        
        return {
            "plane": plane,
            "name": name
        }
    
    def execute(self, args: dict) -> dict:
        """Create the sketch"""
        root_comp = self.context.root_component
        
        # Get the construction plane based on the plane parameter
        if args["plane"] == "XY":
            construction_plane = root_comp.xYConstructionPlane
        elif args["plane"] == "YZ":
            construction_plane = root_comp.yZConstructionPlane
        elif args["plane"] == "XZ":
            construction_plane = root_comp.xZConstructionPlane
        
        # Create the sketch
        sketch = root_comp.sketches.add(construction_plane)
        sketch.name = args["name"]
        
        # Return the created sketch info
        result = {
            "name": sketch.name,
            "plane": args["plane"]
        }
        
        return result


class SketchDrawLineHandler(BaseHandler):
    """Handler for sketch_draw_line action"""
    
    def validate(self, args: dict) -> dict:
        """Validate sketch draw line arguments"""
        self.validators.validate_required_fields(args, ["sketch", "start", "end"])
        
        sketch_name = self.validators.validate_non_empty_string(args["sketch"], "sketch")
        start_point = args["start"]
        end_point = args["end"]
        
        # Validate points
        for point_name, point in [("start", start_point), ("end", end_point)]:
            if not isinstance(point, dict):
                raise ValidationError(f"{point_name} point must be an object")
            if "x" not in point or "y" not in point:
                raise ValidationError(f"{point_name} point must have 'x' and 'y' coordinates")
            try:
                float(point["x"])
                float(point["y"])
            except (ValueError, TypeError):
                raise ValidationError(f"{point_name} coordinates must be numbers")
        
        return {
            "sketch": sketch_name,
            "start": start_point,
            "end": end_point
        }
    
    def execute(self, args: dict) -> dict:
        """Execute sketch draw line action"""
        # Find the sketch by name
        target_sketch = self.resolver.resolve_sketch(args["sketch"])
        
        # Create points
        start_pt = adsk.core.Point3D.create(float(args["start"]["x"]), float(args["start"]["y"]), 0)
        end_pt = adsk.core.Point3D.create(float(args["end"]["x"]), float(args["end"]["y"]), 0)
        
        # Draw the line
        lines = target_sketch.sketchCurves.sketchLines
        line = lines.addByTwoPoints(start_pt, end_pt)
        
        # Return the created line info - match monolithic format exactly
        result = {
            "sketch": args["sketch"],
            "entity": {
                "type": "line",
                "index": lines.count - 1  # Index of the newly created line
            }
        }
        
        return result


class SketchDrawCircleHandler(BaseHandler):
    """Handler for sketch_draw_circle action"""
    
    def validate(self, args: dict) -> dict:
        """Validate sketch draw circle arguments"""
        self.validators.validate_required_fields(args, ["sketch", "center", "radius"])
        
        sketch_name = self.validators.validate_non_empty_string(args["sketch"], "sketch")
        center_point = args["center"]
        radius = self.validators.validate_positive_number(args["radius"], "radius")
        
        # Validate center point
        if not isinstance(center_point, dict):
            raise ValidationError("Center point must be an object")
        if "x" not in center_point or "y" not in center_point:
            raise ValidationError("Center point must have 'x' and 'y' coordinates")
        try:
            float(center_point["x"])
            float(center_point["y"])
        except (ValueError, TypeError):
            raise ValidationError("Center coordinates must be numbers")
        
        return {
            "sketch": sketch_name,
            "center": center_point,
            "radius": radius
        }
    
    def execute(self, args: dict) -> dict:
        """Execute sketch draw circle action"""
        # Find the sketch by name
        target_sketch = self.resolver.resolve_sketch(args["sketch"])
        
        # Create center point
        center_pt = adsk.core.Point3D.create(float(args["center"]["x"]), float(args["center"]["y"]), 0)
        
        # Draw the circle
        circles = target_sketch.sketchCurves.sketchCircles
        circle = circles.addByCenterRadius(center_pt, args["radius"])
        
        # Return the created circle info - match monolithic format exactly
        result = {
            "sketch": args["sketch"],
            "entity": {
                "type": "circle",
                "index": circles.count - 1  # Index of the newly created circle
            }
        }
        
        return result


class SketchDrawRectangleHandler(BaseHandler):
    """Handler for sketch_draw_rectangle action"""
    
    def validate(self, args: dict) -> dict:
        """Validate sketch draw rectangle arguments"""
        self.validators.validate_required_fields(args, ["sketch", "origin", "width", "height"])
        
        sketch_name = self.validators.validate_non_empty_string(args["sketch"], "sketch")
        origin_point = args["origin"]
        width = self.validators.validate_positive_number(args["width"], "width")
        height = self.validators.validate_positive_number(args["height"], "height")
        
        # Validate origin point
        if not isinstance(origin_point, dict):
            raise ValidationError("Origin point must be an object")
        if "x" not in origin_point or "y" not in origin_point:
            raise ValidationError("Origin point must have 'x' and 'y' coordinates")
        try:
            float(origin_point["x"])
            float(origin_point["y"])
        except (ValueError, TypeError):
            raise ValidationError("Origin coordinates must be numbers")
        
        return {
            "sketch": sketch_name,
            "origin": origin_point,
            "width": width,
            "height": height
        }
    
    def execute(self, args: dict) -> dict:
        """Execute sketch draw rectangle action"""
        # Find the sketch by name
        target_sketch = self.resolver.resolve_sketch(args["sketch"])
        
        # Create corner points for the rectangle
        origin_pt = adsk.core.Point3D.create(float(args["origin"]["x"]), float(args["origin"]["y"]), 0)
        opposite_pt = adsk.core.Point3D.create(
            float(args["origin"]["x"]) + args["width"], 
            float(args["origin"]["y"]) + args["height"], 
            0
        )
        
        # Draw the rectangle using two corner points
        lines = target_sketch.sketchCurves.sketchLines
        rectangle = lines.addTwoPointRectangle(origin_pt, opposite_pt)
        
        # The rectangle returns a collection of 4 lines, we'll return the index of the first line
        # Match monolithic format exactly
        result = {
            "sketch": args["sketch"],
            "entity": {
                "type": "rectangle",
                "index": lines.count - 4  # Rectangle adds 4 lines, so index is current length - 4
            }
        }
        
        return result


class CreateSketchFromFaceHandler(BaseHandler):
    """Handler for create_sketch_from_face action"""
    
    def validate(self, args: dict) -> dict:
        """Validate create sketch from face arguments"""
        self.validators.validate_required_fields(args, ["faceRef", "name"])
        
        face_ref = args["faceRef"]
        name = self.validators.validate_non_empty_string(args["name"], "name")
        
        if not isinstance(face_ref, dict):
            raise ValidationError("faceRef must be an object")
        
        # Check for name collision (determinism requirement)
        self.validators.check_sketch_name_collision(name, self.context.root_component)
        
        return {
            "faceRef": face_ref,
            "name": name
        }
    
    def execute(self, args: dict) -> dict:
        """Execute create sketch from face action"""
        root_comp = self.context.root_component
        
        # Resolve face reference
        face = self.resolver.resolve_face_ref(args["faceRef"])
        
        # Ensure face is planar
        if not hasattr(face, 'geometry') or not hasattr(face.geometry, 'normal'):
            raise ValidationError("Target face must be planar")
        
        # Create sketch on face
        sketch = root_comp.sketches.add(face)
        sketch.name = args["name"]
        
        return {"sketchName": sketch.name}


class ProjectEdgesHandler(BaseHandler):
    """Handler for project_edges action"""
    
    def validate(self, args: dict) -> dict:
        """Validate project edges arguments"""
        self.validators.validate_required_fields(args, ["sketch"])
        
        sketch_name = self.validators.validate_non_empty_string(args["sketch"], "sketch")
        face_ref = args.get("faceRef")
        edge_refs = args.get("edgeRefs")
        
        if face_ref is None and edge_refs is None:
            raise ValidationError("Provide either faceRef or edgeRefs")
        
        if edge_refs is not None:
            if not isinstance(edge_refs, list) or not edge_refs:
                raise ValidationError("edgeRefs must be a non-empty array")
        
        return {
            "sketch": sketch_name,
            "faceRef": face_ref,
            "edgeRefs": edge_refs
        }
    
    def execute(self, args: dict) -> dict:
        """Execute project edges action"""
        # Find sketch
        target_sketch = self.resolver.resolve_sketch(args["sketch"])
        
        projected_count = 0
        oc = adsk.core.ObjectCollection.create()
        
        if args["faceRef"] is not None:
            face = self.resolver.resolve_face_ref(args["faceRef"])
            # Project all edges of the face
            for i in range(face.edges.count):
                oc.add(face.edges.item(i))
        elif args["edgeRefs"] is not None:
            edge_refs = args["edgeRefs"]
            for er in edge_refs:
                if not isinstance(er, dict):
                    raise ValidationError("edgeRef must be an object")
                comp = er.get("component")
                body = er.get("body") 
                idx = er.get("edgeIndex")
                
                if comp != self.context.root_component.name:
                    raise ValidationError("Only edges in the root component are supported in v0")
                
                b = self.resolver.resolve_body_ref({"component": comp, "body": body})
                try:
                    eidx = int(idx)
                    if eidx < 0 or eidx >= b.edges.count:
                        raise ValidationError(f"edgeIndex {eidx} out of range (0-{b.edges.count-1})")
                except (TypeError, ValueError):
                    raise ValidationError("edgeIndex must be a non-negative integer")
                oc.add(b.edges.item(eidx))
        
        if oc.count > 0:
            res = target_sketch.project(oc)
            # res may be a collection; conservatively report the number of projected inputs
            projected_count = oc.count
        else:
            projected_count = 0
        
        return {"projectedCount": projected_count}


class SetIsConstructionHandler(BaseHandler):
    """Handler for set_is_construction action"""
    
    def validate(self, args: dict) -> dict:
        """Validate set is construction arguments"""
        self.validators.validate_required_fields(args, ["sketch", "entityRef", "value"])
        
        sketch_name = self.validators.validate_non_empty_string(args["sketch"], "sketch")
        entity_ref = args["entityRef"]
        value = args["value"]
        
        if not isinstance(entity_ref, dict):
            raise ValidationError("entityRef must be an object")
        if not isinstance(value, bool):
            raise ValidationError("value must be a boolean")
        
        ent_type = entity_ref.get("type")
        ent_index = entity_ref.get("index")
        if ent_type != "line":
            raise ValidationError("Only line entity type is supported in v0")
        
        try:
            idx = int(ent_index)
            if idx < 0:
                raise ValueError()
        except Exception:
            raise ValidationError("entityRef.index must be a non-negative integer")
        
        return {
            "sketch": sketch_name,
            "entityRef": entity_ref,
            "value": value
        }
    
    def execute(self, args: dict) -> dict:
        """Execute set is construction action"""
        # Find sketch
        target_sketch = self.resolver.resolve_sketch(args["sketch"])
        
        idx = int(args["entityRef"]["index"])
        lines = target_sketch.sketchCurves.sketchLines
        if idx >= lines.count:
            raise ValidationError(f"Line index {idx} out of range (0-{lines.count-1})")
        
        line = lines.item(idx)
        line.isConstruction = args["value"]
        
        return {"updated": True}
