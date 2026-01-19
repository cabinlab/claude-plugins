# Relief Cuts Pattern

**Status**: Fully Automatable

Relief cuts (also called kerfs or bend reliefs) allow sheet metal to bend cleanly without material interference. This is one of the few sheet metal operations that CAN be fully automated via the Fusion 360 API.

## When to Use

- Before bending sheet material
- At locations where bends would otherwise cause material collision
- When creating patterns of cuts for flexible bending (living hinges)

## Parameters to Establish

Before creating relief cuts, establish these parameters:

| Parameter | Description | Typical Values |
|-----------|-------------|----------------|
| `kerf` | Width of the cut slot | 0.125" - 0.375" (laser/waterjet dependent) |
| `cut_depth` | How deep the cut extends from the edge | Usually `(sheet_width - flat_section) / 2` |
| `bend_section` | Distance between cuts | Based on bend radius + material |

## MCP Tool Sequence

### Step 1: Create Parameters

```
create_parameter(name="kerf", expression="0.25 in", unit="mm")
create_parameter(name="cut_depth", expression="(sheet_width - flat_bottom_width) / 2", unit="mm")
create_parameter(name="bend_section", expression="4 in", unit="mm")
```

### Step 2: Create Sketch on Target Face

First, identify the face where cuts will be made (usually the top face of the sheet):

```
create_sketch_from_face(
  faceRef={component: "ComponentName", body: "BodyName", faceIndex: 0},
  name="ReliefCutSketch"
)
```

### Step 3: Draw Relief Rectangle

Draw a rectangle representing one relief cut:

```
sketch_draw_rectangle(
  sketch="ReliefCutSketch",
  origin={x: bend_section_value, y: sheet_edge_y},
  width=kerf_value,
  height=cut_depth_value
)
```

### Step 4: Add Dimensions (Parametric)

Make the rectangle parametric:

```
add_dimension_distance(
  sketch="ReliefCutSketch",
  a={type: "point", ref: {x: 0, y: 0}},
  b={type: "point", ref: {x: kerf_value, y: 0}},
  orientation="horizontal",
  expression="kerf"
)
```

### Step 5: Extrude as Cut

```
extrude_profile(
  sketch="ReliefCutSketch",
  profile_index=0,
  distance=sheet_thickness_value,
  operation="cut",
  direction="negative"
)
```

### Step 6: Pattern (if multiple cuts needed)

Use Fusion 360's rectangular pattern feature (not currently exposed via MCP - guide user or use native API).

## Example: Toboggan Relief Pattern

From the toboggan design:

```python
# Create kerf-width x cut-depth rectangle
slot_corner1 = Point3D.create(bend_section, half_width, 0)
slot_corner2 = Point3D.create(bend_section + kerf, half_width - cut_depth, 0)
lines.addTwoPointRectangle(slot_corner1, slot_corner2)

# Dimension to parameters
dim_kerf.parameter.expression = 'kerf'
dim_depth.parameter.expression = 'cut_depth'

# Extrude as cut
cut_input.setAllExtent(ExtentDirections.NegativeExtentDirection)
```

## Best Practices

1. **Always use parameters** - Makes the design adaptable to different materials/thicknesses
2. **Cut depth calculation** - For side-bending sheets: `cut_depth = (total_width - flat_section) / 2`
3. **Kerf width** - Match to your cutting process (laser: 0.125", waterjet: 0.25", plasma: 0.375")
4. **Pattern spacing** - Account for kerf width: `spacing = bend_section + kerf`

## What This Pattern Enables

After relief cuts are made, the user can:
1. Convert to sheet metal (manual step)
2. Add bends at each cut location (prepared lines help)
3. Create flat pattern for DXF export
