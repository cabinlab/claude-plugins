# AI CAD Fusion - Claude Code Plugin

AI-powered CAD automation for Autodesk Fusion (formerly Fusion 360). Enables Claude to create parametric designs, sheet metal parts, and automate CAD workflows.

## Prerequisites

Before using this plugin, you need:

1. **Autodesk Fusion** installed and running
2. **uv** (Python package manager) - install from https://docs.astral.sh/uv/
3. **FusionMCPBridge** installed in Fusion (see Step 3)

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

### Step 3: Install FusionMCPBridge in Fusion

Download and run the installer for your platform:

| Platform | Download |
|----------|----------|
| **Windows** | [FusionMCPBridge-0.1.0-win64.msi](https://github.com/cabinlab/claude-plugins/releases/latest/download/FusionMCPBridge-0.1.0-win64.msi) |
| **macOS** | [FusionMCPBridge-0.1.0-macos.pkg](https://github.com/cabinlab/claude-plugins/releases/latest/download/FusionMCPBridge-0.1.0-macos.pkg) |

After installation, restart Fusion. FusionMCPBridge will start automatically on each launch.

### Step 4: Verify the Setup

1. Make sure Fusion is running with a design open
2. In Claude Code, try asking Claude to "get design info"

If successful, Claude will return information about your current Fusion design.

## Troubleshooting

### "Cannot connect to Fusion 360 bridge"

This means the FusionMCPBridge add-in isn't running:
- Is Fusion open?
- Did you restart Fusion after installing FusionMCPBridge?
- Check Scripts and Add-ins (Shift+S) > Add-ins tab
- Is FusionMCPBridge listed and running?
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
Claude Code ──> MCP Server (Python) ──HTTP──> FusionMCPBridge (Fusion Add-in) ──> Fusion API
```

The MCP server runs in Claude's environment. It communicates via HTTP with FusionMCPBridge running inside Fusion on port 18080.

## Development

### Dev Mode (Hot-Reload)

Dev mode allows hot-reloading code changes without restarting Fusion.

**Setup (once):**

Windows PowerShell:
```powershell
[Environment]::SetEnvironmentVariable("FUSIONMCP_DEV_PATH", "C:\path\to\claude-plugins\ai-cad-fusion\FusionMCPBridge.bundle\Contents", "User")
```

macOS/Linux:
```bash
# Add to ~/.bashrc or ~/.zshrc
export FUSIONMCP_DEV_PATH="$HOME/path/to/claude-plugins/ai-cad-fusion/FusionMCPBridge.bundle/Contents"
```

**Verify dev mode is active:**
```bash
curl http://127.0.0.1:18080/health
# Should show: "dev_mode": true, "dev_path": "..."
```

**Workflow:**
1. Edit code in `FusionMCPBridge.bundle/Contents/`
2. Hot-reload: `curl -X POST http://127.0.0.1:18080/dev/reload`
3. Test immediately - changes are live

**Disable dev mode:**
```powershell
# Windows
[Environment]::SetEnvironmentVariable("FUSIONMCP_DEV_PATH", $null, "User")
```

### MCP Server Changes

1. Edit `mcp-server/fusion_mcp_server.py`
2. Reload the plugin in Claude Code

### Building Installers

MSI and PKG installers are built automatically by GitHub Actions when changes are pushed to `FusionMCPBridge.bundle/` or `installer/`. See `.github/workflows/build-fusion-installers.yml`.
