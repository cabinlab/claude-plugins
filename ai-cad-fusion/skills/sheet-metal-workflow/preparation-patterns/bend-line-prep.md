# Bend Line Preparation Pattern

**Status**: Preparation Pattern (requires manual completion)

The Fusion 360 API does NOT allow programmatic creation of sheet metal bends. However, we can prepare geometry so that creating the bend becomes a single-click operation.

## The Problem

User says: "Add a bend 50mm from the edge"

Without preparation:
- User must manually create a sketch
- Draw a line at the right position
- Hope they got the dimension right
- Then use the Bend tool

With preparation:
- We create the sketch on the correct face
- Draw a precisely positioned line
- Mark it as construction geometry
- User simply selects it with the Bend tool

## MCP Tool Sequence

### Step 1: Identify the Target Face

The bend line goes on a planar face of the body. Get the document structure to identify faces:

```
get_document_structure(detail="high")
```

Look for the face where the bend should occur (typically a large planar face).

### Step 2: Create Sketch on Face

```
create_sketch_from_face(
  faceRef={
    component: "RootComponent",
    body: "SheetBody",
    faceIndex: 0  // Index of the target face
  },
  name="BendLineSketch"
)
```

### Step 3: Draw the Bend Line

Draw a line spanning the face at the bend location:

```
sketch_draw_line(
  sketch="BendLineSketch",
  start={x: bend_distance, y: 0},
  end={x: bend_distance, y: face_width}
)
```

**Important**: The line must span the full width of the face for the Bend tool to recognize it.

### Step 4: Mark as Construction Geometry

Construction lines don't create solid geometry but ARE recognized by the Bend tool:

```
set_is_construction(
  sketch="BendLineSketch",
  entityRef={type: "line", index: 0},
  value=true
)
```

### Step 5: Add Parametric Dimension

Make the bend position adjustable:

```
add_dimension_distance(
  sketch="BendLineSketch",
  a={type: "point", ref: {x: 0, y: 0}},  // Sketch origin or reference
  b={type: "point", ref: {x: bend_distance, y: 0}},  // Bend line start
  orientation="horizontal",
  expression="bend_offset"  // Parameter name
)
```

### Step 6: Guide the User

After preparation, inform the user:

```
trigger_ui_command(
  command_id="SheetMetalBendCmd",  // Command ID may vary
  message="Select the prepared bend line in the BendLineSketch, then configure bend angle and radius"
)
```

Or provide manual guidance:
> "I've prepared a bend line at [position]. To complete:
> 1. Go to SHEET METAL > Bend
> 2. Click the construction line I created
> 3. Set your bend angle (typically 90 degrees)
> 4. Click OK"

## Example from Toboggan Design

```python
# Create bend line at fr_bend_section from front edge
bend_p1 = Point3D.create(fr_len * 0.5, 0, 0)
bend_p2 = Point3D.create(fr_len * 0.5, half_width, 0)
bend_line = lines.addByTwoPoints(bend_p1, bend_p2)
bend_line.isConstruction = True

# Dimension from origin to bend line
dim_bend = dims.addDistanceDimension(
    bend_line.startSketchPoint,
    origin_pt,
    DimensionOrientations.HorizontalDimensionOrientation,
    Point3D.create(fr_len/2.0, -fr_len/4.0, 0)
)
dim_bend.parameter.expression = 'fr_bend_section'
```

## Critical Details

### Line Position Accuracy

The line MUST be:
- On a planar face of the body
- Spanning the full width of the bend region
- Perpendicular to the bend direction

### Construction vs. Regular Geometry

**Always mark bend lines as construction**:
- Construction lines are visible but don't affect solid geometry
- The Bend tool specifically looks for construction lines
- Prevents accidental profile creation

### Multiple Bends

For multiple parallel bends:
1. Create all bend lines in the same sketch
2. Each gets its own dimension (can reference the same parameter)
3. User selects all lines at once in Bend tool

## What the User Does After Preparation

1. **SHEET METAL > Bend** (or the bend command)
2. **Select**: Click the prepared construction line(s)
3. **Configure**: Set bend angle (e.g., 90 degrees), bend radius
4. **Apply**: Click OK

Total user effort: 3-4 clicks instead of manually positioning geometry.
