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
- Python packages: `httpx`, `mcp`, `pydantic`
- **AgentBridge add-in must be manually installed in Fusion** (see plugin README)

**Quick Install:**
```
/plugin add cabinlab/claude-plugins --path ai-cad-fusion
pip install httpx mcp pydantic
```

Then install the AgentBridge add-in - see [ai-cad-fusion/README.md](ai-cad-fusion/README.md) for detailed instructions.

**Source:** [cabinlab/fusion360-agents](https://github.com/cabinlab/fusion360-agents)
