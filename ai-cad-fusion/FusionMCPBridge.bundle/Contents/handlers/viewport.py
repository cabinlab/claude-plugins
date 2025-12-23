"""
Viewport-related handlers - visual context for agents
"""
import os
import tempfile
import base64
import adsk.core
import adsk.fusion
from handlers.base import BaseHandler
from core.errors import FusionAPIError, ValidationError


class CaptureViewportHandler(BaseHandler):
    """Handler for capture_viewport action - screenshot current view"""

    def validate(self, args: dict) -> dict:
        """Validate capture arguments"""
        width = args.get("width", 1920)
        height = args.get("height", 1080)
        return_base64 = args.get("return_base64", True)
        path = args.get("path")

        if not isinstance(width, int) or width < 100 or width > 4096:
            raise ValidationError("width must be between 100 and 4096")

        if not isinstance(height, int) or height < 100 or height > 4096:
            raise ValidationError("height must be between 100 and 4096")

        if path is not None:
            path = self.validators.validate_non_empty_string(path, "path")
            # Ensure it ends with .png
            if not path.lower().endswith('.png'):
                path = path + '.png'

        return {
            "width": width,
            "height": height,
            "return_base64": return_base64,
            "path": path
        }

    def execute(self, args: dict) -> dict:
        """Capture the current viewport"""
        try:
            width = args["width"]
            height = args["height"]
            return_base64 = args["return_base64"]
            output_path = args.get("path")

            app = self.context.app
            viewport = app.activeViewport

            if not viewport:
                raise FusionAPIError("No active viewport to capture")

            # Generate temp path if not provided
            if not output_path:
                temp_dir = tempfile.gettempdir()
                output_path = os.path.join(temp_dir, f"fusion_viewport_{os.getpid()}.png")

            # Save the viewport image
            success = viewport.saveAsImageFile(output_path, width, height)

            if not success:
                raise FusionAPIError("Failed to save viewport image")

            result = {
                "format": "png",
                "width": width,
                "height": height,
                "path": output_path
            }

            # Read and encode as base64 if requested
            if return_base64:
                try:
                    with open(output_path, "rb") as f:
                        image_data = f.read()
                    result["data"] = base64.b64encode(image_data).decode('utf-8')
                    result["size_bytes"] = len(image_data)
                except Exception as e:
                    result["base64_error"] = str(e)

            return result

        except ValidationError:
            raise
        except Exception as e:
            raise FusionAPIError(f"Failed to capture viewport: {str(e)}")


class SetCameraHandler(BaseHandler):
    """Handler for set_camera action - set view orientation"""

    STANDARD_VIEWS = {
        "top": {"eye": (0, 0, 1), "up": (0, 1, 0)},
        "bottom": {"eye": (0, 0, -1), "up": (0, -1, 0)},
        "front": {"eye": (0, -1, 0), "up": (0, 0, 1)},
        "back": {"eye": (0, 1, 0), "up": (0, 0, 1)},
        "left": {"eye": (-1, 0, 0), "up": (0, 0, 1)},
        "right": {"eye": (1, 0, 0), "up": (0, 0, 1)},
        "iso": {"eye": (1, -1, 1), "up": (0, 0, 1)},
        "iso_back": {"eye": (-1, 1, 1), "up": (0, 0, 1)}
    }

    def validate(self, args: dict) -> dict:
        """Validate camera arguments"""
        orientation = args.get("orientation")
        fit_all = args.get("fit_all", True)

        if orientation is not None:
            if orientation not in self.STANDARD_VIEWS:
                valid = ", ".join(self.STANDARD_VIEWS.keys())
                raise ValidationError(f"Invalid orientation '{orientation}'. Valid: {valid}")

        return {
            "orientation": orientation,
            "fit_all": fit_all
        }

    def execute(self, args: dict) -> dict:
        """Set the camera orientation"""
        try:
            orientation = args.get("orientation")
            fit_all = args["fit_all"]

            app = self.context.app
            viewport = app.activeViewport

            if not viewport:
                raise FusionAPIError("No active viewport")

            camera = viewport.camera

            if orientation:
                view_config = self.STANDARD_VIEWS[orientation]

                # Set camera position (eye, target, up)
                # Get bounding box center as target
                design = self.context.design
                root_comp = design.rootComponent

                # Try to get bounding box for distance calculation
                distance = 50.0  # Default distance in cm
                target = adsk.core.Point3D.create(0, 0, 0)

                try:
                    bbox = root_comp.boundingBox
                    if bbox and bbox.isValid:
                        # Calculate center
                        cx = (bbox.minPoint.x + bbox.maxPoint.x) / 2
                        cy = (bbox.minPoint.y + bbox.maxPoint.y) / 2
                        cz = (bbox.minPoint.z + bbox.maxPoint.z) / 2
                        target = adsk.core.Point3D.create(cx, cy, cz)

                        # Calculate distance based on bbox size
                        dx = bbox.maxPoint.x - bbox.minPoint.x
                        dy = bbox.maxPoint.y - bbox.minPoint.y
                        dz = bbox.maxPoint.z - bbox.minPoint.z
                        max_dim = max(dx, dy, dz)
                        distance = max_dim * 2.5  # Reasonable framing distance
                except:
                    pass

                # Set eye position
                eye_dir = view_config["eye"]
                eye = adsk.core.Point3D.create(
                    target.x + eye_dir[0] * distance,
                    target.y + eye_dir[1] * distance,
                    target.z + eye_dir[2] * distance
                )

                up_dir = view_config["up"]
                up = adsk.core.Vector3D.create(up_dir[0], up_dir[1], up_dir[2])

                camera.eye = eye
                camera.target = target
                camera.upVector = up

            if fit_all:
                camera.isFitView = True

            # Apply camera changes
            viewport.camera = camera

            # Refresh the view
            viewport.refresh()

            return {
                "orientation": orientation or "custom",
                "fit_all": fit_all
            }

        except ValidationError:
            raise
        except Exception as e:
            raise FusionAPIError(f"Failed to set camera: {str(e)}")


class FitAllHandler(BaseHandler):
    """Handler for fit_all action - fits all geometry in view"""

    def validate(self, args: dict) -> dict:
        """No arguments needed"""
        return args

    def execute(self, args: dict) -> dict:
        """Fit all geometry in view"""
        try:
            app = self.context.app
            viewport = app.activeViewport

            if not viewport:
                raise FusionAPIError("No active viewport")

            camera = viewport.camera
            camera.isFitView = True
            viewport.camera = camera
            viewport.refresh()

            return {"success": True}

        except Exception as e:
            raise FusionAPIError(f"Failed to fit view: {str(e)}")
