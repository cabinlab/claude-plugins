---
name: sheet-metal-workflow
description: |
  Use when user mentions: sheet metal, bend, fold, flange, flat pattern, DXF export,
  relief cut, kerf, brake forming, fabrication, bent enclosure, sheet metal bracket.
  Provides preparation patterns for sheet metal operations that cannot be fully
  automated via Fusion 360 API due to intentional API limitations.
---

# Sheet Metal Workflow Skill

This skill teaches how to work with sheet metal designs in Fusion 360 using a **preparation-first strategy**. Due to intentional Fusion 360 API limitations, many sheet metal operations cannot be fully automated - but we can prepare geometry so manual operations become trivial.

## Core Insight: Preparation-First Strategy

Fusion 360's Sheet Metal API is NOT exposed (confirmed by Brian Ekins, Fusion API designer). We cannot programmatically:
- Create bends
- Convert bodies to sheet metal
- Create flanges
- Unfold/refold sheet metal

**What we CAN do**: Prepare geometry so the user completes the operation in one click.

### The Pattern

1. **Prepare**: Use MCP tools to create precisely positioned geometry
2. **Guide**: Tell the user exactly what to click
3. **Continue**: After manual step, continue automation

## Available Preparation Patterns

### 1. Bend Line Preparation
**When**: User wants to add a bend to sheet metal

Instead of trying to create a bend (impossible), we:
1. Create a sketch on the target face
2. Draw a line at the exact bend location
3. Mark it as construction geometry
4. Guide user: "Select this line with SHEET METAL > Bend tool"

See: [preparation-patterns/bend-line-prep.md](preparation-patterns/bend-line-prep.md)

### 2. Relief Cuts (Fully Automatable)
**When**: User needs relief cuts/kerfs for bending

This IS fully automatable:
1. Create sketch on face
2. Draw rectangle (kerf width x cut depth)
3. Extrude as cut through body
4. Pattern as needed

See: [preparation-patterns/relief-cuts.md](preparation-patterns/relief-cuts.md)

### 3. Sheet Metal Conversion Preparation
**When**: User wants to convert a solid body to sheet metal

We prepare by:
1. Ensuring body has uniform thickness
2. Adding relief cuts first (if needed)
3. Identifying the stationary face
4. Guiding user through Convert to Sheet Metal dialog

See: [preparation-patterns/sm-conversion-prep.md](preparation-patterns/sm-conversion-prep.md)

## Workflow Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    SHEET METAL WORKFLOW                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. CREATE BASE GEOMETRY                                     │
│     └─ Fully automated: sketch → extrude → solid body       │
│                                                              │
│  2. PREPARE FOR SHEET METAL                                  │
│     ├─ Add relief cuts (automated)                          │
│     ├─ Draw bend lines (automated preparation)              │
│     └─ Identify faces/features                              │
│                                                              │
│  3. CONVERT TO SHEET METAL ← Manual step                    │
│     └─ trigger_ui_command or guide user                     │
│                                                              │
│  4. ADD BENDS ← Manual steps                                │
│     └─ User clicks prepared bend lines                      │
│                                                              │
│  5. FLAT PATTERN                                            │
│     └─ trigger_ui_command or guide user                     │
│                                                              │
│  6. EXPORT                                                   │
│     └─ DXF export for fabrication                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## When to Use This Skill

Invoke this skill when the user's request involves:
- Designing parts that will be laser cut and bent
- Creating enclosures, brackets, or panels
- Working with sheet stock (aluminum, steel, UHMW, etc.)
- Mentioning flat patterns or DXF export
- Asking about bend allowance, K-factor, or relief cuts

## What This Skill Does NOT Cover

- Fully automated sheet metal creation (not possible via API)
- Sheet metal simulation/analysis
- Material-specific bend calculations (user must configure in Fusion)

## Tool Reference

See [tool-reference.md](tool-reference.md) for complete documentation of available MCP tools.

## Worked Example

See [examples/toboggan-workflow.md](examples/toboggan-workflow.md) for a complete real-world example based on the UHMW toboggan design.
