"""
Context-related handlers - provides agents with awareness of current Fusion state
"""
import adsk.core
import adsk.fusion
from handlers.base import BaseHandler
from core.errors import FusionAPIError, ValidationError


class GetEditContextHandler(BaseHandler):
    """Handler for get_edit_context action - lightweight summary of current state"""

    def validate(self, args: dict) -> dict:
        """No arguments needed"""
        return args

    def execute(self, args: dict) -> dict:
        """Get current editing context"""
        try:
            app = self.context.app
            ui = app.userInterface

            result = {
                "document": None,
                "activeComponent": None,
                "editMode": None,
                "selectionCount": 0
            }

            # Document info
            active_doc = app.activeDocument
            if active_doc:
                design = adsk.fusion.Design.cast(app.activeProduct)
                result["document"] = {
                    "name": active_doc.name,
                    "designType": "parametric" if (design and design.designType == adsk.fusion.DesignTypes.ParametricDesignType) else "direct",
                    "hasUnsavedChanges": getattr(active_doc, 'isModified', False)
                }

            # Active component
            if design:
                active_comp = design.activeComponent
                if active_comp:
                    result["activeComponent"] = {
                        "name": active_comp.name,
                        "isRoot": active_comp == design.rootComponent
                    }

            # Edit mode detection
            edit_obj = app.activeEditObject
            if edit_obj:
                edit_mode = self._detect_edit_mode(edit_obj)
                result["editMode"] = edit_mode
            else:
                result["editMode"] = {"type": "model"}

            # Selection count
            if ui and ui.activeSelections:
                result["selectionCount"] = ui.activeSelections.count

            return result

        except Exception as e:
            raise FusionAPIError(f"Failed to get edit context: {str(e)}")

    def _detect_edit_mode(self, edit_obj) -> dict:
        """Detect what type of object is being edited"""
        # Check if it's a sketch
        sketch = adsk.fusion.Sketch.cast(edit_obj)
        if sketch:
            plane_name = "custom"
            try:
                # Try to determine sketch plane
                ref_plane = sketch.referencePlane
                if ref_plane:
                    if hasattr(ref_plane, 'name'):
                        plane_name = ref_plane.name
            except:
                pass

            return {
                "type": "sketch",
                "target": sketch.name,
                "sketchPlane": plane_name
            }

        # Check if it's a component
        component = adsk.fusion.Component.cast(edit_obj)
        if component:
            return {
                "type": "component",
                "target": component.name
            }

        # Check for form (T-spline) editing
        form = adsk.fusion.FormFeature.cast(edit_obj)
        if form:
            return {
                "type": "form",
                "target": form.name if hasattr(form, 'name') else "Form"
            }

        # Default to model editing
        return {"type": "model"}


class GetSketchStateHandler(BaseHandler):
    """Handler for get_sketch_state action - detailed sketch info when in sketch edit mode"""

    def validate(self, args: dict) -> dict:
        """Validate arguments - optional sketch name"""
        sketch_name = args.get("sketch")
        if sketch_name is not None:
            sketch_name = self.validators.validate_non_empty_string(sketch_name, "sketch")
        return {"sketch": sketch_name}

    def execute(self, args: dict) -> dict:
        """Get detailed sketch state"""
        try:
            app = self.context.app
            sketch_name = args.get("sketch")

            target_sketch = None

            if sketch_name:
                # Find sketch by name
                target_sketch = self.resolver.resolve_sketch(sketch_name)
            else:
                # Try to get active sketch from edit object
                edit_obj = app.activeEditObject
                if edit_obj:
                    target_sketch = adsk.fusion.Sketch.cast(edit_obj)

                if not target_sketch:
                    raise ValidationError("No sketch specified and not currently editing a sketch")

            # Build sketch state
            result = {
                "sketchName": target_sketch.name,
                "plane": self._get_plane_name(target_sketch),
                "isFullyConstrained": False,  # Will be updated below
                "constraintHealth": {
                    "totalDOF": 0,
                    "underconstrainedEntities": 0
                },
                "profiles": {
                    "count": 0,
                    "closed": 0,
                    "open": 0
                },
                "entities": {
                    "lines": 0,
                    "circles": 0,
                    "arcs": 0,
                    "points": 0,
                    "construction": 0
                },
                "constraints": {}
            }

            # Count profiles
            try:
                profiles = target_sketch.profiles
                result["profiles"]["count"] = profiles.count
                # All profiles in Fusion are closed by definition
                result["profiles"]["closed"] = profiles.count
            except:
                pass

            # Count entities by type
            try:
                curves = target_sketch.sketchCurves
                construction_count = 0

                # Lines
                lines = curves.sketchLines
                result["entities"]["lines"] = lines.count
                for i in range(lines.count):
                    if lines.item(i).isConstruction:
                        construction_count += 1

                # Circles
                circles = curves.sketchCircles
                result["entities"]["circles"] = circles.count
                for i in range(circles.count):
                    if circles.item(i).isConstruction:
                        construction_count += 1

                # Arcs
                arcs = curves.sketchArcs
                result["entities"]["arcs"] = arcs.count
                for i in range(arcs.count):
                    if arcs.item(i).isConstruction:
                        construction_count += 1

                result["entities"]["construction"] = construction_count

                # Points
                points = target_sketch.sketchPoints
                result["entities"]["points"] = points.count

            except Exception as e:
                print(f"[CONTEXT] Error counting entities: {e}")

            # Count constraints by type
            try:
                constraints = target_sketch.geometricConstraints
                constraint_counts = {}

                for i in range(constraints.count):
                    constraint = constraints.item(i)
                    constraint_type = type(constraint).__name__
                    # Simplify constraint type names
                    simple_type = constraint_type.replace("Sketch", "").replace("Constraint", "").lower()
                    constraint_counts[simple_type] = constraint_counts.get(simple_type, 0) + 1

                result["constraints"] = constraint_counts

            except Exception as e:
                print(f"[CONTEXT] Error counting constraints: {e}")

            # Count dimensions
            try:
                dims = target_sketch.sketchDimensions
                result["constraints"]["dimensions"] = dims.count
            except:
                pass

            # Check if fully constrained (approximation - check if any points are underconstrained)
            # Fusion doesn't directly expose DOF, so we check sketch.isFullyConstrained if available
            try:
                # This property may not exist in all Fusion versions
                if hasattr(target_sketch, 'isFullyConstrained'):
                    result["isFullyConstrained"] = target_sketch.isFullyConstrained
            except:
                pass

            return result

        except ValidationError:
            raise
        except Exception as e:
            raise FusionAPIError(f"Failed to get sketch state: {str(e)}")

    def _get_plane_name(self, sketch) -> str:
        """Get the name of the sketch plane"""
        try:
            ref_plane = sketch.referencePlane
            if ref_plane:
                # Check if it's a construction plane
                if hasattr(ref_plane, 'name'):
                    return ref_plane.name

                # Check if it's an origin plane
                plane = adsk.fusion.ConstructionPlane.cast(ref_plane)
                if plane:
                    return plane.name

            return "custom"
        except:
            return "unknown"


class GetCameraStateHandler(BaseHandler):
    """Handler for get_camera_state action - current view orientation"""

    def validate(self, args: dict) -> dict:
        """No arguments needed"""
        return args

    def execute(self, args: dict) -> dict:
        """Get current camera/view state"""
        try:
            app = self.context.app
            viewport = app.activeViewport

            if not viewport:
                raise FusionAPIError("No active viewport")

            camera = viewport.camera

            result = {
                "orientation": self._detect_orientation(camera),
                "isFitAll": camera.isFitView if hasattr(camera, 'isFitView') else False,
                "viewExtents": camera.viewExtents if hasattr(camera, 'viewExtents') else None
            }

            # Eye position
            if camera.eye:
                result["eye"] = {
                    "x": camera.eye.x,
                    "y": camera.eye.y,
                    "z": camera.eye.z
                }

            # Target position
            if camera.target:
                result["target"] = {
                    "x": camera.target.x,
                    "y": camera.target.y,
                    "z": camera.target.z
                }

            # Up vector
            if camera.upVector:
                result["upVector"] = {
                    "x": camera.upVector.x,
                    "y": camera.upVector.y,
                    "z": camera.upVector.z
                }

            return result

        except Exception as e:
            raise FusionAPIError(f"Failed to get camera state: {str(e)}")

    def _detect_orientation(self, camera) -> str:
        """Detect standard view orientation from camera position"""
        try:
            if not camera.eye or not camera.target:
                return "custom"

            # Get view direction (normalized)
            dx = camera.eye.x - camera.target.x
            dy = camera.eye.y - camera.target.y
            dz = camera.eye.z - camera.target.z

            length = (dx*dx + dy*dy + dz*dz) ** 0.5
            if length < 0.001:
                return "custom"

            dx, dy, dz = dx/length, dy/length, dz/length

            # Check for standard views (with tolerance)
            tolerance = 0.1

            if abs(dz - 1) < tolerance and abs(dx) < tolerance and abs(dy) < tolerance:
                return "top"
            if abs(dz + 1) < tolerance and abs(dx) < tolerance and abs(dy) < tolerance:
                return "bottom"
            if abs(dy - 1) < tolerance and abs(dx) < tolerance and abs(dz) < tolerance:
                return "front"
            if abs(dy + 1) < tolerance and abs(dx) < tolerance and abs(dz) < tolerance:
                return "back"
            if abs(dx - 1) < tolerance and abs(dy) < tolerance and abs(dz) < tolerance:
                return "right"
            if abs(dx + 1) < tolerance and abs(dy) < tolerance and abs(dz) < tolerance:
                return "left"

            # Check for isometric-ish views
            if abs(dx) > 0.3 and abs(dy) > 0.3 and abs(dz) > 0.3:
                return "iso"

            return "custom"

        except:
            return "unknown"
