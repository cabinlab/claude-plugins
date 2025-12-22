# MCP Tool Reference for Sheet Metal Workflows

This document lists all available MCP tools relevant to sheet metal design workflows.

## Core Sketch Tools

### create_sketch
Create a new sketch on a construction plane.

```json
{
  "plane": "XY" | "YZ" | "XZ",
  "name": "SketchName"
}
```

**Returns**: `{name: string, plane: string}`

### create_sketch_from_face
Create a sketch on an existing face of a body. **Essential for sheet metal bend line preparation.**

```json
{
  "faceRef": {
    "component": "ComponentName",
    "body": "BodyName",
    "faceIndex": 0
  },
  "name": "SketchName"
}
```

**Returns**: `{sketchName: string}`

**Use case**: Creating sketches on sheet metal faces for bend lines, relief cuts, or additional features.

### sketch_draw_line
Draw a line in an existing sketch.

```json
{
  "sketch": "SketchName",
  "start": {"x": 0, "y": 0},
  "end": {"x": 100, "y": 0}
}
```

**Returns**: `{sketch: string, entity: {type: "line", index: number}}`

### sketch_draw_rectangle
Draw a rectangle in an existing sketch.

```json
{
  "sketch": "SketchName",
  "origin": {"x": 0, "y": 0},
  "width": 10,
  "height": 5
}
```

**Returns**: `{sketch: string, entity: {type: "rectangle", index: number}}`

**Use case**: Creating relief cut profiles.

### sketch_draw_circle
Draw a circle in an existing sketch.

```json
{
  "sketch": "SketchName",
  "center": {"x": 0, "y": 0},
  "radius": 5
}
```

**Returns**: `{sketch: string, entity: {type: "circle", index: number}}`

## Sketch Modification Tools

### set_is_construction
Mark a sketch entity as construction geometry. **Critical for bend line preparation.**

```json
{
  "sketch": "SketchName",
  "entityRef": {
    "type": "line",
    "index": 0
  },
  "value": true
}
```

**Returns**: `{updated: boolean}`

**Use case**: Bend lines should be marked as construction so they're recognized by the Bend tool but don't create solid geometry.

### project_edges
Project edges from a face or specific edges onto a sketch.

```json
{
  "sketch": "SketchName",
  "faceRef": {"component": "...", "body": "...", "faceIndex": 0}
}
```
OR
```json
{
  "sketch": "SketchName",
  "edgeRefs": [{"component": "...", "body": "...", "edgeIndex": 0}]
}
```

**Returns**: `{projectedCount: number}`

**Use case**: Projecting body edges to reference for positioning bend lines or cuts.

## Constraint & Dimension Tools

### add_constraints
Apply geometric constraints in a sketch.

```json
{
  "sketch": "SketchName",
  "type": "horizontal" | "vertical" | "parallel" | "perpendicular" | "tangent" | "coincident",
  "refs": [
    {"sketch": "SketchName", "type": "line", "index": 0}
  ]
}
```

**Returns**: `{applied: boolean}`

### add_dimension_distance
Add a distance dimension (point-to-point).

```json
{
  "sketch": "SketchName",
  "a": {"type": "point", "ref": {"x": 0, "y": 0}},
  "b": {"type": "point", "ref": {"x": 50, "y": 0}},
  "orientation": "horizontal" | "vertical" | "aligned",
  "expression": "bend_offset"
}
```

**Returns**: `{dimensionName: string}`

**Use case**: Making bend line positions parametric.

## Feature Tools

### extrude_profile
Extrude a profile to create or modify 3D geometry.

```json
{
  "sketch": "SketchName",
  "profile_index": 0,
  "distance": 10,
  "operation": "new_body" | "join" | "cut" | "intersect",
  "direction": "positive" | "negative" | "symmetric"
}
```

**Returns**: `{feature: {type: string, name: string}, bodies: [...], createdBodies: [...]}`

**Use case**: Creating relief cuts with `operation: "cut"`.

### combine_bodies
Combine target bodies with tool bodies.

```json
{
  "targets": [{"component": "...", "body": "TargetBody"}],
  "tools": [{"component": "...", "body": "ToolBody"}],
  "operation": "join" | "cut" | "intersect"
}
```

**Returns**: `{success: boolean}`

## Parameter Tools

### create_parameter
Create a user parameter.

```json
{
  "name": "kerf",
  "expression": "0.25 in",
  "unit": "mm",
  "comment": "Width of relief cuts"
}
```

**Returns**: `{name, expression, unit, comment}`

**Use case**: Creating parametric dimensions for kerf, bend section length, cut depth, etc.

### update_parameter
Update an existing parameter.

```json
{
  "name": "kerf",
  "expression": "0.375 in"
}
```

**Returns**: `{name, expression, unit, comment}`

## Inspection Tools

### get_design_info
Get information about the active design.

```json
{}
```

**Returns**: `{documentName, units, components, bodies, parameters}`

### get_document_structure
Get structural overview of components and bodies.

```json
{
  "detail": "low" | "high"
}
```

**Returns**: `{components: [...], bodies: [...]}`

**Use case**: Finding faces for creating sketches, identifying body structure.

### measure_geometry
Measure properties of geometry.

```json
{
  "refs": [
    {"type": "body", "component": "...", "body": "..."}
  ]
}
```

**Returns**: `{measurements: [...]}`

## UI Command Tools

### trigger_ui_command
Trigger a Fusion 360 UI command/dialog.

```json
{
  "command_id": "CommandID",
  "message": "Guidance for user"
}
```

**Returns**: `{triggered: boolean, command_id: string, guidance: string}`

**Use case**: Opening sheet metal dialogs like Convert to Sheet Metal, Bend, Flat Pattern.

**Note**: Command IDs must be discovered. Use Fusion 360's Text Commands (Shift+S) to find command IDs.

## Tool Availability Summary

| Tool | Status | Sheet Metal Relevance |
|------|--------|----------------------|
| `create_sketch` | Available | Base sketches |
| `create_sketch_from_face` | Available | **Critical** - bend line sketches |
| `sketch_draw_line` | Available | Bend lines |
| `sketch_draw_rectangle` | Available | Relief cuts |
| `sketch_draw_circle` | Available | Holes, lightening |
| `set_is_construction` | Available | **Critical** - mark bend lines |
| `project_edges` | Available | Reference geometry |
| `add_constraints` | Available | Sketch control |
| `add_dimension_distance` | Available | Parametric positioning |
| `extrude_profile` | Available | Relief cuts (cut operation) |
| `create_parameter` | Available | Parametric design |
| `get_document_structure` | Available | Finding faces |
| `trigger_ui_command` | Available | Opening dialogs |

## Tools NOT Available (API Limitations)

These operations cannot be automated and require manual user interaction:

- **Create Bend** - Use bend-line-prep pattern instead
- **Convert to Sheet Metal** - Use sm-conversion-prep pattern instead
- **Create Flange** - Manual operation
- **Unfold/Refold** - Manual operation
- **Create Flat Pattern** - trigger_ui_command or manual
- **Sheet Metal Rules** - Manual configuration
