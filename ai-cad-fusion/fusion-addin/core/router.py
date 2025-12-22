"""
Central registry for action handlers
"""
from core.errors import ActionNotSupportedError
from services.fusion_context import FusionContext
from services.entity_resolver import EntityResolver
from services.validators import ValidationService
from handlers.base import BaseHandler


class HandlerRegistry:
    """Central registry for action handlers"""
    
    def __init__(self, context: FusionContext):
        self._handlers = {}
        self._context = context
        self._resolver = EntityResolver(context)
        self._validators = ValidationService()
        self._initialize_handlers()
        
    def _initialize_handlers(self):
        """Register all handlers"""
        try:
            # Document handlers
            from handlers.document import (
                GetDesignInfoHandler,
                ListOpenDocumentsHandler,
                GetOpenDocumentInfoHandler,
                OpenDocumentHandler,
                FocusDocumentHandler,
                CloseDocumentHandler,
                BackupDocumentHandler,
                GetDocumentTypeHandler,
                GetDocumentStructureHandler
            )
            print("[ROUTER] Document handlers imported successfully")
        except Exception as e:
            print(f"[ROUTER] Failed to import document handlers: {e}")
            raise
        
        try:
            # Parameter handlers
            from handlers.parameters import CreateParameterHandler, UpdateParameterHandler
            print("[ROUTER] Parameter handlers imported successfully")
        except Exception as e:
            print(f"[ROUTER] Failed to import parameter handlers: {e}")
            raise
        
        try:
            # Sketch handlers
            from handlers.sketches import (
                CreateSketchHandler,
                SketchDrawLineHandler,
                SketchDrawCircleHandler,
                SketchDrawRectangleHandler,
                CreateSketchFromFaceHandler,
                ProjectEdgesHandler,
                SetIsConstructionHandler
            )
            print("[ROUTER] Sketch handlers imported successfully")
        except Exception as e:
            print(f"[ROUTER] Failed to import sketch handlers: {e}")
            raise
        
        try:
            # Feature handlers
            from handlers.features import ExtrudeProfileHandler, RevolveProfileHandler, CombineBodiesHandler, RotateBodyHandler
            print("[ROUTER] Feature handlers imported successfully")
        except Exception as e:
            print(f"[ROUTER] Failed to import feature handlers: {e}")
            raise
        
        try:
            # Constraint handlers
            from handlers.constraints import AddConstraintsHandler, AddDimensionDistanceHandler
            print("[ROUTER] Constraint handlers imported successfully")
        except Exception as e:
            print(f"[ROUTER] Failed to import constraint handlers: {e}")
            raise
        
        try:
            # Inspection handlers
            from handlers.inspection import MeasureGeometryHandler
            print("[ROUTER] Inspection handlers imported successfully")
        except Exception as e:
            print(f"[ROUTER] Failed to import inspection handlers: {e}")
            raise

        try:
            # UI handlers
            from handlers.ui import TriggerUICommandHandler
            print("[ROUTER] UI handlers imported successfully")
        except Exception as e:
            print(f"[ROUTER] Failed to import UI handlers: {e}")
            raise
        
        # Register Phase 1 proof-of-concept handlers
        self.register("get_design_info", GetDesignInfoHandler)
        self.register("create_parameter", CreateParameterHandler)
        self.register("update_parameter", UpdateParameterHandler)
        self.register("create_sketch", CreateSketchHandler)
        self.register("extrude_profile", ExtrudeProfileHandler)
        
        # Register Phase 2 document handlers
        self.register("list_open_documents", ListOpenDocumentsHandler)
        self.register("get_open_document_info", GetOpenDocumentInfoHandler)
        self.register("open_document", OpenDocumentHandler)
        self.register("focus_document", FocusDocumentHandler)
        self.register("close_document", CloseDocumentHandler)
        self.register("backup_document", BackupDocumentHandler)
        self.register("get_document_type", GetDocumentTypeHandler)
        self.register("get_document_structure", GetDocumentStructureHandler)
        
        # Register Phase 2 sketch drawing handlers
        self.register("sketch_draw_line", SketchDrawLineHandler)
        self.register("sketch_draw_circle", SketchDrawCircleHandler)
        self.register("sketch_draw_rectangle", SketchDrawRectangleHandler)
        
        # Register Phase 2 advanced sketch handlers (now exposed via MCP for sheet metal workflows)
        self.register("create_sketch_from_face", CreateSketchFromFaceHandler)
        self.register("project_edges", ProjectEdgesHandler)
        self.register("set_is_construction", SetIsConstructionHandler)
        
        # Register Phase 2 feature handlers
        self.register("revolve_profile", RevolveProfileHandler)
        self.register("combine_bodies", CombineBodiesHandler)

        # Register Phase 3 feature handlers
        self.register("rotate_body", RotateBodyHandler)
        
        # Register Phase 2 constraint handlers
        self.register("add_constraints", AddConstraintsHandler)
        self.register("add_dimension_distance", AddDimensionDistanceHandler)
        
        # Register Phase 2 inspection handlers
        self.register("measure_geometry", MeasureGeometryHandler)

        # Register UI handlers
        self.register("trigger_ui_command", TriggerUICommandHandler)
        
        # Log all registered actions for debugging
        registered_actions = sorted(self._handlers.keys())
        print(f"[ROUTER] ✅ Successfully registered {len(registered_actions)} handlers:")
        for action in registered_actions:
            handler_class_name = self._handlers[action].__class__.__name__
            print(f"[ROUTER]   • {action} -> {handler_class_name}")
        print(f"[ROUTER] Registration complete. Split mode ready.")
        
    def register(self, action: str, handler_class: type):
        """Register a handler class for an action"""
        try:
            self._handlers[action] = handler_class(self._context, self._resolver, self._validators)
            print(f"[ROUTER] ✓ Registered '{action}' -> {handler_class.__name__}")
        except Exception as e:
            print(f"[ROUTER] ✗ Failed to register '{action}': {e}")
            # Re-raise to prevent silent failures
            raise
        
    def get_handler(self, action: str) -> BaseHandler:
        """Get handler for an action"""
        if action not in self._handlers:
            raise ActionNotSupportedError(action)
        return self._handlers[action]
        
    def handle_action(self, action: str, args: dict) -> dict:
        """Execute an action with its handler"""
        handler = self.get_handler(action)
        return handler.handle(args)
