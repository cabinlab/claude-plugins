# Sheet Metal Conversion Preparation Pattern

**Status**: Preparation Pattern (requires manual completion)

Converting a solid body to sheet metal is a manual operation in Fusion 360. However, proper preparation ensures the conversion succeeds on the first try.

## The Problem

User says: "Convert this to sheet metal"

Without preparation:
- User opens Convert to Sheet Metal dialog
- Selects random face as stationary
- Conversion might fail due to non-uniform thickness
- Multiple trial-and-error attempts

With preparation:
- We verify body is suitable for conversion
- Add any needed relief cuts first
- Identify the best stationary face
- Guide user to correct dialog settings

## Prerequisites for Sheet Metal Conversion

A body can be converted to sheet metal if:

1. **Uniform Thickness**: The body must have consistent wall thickness
2. **Planar Faces**: At least one face must be planar (becomes the stationary face)
3. **No Internal Voids**: Solid body only
4. **Compatible Geometry**: Bends must be possible without self-intersection

## MCP Tool Sequence

### Step 1: Inspect the Body

```
get_document_structure(detail="high")
measure_geometry(refs=[{type: "body", component: "Component", body: "BodyName"}])
```

Verify:
- Body exists and is solid
- Check face count and types

### Step 2: Verify Thickness (Manual Check)

Currently, there's no MCP tool to measure thickness directly. Guide user:

> "Before conversion, verify your body has uniform thickness:
> 1. Use INSPECT > Section Analysis
> 2. Confirm all walls are the same thickness
> 3. Note the thickness value for the conversion dialog"

### Step 3: Add Relief Cuts if Needed

If the design requires bending, add relief cuts BEFORE conversion:

```
// See relief-cuts.md for full pattern
create_sketch_from_face(...)
sketch_draw_rectangle(...)
extrude_profile(..., operation="cut")
```

**Why before conversion?** Once converted to sheet metal, the body's features become constrained differently. It's easier to add relief cuts as solid operations.

### Step 4: Identify Stationary Face

The stationary face:
- Remains fixed during unfolding
- Should be the largest planar face
- Usually the "base" of the part

```
get_document_structure(detail="high")
```

Look for the largest planar face (often faceIndex 0 on main faces).

### Step 5: Create Reference Sketch (Optional)

To help the user identify the stationary face:

```
create_sketch_from_face(
  faceRef={component: "...", body: "...", faceIndex: N},
  name="StationaryFaceReference"
)
```

This visually highlights the face to select.

### Step 6: Guide the Conversion

```
trigger_ui_command(
  command_id="ConvertToSheetMetalCmd",  // Command ID may need verification
  message="Select the large flat face as the Stationary Face. Set thickness to match your material."
)
```

Or provide manual guidance:

> "To convert to sheet metal:
> 1. SHEET METAL > Convert to Sheet Metal (or right-click body > Convert to Sheet Metal)
> 2. Stationary Face: Select [identified face]
> 3. Thickness: Enter your material thickness (e.g., 0.25 in)
> 4. Sheet Metal Rule: Select or create appropriate rule
> 5. Click OK"

## Conversion Dialog Settings

Guide the user on these settings:

| Setting | Guidance |
|---------|----------|
| Stationary Face | The face that stays fixed when unfolding - usually the largest flat face |
| Thickness | Must match actual body thickness exactly |
| Sheet Metal Rule | Contains bend radius, relief settings - select or create appropriate rule |
| Direction | Usually doesn't matter for uniform bodies |

## Common Conversion Failures

### "Cannot convert - non-uniform thickness"
- Body has varying wall thickness
- Solution: Redesign with uniform thickness

### "Cannot convert - geometry too complex"
- Internal features prevent conversion
- Solution: Simplify internal geometry

### "Bend radius too small"
- Sheet metal rule has smaller bend radius than geometry
- Solution: Update sheet metal rule or redesign corners

## Example Workflow

```
1. User: "I have a box shape, convert it to sheet metal"

2. Agent checks:
   - get_document_structure() -> Finds body with 6 faces
   - Identifies largest planar face (bottom)

3. Agent prepares:
   - Optionally creates reference sketch on stationary face
   - Verifies no relief cuts needed (simple box)

4. Agent guides:
   "Your box is ready for sheet metal conversion:
   1. Go to SHEET METAL > Convert to Sheet Metal
   2. Select the bottom face as Stationary Face
   3. Enter thickness: [X] inches
   4. Use default sheet metal rules
   5. Click OK

   After conversion, you can unfold to create a flat pattern."
```

## After Conversion

Once converted, the body becomes a sheet metal body with:
- Bend features at corners
- Ability to create flat patterns
- Sheet metal-specific features available

The agent can then continue with:
- Adding bend lines (see bend-line-prep.md)
- Creating flat patterns
- Exporting DXF for fabrication
