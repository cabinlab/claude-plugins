# Arbor Plugin

Graph-native code intelligence for Claude Code using [arbor](https://github.com/Anandb71/arbor).

## What is Arbor?

Arbor builds a semantic graph of your codebase where functions, classes, and imports are nodes, and dependencies are edges. Instead of text search, it traces actual call graphs to understand code relationships.

## Installation

1. Install arbor via cargo:
   ```bash
   cargo install arbor-graph-cli
   ```

2. Install this plugin in Claude Code:
   ```
   /plugin install
   ```

## Usage

Initialize in your project:
```bash
arbor init
arbor index
```

Then ask Claude things like:
- "What would break if I rename this function?"
- "Explain how the authentication flow works"
- "Show me the blast radius of changing this API"

## Skill

This plugin provides an `arbor` skill that teaches Claude when and how to use arbor for:
- Impact/blast radius analysis before refactoring
- Understanding code relationships across files
- Graph-backed code explanations

## Supported Languages

Rust, TypeScript, JavaScript, Python, Go, Java, C, C++, C#, Dart
