# Worked Example: UHMW Toboggan Design

This example demonstrates a complete sheet metal workflow based on a real design: a UHMW (Ultra High Molecular Weight Polyethylene) toboggan with bendable sections.

## Design Overview

The toboggan is created from a single sheet of UHMW plastic that:
- Has a flat bottom section
- Bends up at the front (multiple bend sections)
- Bends up at the back (fewer bend sections)
- Uses relief cuts to allow the material to bend cleanly

## Parameters

```
sheet_width       = 60 in    (total width of sheet)
sheet_length      = 144 in   (12 feet)
flat_bottom_width = 48 in    (width of flat section)
sheet_thickness   = 0.25 in  (UHMW sheet thickness)
kerf              = 0.25 in  (waterjet cut width)
front_sections    = 9        (number of front bend sections)
back_sections     = 3        (number of back bend sections)
fr_bend_section   = 4 in     (length of each front section)
bk_bend_section   = 4 in     (length of each back section)
cut_depth         = (sheet_width - flat_bottom_width) / 2  (6 inches from edge)
```

## Workflow Steps

### Step 1: Create Parameters

Using MCP tools:

```json
// Create driving parameters
create_parameter({name: "sheet_width", expression: "60 in", unit: "mm"})
create_parameter({name: "sheet_length", expression: "144 in", unit: "mm"})
create_parameter({name: "flat_bottom_width", expression: "48 in", unit: "mm"})
create_parameter({name: "sheet_thickness", expression: "0.25 in", unit: "mm"})
create_parameter({name: "kerf", expression: "0.25 in", unit: "mm"})
create_parameter({name: "front_sections", expression: "9", unit: ""})
create_parameter({name: "fr_bend_section", expression: "4 in", unit: "mm"})

// Computed parameter
create_parameter({
  name: "cut_depth",
  expression: "(sheet_width - flat_bottom_width) / 2",
  unit: "mm",
  comment: "Depth of relief cuts from side toward center"
})
```

### Step 2: Create Base Sheet

```json
// Create sketch for base rectangle
create_sketch({plane: "XY", name: "BaseSheetSketch"})

// Draw rectangle (length x width)
sketch_draw_rectangle({
  sketch: "BaseSheetSketch",
  origin: {x: 0, y: 0},
  width: 3657.6,  // 144 inches in mm
  height: 1524    // 60 inches in mm
})

// Extrude to thickness
extrude_profile({
  sketch: "BaseSheetSketch",
  profile_index: 0,
  distance: 6.35,  // 0.25 inches in mm
  operation: "new_body"
})
```

### Step 3: Create Front Relief Pattern

First, identify the top face of the extruded body:

```json
get_document_structure({detail: "high"})
// Find the top planar face (normal pointing +Z)
```

Create sketch on top face:

```json
create_sketch_from_face({
  faceRef: {component: "RootComponent", body: "Body1", faceIndex: 0},
  name: "FrontReliefSketch"
})
```

Draw bend line (construction) and relief cut:

```json
// Bend line at fr_bend_section from front edge
sketch_draw_line({
  sketch: "FrontReliefSketch",
  start: {x: 101.6, y: 0},      // 4 inches = 101.6 mm
  end: {x: 101.6, y: 762}       // Spans half width (30 in = 762 mm)
})

// Mark as construction
set_is_construction({
  sketch: "FrontReliefSketch",
  entityRef: {type: "line", index: 0},
  value: true
})

// Relief cut rectangle starting at bend section
sketch_draw_rectangle({
  sketch: "FrontReliefSketch",
  origin: {x: 101.6, y: 762},   // At bend section, outer edge
  width: 6.35,                   // kerf = 0.25 in
  height: -152.4                 // cut_depth = 6 in (negative = toward center)
})
```

Dimension parametrically:

```json
add_dimension_distance({
  sketch: "FrontReliefSketch",
  a: {type: "point", ref: {x: 0, y: 0}},
  b: {type: "point", ref: {x: 101.6, y: 0}},
  orientation: "horizontal",
  expression: "fr_bend_section"
})
```

Extrude relief cut:

```json
extrude_profile({
  sketch: "FrontReliefSketch",
  profile_index: 0,  // The small rectangle profile
  distance: 6.35,
  operation: "cut",
  direction: "negative"
})
```

### Step 4: Pattern Relief Cuts

**Note**: Rectangular pattern is not currently exposed via MCP. Guide user:

> "I've created the first relief cut. To pattern it:
> 1. SOLID > Pattern > Rectangular Pattern
> 2. Select the extrusion feature
> 3. Direction: X axis (along length)
> 4. Quantity: `front_sections` (9)
> 5. Distance Type: Spacing
> 6. Distance: `fr_bend_section + kerf`
> 7. Click OK"

### Step 5: Create Back Relief Pattern

Similar process for back end, starting from `sheet_length - bk_bend_section`.

### Step 6: Mirror for Full Width

The design works on half the sheet (modeling efficiency). Mirror to create full width:

> "Mirror the body across the XZ plane (centerline) to create the full-width toboggan."

### Step 7: Sheet Metal Conversion (Manual)

With all relief cuts in place:

> "The toboggan geometry is ready for sheet metal conversion:
> 1. Right-click the body > Convert to Sheet Metal
> 2. Stationary Face: Select the large bottom face
> 3. Thickness: 0.25 in
> 4. Click OK
>
> After conversion, create bends using the construction lines I prepared."

### Step 8: Flat Pattern for Fabrication

> "To create a flat pattern for cutting:
> 1. SHEET METAL > Create Flat Pattern
> 2. Select the sheet metal body
> 3. Click OK
>
> Export the flat pattern as DXF for waterjet/laser cutting."

## Key Insights from This Example

### 1. Parametric Design is Critical

All dimensions reference parameters. Changing `sheet_width` automatically updates:
- The base rectangle
- The cut depth
- All relief cut positions

### 2. Relief Cuts Enable Bending

UHMW plastic doesn't bend like metal. The relief cuts act as "living hinges" allowing controlled bending without material stress.

### 3. Preparation Reduces Manual Work

Even though we can't automate:
- Sheet metal conversion
- Bend creation
- Pattern creation

We CAN prepare:
- Parametric geometry
- Precisely positioned construction lines
- Relief cut profiles

The user's manual work becomes "click what the agent prepared" rather than "figure out where everything goes."

### 4. Half-Model Strategy

Modeling half the part and mirroring:
- Reduces feature count
- Ensures symmetry
- Simplifies parameters

## Files Created in This Workflow

```
BaseSheetSketch       - Base rectangle profile
Body1                 - Extruded sheet body
FrontReliefSketch     - Front relief cuts + bend lines
BackReliefSketch      - Back relief cuts + bend lines
FrontReliefPattern    - Patterned front cuts (manual)
BackReliefPattern     - Patterned back cuts (manual)
```

## What the Agent Automated vs. Manual

| Step | Agent (MCP) | Manual |
|------|-------------|--------|
| Create parameters | Yes | |
| Create base sheet | Yes | |
| Create relief sketches | Yes | |
| Draw bend lines | Yes | |
| Mark as construction | Yes | |
| Draw relief rectangles | Yes | |
| Dimension parametrically | Yes | |
| Extrude first cut | Yes | |
| Pattern cuts | | Rectangular pattern |
| Mirror body | | Mirror feature |
| Convert to sheet metal | | Dialog |
| Add bends | | Click prepared lines |
| Create flat pattern | | Dialog |
| Export DXF | | Export command |

The agent handles the tedious, precise work. The user handles the operations Fusion 360's API intentionally doesn't expose.
