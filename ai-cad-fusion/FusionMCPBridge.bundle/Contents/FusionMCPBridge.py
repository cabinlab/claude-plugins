"""
Fusion 360 MCP Bridge Add-in (clean server)
HTTP API server for AI assistant integration via Model Context Protocol
Delegates all actions to the split handler registry
"""

import adsk.core
import adsk.fusion
import json
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import os
import sys
from importlib import import_module, invalidate_caches

# Ensure this add-in directory is importable
_here = os.path.dirname(__file__)
if _here and _here not in sys.path:
    sys.path.append(_here)

# Config values are fetched dynamically at runtime to support /dev/reload of config.py

# Dev reload enablement helper: environment variable or config.DEV_RELOAD_ENABLED
# We evaluate this at request time to avoid needing a full restart after toggling.

def _is_dev_reload_enabled() -> bool:
    try:
        if os.environ.get("BRIDGE_DEV_RELOAD"):
            return True
        cfg = import_module('config')
        # Support both DEV_RELOAD_ENABLED and BRIDGE_DEV_RELOAD (int/bool)
        cfg_flag = getattr(cfg, 'DEV_RELOAD_ENABLED', None)
        if cfg_flag is not None:
            return bool(cfg_flag)
        cfg_legacy = getattr(cfg, 'BRIDGE_DEV_RELOAD', None)
        if cfg_legacy is not None:
            try:
                return bool(int(cfg_legacy))
            except Exception:
                return bool(cfg_legacy)
        return False
    except Exception:
        return False


def _cfg(name: str, default=None):
    """Get a config value dynamically so /dev/reload can update it."""
    try:
        cfg = import_module('config')
        return getattr(cfg, name, default)
    except Exception:
        return default


def _get_bind_addr():
    host = _cfg('BRIDGE_HOST', '0.0.0.0')
    port = _cfg('BRIDGE_PORT', 18080)
    try:
        port = int(port)
    except Exception:
        port = 18080
    return host, port


def _cfg_version() -> str:
    v = _cfg('BRIDGE_VERSION', 'unknown')
    try:
        return str(v)
    except Exception:
        return 'unknown'


def _cfg_auth_token():
    return _cfg('BRIDGE_AUTH_TOKEN', None)

# Globals
_app = None
_ui = None
_server = None
_server_thread = None
_registry = None


def run(context):
    """Entry point for the add-in"""
    global _app, _ui
    _app = adsk.core.Application.get()
    _ui = _app.userInterface

    try:
        start_server()
        host, port = _get_bind_addr()
        print(f"[BRIDGE] FusionMCPBridge started on http://{host}:{port}")

    except OSError as e:
        # Handle specific OS errors with helpful messages
        error_str = str(e).lower()
        host, port = _get_bind_addr()

        if "address already in use" in error_str or "errno 98" in error_str or "errno 10048" in error_str:
            _ui.messageBox(
                f"FusionMCPBridge: Port {port} is already in use.\n\n"
                "Possible causes:\n"
                "• Another instance of FusionMCPBridge is running\n"
                "• Another application is using port {port}\n\n"
                "Try restarting Fusion or check for conflicting applications.",
                "FusionMCPBridge - Startup Error"
            )
        elif "permission denied" in error_str or "errno 13" in error_str:
            _ui.messageBox(
                f"FusionMCPBridge: Permission denied for port {port}.\n\n"
                "The port may require elevated privileges or be blocked by firewall.",
                "FusionMCPBridge - Startup Error"
            )
        else:
            _ui.messageBox(
                f"FusionMCPBridge: Network error during startup.\n\n{str(e)}",
                "FusionMCPBridge - Startup Error"
            )
        raise

    except Exception as e:
        _ui.messageBox(
            f"FusionMCPBridge: Failed to start.\n\n{str(e)}",
            "FusionMCPBridge - Startup Error"
        )
        raise


def stop(context):
    """Cleanup when add-in is stopped"""
    try:
        global _server, _server_thread, _registry
        
        if _server:
            _server.shutdown()
            _server = None
            
        if _server_thread:
            _server_thread.join(timeout=2)
            _server_thread = None
        
        # Drop references to help GC
        _registry = None
        
        # Purge bridge modules so next start() picks up code changes without Fusion restart
        _purge_bridge_modules()
        
        print("[BRIDGE] FusionMCPBridge stopped and modules purged")
        
    except Exception as e:
        if _ui:
            _ui.messageBox(f"Error stopping FusionMCPBridge: {str(e)}")


def make_handler_class(registry):
    """Factory to create handler class with bound registry"""
    class BridgeRequestHandler(BaseHTTPRequestHandler):
        _registry = registry

        def log_message(self, format, *args):
            """Override to suppress default logging"""
            pass

        def _check_auth(self) -> bool:
            """Check authorization if enabled"""
            auth_token = _cfg_auth_token()
            if auth_token is None:
                return True  # Auth disabled
            
            token = self.headers.get("X-Bridge-Token")
            if token != auth_token:
                self._send_error(200, "E_UNAUTHORIZED", "Invalid or missing X-Bridge-Token header")
                return False
            return True

        def do_GET(self):
            """Handle GET requests"""
            try:
                if not self._check_auth():
                    return
                    
                parsed = urlparse(self.path)
                
                if parsed.path == "/health":
                    fusion = get_fusion_state()
                    ver = _cfg_version()
                    print(f"[AGENT] Health check - version from config: {ver}")
                    body = {
                        "status": "ok",
                        "version": ver,
                        "fusion": fusion
                    }
                    self._send_json_response(200, body)
                else:
                    self._send_json_response(404, {
                        "status": "error",
                        "error": {"code": "E_NOT_FOUND", "message": "Endpoint not found"}
                    })
                    
            except Exception as e:
                self._send_json_response(500, {
                    "status": "error",
                    "error": {"code": "E_INTERNAL", "message": str(e)}
                })

        def do_POST(self):
            """Handle POST requests - always return 200"""
            try:
                if not self._check_auth():
                    return
                    
                parsed = urlparse(self.path)
                
                # Dev reload endpoint (hot-reload split modules)
                if parsed.path == "/dev/reload":
                    if not _is_dev_reload_enabled():
                        self._send_error(200, "E_UNAUTHORIZED", "Dev reload disabled (set BRIDGE_DEV_RELOAD=1 or config.DEV_RELOAD_ENABLED=True)")
                        return
                    try:
                        new_registry = _reload_and_rebuild_registry()
                        # Swap registry on current handler class
                        self.__class__._registry = new_registry
                        # Also rebuild the RequestHandlerClass so future connections use a fresh class binding
                        try:
                            self.server.RequestHandlerClass = make_handler_class(new_registry)
                        except Exception:
                            pass
                        # Update global reference as well
                        global _registry
                        _registry = new_registry
                        self._send_json_response(200, {"status": "ok", "reloaded": True})
                    except Exception as e:
                        self._send_error(200, "E_RUNTIME", str(e))
                    return
                
                if parsed.path != "/v1/execute":
                    self._send_error(200, "E_NOT_FOUND", "Endpoint not found")
                    return

                content_length = int(self.headers.get("Content-Length", 0))
                if content_length <= 0:
                    self._send_error(200, "E_BAD_ARGS", "Missing request body")
                    return

                payload = self.rfile.read(content_length).decode("utf-8")
                req = json.loads(payload)
                action = req.get("action")
                args = req.get("args", {})
                request_id = req.get("id")

                if not action:
                    self._send_error(200, "E_BAD_ARGS", "Missing 'action' field", request_id=request_id)
                    return

                start = time.time()
                req_id_str = request_id if request_id else "none"
                
                # Import fresh error classes so catches match reloaded modules
                _errors = import_module('core.errors')
                ValidationError = getattr(_errors, 'ValidationError', Exception)
                FusionAPIError = getattr(_errors, 'FusionAPIError', Exception)
                ActionNotSupportedError = getattr(_errors, 'ActionNotSupportedError', Exception)
                
                try:
                    result = self._registry.handle_action(action, args)
                    elapsed = int((time.time() - start) * 1000)
                    print(f"[BRIDGE] {action} {req_id_str} -> OK ({elapsed}ms)")
                    
                    resp = {"status": "ok", "result": result}
                    if request_id:
                        resp["id"] = request_id
                    self._send_json_response(200, resp)
                    
                except ActionNotSupportedError as e:
                    elapsed = int((time.time() - start) * 1000)
                    print(f"[BRIDGE] {action} {req_id_str} -> ERR ({elapsed}ms): {str(e)}")
                    self._send_error(200, e.code, e.message, request_id=request_id)
                except ValidationError as e:
                    elapsed = int((time.time() - start) * 1000)
                    print(f"[BRIDGE] {action} {req_id_str} -> ERR ({elapsed}ms): {str(e)}")
                    self._send_error(200, e.code, e.message, getattr(e, "details", None), request_id)
                except FusionAPIError as e:
                    elapsed = int((time.time() - start) * 1000)
                    print(f"[BRIDGE] {action} {req_id_str} -> ERR ({elapsed}ms): {str(e)}")
                    self._send_error(200, e.code, e.message, getattr(e, "details", None), request_id)
                except Exception as e:
                    elapsed = int((time.time() - start) * 1000)
                    print(f"[BRIDGE] {action} {req_id_str} -> ERR ({elapsed}ms): {str(e)}")
                    self._send_error(200, "E_RUNTIME", str(e), request_id=request_id)

            except json.JSONDecodeError as e:
                self._send_error(200, "E_BAD_JSON", f"Invalid JSON: {str(e)}")
            except Exception as e:
                # Try to get request_id from parsed data if available
                try:
                    request_id = req.get("id") if 'req' in locals() else None
                except:
                    request_id = None
                self._send_error(200, "E_RUNTIME", str(e), request_id=request_id)

        def _send_json_response(self, status_code, data):
            """Send JSON response"""
            blob = json.dumps(data, indent=2).encode("utf-8")
            
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(blob)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(blob)

        def _send_error(self, status_code, code, message, details=None, request_id=None):
            """Send structured error response"""
            body = {
                "status": "error",
                "error": {
                    "code": code,
                    "message": message
                }
            }
            
            if details:
                body["error"]["details"] = details
            if request_id:
                body["id"] = request_id
                
            # Contract: always 200 for POST errors
            self._send_json_response(200, body)

    return BridgeRequestHandler


def start_server():
    """Start the HTTP server in a background thread"""
    global _server, _server_thread, _registry
    
    try:
        # Initialize registry (no feature flags) with fresh imports
        _registry = _reload_and_rebuild_registry()

        handler_class = make_handler_class(_registry)
        host, port = _get_bind_addr()
        _server = HTTPServer((host, port), handler_class)
        _server_thread = threading.Thread(target=_server.serve_forever, daemon=True)
        _server_thread.start()
        
    except Exception as e:
        raise Exception(f"Failed to start server: {str(e)}")


def get_fusion_state():
    """Get current Fusion 360 state for health check"""
    try:
        app = adsk.core.Application.get()
        design = app.activeProduct
        
        info = {
            "running": True,
            "documentName": "No active document",
            "units": "mm"
        }
        
        if design and hasattr(design, "rootComponent"):
            info["documentName"] = app.activeDocument.name
            um = getattr(design, "unitsManager", None)
            if um:
                info["units"] = um.defaultLengthUnits
                
        return info
        
    except Exception as e:
        return {
            "running": False,
            "error": str(e),
            "units": "unknown"
        }


def _purge_bridge_modules():
    """Remove all modules under this add-in directory from sys.modules and invalidate caches."""
    try:
        root = os.path.abspath(os.path.dirname(__file__))
        victims = []
        for name, m in list(sys.modules.items()):
            f = getattr(m, "__file__", None)
            if not f:
                continue
            try:
                f_abs = os.path.abspath(f)
            except Exception:
                continue
            if f_abs.startswith(root) and not f_abs.endswith("FusionMCPBridge.py"):
                victims.append(name)
        for name in victims:
            sys.modules.pop(name, None)
        invalidate_caches()
        print(f"[BRIDGE] Purged {len(victims)} modules under {root}")
    except Exception as e:
        print(f"[BRIDGE] Module purge error: {e}")


def _reload_and_rebuild_registry():
    """Purge bridge modules, re-import split modules, and return a fresh HandlerRegistry."""
    _purge_bridge_modules()
    # Fresh imports
    core_router = import_module('core.router')
    services_fc = import_module('services.fusion_context')
    HandlerRegistry = getattr(core_router, 'HandlerRegistry')
    FusionContext = getattr(services_fc, 'FusionContext')
    context = FusionContext()
    return HandlerRegistry(context)
