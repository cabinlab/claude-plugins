"""
Selection-related handlers - provides agents with awareness of user selections
"""
import adsk.core
import adsk.fusion
from handlers.base import BaseHandler
from core.errors import FusionAPIError, ValidationError


class GetSelectionHandler(BaseHandler):
    """Handler for get_selection action - returns info about currently selected entities"""

    MAX_ENTITIES = 20  # Cap to avoid context explosion

    def validate(self, args: dict) -> dict:
        """No arguments needed"""
        return args

    def execute(self, args: dict) -> dict:
        """Get current selection state"""
        try:
            app = self.context.app
            ui = app.userInterface

            if not ui or not ui.activeSelections:
                return {
                    "count": 0,
                    "entities": [],
                    "truncated": False
                }

            selections = ui.activeSelections
            total_count = selections.count

            entities = []
            for i in range(min(total_count, self.MAX_ENTITIES)):
                sel = selections.item(i)
                entity = sel.entity

                entity_info = self._describe_entity(entity, i)
                if entity_info:
                    entities.append(entity_info)

            return {
                "count": total_count,
                "entities": entities,
                "truncated": total_count > self.MAX_ENTITIES
            }

        except Exception as e:
            raise FusionAPIError(f"Failed to get selection: {str(e)}")

    def _describe_entity(self, entity, index: int) -> dict:
        """Describe a selected entity with enough info to reference it later"""
        try:
            # Try to cast to various types and extract relevant info

            # BRep Face
            face = adsk.fusion.BRepFace.cast(entity)
            if face:
                return self._describe_face(face, index)

            # BRep Edge
            edge = adsk.fusion.BRepEdge.cast(entity)
            if edge:
                return self._describe_edge(edge, index)

            # BRep Vertex
            vertex = adsk.fusion.BRepVertex.cast(entity)
            if vertex:
                return self._describe_vertex(vertex, index)

            # BRep Body
            body = adsk.fusion.BRepBody.cast(entity)
            if body:
                return self._describe_body(body, index)

            # Component
            component = adsk.fusion.Component.cast(entity)
            if component:
                return {
                    "type": "component",
                    "index": index,
                    "name": component.name
                }

            # Occurrence
            occurrence = adsk.fusion.Occurrence.cast(entity)
            if occurrence:
                return {
                    "type": "occurrence",
                    "index": index,
                    "name": occurrence.name,
                    "componentName": occurrence.component.name if occurrence.component else None
                }

            # Sketch entities
            sketch_entity = self._describe_sketch_entity(entity, index)
            if sketch_entity:
                return sketch_entity

            # Sketch itself
            sketch = adsk.fusion.Sketch.cast(entity)
            if sketch:
                return {
                    "type": "sketch",
                    "index": index,
                    "name": sketch.name
                }

            # Construction plane
            plane = adsk.fusion.ConstructionPlane.cast(entity)
            if plane:
                return {
                    "type": "constructionPlane",
                    "index": index,
                    "name": plane.name if hasattr(plane, 'name') else "ConstructionPlane"
                }

            # Unknown type
            return {
                "type": "unknown",
                "index": index,
                "objectType": type(entity).__name__
            }

        except Exception as e:
            return {
                "type": "error",
                "index": index,
                "error": str(e)
            }

    def _describe_face(self, face: adsk.fusion.BRepFace, index: int) -> dict:
        """Describe a BRep face"""
        result = {
            "type": "face",
            "index": index
        }

        # Get parent body info
        try:
            body = face.body
            if body:
                result["bodyName"] = body.name

                # Get component
                comp = body.parentComponent
                if comp:
                    result["componentName"] = comp.name

                # Find face index within body
                for i in range(body.faces.count):
                    if body.faces.item(i) == face:
                        result["faceIndex"] = i
                        break
        except:
            pass

        # Get surface type
        try:
            geometry = face.geometry
            surface_type = type(geometry).__name__
            result["surfaceType"] = surface_type.replace("Surface", "").lower()
        except:
            result["surfaceType"] = "unknown"

        # Get area
        try:
            result["area_cm2"] = face.area
        except:
            pass

        return result

    def _describe_edge(self, edge: adsk.fusion.BRepEdge, index: int) -> dict:
        """Describe a BRep edge"""
        result = {
            "type": "edge",
            "index": index
        }

        # Get parent body info
        try:
            body = edge.body
            if body:
                result["bodyName"] = body.name

                comp = body.parentComponent
                if comp:
                    result["componentName"] = comp.name

                # Find edge index within body
                for i in range(body.edges.count):
                    if body.edges.item(i) == edge:
                        result["edgeIndex"] = i
                        break
        except:
            pass

        # Get curve type
        try:
            geometry = edge.geometry
            curve_type = type(geometry).__name__
            result["curveType"] = curve_type.replace("Curve3D", "").replace("3D", "").lower()
        except:
            result["curveType"] = "unknown"

        # Get length
        try:
            result["length_cm"] = edge.length
        except:
            pass

        return result

    def _describe_vertex(self, vertex: adsk.fusion.BRepVertex, index: int) -> dict:
        """Describe a BRep vertex"""
        result = {
            "type": "vertex",
            "index": index
        }

        # Get parent body info
        try:
            # Vertices don't have direct body reference, get from an edge
            edges = vertex.edges
            if edges.count > 0:
                edge = edges.item(0)
                body = edge.body
                if body:
                    result["bodyName"] = body.name

                    comp = body.parentComponent
                    if comp:
                        result["componentName"] = comp.name
        except:
            pass

        # Get position
        try:
            point = vertex.geometry
            result["position"] = {
                "x": point.x,
                "y": point.y,
                "z": point.z
            }
        except:
            pass

        return result

    def _describe_body(self, body: adsk.fusion.BRepBody, index: int) -> dict:
        """Describe a BRep body"""
        result = {
            "type": "body",
            "index": index,
            "bodyName": body.name
        }

        # Get component
        try:
            comp = body.parentComponent
            if comp:
                result["componentName"] = comp.name
        except:
            pass

        # Get face/edge counts
        try:
            result["faceCount"] = body.faces.count
            result["edgeCount"] = body.edges.count
        except:
            pass

        # Get volume if available
        try:
            props = body.physicalProperties
            if props:
                result["volume_cm3"] = props.volume
        except:
            pass

        return result

    def _describe_sketch_entity(self, entity, index: int) -> dict:
        """Try to describe as sketch entity"""

        # Sketch line
        line = adsk.fusion.SketchLine.cast(entity)
        if line:
            result = {
                "type": "sketchLine",
                "index": index,
                "isConstruction": line.isConstruction
            }
            try:
                result["sketchName"] = line.parentSketch.name
                result["length_cm"] = line.length

                # Find line index in sketch
                lines = line.parentSketch.sketchCurves.sketchLines
                for i in range(lines.count):
                    if lines.item(i) == line:
                        result["entityIndex"] = i
                        break
            except:
                pass
            return result

        # Sketch circle
        circle = adsk.fusion.SketchCircle.cast(entity)
        if circle:
            result = {
                "type": "sketchCircle",
                "index": index,
                "isConstruction": circle.isConstruction
            }
            try:
                result["sketchName"] = circle.parentSketch.name
                result["radius_cm"] = circle.radius

                circles = circle.parentSketch.sketchCurves.sketchCircles
                for i in range(circles.count):
                    if circles.item(i) == circle:
                        result["entityIndex"] = i
                        break
            except:
                pass
            return result

        # Sketch arc
        arc = adsk.fusion.SketchArc.cast(entity)
        if arc:
            result = {
                "type": "sketchArc",
                "index": index,
                "isConstruction": arc.isConstruction
            }
            try:
                result["sketchName"] = arc.parentSketch.name
                result["radius_cm"] = arc.radius

                arcs = arc.parentSketch.sketchCurves.sketchArcs
                for i in range(arcs.count):
                    if arcs.item(i) == arc:
                        result["entityIndex"] = i
                        break
            except:
                pass
            return result

        # Sketch point
        point = adsk.fusion.SketchPoint.cast(entity)
        if point:
            result = {
                "type": "sketchPoint",
                "index": index
            }
            try:
                result["sketchName"] = point.parentSketch.name
                geo = point.geometry
                result["position"] = {
                    "x": geo.x,
                    "y": geo.y,
                    "z": geo.z
                }

                points = point.parentSketch.sketchPoints
                for i in range(points.count):
                    if points.item(i) == point:
                        result["entityIndex"] = i
                        break
            except:
                pass
            return result

        return None


class HighlightEntitiesHandler(BaseHandler):
    """Handler for highlight_entities action - temporarily highlights geometry"""

    def validate(self, args: dict) -> dict:
        """Validate highlight arguments"""
        refs = args.get("refs", [])
        if not isinstance(refs, list):
            raise ValidationError("refs must be an array")

        if len(refs) == 0:
            raise ValidationError("refs array cannot be empty")

        if len(refs) > 50:
            raise ValidationError("Cannot highlight more than 50 entities at once")

        color = args.get("color", "yellow")
        if color not in ["yellow", "red", "green", "blue", "orange", "cyan", "magenta"]:
            raise ValidationError(f"Invalid color '{color}'. Use: yellow, red, green, blue, orange, cyan, magenta")

        duration_ms = args.get("duration_ms", 3000)
        if not isinstance(duration_ms, (int, float)) or duration_ms < 500 or duration_ms > 10000:
            raise ValidationError("duration_ms must be between 500 and 10000")

        return {
            "refs": refs,
            "color": color,
            "duration_ms": int(duration_ms)
        }

    def execute(self, args: dict) -> dict:
        """Highlight entities in the viewport"""
        try:
            refs = args["refs"]
            color = args["color"]
            # duration_ms = args["duration_ms"]  # Note: Fusion doesn't support timed highlight directly

            app = self.context.app
            ui = app.userInterface
            design = self.context.design

            # Map color names to RGB
            color_map = {
                "yellow": (255, 255, 0),
                "red": (255, 0, 0),
                "green": (0, 255, 0),
                "blue": (0, 0, 255),
                "orange": (255, 165, 0),
                "cyan": (0, 255, 255),
                "magenta": (255, 0, 255)
            }
            rgb = color_map.get(color, (255, 255, 0))

            highlighted_count = 0
            errors = []

            # Create custom graphics group for highlighting
            root_comp = design.rootComponent
            graphics = root_comp.customGraphicsGroups

            # Add to selection instead (more reliable visual feedback)
            # Clear current selection first
            ui.activeSelections.clear()

            for ref in refs:
                try:
                    entity = self._resolve_ref(ref)
                    if entity:
                        # Add to selection for visual feedback
                        ui.activeSelections.add(entity)
                        highlighted_count += 1
                except Exception as e:
                    errors.append(f"Failed to highlight {ref}: {str(e)}")

            result = {
                "highlighted": highlighted_count,
                "color": color
            }

            if errors:
                result["errors"] = errors

            return result

        except Exception as e:
            raise FusionAPIError(f"Failed to highlight entities: {str(e)}")

    def _resolve_ref(self, ref: dict):
        """Resolve an entity reference to a Fusion object"""
        ref_type = ref.get("type")

        if ref_type == "face":
            return self._resolve_face_ref(ref)
        elif ref_type == "edge":
            return self._resolve_edge_ref(ref)
        elif ref_type == "body":
            return self._resolve_body_ref(ref)
        elif ref_type == "component":
            return self._resolve_component_ref(ref)
        else:
            raise ValidationError(f"Unsupported ref type: {ref_type}")

    def _resolve_face_ref(self, ref: dict):
        """Resolve face reference"""
        component_name = ref.get("component") or ref.get("componentName")
        body_name = ref.get("body") or ref.get("bodyName")
        face_index = ref.get("faceIndex")

        if face_index is None:
            raise ValidationError("Face reference requires faceIndex")

        body = self.resolver.resolve_body_ref({
            "component": component_name,
            "body": body_name
        })

        if face_index >= body.faces.count:
            raise ValidationError(f"Face index {face_index} out of range (body has {body.faces.count} faces)")

        return body.faces.item(face_index)

    def _resolve_edge_ref(self, ref: dict):
        """Resolve edge reference"""
        component_name = ref.get("component") or ref.get("componentName")
        body_name = ref.get("body") or ref.get("bodyName")
        edge_index = ref.get("edgeIndex")

        if edge_index is None:
            raise ValidationError("Edge reference requires edgeIndex")

        body = self.resolver.resolve_body_ref({
            "component": component_name,
            "body": body_name
        })

        if edge_index >= body.edges.count:
            raise ValidationError(f"Edge index {edge_index} out of range (body has {body.edges.count} edges)")

        return body.edges.item(edge_index)

    def _resolve_body_ref(self, ref: dict):
        """Resolve body reference"""
        component_name = ref.get("component") or ref.get("componentName")
        body_name = ref.get("body") or ref.get("bodyName")

        return self.resolver.resolve_body_ref({
            "component": component_name,
            "body": body_name
        })

    def _resolve_component_ref(self, ref: dict):
        """Resolve component reference"""
        name = ref.get("name")
        if not name:
            raise ValidationError("Component reference requires name")

        design = self.context.design
        for comp in design.allComponents:
            if comp.name == name:
                return comp

        raise ValidationError(f"Component '{name}' not found")


class ClearSelectionHandler(BaseHandler):
    """Handler for clear_selection action - clears current selection"""

    def validate(self, args: dict) -> dict:
        """No arguments needed"""
        return args

    def execute(self, args: dict) -> dict:
        """Clear the current selection"""
        try:
            app = self.context.app
            ui = app.userInterface

            if ui and ui.activeSelections:
                count = ui.activeSelections.count
                ui.activeSelections.clear()
                return {"cleared": count}

            return {"cleared": 0}

        except Exception as e:
            raise FusionAPIError(f"Failed to clear selection: {str(e)}")
