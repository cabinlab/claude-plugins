#!/bin/bash
# Voice-agent Layer 2 bash security hook (PreToolUse).
# Receives tool call JSON on stdin, outputs permission decision JSON.
#
# Checks:
# 1. Strip ANTHROPIC_API_KEY, CLAUDE_CODE_OAUTH_TOKEN from command env
# 2. Block /proc/self/environ reads
# 3. Warn/block curl, wget, nc to non-allowlisted hosts
# 4. Warn/block package installation (npm i, pip install, apt install)
# 5. Warn/block destructive filesystem operations (rm -rf /, chmod 777, etc.)
set -euo pipefail

INPUT=$(cat)

COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if [[ -z "$COMMAND" ]]; then
  exit 0
fi

# Helper: output a deny decision and exit
deny() {
  local reason="$1"
  jq -n --arg reason "$reason" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: $reason
    }
  }'
  exit 0
}

# --- Check 1: Strip credentials from env ---
# We cannot modify the command, but we can prepend unset commands.
# If the command references these env vars, block it.
if echo "$COMMAND" | grep -qE '\$ANTHROPIC_API_KEY|\$CLAUDE_CODE_OAUTH_TOKEN|\$\{ANTHROPIC_API_KEY\}|\$\{CLAUDE_CODE_OAUTH_TOKEN\}'; then
  deny "BLOCKED: Command references credential environment variables (ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN). These must not be used in bash commands."
fi

# --- Check 2: Block /proc/self/environ reads ---
if echo "$COMMAND" | grep -qE '/proc/self/environ|/proc/[0-9]+/environ'; then
  deny "BLOCKED: Reading /proc/*/environ is not allowed. This could expose sensitive environment variables."
fi

# --- Check 3: Warn/block network tools to non-allowlisted hosts ---
# Allowlisted hosts for network access
ALLOWED_HOSTS="api.anthropic.com|api.voyageai.com|api.github.com|api.groq.com|api.inworld.ai|api.telnyx.com|localhost|127.0.0.1"

if echo "$COMMAND" | grep -qE '\b(curl|wget|nc|netcat|ncat)\b'; then
  # Extract the target (rough heuristic: first URL or hostname after the command)
  TARGET=$(echo "$COMMAND" | grep -oE 'https?://[^/[:space:]]+' | head -1 | sed 's|https\?://||')
  if [[ -z "$TARGET" ]]; then
    TARGET=$(echo "$COMMAND" | grep -oE '(curl|wget|nc|netcat|ncat)[[:space:]]+[^[:space:]-]+' | head -1 | awk '{print $2}')
  fi

  if [[ -n "$TARGET" ]]; then
    # Strip port if present
    HOST=$(echo "$TARGET" | sed 's/:.*//')
    if ! echo "$HOST" | grep -qE "^($ALLOWED_HOSTS)$"; then
      deny "BLOCKED: Network request to '$HOST' is not in the allowlist. Allowed hosts: ${ALLOWED_HOSTS//|/, }. Use gateway APIs for external access."
    fi
  fi
fi

# --- Check 4: Warn/block package installation ---
if echo "$COMMAND" | grep -qE '\bnpm\s+(i|install|ci)\b|\bpip\s+install\b|\bpip3\s+install\b|\bapt\s+install\b|\bapt-get\s+install\b|\byarn\s+add\b|\bpnpm\s+(add|install)\b|\bbun\s+(add|install)\b'; then
  deny "BLOCKED: Package installation commands are not allowed in the agent runtime. Dependencies should be declared in project configuration and installed at build time."
fi

# --- Check 5: Warn/block destructive filesystem operations ---
# Block rm -rf on root or broad paths
if echo "$COMMAND" | grep -qE '\brm\s+-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+/($|\s)|\brm\s+-[a-zA-Z]*f[a-zA-Z]*r[a-zA-Z]*\s+/($|\s)'; then
  deny "BLOCKED: 'rm -rf /' or similar root-level destructive command detected."
fi

# Block chmod 777
if echo "$COMMAND" | grep -qE '\bchmod\s+777\b'; then
  deny "BLOCKED: 'chmod 777' sets world-writable permissions, which is a security risk."
fi

# Block mkfs, dd to devices, fdisk
if echo "$COMMAND" | grep -qE '\b(mkfs|fdisk)\b|\bdd\s.*of=/dev/'; then
  deny "BLOCKED: Destructive disk operations (mkfs, fdisk, dd to device) are not allowed."
fi

# Block /etc modifications
if echo "$COMMAND" | grep -qE '>\s*/etc/|tee\s+/etc/'; then
  deny "BLOCKED: Writing to /etc is not allowed in the agent runtime."
fi

# If all checks pass, allow (output nothing — default is to proceed)
exit 0
