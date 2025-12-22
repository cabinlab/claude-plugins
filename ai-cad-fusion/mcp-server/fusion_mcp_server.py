#!/usr/bin/env python3
"""
Fusion 360 MCP Server
Model Context Protocol server for Fusion 360 bridge integration
"""

import asyncio
import json
import logging
import sys
import uuid
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx
import os
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    TextContent,
    Tool,
)
from pydantic import BaseModel, ValidationError


# Configuration
import re

def _detect_windows_host_ip_from_wsl() -> str | None:
    try:
        with open("/etc/resolv.conf", "r") as f:
            import re as _re
            for line in f:
                m = _re.search(r"^nameserver\s+(\S+)", line)
                if m:
                    return m.group(1)
    except Exception:
        pass
    return None

def _resolve_bridge_base_url() -> str:
    env_val = os.getenv("BRIDGE_BASE_URL")
    if env_val and not env_val.startswith("http://127.0.0.1"):
        return env_val
    ip = _detect_windows_host_ip_from_wsl()
    if ip:
        return f"http://{ip}:18080"
    return "http://127.0.0.1:18080"

BRIDGE_BASE_URL = _resolve_bridge_base_url()
# DEFAULT_GW_FALLBACK: adjust for WSL default gateway if needed

# NAMESERVER_TO_GW_FIX: prefer default gateway over resolv.conf nameserver in WSL
try:
    from urllib.parse import urlparse
    host = urlparse(BRIDGE_BASE_URL).hostname or ""
    ns_ip = None
    try:
        with open("/etc/resolv.conf", "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("nameserver "):
                    ns_ip = line.split()[1]
                    break
    except Exception:
        pass
    if ns_ip and host == ns_ip:
        import subprocess, shlex
        out = subprocess.check_output(shlex.split("ip route show default"), text=True).strip()
        parts = out.split()
        if "via" in parts:
            gw = parts[parts.index("via")+1]
            if gw:
                BRIDGE_BASE_URL = f"http://{gw}:18080"
except Exception:
    pass

try:
    import subprocess, shlex
    if BRIDGE_BASE_URL.startswith("http://127."):
        out = subprocess.check_output(shlex.split("ip route show default"), text=True).strip()
        parts = out.split()
        if "via" in parts:
            gw = parts[parts.index("via")+1]
            if gw:
                BRIDGE_BASE_URL = f"http://{gw}:18080"
except Exception:
    pass

BRIDGE_TIMEOUT = 1.0  # Fail fast - bridge responds in <100ms when running
SERVER_VERSION = "0.0.1"
SCHEMA_VERSION = "0.1"

# Setup logging
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

# Global HTTP client
http_client: Optional[httpx.AsyncClient] = None

def _get_http_client() -> httpx.AsyncClient:
    """Return a process-wide AsyncClient to enable connection pooling."""
    global http_client
    if http_client is None:
        # Default timeouts can be tuned if needed; per-call timeout still applies
        http_client = httpx.AsyncClient()
    return http_client


class BridgeError(Exception):
    """Bridge communication error"""
    def __init__(self, code: str, message: str, details: Optional[Dict] = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"{code}: {message}")


class BridgeClient:
    """HTTP client for communicating with Fusion 360 bridge"""
    
    def __init__(self, base_url: str, timeout: float = BRIDGE_TIMEOUT):
        self.base_url = base_url
        self.timeout = timeout
    
    async def health_check(self) -> Dict[str, Any]:
        """Check bridge health"""
        try:
            client = _get_http_client()
            response = await client.get(
                urljoin(self.base_url, "/health"),
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            raise BridgeError("E_CONNECTION", "Cannot connect to Fusion bridge - is Fusion running with AgentBridge add-in enabled? Do NOT retry - fix the setup first.")
        except httpx.TimeoutException:
            raise BridgeError("E_TIMEOUT", "Bridge health check timed out")
        except httpx.HTTPStatusError as e:
            raise BridgeError("E_HTTP", f"Bridge returned {e.response.status_code}")
        except Exception as e:
            raise BridgeError("E_UNKNOWN", f"Unexpected error: {str(e)}")
    
    async def execute_action(self, action: str, args: Dict[str, Any], request_id: Optional[str] = None) -> Any:
        """Execute an action on the bridge"""
        try:
            request_data = {
                "action": action,
                "args": args
            }
            if request_id:
                request_data["id"] = request_id
            
            client = _get_http_client()
            response = await client.post(
                urljoin(self.base_url, "/v1/execute"),
                json=request_data,
                timeout=self.timeout
            )
            response.raise_for_status()
            response_data = response.json()
            
            if response_data.get("status") == "error":
                error = response_data["error"]
                raise BridgeError(
                    error.get("code", "E_BRIDGE_ERROR"),
                    error.get("message", "Unknown bridge error"),
                    error.get("details")
                )
            
            result = response_data.get("result")
            return result
                
        except httpx.ConnectError:
            raise BridgeError("E_CONNECTION", "Cannot connect to Fusion bridge - is Fusion running with AgentBridge add-in enabled? Do NOT retry - fix the setup first.")
        except httpx.TimeoutException:
            raise BridgeError("E_TIMEOUT", f"Action '{action}' timed out")
        except httpx.HTTPStatusError as e:
            raise BridgeError("E_HTTP", f"Bridge returned {e.response.status_code}")
        except BridgeError:
            raise  # Re-raise bridge errors
        except Exception as e:
            raise BridgeError("E_UNKNOWN", f"Unexpected error: {str(e)}")


# Tool argument models for validation
class GetDesignInfoArgs(BaseModel):
    """Arguments for get_design_info tool - none required"""
    pass


class CreateParameterArgs(BaseModel):
    """Arguments for create_parameter tool"""
    name: str
    expression: str
    unit: str
    comment: Optional[str] = None


class CreateSketchArgs(BaseModel):
    """Arguments for create_sketch tool"""
    plane: str
    name: str


class SketchDrawLineArgs(BaseModel):
    """Arguments for sketch_draw_line tool"""
    sketch: str
    start: dict
    end: dict


class SketchDrawCircleArgs(BaseModel):
    """Arguments for sketch_draw_circle tool"""
    sketch: str
    center: dict
    radius: float


class SketchDrawRectangleArgs(BaseModel):
    """Arguments for sketch_draw_rectangle tool"""
    sketch: str
    origin: dict
    width: float
    height: float


class ExtrudeProfileArgs(BaseModel):
    """Arguments for extrude_profile tool"""
    sketch: str
    profile_index: int
    distance: float
    operation: str = "new_body"
    direction: str = "positive"


class UpdateParameterArgs(BaseModel):
    """Arguments for update_parameter tool"""
    name: str
    expression: Optional[str] = None
    unit: Optional[str] = None
    comment: Optional[str] = None


class AddConstraintsArgs(BaseModel):
    """Arguments for add_constraints tool"""
    sketch: str
    type: str
    refs: List[Dict[str, Any]]


class AddDimensionDistanceArgs(BaseModel):
    """Arguments for add_dimension_distance tool"""
    sketch: str
    a: Dict[str, Any]
    b: Dict[str, Any]
    orientation: str
    expression: str


# Phase 0 - Foundation argument models
class ListOpenDocumentsArgs(BaseModel):
    """Arguments for list_open_documents tool - none required"""
    pass


class GetOpenDocumentInfoArgs(BaseModel):
    """Arguments for get_open_document_info tool"""
    name: Optional[str] = None
    fullPath: Optional[str] = None


class OpenDocumentArgs(BaseModel):
    """Arguments for open_document tool"""
    path: str
    read_only: Optional[bool] = False


class FocusDocumentArgs(BaseModel):
    """Arguments for focus_document tool"""
    name: Optional[str] = None
    fullPath: Optional[str] = None


class CloseDocumentArgs(BaseModel):
    """Arguments for close_document tool"""
    save: Optional[bool] = False


class BackupDocumentArgs(BaseModel):
    """Arguments for backup_document tool"""
    path: Optional[str] = None
    format: Optional[str] = "f3d"


class GetDocumentTypeArgs(BaseModel):
    """Arguments for get_document_type tool - none required"""
    pass


# Phase 1 - Inspection argument models
class GetDocumentStructureArgs(BaseModel):
    """Arguments for get_document_structure tool"""
    detail: Optional[str] = "low"


class MeasureGeometryArgs(BaseModel):
    """Arguments for measure_geometry tool"""
    refs: List[Dict[str, Any]]


# Phase 2 - Core Parametrics argument models
class CreateSketchFromFaceArgs(BaseModel):
    """Arguments for create_sketch_from_face tool"""
    faceRef: Dict[str, Any]  # {component: str, body: str, faceIndex: int}
    name: str


class ProjectEdgesArgs(BaseModel):
    """Arguments for project_edges tool"""
    sketch: str
    faceRef: Optional[Dict[str, Any]] = None  # {component: str, body: str, faceIndex: int}
    edgeRefs: Optional[List[Dict[str, Any]]] = None  # [{component: str, body: str, edgeIndex: int}]


class SetIsConstructionArgs(BaseModel):
    """Arguments for set_is_construction tool"""
    sketch: str
    entityRef: Dict[str, Any]  # {type: "line", index: int}
    value: bool


class TriggerUICommandArgs(BaseModel):
    """Arguments for trigger_ui_command tool"""
    command_id: str
    message: Optional[str] = ""


# Phase 3 - Features
class CombineBodiesArgs(BaseModel):
    """Arguments for combine_bodies tool"""
    targets: List[Dict[str, Any]]  # [bodyRef]
    tools: List[Dict[str, Any]]    # [bodyRef]
    operation: Optional[str] = "join"  # join|cut|intersect


class RotateBodyArgs(BaseModel):
    """Arguments for rotate_body tool"""
    bodyRef: Dict[str, Any]  # {component: str, body: str}
    pivot: Dict[str, Any]    # {type: "origin_axis"|"edge_axis", axis?: "X"|"Y"|"Z", edgeRef?: {...}}
    angle: float             # degrees
    copy: Optional[bool] = False


# Initialize bridge client
bridge = BridgeClient(BRIDGE_BASE_URL, BRIDGE_TIMEOUT)

# Initialize MCP server
server = Server("fusion360-mcp-server")


def create_json_response(data: Any, success: bool = True) -> List[TextContent]:
    """Create a structured JSON response with metadata"""
    response = {
        "success": success,
        "data": data,
        "format": "json"
    }
    
    return [TextContent(
        type="text",
        text=json.dumps(response, indent=2)
    )]


def create_error_response(error_message: str, error_code: str = None) -> List[TextContent]:
    """Create a structured error response"""
    response = {
        "success": False,
        "error": error_message,
        "format": "json"
    }
    
    if error_code:
        response["error_code"] = error_code
    
    return [TextContent(
        type="text", 
        text=json.dumps(response, indent=2)
    )]


@server.list_tools()
async def list_tools(params=None) -> List[Tool]:
    """List available MCP tools"""
    return [
        Tool(
            name="get_design_info",
            description="Get information about the active Fusion 360 design",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
                "_meta": {
                    "schemaVersion": SCHEMA_VERSION,
                    "returnSchema": {
                        "type": "object",
                        "properties": {
                            "documentName": {"type": "string"},
                            "units": {"type": "string"},
                            "components": {"type": "array"},
                            "bodies": {"type": "array"},
                            "parameters": {"type": "array"}
                        }
                    }
                }
            }
        ),
        Tool(
            name="create_parameter",
            description="Create a new user parameter in the active Fusion 360 design",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Parameter name (must be unique)"
                    },
                    "expression": {
                        "type": "string",
                        "description": "Parameter expression (e.g., '10', '5*2', 'height/2')"
                    },
                    "unit": {
                        "type": "string", 
                        "description": "Parameter unit (e.g., 'mm', 'deg', '')"
                    },
                    "comment": {
                        "type": "string",
                        "description": "Optional human-first comment describing purpose/usage"
                    }
                },
                "required": ["name", "expression", "unit"],
                "_meta": {
                    "schemaVersion": SCHEMA_VERSION,
                    "returnSchema": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "expression": {"type": "string"},
                            "unit": {"type": "string"},
                            "comment": {"type": "string"}
                        }
                    }
                }
            }
        ),
        Tool(
            name="create_sketch",
            description="Create a new sketch on a construction plane in Fusion 360",
            inputSchema={
                "type": "object",
                "properties": {
                    "plane": {
                        "type": "string",
                        "enum": ["XY", "YZ", "XZ"],
                        "description": "Construction plane for the sketch"
                    },
                    "name": {
                        "type": "string",
                        "description": "Name for the sketch (must be unique)"
                    }
                },
                "required": ["plane", "name"],
                "_meta": {
                    "schemaVersion": SCHEMA_VERSION,
                    "returnSchema": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "plane": {"type": "string"}
                        }
                    }
                }
            }
        ),
        Tool(
            name="sketch_draw_line",
            description="Draw a line in an existing sketch by specifying start and end coordinates",
            inputSchema={
                "type": "object",
                "properties": {
                    "sketch": {
                        "type": "string",
                        "description": "Name of the sketch to draw in"
                    },
                    "start": {
                        "type": "object",
                        "properties": {
                            "x": {"type": "number", "description": "X coordinate of start point"},
                            "y": {"type": "number", "description": "Y coordinate of start point"}
                        },
                        "required": ["x", "y"],
                        "description": "Start point coordinates"
                    },
                    "end": {
                        "type": "object",
                        "properties": {
                            "x": {"type": "number", "description": "X coordinate of end point"},
                            "y": {"type": "number", "description": "Y coordinate of end point"}
                        },
                        "required": ["x", "y"],
                        "description": "End point coordinates"
                    }
                },
                "required": ["sketch", "start", "end"],
                "_meta": {
                    "schemaVersion": SCHEMA_VERSION,
                    "returnSchema": {
                        "type": "object",
                        "properties": {
                            "sketch": {"type": "string"},
                            "entity": {
                                "type": "object",
                                "properties": {
                                    "type": {"type": "string"},
                                    "index": {"type": "number"}
                                }
                            }
                        }
                    }
                }
            }
        ),
        Tool(
            name="sketch_draw_circle",
            description="Draw a circle in an existing sketch in Fusion 360",
            inputSchema={
                "type": "object",
                "properties": {
                    "sketch": {
                        "type": "string",
                        "description": "Name of the target sketch"
                    },
                    "center": {
                        "type": "object",
                        "properties": {
                            "x": {"type": "number"},
                            "y": {"type": "number"}
                        },
                        "required": ["x", "y"],
                        "description": "Center point coordinates"
                    },
                    "radius": {
                        "type": "number",
                        "description": "Circle radius (must be positive)"
                    }
                },
                "required": ["sketch", "center", "radius"],
                "_meta": {
                    "schemaVersion": SCHEMA_VERSION,
                    "returnSchema": {
                        "type": "object",
                        "properties": {
                            "sketch": {"type": "string"},
                            "entity": {
                                "type": "object",
                                "properties": {
                                    "type": {"type": "string"},
                                    "index": {"type": "number"}
                                }
                            }
                        }
                    }
                }
            }
        ),
        Tool(
            name="sketch_draw_rectangle",
            description="Draw a rectangle in an existing sketch in Fusion 360",
            inputSchema={
                "type": "object",
                "properties": {
                    "sketch": {
                        "type": "string",
                        "description": "Name of the target sketch"
                    },
                    "origin": {
                        "type": "object",
                        "properties": {
                            "x": {"type": "number"},
                            "y": {"type": "number"}
                        },
                        "required": ["x", "y"],
                        "description": "Origin point coordinates (bottom-left corner)"
                    },
                    "width": {
                        "type": "number",
                        "description": "Rectangle width (must be positive)"
                    },
                    "height": {
                        "type": "number",
                        "description": "Rectangle height (must be positive)"
                    }
                },
                "required": ["sketch", "origin", "width", "height"],
                "_meta": {
                    "schemaVersion": SCHEMA_VERSION,
                    "returnSchema": {
                        "type": "object",
                        "properties": {
                            "sketch": {"type": "string"},
                            "entity": {
                                "type": "object",
                                "properties": {
                                    "type": {"type": "string"},
                                    "index": {"type": "number"}
                                }
                            }
                        }
                    }
                }
            }
        ),
        Tool(
            name="extrude_profile",
            description="Extrude a profile from a sketch to create 3D geometry in Fusion 360",
            inputSchema={
                "type": "object",
                "properties": {
                    "sketch": {
                        "type": "string",
                        "description": "Name of the sketch containing the profile"
                    },
                    "profile_index": {
                        "type": "integer",
                        "minimum": 0,
                        "description": "Index of the profile to extrude (0-based)"
                    },
                    "distance": {
                        "type": "number",
                        "minimum": 0.001,
                        "description": "Extrusion distance (must be positive)"
                    },
                    "operation": {
                        "type": "string",
                        "enum": ["new_body", "join", "cut", "intersect"],
                        "default": "new_body",
                        "description": "Extrusion operation type"
                    },
                    "direction": {
                        "type": "string",
                        "enum": ["positive", "negative", "symmetric"],
                        "default": "positive",
                        "description": "Extrusion direction"
                    }
                },
                "required": ["sketch", "profile_index", "distance"],
                "_meta": {
                    "schemaVersion": SCHEMA_VERSION,
                    "returnSchema": {
                        "type": "object",
                        "properties": {
                            "feature": {
                                "type": "object",
                                "properties": {
                                    "type": {"type": "string"},
                                    "name": {"type": "string"}
                                }
                            },
                            "bodies": {
                                "type": "array",
                                "description": "Bodies created by the extrusion (if any)",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "type": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        ),
        Tool(
            name="revolve_profile",
            description="Revolve a sketch profile around an axis to create 3D geometry",
            inputSchema={
                "type": "object",
                "properties": {
                    "sketch": {"type": "string", "description": "Name of the sketch containing the profile"},
                    "profile_index": {"type": "integer", "minimum": 0, "description": "Index of the profile (0-based)"},
                    "axisRef": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "enum": ["origin_axis"]},
                            "axis": {"type": "string", "enum": ["X", "Y", "Z"]}
                        },
                        "required": ["type", "axis"],
                        "description": "Axis reference; v0 supports origin axes X/Y/Z"
                    },
                    "angle": {"type": "number", "minimum": 0.001, "description": "Revolve angle in degrees"},
                    "operation": {"type": "string", "enum": ["new_body", "join", "cut", "intersect"], "default": "new_body"}
                },
                "required": ["sketch", "profile_index", "axisRef", "angle"],
                "_meta": {
                    "schemaVersion": SCHEMA_VERSION,
                    "returnSchema": {
                        "type": "object",
                        "properties": {
                            "feature": {"type": "object", "properties": {"type": {"type": "string"}, "name": {"type": "string"}}},
                            "createdBodies": {"type": "array", "items": {"type": "object"}}
                        }
                    }
                }
            }
        ),
        Tool(
            name="combine_bodies",
            description="Combine target bodies with tool bodies (join/cut/intersect)",
            inputSchema={
                "type": "object",
                "properties": {
                    "targets": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Target bodies (bodyRef objects)"
                    },
                    "tools": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Tool bodies (bodyRef objects)"
                    },
                    "operation": {
                        "type": "string",
                        "enum": ["join", "cut", "intersect"],
                        "default": "join",
                        "description": "Combine operation type"
                    }
                },
                "required": ["targets", "tools"],
                "_meta": {
                    "schemaVersion": SCHEMA_VERSION,
                    "returnSchema": {
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean"}
                        }
                    }
                }
            }
        ),
        Tool(
            name="rotate_body",
            description="Rotate a body around an axis (origin X/Y/Z or edge pivot)",
            inputSchema={
                "type": "object",
                "properties": {
                    "bodyRef": {
                        "type": "object",
                        "properties": {
                            "component": {"type": "string"},
                            "body": {"type": "string"}
                        },
                        "required": ["component", "body"],
                        "description": "Reference to the body to rotate"
                    },
                    "pivot": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "enum": ["origin_axis", "edge_axis"]},
                            "axis": {"type": "string", "enum": ["X", "Y", "Z"], "description": "For origin_axis: rotation axis"},
                            "edgeRef": {
                                "type": "object",
                                "properties": {
                                    "component": {"type": "string"},
                                    "body": {"type": "string"},
                                    "edgeIndex": {"type": "integer"}
                                },
                                "description": "For edge_axis: edge to use as rotation axis"
                            }
                        },
                        "required": ["type"],
                        "description": "Pivot point/axis for rotation"
                    },
                    "angle": {
                        "type": "number",
                        "description": "Rotation angle in degrees (positive = counterclockwise)"
                    },
                    "copy": {
                        "type": "boolean",
                        "default": False,
                        "description": "If true, create rotated copy; if false, transform in place"
                    }
                },
                "required": ["bodyRef", "pivot", "angle"],
                "_meta": {
                    "schemaVersion": SCHEMA_VERSION,
                    "returnSchema": {
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean"},
                            "transformedBody": {"type": "object", "description": "bodyRef of transformed body (when copy=false)"},
                            "createdBody": {"type": "object", "description": "bodyRef of new body (when copy=true)"}
                        }
                    }
                }
            }
        ),

        # Phase 0 - Foundation tools
        Tool(
            name="list_open_documents",
            description="List all open documents in Fusion 360",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
                "_meta": {
                    "schemaVersion": SCHEMA_VERSION,
                    "returnSchema": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "isActive": {"type": "boolean"},
                                "isDirty": {"type": "boolean"},
                                "isCloudDocument": {"type": "boolean"},
                                "id": {"type": "string"},
                                "fullPath": {"type": "string"},
                                "cloudId": {"type": "string"},
                                "projectName": {"type": "string"}
                            }
                        }
                    }
                }
            }
        ),
        Tool(
            name="get_open_document_info",
            description="Get detailed information about a specific open document",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Document name to query"
                    },
                    "fullPath": {
                        "type": "string",
                        "description": "Full path to document file"
                    }
                },
                "required": [],
                "_meta": {
                    "schemaVersion": SCHEMA_VERSION,
                    "returnSchema": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "isActive": {"type": "boolean"},
                            "isDirty": {"type": "boolean"},
                            "isCloudDocument": {"type": "boolean"},
                            "id": {"type": "string"}
                        }
                    }
                }
            }
        ),
        Tool(
            name="open_document",
            description="Open a local Fusion 360 document file",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Full path to the Fusion 360 document file"
                    },
                    "read_only": {
                        "type": "boolean",
                        "default": False,
                        "description": "Open document in read-only mode"
                    }
                },
                "required": ["path"],
                "_meta": {
                    "schemaVersion": SCHEMA_VERSION,
                    "returnSchema": {
                        "type": "object",
                        "properties": {
                            "documentName": {"type": "string"},
                            "fullPath": {"type": "string"},
                            "units": {"type": "string"}
                        }
                    }
                }
            }
        ),
        Tool(
            name="focus_document",
            description="Activate/focus a specific open document in Fusion 360",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Document name to activate"
                    },
                    "fullPath": {
                        "type": "string",
                        "description": "Full path to document file"
                    }
                },
                "required": [],
                "_meta": {
                    "schemaVersion": SCHEMA_VERSION,
                    "returnSchema": {
                        "type": "object",
                        "properties": {
                            "documentName": {"type": "string"}
                        }
                    }
                }
            }
        ),
        Tool(
            name="close_document",
            description="Close the active document in Fusion 360",
            inputSchema={
                "type": "object",
                "properties": {
                    "save": {
                        "type": "boolean",
                        "default": False,
                        "description": "Save document before closing"
                    }
                },
                "required": [],
                "_meta": {
                    "schemaVersion": SCHEMA_VERSION,
                    "returnSchema": {
                        "type": "object",
                        "properties": {
                            "closed": {"type": "boolean"}
                        }
                    }
                }
            }
        ),
        Tool(
            name="backup_document",
            description="Create a backup copy of the active document",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Backup file path (optional, auto-generated if not provided)"
                    },
                    "format": {
                        "type": "string",
                        "enum": ["f3d", "step"],
                        "default": "f3d",
                        "description": "Backup format"
                    }
                },
                "required": [],
                "_meta": {
                    "schemaVersion": SCHEMA_VERSION,
                    "returnSchema": {
                        "type": "object",
                        "properties": {
                            "savedTo": {"type": "string"}
                        }
                    }
                }
            }
        ),
        Tool(
            name="get_document_type",
            description="Determine if the active document is parametric or direct modeling",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
                "_meta": {
                    "schemaVersion": SCHEMA_VERSION,
                    "returnSchema": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "designHistoryEnabled": {"type": "boolean"}
                        }
                    }
                }
            }
        ),
        
        # Phase 1 - Inspection tools  
        Tool(
            name="get_document_structure",
            description="Get structural overview of components and bodies in the document",
            inputSchema={
                "type": "object",
                "properties": {
                    "detail": {
                        "type": "string",
                        "enum": ["low", "high"],
                        "default": "low",
                        "description": "Detail level for structure information"
                    }
                },
                "required": [],
                "_meta": {
                    "schemaVersion": SCHEMA_VERSION,
                    "returnSchema": {
                        "type": "object",
                        "properties": {
                            "components": {"type": "array"},
                            "bodies": {"type": "array"}
                        }
                    }
                }
            }
        ),
        Tool(
            name="measure_geometry",
            description="Measure basic properties of geometry (bodies, faces, edges)",
            inputSchema={
                "type": "object",
                "properties": {
                    "refs": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "component": {"type": "string"},
                                "body": {"type": "string"}
                            },
                            "required": ["type", "component", "body"]
                        },
                        "description": "Array of geometry references to measure"
                    }
                },
                "required": ["refs"],
                "_meta": {
                    "schemaVersion": SCHEMA_VERSION,
                    "returnSchema": {
                        "type": "object",
                        "properties": {
                            "measurements": {"type": "array"}
                        }
                    }
                }
            }
        ),
        
        # Phase 2 - Core Parametrics tools
        Tool(
            name="update_parameter",
            description="Update an existing user parameter's expression and optionally its unit",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the parameter to update"
                    },
                    "expression": {
                        "type": "string", 
                        "description": "New expression for the parameter (optional)"
                    },
                    "unit": {
                        "type": "string",
                        "description": "Optional new unit for the parameter"
                    },
                    "comment": {
                        "type": "string",
                        "description": "Optional new comment for the parameter"
                    }
                },
                "required": ["name"],
                "_meta": {
                    "schemaVersion": SCHEMA_VERSION,
                    "returnSchema": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "expression": {"type": "string"},
                            "unit": {"type": "string"},
                            "comment": {"type": "string"}
                        }
                    }
                }
            }
        ),
        Tool(
            name="add_constraints",
            description="Apply geometric constraints in a sketch (basic: horizontal, vertical, parallel, perpendicular, tangent)",
            inputSchema={
                "type": "object",
                "properties": {
                    "sketch": {
                        "type": "string",
                        "description": "Name of the target sketch"
                    },
                    "type": {
                        "type": "string", 
                        "enum": ["horizontal", "vertical", "parallel", "perpendicular", "tangent", "coincident"],
                        "description": "Type of constraint to apply"
                    },
                    "refs": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "sketch": {"type": "string", "description": "Sketch name"},
                                "type": {"type": "string", "enum": ["line", "arc", "circle"], "description": "Entity type"},
                                "index": {"type": "integer", "minimum": 0, "description": "Entity index"}
                            },
                            "required": ["sketch", "type", "index"]
                        },
                        "description": "Array of entity references for the constraint"
                    }
                },
                "required": ["sketch", "type", "refs"],
                "_meta": {
                    "schemaVersion": SCHEMA_VERSION,
                    "returnSchema": {
                        "type": "object",
                        "properties": {
                            "applied": {"type": "boolean"}
                        }
                    }
                }
            }
        ),
        Tool(
            name="add_dimension_distance",
            description="Add a distance dimension in a sketch (v0: point-point only)",
            inputSchema={
                "type": "object",
                "properties": {
                    "sketch": {
                        "type": "string",
                        "description": "Name of the target sketch"
                    },
                    "a": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "enum": ["point"]},
                            "ref": {
                                "type": "object",
                                "properties": {
                                    "x": {"type": "number"},
                                    "y": {"type": "number"}
                                },
                                "required": ["x", "y"]
                            }
                        },
                        "required": ["type", "ref"],
                        "description": "First point for dimension"
                    },
                    "b": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "enum": ["point"]},
                            "ref": {
                                "type": "object",
                                "properties": {
                                    "x": {"type": "number"},
                                    "y": {"type": "number"}
                                },
                                "required": ["x", "y"]
                            }
                        },
                        "required": ["type", "ref"],
                        "description": "Second point for dimension"
                    },
                    "orientation": {
                        "type": "string",
                        "enum": ["horizontal", "vertical", "aligned"],
                        "description": "Dimension orientation"
                    },
                    "expression": {
                        "type": "string",
                        "description": "Expression for the dimension (can reference parameters)"
                    }
                },
                "required": ["sketch", "a", "b", "orientation", "expression"],
                "_meta": {
                    "schemaVersion": SCHEMA_VERSION,
                    "returnSchema": {
                        "type": "object",
                        "properties": {
                            "dimensionName": {"type": "string"}
                        }
                    }
                }
            }
        ),

        # Sheet Metal Workflow Tools
        Tool(
            name="create_sketch_from_face",
            description="Create a new sketch on an existing face of a body (essential for sheet metal bend line preparation)",
            inputSchema={
                "type": "object",
                "properties": {
                    "faceRef": {
                        "type": "object",
                        "properties": {
                            "component": {"type": "string", "description": "Component name"},
                            "body": {"type": "string", "description": "Body name"},
                            "faceIndex": {"type": "integer", "minimum": 0, "description": "Face index on the body"}
                        },
                        "required": ["component", "body", "faceIndex"],
                        "description": "Reference to the target face"
                    },
                    "name": {
                        "type": "string",
                        "description": "Name for the new sketch (must be unique)"
                    }
                },
                "required": ["faceRef", "name"],
                "_meta": {
                    "schemaVersion": SCHEMA_VERSION,
                    "returnSchema": {
                        "type": "object",
                        "properties": {
                            "sketchName": {"type": "string"}
                        }
                    }
                }
            }
        ),
        Tool(
            name="project_edges",
            description="Project edges from a face or specific edges onto a sketch",
            inputSchema={
                "type": "object",
                "properties": {
                    "sketch": {
                        "type": "string",
                        "description": "Name of the target sketch"
                    },
                    "faceRef": {
                        "type": "object",
                        "properties": {
                            "component": {"type": "string"},
                            "body": {"type": "string"},
                            "faceIndex": {"type": "integer", "minimum": 0}
                        },
                        "description": "Project all edges of this face (provide faceRef OR edgeRefs, not both)"
                    },
                    "edgeRefs": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "component": {"type": "string"},
                                "body": {"type": "string"},
                                "edgeIndex": {"type": "integer", "minimum": 0}
                            },
                            "required": ["component", "body", "edgeIndex"]
                        },
                        "description": "Project specific edges (provide faceRef OR edgeRefs, not both)"
                    }
                },
                "required": ["sketch"],
                "_meta": {
                    "schemaVersion": SCHEMA_VERSION,
                    "returnSchema": {
                        "type": "object",
                        "properties": {
                            "projectedCount": {"type": "integer"}
                        }
                    }
                }
            }
        ),
        Tool(
            name="set_is_construction",
            description="Mark a sketch entity (line) as construction geometry. Construction lines are used for reference and don't create solid geometry.",
            inputSchema={
                "type": "object",
                "properties": {
                    "sketch": {
                        "type": "string",
                        "description": "Name of the sketch containing the entity"
                    },
                    "entityRef": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "enum": ["line"], "description": "Entity type (v0 supports line only)"},
                            "index": {"type": "integer", "minimum": 0, "description": "Index of the entity in the sketch"}
                        },
                        "required": ["type", "index"],
                        "description": "Reference to the sketch entity"
                    },
                    "value": {
                        "type": "boolean",
                        "description": "True to mark as construction, false to mark as regular geometry"
                    }
                },
                "required": ["sketch", "entityRef", "value"],
                "_meta": {
                    "schemaVersion": SCHEMA_VERSION,
                    "returnSchema": {
                        "type": "object",
                        "properties": {
                            "updated": {"type": "boolean"}
                        }
                    }
                }
            }
        ),
        Tool(
            name="trigger_ui_command",
            description="Trigger a Fusion 360 UI command/dialog by its command ID. Use for operations that cannot be fully automated via API (e.g., Convert to Sheet Metal). The command opens a dialog for user interaction.",
            inputSchema={
                "type": "object",
                "properties": {
                    "command_id": {
                        "type": "string",
                        "description": "Fusion 360 command ID (use Text Commands Shift+S to discover IDs)"
                    },
                    "message": {
                        "type": "string",
                        "description": "Optional guidance message for the user about what to do in the dialog"
                    }
                },
                "required": ["command_id"],
                "_meta": {
                    "schemaVersion": SCHEMA_VERSION,
                    "returnSchema": {
                        "type": "object",
                        "properties": {
                            "triggered": {"type": "boolean"},
                            "command_id": {"type": "string"},
                            "guidance": {"type": "string"}
                        }
                    }
                }
            }
        )
    ]



# Dispatcher handlers (refactor of long if/elif)
from typing import Awaitable, Callable

Handler = Callable[[dict, str], Awaitable[List[TextContent]]]

async def _handle_get_design_info(arguments: dict, request_id: str) -> List[TextContent]:
    try:
        validated_args = GetDesignInfoArgs(**arguments)
    except ValidationError as e:
        logger.error(f"[{request_id}] Validation error: {str(e)}")
        return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
    result = await bridge.execute_action("get_design_info", validated_args.dict(), request_id=request_id)
    logger.info(f"[{request_id}] get_design_info completed successfully")
    return create_json_response(result)

async def _handle_create_parameter(arguments: dict, request_id: str) -> List[TextContent]:
    try:
        validated_args = CreateParameterArgs(**arguments)
    except ValidationError as e:
        logger.error(f"[{request_id}] Validation error: {str(e)}")
        return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
    args_payload = validated_args.dict(exclude_none=True)
    if "comment" not in args_payload:
        default_comment = f"Controls {validated_args.name}. Units: {validated_args.unit}.\n@tags: parameter"
        args_payload["comment"] = default_comment
    result = await bridge.execute_action("create_parameter", args_payload, request_id=request_id)
    logger.info(f"[{request_id}] create_parameter completed successfully")
    return create_json_response({
        "message": "Parameter created successfully",
        "parameter": result
    })

async def _handle_create_sketch(arguments: dict, request_id: str) -> List[TextContent]:
    try:
        validated_args = CreateSketchArgs(**arguments)
    except ValidationError as e:
        logger.error(f"[{request_id}] Validation error: {str(e)}")
        return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
    result = await bridge.execute_action("create_sketch", validated_args.dict(), request_id=request_id)
    logger.info(f"[{request_id}] create_sketch completed successfully")
    return create_json_response({
        "message": "Sketch created successfully",
        "sketch": result
    })

async def _handle_sketch_draw_line(arguments: dict, request_id: str) -> List[TextContent]:
    try:
        validated_args = SketchDrawLineArgs(**arguments)
    except ValidationError as e:
        logger.error(f"[{request_id}] Validation error: {str(e)}")
        return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
    result = await bridge.execute_action("sketch_draw_line", validated_args.dict(), request_id=request_id)
    logger.info(f"[{request_id}] sketch_draw_line completed successfully")
    return create_json_response({
        "message": "Line drawn successfully",
        "line": result
    })

async def _handle_sketch_draw_circle(arguments: dict, request_id: str) -> List[TextContent]:
    try:
        validated_args = SketchDrawCircleArgs(**arguments)
    except ValidationError as e:
        logger.error(f"[{request_id}] Validation error: {str(e)}")
        return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
    result = await bridge.execute_action("sketch_draw_circle", validated_args.dict(), request_id=request_id)
    logger.info(f"[{request_id}] sketch_draw_circle completed successfully")
    return create_json_response({
        "message": "Circle drawn successfully",
        "circle": result
    })

async def _handle_sketch_draw_rectangle(arguments: dict, request_id: str) -> List[TextContent]:
    try:
        validated_args = SketchDrawRectangleArgs(**arguments)
    except ValidationError as e:
        logger.error(f"[{request_id}] Validation error: {str(e)}")
        return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
    result = await bridge.execute_action("sketch_draw_rectangle", validated_args.dict(), request_id=request_id)
    logger.info(f"[{request_id}] sketch_draw_rectangle completed successfully")
    return create_json_response({
        "message": "Rectangle drawn successfully",
        "rectangle": result
    })

async def _handle_extrude_profile(arguments: dict, request_id: str) -> List[TextContent]:
    try:
        validated_args = ExtrudeProfileArgs(**arguments)
    except ValidationError as e:
        logger.error(f"[{request_id}] Validation error: {str(e)}")
        return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
    result = await bridge.execute_action("extrude_profile", validated_args.dict(), request_id=request_id)
    logger.info(f"[{request_id}] extrude_profile completed successfully")
    return create_json_response({
        "message": "Profile extruded successfully",
        "extrude": result
    })

async def _handle_list_open_documents(arguments: dict, request_id: str) -> List[TextContent]:
    try:
        validated_args = ListOpenDocumentsArgs(**arguments)
    except ValidationError as e:
        logger.error(f"[{request_id}] Validation error: {str(e)}")
        return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
    result = await bridge.execute_action("list_open_documents", validated_args.dict(), request_id=request_id)
    logger.info(f"[{request_id}] list_open_documents completed successfully")
    return create_json_response(result)

async def _handle_get_open_document_info(arguments: dict, request_id: str) -> List[TextContent]:
    try:
        validated_args = GetOpenDocumentInfoArgs(**arguments)
    except ValidationError as e:
        logger.error(f"[{request_id}] Validation error: {str(e)}")
        return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
    result = await bridge.execute_action("get_open_document_info", validated_args.dict(), request_id=request_id)
    logger.info(f"[{request_id}] get_open_document_info completed successfully")
    return create_json_response(result)

async def _handle_open_document(arguments: dict, request_id: str) -> List[TextContent]:
    try:
        validated_args = OpenDocumentArgs(**arguments)
    except ValidationError as e:
        logger.error(f"[{request_id}] Validation error: {str(e)}")
        return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
    result = await bridge.execute_action("open_document", validated_args.dict(), request_id=request_id)
    logger.info(f"[{request_id}] open_document completed successfully")
    return create_json_response({
        "message": "Document opened successfully",
        "document": result
    })

async def _handle_focus_document(arguments: dict, request_id: str) -> List[TextContent]:
    try:
        validated_args = FocusDocumentArgs(**arguments)
    except ValidationError as e:
        logger.error(f"[{request_id}] Validation error: {str(e)}")
        return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
    result = await bridge.execute_action("focus_document", validated_args.dict(), request_id=request_id)
    logger.info(f"[{request_id}] focus_document completed successfully")
    return create_json_response({
        "message": "Document focused successfully",
        "document": result
    })

async def _handle_close_document(arguments: dict, request_id: str) -> List[TextContent]:
    try:
        validated_args = CloseDocumentArgs(**arguments)
    except ValidationError as e:
        logger.error(f"[{request_id}] Validation error: {str(e)}")
        return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
    result = await bridge.execute_action("close_document", validated_args.dict(), request_id=request_id)
    logger.info(f"[{request_id}] close_document completed successfully")
    return create_json_response({
        "message": "Document closed successfully",
        "result": result
    })

async def _handle_backup_document(arguments: dict, request_id: str) -> List[TextContent]:
    try:
        validated_args = BackupDocumentArgs(**arguments)
    except ValidationError as e:
        logger.error(f"[{request_id}] Validation error: {str(e)}")
        return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
    result = await bridge.execute_action("backup_document", validated_args.dict(), request_id=request_id)
    logger.info(f"[{request_id}] backup_document completed successfully")
    return create_json_response({
        "message": "Document backed up successfully",
        "backup": result
    })

async def _handle_get_document_type(arguments: dict, request_id: str) -> List[TextContent]:
    try:
        validated_args = GetDocumentTypeArgs(**arguments)
    except ValidationError as e:
        logger.error(f"[{request_id}] Validation error: {str(e)}")
        return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
    result = await bridge.execute_action("get_document_type", validated_args.dict(), request_id=request_id)
    logger.info(f"[{request_id}] get_document_type completed successfully")
    return create_json_response(result)

async def _handle_get_document_structure(arguments: dict, request_id: str) -> List[TextContent]:
    try:
        validated_args = GetDocumentStructureArgs(**arguments)
    except ValidationError as e:
        logger.error(f"[{request_id}] Validation error: {str(e)}")
        return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
    result = await bridge.execute_action("get_document_structure", validated_args.dict(), request_id=request_id)
    logger.info(f"[{request_id}] get_document_structure completed successfully")
    return create_json_response(result)

async def _handle_measure_geometry(arguments: dict, request_id: str) -> List[TextContent]:
    try:
        validated_args = MeasureGeometryArgs(**arguments)
    except ValidationError as e:
        logger.error(f"[{request_id}] Validation error: {str(e)}")
        return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
    result = await bridge.execute_action("measure_geometry", validated_args.dict(), request_id=request_id)
    logger.info(f"[{request_id}] measure_geometry completed successfully")
    return create_json_response(result)

async def _handle_update_parameter(arguments: dict, request_id: str) -> List[TextContent]:
    try:
        validated_args = UpdateParameterArgs(**arguments)
    except ValidationError as e:
        logger.error(f"[{request_id}] Validation error: {str(e)}")
        return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
    result = await bridge.execute_action("update_parameter", validated_args.dict(exclude_none=True), request_id=request_id)
    logger.info(f"[{request_id}] update_parameter completed successfully")
    return create_json_response(result)

async def _handle_add_constraints(arguments: dict, request_id: str) -> List[TextContent]:
    try:
        validated_args = AddConstraintsArgs(**arguments)
    except ValidationError as e:
        logger.error(f"[{request_id}] Validation error: {str(e)}")
        return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
    result = await bridge.execute_action("add_constraints", validated_args.dict(), request_id=request_id)
    logger.info(f"[{request_id}] add_constraints completed successfully")
    return create_json_response(result)

async def _handle_add_dimension_distance(arguments: dict, request_id: str) -> List[TextContent]:
    try:
        validated_args = AddDimensionDistanceArgs(**arguments)
    except ValidationError as e:
        logger.error(f"[{request_id}] Validation error: {str(e)}")
        return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
    result = await bridge.execute_action("add_dimension_distance", validated_args.dict(), request_id=request_id)
    logger.info(f"[{request_id}] add_dimension_distance completed successfully")
    return create_json_response(result)

async def _handle_revolve_profile(arguments: dict, request_id: str) -> List[TextContent]:
    # Forward raw args to bridge; validation handled by bridge for this tool
    result = await bridge.execute_action("revolve_profile", arguments, request_id=request_id)
    logger.info(f"[{request_id}] revolve_profile completed successfully")
    return create_json_response(result)

async def _handle_combine_bodies(arguments: dict, request_id: str) -> List[TextContent]:
    try:
        validated_args = CombineBodiesArgs(**arguments)
    except ValidationError as e:
        logger.error(f"[{request_id}] Validation error: {str(e)}")
        return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
    result = await bridge.execute_action("combine_bodies", validated_args.dict(exclude_none=True), request_id=request_id)
    logger.info(f"[{request_id}] combine_bodies completed successfully")
    return create_json_response(result)

async def _handle_rotate_body(arguments: dict, request_id: str) -> List[TextContent]:
    try:
        validated_args = RotateBodyArgs(**arguments)
    except ValidationError as e:
        logger.error(f"[{request_id}] Validation error: {str(e)}")
        return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
    result = await bridge.execute_action("rotate_body", validated_args.dict(exclude_none=True), request_id=request_id)
    logger.info(f"[{request_id}] rotate_body completed successfully")
    return create_json_response(result)

# Sheet Metal Workflow handlers
async def _handle_create_sketch_from_face(arguments: dict, request_id: str) -> List[TextContent]:
    try:
        validated_args = CreateSketchFromFaceArgs(**arguments)
    except ValidationError as e:
        logger.error(f"[{request_id}] Validation error: {str(e)}")
        return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
    result = await bridge.execute_action("create_sketch_from_face", validated_args.dict(), request_id=request_id)
    logger.info(f"[{request_id}] create_sketch_from_face completed successfully")
    return create_json_response({
        "message": "Sketch created on face successfully",
        "sketch": result
    })

async def _handle_project_edges(arguments: dict, request_id: str) -> List[TextContent]:
    try:
        validated_args = ProjectEdgesArgs(**arguments)
    except ValidationError as e:
        logger.error(f"[{request_id}] Validation error: {str(e)}")
        return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
    result = await bridge.execute_action("project_edges", validated_args.dict(exclude_none=True), request_id=request_id)
    logger.info(f"[{request_id}] project_edges completed successfully")
    return create_json_response(result)

async def _handle_set_is_construction(arguments: dict, request_id: str) -> List[TextContent]:
    try:
        validated_args = SetIsConstructionArgs(**arguments)
    except ValidationError as e:
        logger.error(f"[{request_id}] Validation error: {str(e)}")
        return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
    result = await bridge.execute_action("set_is_construction", validated_args.dict(), request_id=request_id)
    logger.info(f"[{request_id}] set_is_construction completed successfully")
    return create_json_response(result)

async def _handle_trigger_ui_command(arguments: dict, request_id: str) -> List[TextContent]:
    try:
        validated_args = TriggerUICommandArgs(**arguments)
    except ValidationError as e:
        logger.error(f"[{request_id}] Validation error: {str(e)}")
        return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
    result = await bridge.execute_action("trigger_ui_command", validated_args.dict(exclude_none=True), request_id=request_id)
    logger.info(f"[{request_id}] trigger_ui_command completed successfully")
    return create_json_response(result)

_TOOL_HANDLERS: dict[str, Handler] = {
    "get_design_info": _handle_get_design_info,
    "create_parameter": _handle_create_parameter,
    "create_sketch": _handle_create_sketch,
    "sketch_draw_line": _handle_sketch_draw_line,
    "sketch_draw_circle": _handle_sketch_draw_circle,
    "sketch_draw_rectangle": _handle_sketch_draw_rectangle,
    "extrude_profile": _handle_extrude_profile,
    # Phase 0
    "list_open_documents": _handle_list_open_documents,
    "get_open_document_info": _handle_get_open_document_info,
    "open_document": _handle_open_document,
    "focus_document": _handle_focus_document,
    "close_document": _handle_close_document,
    "backup_document": _handle_backup_document,
    "get_document_type": _handle_get_document_type,
    # Phase 1
    "get_document_structure": _handle_get_document_structure,
    "measure_geometry": _handle_measure_geometry,
    # Update parameter
    "update_parameter": _handle_update_parameter,
    # Phase 2 & 3
    "add_constraints": _handle_add_constraints,
    "add_dimension_distance": _handle_add_dimension_distance,
    "revolve_profile": _handle_revolve_profile,
    "combine_bodies": _handle_combine_bodies,
    "rotate_body": _handle_rotate_body,
    # Sheet Metal Workflow tools
    "create_sketch_from_face": _handle_create_sketch_from_face,
    "project_edges": _handle_project_edges,
    "set_is_construction": _handle_set_is_construction,
    "trigger_ui_command": _handle_trigger_ui_command,
}

@server.call_tool()
async def call_tool(name, arguments) -> List[TextContent]:
    """Handle tool calls"""
    try:
        tool_name = name or ""
        arguments = arguments or {}

        # Normalize namespaced tool names (e.g., "mcp__fusion360__get_design_info")
        if "__" in tool_name:
            tool_name = tool_name.split("__")[-1]
        
        # Generate request ID for traceability
        request_id = uuid.uuid4().hex[:8]  # Short ID for readability
        
        logger.info(f"[{request_id}] Calling tool: {tool_name} with args: {arguments}")
        # Registry-based dispatch
        handler = _TOOL_HANDLERS.get(tool_name)
        if handler is not None:
            return await handler(arguments, request_id)
        
        logger.error(f"[{request_id}] Unknown tool: {tool_name}")
        return create_error_response(f"Unknown tool: {tool_name}", "UNKNOWN_TOOL")
        
        # The following code is kept for reference only and is no longer executed
        # All tools have been migrated to the registry-based dispatch system
        if False and tool_name == "get_design_info":
            # Validate arguments
            try:
                validated_args = GetDesignInfoArgs(**arguments)
            except ValidationError as e:
                logger.error(f"[{request_id}] Validation error: {str(e)}")
                return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
            
            # Execute action with request ID
            result = await bridge.execute_action("get_design_info", validated_args.dict(), request_id=request_id)
            
            logger.info(f"[{request_id}] get_design_info completed successfully")
            return create_json_response(result)
            
        elif tool_name == "create_parameter":
            # Validate arguments
            try:
                validated_args = CreateParameterArgs(**arguments)
            except ValidationError as e:
                logger.error(f"[{request_id}] Validation error: {str(e)}")
                return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
            
            # Synthesize a default human-first comment if missing
            args_payload = validated_args.dict(exclude_none=True)
            if "comment" not in args_payload:
                default_comment = f"Controls {validated_args.name}. Units: {validated_args.unit}.\n@tags: parameter"
                args_payload["comment"] = default_comment

            # Execute action with request ID
            result = await bridge.execute_action("create_parameter", args_payload, request_id=request_id)
            
            logger.info(f"[{request_id}] create_parameter completed successfully")
            return create_json_response({
                "message": "Parameter created successfully",
                "parameter": result
            })
            
        elif tool_name == "create_sketch":
            # Validate arguments
            try:
                validated_args = CreateSketchArgs(**arguments)
            except ValidationError as e:
                logger.error(f"[{request_id}] Validation error: {str(e)}")
                return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
            
            # Execute action with request ID
            result = await bridge.execute_action("create_sketch", validated_args.dict(), request_id=request_id)
            
            logger.info(f"[{request_id}] create_sketch completed successfully")
            return create_json_response({
                "message": "Sketch created successfully",
                "sketch": result
            })
            
        elif tool_name == "sketch_draw_line":
            # Validate arguments
            try:
                validated_args = SketchDrawLineArgs(**arguments)
            except ValidationError as e:
                logger.error(f"[{request_id}] Validation error: {str(e)}")
                return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
            
            # Execute action with request ID
            result = await bridge.execute_action("sketch_draw_line", validated_args.dict(), request_id=request_id)
            
            logger.info(f"[{request_id}] sketch_draw_line completed successfully")
            return create_json_response({
                "message": "Line drawn successfully",
                "line": result
            })
            
        elif tool_name == "sketch_draw_circle":
            # Validate arguments
            try:
                validated_args = SketchDrawCircleArgs(**arguments)
            except ValidationError as e:
                logger.error(f"[{request_id}] Validation error: {str(e)}")
                return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
            
            # Execute action with request ID
            result = await bridge.execute_action("sketch_draw_circle", validated_args.dict(), request_id=request_id)
            
            logger.info(f"[{request_id}] sketch_draw_circle completed successfully")
            return create_json_response({
                "message": "Circle drawn successfully",
                "circle": result
            })
            
        elif tool_name == "sketch_draw_rectangle":
            # Validate arguments
            try:
                validated_args = SketchDrawRectangleArgs(**arguments)
            except ValidationError as e:
                logger.error(f"[{request_id}] Validation error: {str(e)}")
                return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
            
            # Execute action with request ID
            result = await bridge.execute_action("sketch_draw_rectangle", validated_args.dict(), request_id=request_id)
            
            logger.info(f"[{request_id}] sketch_draw_rectangle completed successfully")
            return create_json_response({
                "message": "Rectangle drawn successfully",
                "rectangle": result
            })
            
        elif tool_name == "extrude_profile":
            # Validate arguments
            try:
                validated_args = ExtrudeProfileArgs(**arguments)
            except ValidationError as e:
                logger.error(f"[{request_id}] Validation error: {str(e)}")
                return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
            
            # Execute action with request ID
            result = await bridge.execute_action("extrude_profile", validated_args.dict(), request_id=request_id)
            
            logger.info(f"[{request_id}] extrude_profile completed successfully")
            return create_json_response({
                "message": "Profile extruded successfully",
                "extrude": result
            })
        
        # Phase 0 - Foundation tools
        elif tool_name == "list_open_documents":
            try:
                validated_args = ListOpenDocumentsArgs(**arguments)
            except ValidationError as e:
                logger.error(f"[{request_id}] Validation error: {str(e)}")
                return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
            
            result = await bridge.execute_action("list_open_documents", validated_args.dict(), request_id=request_id)
            logger.info(f"[{request_id}] list_open_documents completed successfully")
            return create_json_response(result)
        
        elif tool_name == "get_open_document_info":
            try:
                validated_args = GetOpenDocumentInfoArgs(**arguments)
            except ValidationError as e:
                logger.error(f"[{request_id}] Validation error: {str(e)}")
                return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
            
            result = await bridge.execute_action("get_open_document_info", validated_args.dict(), request_id=request_id)
            logger.info(f"[{request_id}] get_open_document_info completed successfully")
            return create_json_response(result)
        
        elif tool_name == "open_document":
            try:
                validated_args = OpenDocumentArgs(**arguments)
            except ValidationError as e:
                logger.error(f"[{request_id}] Validation error: {str(e)}")
                return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
            
            result = await bridge.execute_action("open_document", validated_args.dict(), request_id=request_id)
            logger.info(f"[{request_id}] open_document completed successfully")
            return create_json_response({
                "message": "Document opened successfully",
                "document": result
            })
        
        elif tool_name == "focus_document":
            try:
                validated_args = FocusDocumentArgs(**arguments)
            except ValidationError as e:
                logger.error(f"[{request_id}] Validation error: {str(e)}")
                return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
            
            result = await bridge.execute_action("focus_document", validated_args.dict(), request_id=request_id)
            logger.info(f"[{request_id}] focus_document completed successfully")
            return create_json_response({
                "message": "Document focused successfully",
                "document": result
            })
        
        elif tool_name == "close_document":
            try:
                validated_args = CloseDocumentArgs(**arguments)
            except ValidationError as e:
                logger.error(f"[{request_id}] Validation error: {str(e)}")
                return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
            
            result = await bridge.execute_action("close_document", validated_args.dict(), request_id=request_id)
            logger.info(f"[{request_id}] close_document completed successfully")
            return create_json_response({
                "message": "Document closed successfully",
                "result": result
            })
        
        elif tool_name == "backup_document":
            try:
                validated_args = BackupDocumentArgs(**arguments)
            except ValidationError as e:
                logger.error(f"[{request_id}] Validation error: {str(e)}")
                return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
            
            result = await bridge.execute_action("backup_document", validated_args.dict(), request_id=request_id)
            logger.info(f"[{request_id}] backup_document completed successfully")
            return create_json_response({
                "message": "Document backed up successfully",
                "backup": result
            })
        
        elif tool_name == "get_document_type":
            try:
                validated_args = GetDocumentTypeArgs(**arguments)
            except ValidationError as e:
                logger.error(f"[{request_id}] Validation error: {str(e)}")
                return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
            
            result = await bridge.execute_action("get_document_type", validated_args.dict(), request_id=request_id)
            logger.info(f"[{request_id}] get_document_type completed successfully")
            return create_json_response(result)
        
        # Phase 1 - Inspection tools
        elif tool_name == "get_document_structure":
            try:
                validated_args = GetDocumentStructureArgs(**arguments)
            except ValidationError as e:
                logger.error(f"[{request_id}] Validation error: {str(e)}")
                return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
            
            result = await bridge.execute_action("get_document_structure", validated_args.dict(), request_id=request_id)
            logger.info(f"[{request_id}] get_document_structure completed successfully")
            return create_json_response(result)
        
        elif tool_name == "measure_geometry":
            try:
                validated_args = MeasureGeometryArgs(**arguments)
            except ValidationError as e:
                logger.error(f"[{request_id}] Validation error: {str(e)}")
                return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
            
            result = await bridge.execute_action("measure_geometry", validated_args.dict(), request_id=request_id)
            logger.info(f"[{request_id}] measure_geometry completed successfully")
            return create_json_response(result)
        
        elif tool_name == "update_parameter":
            try:
                validated_args = UpdateParameterArgs(**arguments)
            except ValidationError as e:
                logger.error(f"[{request_id}] Validation error: {str(e)}")
                return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
            
            result = await bridge.execute_action("update_parameter", validated_args.dict(exclude_none=True), request_id=request_id)
            logger.info(f"[{request_id}] update_parameter completed successfully")
            return create_json_response(result)
        
        elif tool_name == "add_constraints":
            try:
                validated_args = AddConstraintsArgs(**arguments)
            except ValidationError as e:
                logger.error(f"[{request_id}] Validation error: {str(e)}")
                return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
            
            result = await bridge.execute_action("add_constraints", validated_args.dict(), request_id=request_id)
            logger.info(f"[{request_id}] add_constraints completed successfully")
            return create_json_response(result)
        
        elif tool_name == "add_dimension_distance":
            try:
                validated_args = AddDimensionDistanceArgs(**arguments)
            except ValidationError as e:
                logger.error(f"[{request_id}] Validation error: {str(e)}")
                return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
            
            result = await bridge.execute_action("add_dimension_distance", validated_args.dict(), request_id=request_id)
            logger.info(f"[{request_id}] add_dimension_distance completed successfully")
            return create_json_response(result)
        elif tool_name == "revolve_profile":
            # Forward to bridge; bridge validates axisRef/angle/operation and maps errors
            result = await bridge.execute_action("revolve_profile", arguments, request_id=request_id)
            logger.info(f"[{request_id}] revolve_profile completed successfully")
            return create_json_response(result)
        
        elif tool_name == "combine_bodies":
            try:
                validated_args = CombineBodiesArgs(**arguments)
            except ValidationError as e:
                logger.error(f"[{request_id}] Validation error: {str(e)}")
                return create_error_response(f"Validation error: {str(e)}", "VALIDATION_ERROR")
            
            result = await bridge.execute_action(
                "combine_bodies", validated_args.dict(exclude_none=True), request_id=request_id
            )
            logger.info(f"[{request_id}] combine_bodies completed successfully")
            return create_json_response(result)
            
        else:
            logger.error(f"[{request_id}] Unknown tool: {tool_name}")
            return create_error_response(f"Unknown tool: {tool_name}", "UNKNOWN_TOOL")
            
    except BridgeError as e:
        # Try to get request_id from local scope if available
        req_id = locals().get('request_id', 'unknown')
        logger.error(f"[{req_id}] Bridge error ({e.code}): {e.message}")
        
        error_details = {"bridge_code": e.code}
        if e.details:
            error_details["bridge_details"] = e.details
            
        return create_error_response(f"Bridge error ({e.code}): {e.message}", "BRIDGE_ERROR")
        
    except Exception as e:
        req_id = locals().get('request_id', 'unknown')
        logger.exception(f"[{req_id}] Unexpected error in call_tool")
        return create_error_response(f"Unexpected error: {str(e)}", "INTERNAL_ERROR")


async def main():
    """Main entry point"""
    logger.info(f"Starting Fusion 360 MCP Server v{SERVER_VERSION}")
    logger.info(f"Bridge URL: {BRIDGE_BASE_URL}")
    logger.info(f"Schema version: {SCHEMA_VERSION}")
    
    # Skip blocking health check to avoid startup delays in clients with short timeouts
    # Emit a quick readiness line to stderr for client logs
    print("[fusion360-mcp] READY", file=sys.stderr, flush=True)
    
    # Start the stdio server
    async with stdio_server() as streams:
        await server.run(streams[0], streams[1], server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
