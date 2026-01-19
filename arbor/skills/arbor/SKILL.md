---
name: arbor
description: Use when analyzing code relationships, checking refactoring impact/blast radius, understanding how functions connect across files, or explaining code flow. Use before renaming functions, modifying APIs, or making changes that could break callers.
---

# Arbor - Graph-Native Code Intelligence

Arbor builds a semantic graph of codebases where functions, classes, and imports are nodes, and dependencies are edges. Use it instead of grep/search when you need to understand how code connects.

## IMPORTANT: Check Project Status

**Always run this before using arbor commands:**
```bash
arbor status
```

If not initialized, run setup:
```bash
arbor init      # Creates .arbor/ config
arbor index     # Builds the graph
```

## Commands (require index)

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `arbor status` | Index health and stats | **Run first** to check if index exists |
| `arbor init` | Create .arbor/ config | Once per project, before indexing |
| `arbor index` | Build/update the graph | After init, or after major changes |
| `arbor refactor <name>` | Show blast radius | Before renaming/modifying anything |
| `arbor explain <name>` | Graph-backed explanation | Understanding how code flows |
| `arbor query <q>` | Search the graph | Finding related code |
| `arbor export` | Export graph to JSON | Analyze graph data directly |
| `arbor viz` | Launch visualizer | Visual exploration |
| `arbor check-health` | System diagnostics | Troubleshooting setup issues |

## Typical Workflows

### Before Refactoring
```bash
arbor refactor function_name    # See what breaks
arbor refactor ClassName        # Check class dependencies
```

### Understanding Code
```bash
arbor explain handleAuth        # How does auth flow work?
arbor query "database"          # Find database-related code
```

### Detailed Output
```bash
arbor refactor foo --json       # Machine-readable output
arbor refactor foo --why        # Explain reasoning
arbor export -o graph.json      # Export full graph for analysis
```

### Diagnostics
```bash
arbor status                    # Check if index exists and is current
arbor status --files            # Show detailed file statistics
arbor check-health              # Verify system setup
```

## Supported Languages

Rust, TypeScript, JavaScript, Python, Go, Java, C, C++, C#, Dart

## When to Use Arbor vs Other Tools

| Need | Tool |
|------|------|
| "What calls this function?" | `arbor refactor` |
| "What does this code do?" | `arbor explain` |
| "Find text pattern" | grep/Grep tool |
| "Find file by name" | glob/Glob tool |

## Tips

- Run `arbor index` after pulling major changes
- Use `--follow-symlinks` for monorepos with symlinked packages
- The graph persists in `.arbor/` - only modified files re-index
- If commands fail, run `arbor check-health` to diagnose setup issues
