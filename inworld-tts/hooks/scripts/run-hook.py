#!/usr/bin/env python3
"""Cross-platform hook launcher for bash scripts.

Converts Windows backslash paths to POSIX format before invoking bash.
Works on Windows (cmd.exe -> python3 -> bash), Linux, macOS, and WSL.
"""
import subprocess, sys, os, re

if len(sys.argv) < 2:
    sys.exit(1)

script = sys.argv[1]

# Convert Windows paths: C:\Users\... -> /c/Users/...
script = script.replace("\\", "/")
script = re.sub(r"^([A-Za-z]):", lambda m: "/" + m.group(1).lower(), script)

# Pass through hook environment and any extra args
result = subprocess.run(
    ["bash", script] + sys.argv[2:],
    env=os.environ,
)
sys.exit(result.returncode)
