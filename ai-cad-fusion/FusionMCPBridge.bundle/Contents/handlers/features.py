"""
3D Feature-related handlers
"""
import adsk.core
import adsk.fusion
from handlers.base import BaseHandler
from core.errors import ValidationError, FusionAPIError


class ExtrudeProfileHandler(BaseHandler):
    """Handler for extrude_profile action"""
    
    def validate(self, args: dict) -> dict:
        """Validate extrude profile arguments"""
        self.validators.validate_required_fields(args, ["sketch", "profile_index", "distance"])
        
        # Validate sketch name
        sketch_name = self.validators.validate_non_empty_string(args["sketch"], "sketch")
        
        # Validate profile index
        profile_index = self.validators.validate_non_negative_int(args["profile_index"], "profile_index")
        
        # Validate distance
        distance = self.validators.validate_positive_number(args["distance"], "distance")
        
        # Validate operation (optional)
        operation = args.get("operation", "new_body")
        self.validators.validate_operation(operation)
        
        # Validate direction (optional)
        direction = args.get("direction", "positive")
        self.validators.validate_direction(direction)
        
        return {
            "sketch": sketch_name,
            "profile_index": profile_index,
            "distance": distance,
            "operation": operation,
            "direction": direction
        }
    
    def execute(self, args: dict) -> dict:
        """Execute extrude profile action"""
        root_comp = self.context.root_component
        
        # Find the sketch by name
        target_sketch = self.resolver.resolve_sketch(args["sketch"])
        
        # Get all profiles from the sketch
        profiles = target_sketch.profiles
        if profiles.count == 0:
            raise ValidationError(f"Sketch '{args['sketch']}' has no profiles to extrude")
        
        # Validate profile index exists
        if args["profile_index"] >= profiles.count:
            raise ValidationError(f"Profile index {args['profile_index']} not found. Sketch has {profiles.count} profiles (0-{profiles.count-1})")
        
        # Get the specific profile
        profile = profiles.item(args["profile_index"])
        
        # Create extrude input
        extrudes = root_comp.features.extrudeFeatures
        extrude_input = extrudes.createInput(profile, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        
        # Map operation string to Fusion operation
        operation_mapping = {
            "new_body": adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
            "join": adsk.fusion.FeatureOperations.JoinFeatureOperation,
            "cut": adsk.fusion.FeatureOperations.CutFeatureOperation,
            "intersect": adsk.fusion.FeatureOperations.IntersectFeatureOperation
        }
        extrude_input.operation = operation_mapping[args["operation"]]
        
        # Set distance with direction
        distance_input = adsk.core.ValueInput.createByReal(args["distance"])
        
        if args["direction"] == "positive":
            extrude_input.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(distance_input), adsk.fusion.ExtentDirections.PositiveExtentDirection)
        elif args["direction"] == "negative":
            extrude_input.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(distance_input), adsk.fusion.ExtentDirections.NegativeExtentDirection)
        elif args["direction"] == "symmetric":
            # For symmetric, use full distance (Fusion splits equally)
            extrude_input.setSymmetricExtent(distance_input, True)
        
        # Create the extrusion
        extrude_feature = extrudes.add(extrude_input)
        
        # Get created bodies from the feature
        created_bodies = []
        if extrude_feature.bodies:
            for i in range(extrude_feature.bodies.count):
                body = extrude_feature.bodies.item(i)
                created_bodies.append({
                    "name": body.name if hasattr(body, 'name') else None,
                    "type": body.bodyType.name if hasattr(body, 'bodyType') else None
                })
        
        # Return feature and body information
        result = {
            "feature": {
                "type": "extrude",
                "name": extrude_feature.name if hasattr(extrude_feature, 'name') else None
            }
        }
        
        # Add body info if any bodies were created (legacy shape)
        if created_bodies:
            result["bodies"] = created_bodies
        
        # Also provide createdBodies in bodyRef form per API_BRIDGE.md
        try:
            if created_bodies:
                created_refs = []
                for body in extrude_feature.bodies:
                    created_refs.append({
                        "component": root_comp.name,
                        "body": body.name if hasattr(body, 'name') else None
                    })
                result["createdBodies"] = created_refs
        except Exception:
            pass
        
        return result


class CombineBodiesHandler(BaseHandler):
    """Handler for combine_bodies action"""
    
    def validate(self, args: dict) -> dict:
        """Validate combine bodies arguments"""
        self.validators.validate_required_fields(args, ["targets", "tools"])
        
        targets = args["targets"]
        tools = args["tools"]
        operation = args.get("operation", "join")
        
        # Validate operation
        if operation not in ["join", "cut", "intersect"]:
            raise ValidationError("operation must be one of: join, cut, intersect")
        
        # Validate targets
        if not isinstance(targets, list) or not targets:
            raise ValidationError("targets must be a non-empty array of bodyRef")
        
        # Validate tools
        if not isinstance(tools, list) or not tools:
            raise ValidationError("tools must be a non-empty array of bodyRef")
        
        # v0: require exactly one target body
        if len(targets) != 1:
            raise ValidationError("targets must contain exactly one bodyRef in v0")
        
        # v0: require exactly one tool body
        if len(tools) != 1:
            raise ValidationError("tools must contain exactly one bodyRef in v0")
        
        return {
            "targets": targets,
            "tools": tools,
            "operation": operation
        }
    
    def execute(self, args: dict) -> dict:
        """Execute combine bodies action"""
        root_comp = self.context.root_component
        
        # Resolve target and tool bodies
        target_body = self.resolver.resolve_body_ref(args["targets"][0])
        tool_body = self.resolver.resolve_body_ref(args["tools"][0])
        
        # Create object collections
        target_collection = adsk.core.ObjectCollection.create()
        target_collection.add(target_body)
        tool_collection = adsk.core.ObjectCollection.create()
        tool_collection.add(tool_body)
        
        # Get combine features
        combine_feats = root_comp.features.combineFeatures
        
        # Map operation string to Fusion operation
        input_op = {
            "join": adsk.fusion.FeatureOperations.JoinFeatureOperation,
            "cut": adsk.fusion.FeatureOperations.CutFeatureOperation,
            "intersect": adsk.fusion.FeatureOperations.IntersectFeatureOperation,
        }[args["operation"]]
        
        # Some API bindings differ; try common permutations like monolithic implementation
        combine_input = None
        last_err = None
        for sig in ("targetsOC_toolsBody", "targetBody_toolsOC", "targetsOC_toolsOC"):
            try:
                if sig == "targetsOC_toolsBody":
                    combine_input = combine_feats.createInput(target_collection, tool_body)
                elif sig == "targetBody_toolsOC":
                    combine_input = combine_feats.createInput(target_body, tool_collection)
                else:
                    combine_input = combine_feats.createInput(target_collection, tool_collection)
                print(f"[COMBINE] Success with signature: {sig}")
                break
            except Exception as e:
                print(f"[COMBINE] Failed signature {sig}: {str(e)}")
                last_err = e
                continue
        
        if combine_input is None:
            raise FusionAPIError(str(last_err) if last_err else "Failed to create combine input")
        
        combine_input.operation = input_op
        # Keep tools: false for destructive by default; users can duplicate bodies if needed
        combine_input.isKeepToolBodies = False
        
        # Execute the combine operation
        combine_feats.add(combine_input)
        
        return {"success": True}


class RevolveProfileHandler(BaseHandler):
    """Handler for revolve_profile action"""
    
    def validate(self, args: dict) -> dict:
        """Validate revolve profile arguments"""
        self.validators.validate_required_fields(args, ["sketch", "profile_index", "axisRef", "angle"])
        
        sketch_name = self.validators.validate_non_empty_string(args["sketch"], "sketch")
        profile_index = self.validators.validate_non_negative_int(args["profile_index"], "profile_index")
        axis_ref = args["axisRef"]
        angle = self.validators.validate_positive_number(args["angle"], "angle")
        operation = args.get("operation", "new_body")
        
        # Validate operation
        self.validators.validate_operation(operation)
        
        # Validate axisRef
        if not isinstance(axis_ref, dict):
            raise ValidationError("axisRef must be an object")
        
        axis_type = axis_ref.get("type")
        if axis_type != "origin_axis":
            raise ValidationError("axisRef.type must be 'origin_axis' in v0")
        
        axis_name = str(axis_ref.get("axis", "")).upper()
        if axis_name not in ("X", "Y", "Z"):
            raise ValidationError("axisRef.axis must be one of: X, Y, Z")
        
        return {
            "sketch": sketch_name,
            "profile_index": profile_index,
            "axisRef": axis_ref,
            "angle": angle,
            "operation": operation
        }
    
    def execute(self, args: dict) -> dict:
        """Execute revolve profile action"""
        root_comp = self.context.root_component
        
        # Find sketch
        target_sketch = self.resolver.resolve_sketch(args["sketch"])
        
        # Get profile
        profiles = target_sketch.profiles
        if profiles.count == 0:
            raise ValidationError(f"Sketch '{args['sketch']}' has no profiles to revolve")
        if args["profile_index"] >= profiles.count:
            raise ValidationError(f"Profile index {args['profile_index']} not found. Sketch has {profiles.count} profiles (0-{profiles.count-1})")
        
        profile = profiles.item(args["profile_index"])
        
        # Resolve axis - v0 supports origin axis X/Y/Z in root component
        axis_name = str(args["axisRef"].get("axis", "")).upper()
        axis_obj = None
        try:
            # Use the root component's origin construction axes
            if axis_name == "X":
                axis_obj = root_comp.xConstructionAxis
            elif axis_name == "Y":
                axis_obj = root_comp.yConstructionAxis
            else:
                axis_obj = root_comp.zConstructionAxis
        except Exception as e:
            raise FusionAPIError(f"Failed to access origin axis {axis_name}: {str(e)}")
        
        if axis_obj is None:
            raise FusionAPIError(f"Origin axis {axis_name} unavailable")
        
        # Build revolve input
        rev_feats = root_comp.features.revolveFeatures
        op_map = {
            "new_body": adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
            "join": adsk.fusion.FeatureOperations.JoinFeatureOperation,
            "cut": adsk.fusion.FeatureOperations.CutFeatureOperation,
            "intersect": adsk.fusion.FeatureOperations.IntersectFeatureOperation,
        }
        
        angle_input = adsk.core.ValueInput.createByString(f"{args['angle']} deg")
        # Use 3-arg createInput(profile, axis, operation) then specify angle extent
        rev_input = rev_feats.createInput(profile, axis_obj, op_map[args["operation"]])
        try:
            rev_input.setAngleExtent(False, angle_input)
        except Exception as e:
            raise FusionAPIError(f"Failed to set revolve angle: {str(e)}")
        
        # Execute the revolve operation
        try:
            rev_feature = rev_feats.add(rev_input)
        except Exception as e:
            error_msg = str(e).lower()
            if "tangent" in error_msg and "axis" in error_msg:
                raise ValidationError("Profile cannot be tangent to or intersect the axis of revolution. Ensure the profile is positioned away from the axis.")
            else:
                raise FusionAPIError(f"Failed to revolve profile: {str(e)}")
        
        # Prepare result - match monolithic format exactly
        result = {
            "feature": {
                "type": "revolve",
                "name": getattr(rev_feature, 'name', None)
            }
        }
        
        # Add createdBodies in bodyRef form per API_BRIDGE.md
        try:
            if rev_feature.bodies and rev_feature.bodies.count > 0:
                created_refs = []
                for i in range(rev_feature.bodies.count):
                    b = rev_feature.bodies.item(i)
                    created_refs.append({
                        "component": root_comp.name,
                        "body": getattr(b, 'name', None)
                    })
                result["createdBodies"] = created_refs
        except Exception:
            pass

        return result


class RotateBodyHandler(BaseHandler):
    """Handler for rotate_body action"""

    def validate(self, args: dict) -> dict:
        """Validate rotate body arguments"""
        self.validators.validate_required_fields(args, ["bodyRef", "pivot", "angle"])

        body_ref = args["bodyRef"]
        pivot = args["pivot"]
        angle = args["angle"]
        copy = args.get("copy", False)

        # Validate bodyRef
        if not isinstance(body_ref, dict):
            raise ValidationError("bodyRef must be an object")
        if "component" not in body_ref or "body" not in body_ref:
            raise ValidationError("bodyRef must contain 'component' and 'body' fields")

        # Validate pivot
        if not isinstance(pivot, dict):
            raise ValidationError("pivot must be an object")

        pivot_type = pivot.get("type")
        if pivot_type not in ("origin_axis", "edge_axis"):
            raise ValidationError("pivot.type must be 'origin_axis' or 'edge_axis'")

        if pivot_type == "origin_axis":
            axis = str(pivot.get("axis", "")).upper()
            if axis not in ("X", "Y", "Z"):
                raise ValidationError("pivot.axis must be one of: X, Y, Z")
        elif pivot_type == "edge_axis":
            edge_ref = pivot.get("edgeRef")
            if not edge_ref or not isinstance(edge_ref, dict):
                raise ValidationError("pivot.edgeRef is required when type is 'edge_axis'")
            if "component" not in edge_ref or "body" not in edge_ref or "edgeIndex" not in edge_ref:
                raise ValidationError("edgeRef must contain 'component', 'body', and 'edgeIndex' fields")

        # Validate angle (can be positive or negative)
        if not isinstance(angle, (int, float)):
            raise ValidationError("angle must be a number")

        # Validate copy
        if not isinstance(copy, bool):
            raise ValidationError("copy must be a boolean")

        return {
            "bodyRef": body_ref,
            "pivot": pivot,
            "angle": angle,
            "copy": copy
        }

    def execute(self, args: dict) -> dict:
        """Execute rotate body action"""
        import math

        root_comp = self.context.root_component

        # Resolve the body
        body = self.resolver.resolve_body_ref(args["bodyRef"])

        # Get pivot information
        pivot = args["pivot"]
        pivot_type = pivot["type"]
        angle_deg = args["angle"]
        angle_rad = math.radians(angle_deg)
        copy_mode = args["copy"]

        # Create the rotation transform
        transform = adsk.core.Matrix3D.create()

        if pivot_type == "origin_axis":
            axis = pivot["axis"].upper()
            origin = adsk.core.Point3D.create(0, 0, 0)

            if axis == "X":
                axis_vector = adsk.core.Vector3D.create(1, 0, 0)
            elif axis == "Y":
                axis_vector = adsk.core.Vector3D.create(0, 1, 0)
            else:  # Z
                axis_vector = adsk.core.Vector3D.create(0, 0, 1)

            transform.setToRotation(angle_rad, axis_vector, origin)

        elif pivot_type == "edge_axis":
            # Resolve the edge for pivot
            edge_ref = pivot["edgeRef"]
            edge = self.resolver.resolve_edge_ref(edge_ref)

            # Get the edge geometry to determine axis and point
            geom = edge.geometry
            if hasattr(geom, 'startPoint') and hasattr(geom, 'endPoint'):
                # Line edge - use direction as axis
                start_pt = geom.startPoint
                end_pt = geom.endPoint
                axis_vector = adsk.core.Vector3D.create(
                    end_pt.x - start_pt.x,
                    end_pt.y - start_pt.y,
                    end_pt.z - start_pt.z
                )
                axis_vector.normalize()
                origin = start_pt
            else:
                raise ValidationError("Edge pivot currently only supports linear edges")

            transform.setToRotation(angle_rad, axis_vector, origin)

        # Create object collection for the body
        body_collection = adsk.core.ObjectCollection.create()
        body_collection.add(body)

        if copy_mode:
            # Use copy feature to create a rotated copy
            copy_feats = root_comp.features.copyPasteBodies
            # copyBodies returns new bodies
            try:
                new_bodies = copy_feats.add(body_collection)
                if new_bodies.count > 0:
                    new_body = new_bodies.item(0)
                    # Now move the copied body
                    move_feats = root_comp.features.moveFeatures
                    new_body_collection = adsk.core.ObjectCollection.create()
                    new_body_collection.add(new_body)
                    move_input = move_feats.createInput(new_body_collection, transform)
                    move_feats.add(move_input)

                    return {
                        "success": True,
                        "createdBody": {
                            "component": root_comp.name,
                            "body": new_body.name
                        }
                    }
                else:
                    raise FusionAPIError("Copy operation did not create any bodies")
            except Exception as e:
                raise FusionAPIError(f"Failed to copy and rotate body: {str(e)}")
        else:
            # Use move feature to transform in place
            move_feats = root_comp.features.moveFeatures
            try:
                move_input = move_feats.createInput(body_collection, transform)
                move_feats.add(move_input)

                return {
                    "success": True,
                    "transformedBody": {
                        "component": root_comp.name,
                        "body": body.name
                    }
                }
            except Exception as e:
                raise FusionAPIError(f"Failed to rotate body: {str(e)}")
