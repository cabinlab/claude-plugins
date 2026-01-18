---
name: arbor
description: Use when analyzing code relationships, checking refactoring impact/blast radius, understanding how functions connect across files, or explaining code flow. Use before renaming functions, modifying APIs, or making changes that could break callers.
---

# Arbor - Graph-Native Code Intelligence

Arbor builds a semantic graph of codebases where functions, classes, and imports are nodes, and dependencies are edges. Use it instead of grep/search when you need to understand how code connects.

## Setup (once per project)

```bash
arbor init      # Creates .arbor/ config
arbor index     # Builds the graph (re-run after major changes)
```

## Core Commands

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `arbor refactor <name>` | Show blast radius | Before renaming/modifying anything |
| `arbor explain <name>` | Graph-backed explanation | Understanding how code flows |
| `arbor query <q>` | Search the graph | Finding related code |
| `arbor viz` | Launch visualizer | Visual exploration |

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
