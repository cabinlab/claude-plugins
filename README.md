# cabinlab Claude Code Plugins

Private marketplace for Claude Code plugins.

## Installation

```
/plugin marketplace add cabinlab/claude-plugins
```

## Available Plugins

### ai-cad-fusion

AI-powered CAD automation for Autodesk Fusion (formerly Fusion 360).

**Features:**
- MCP tools for Fusion automation (sketching, extrusions, parameters, etc.)
- Sheet metal workflow skill with preparation patterns
- Support for bend line preparation, relief cuts, and conversion guidance

**Requirements:**
- Autodesk Fusion installed
- [uv](https://docs.astral.sh/uv/) (Python dependencies are auto-installed)
- FusionMCPBridge add-in (MSI/PKG installer)

**Quick Install:**
```
/plugin add cabinlab/claude-plugins --path ai-cad-fusion
```

See [ai-cad-fusion/README.md](ai-cad-fusion/README.md) for full setup instructions including FusionMCPBridge installation.
