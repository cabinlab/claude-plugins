# AI CAD Fusion - Claude Code Plugin

AI-powered CAD automation for Autodesk Fusion (formerly Fusion 360). Enables Claude to create parametric designs, sheet metal parts, and automate CAD workflows.

## Prerequisites

Before using this plugin, you need:

1. **Autodesk Fusion** installed and running
2. **uv** (Python package manager) - install from https://docs.astral.sh/uv/
3. **AgentBridge add-in** installed in Fusion

## Installation Steps

### Step 1: Install the Claude Code Plugin

```
/plugin add cabinlab/claude-plugins --path ai-cad-fusion
```

### Step 2: Install uv (if not already installed)

The MCP server uses `uv` to automatically manage Python dependencies. Install it:

**Windows (PowerShell):**
```powershell
irm https://astral.sh/uv/install.ps1 | iex
```

**WSL / macOS / Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Python dependencies (`httpx`, `mcp`, `pydantic`) are installed automatically on first run.

### Step 3: Install the AgentBridge Add-in in Fusion

This is the critical step that's often missed. The plugin includes a Fusion add-in that must be installed manually.

#### Find your Fusion Add-ins folder:

- **Windows:** `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns`
- **Mac:** `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns`

(Note: The folder path still uses "Fusion 360" for compatibility)

#### Copy the add-in:

1. Clone or download this repo
2. Copy the entire `fusion-addin` folder to your Add-ins directory
3. Rename it to `AgentBridge` (the folder name matters)

The result should look like:
```
AddIns/
└── AgentBridge/
    ├── AgentBridge.py
    ├── AgentBridge.manifest
    ├── config.py
    ├── core/
    ├── handlers/
    └── services/
```

#### Enable the add-in:

1. In Fusion 360, press **Shift+S** to open Scripts and Add-ins
2. Go to the **Add-ins** tab
3. Find **AgentBridge** in the list
4. Click **Run**
5. (Optional) Check "Run on Startup" to auto-start

### Step 4: Verify the Setup

1. Make sure Fusion is running with a design open
2. Make sure AgentBridge shows as "Running" in the Add-ins panel
3. In Claude Code, try asking Claude to "get design info"

If successful, Claude will return information about your current Fusion design.

## Troubleshooting

### "Cannot connect to Fusion 360 bridge"

This means the AgentBridge add-in isn't running:
- Is Fusion open?
- Check Scripts and Add-ins (Shift+S) > Add-ins tab
- Is AgentBridge listed and running?
- Try stopping and starting it again

### MCP Server fails to start

Check that `uv` is installed and working:
```bash
uv --version
```

If `uv` is not found, install it (see Step 2 above).

### WSL users: Connection issues

The add-in runs on Windows (inside Fusion), but Claude Code may run in WSL. The MCP server automatically tries to detect the Windows host IP. If it fails:

Set the environment variable before starting Claude Code:
```bash
export BRIDGE_BASE_URL="http://<windows-host-ip>:18080"
```

## Features

### MCP Tools

The plugin provides these tools for Claude:
- Design inspection (get_design_info, get_document_structure)
- Sketching (create_sketch, draw_line, draw_circle, draw_rectangle)
- 3D features (extrude_profile, revolve_profile, combine_bodies)
- Parameters (create_parameter, update_parameter)
- Sheet metal workflow support

### Skills

- **sheet-metal-workflow:** Guides Claude through sheet metal design patterns including bend line preparation, relief cuts, and conversion to sheet metal

## Architecture

```
Claude Code ──> MCP Server (Python) ──HTTP──> AgentBridge (Fusion Add-in) ──> Fusion API
```

The MCP server runs in Claude's environment. It communicates via HTTP with the AgentBridge add-in running inside Fusion on port 18080.

## Development

See the [](https://github.com/cabinlab/) repo for development documentation.
