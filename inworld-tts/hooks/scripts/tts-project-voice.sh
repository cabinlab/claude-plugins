#!/bin/bash
# Per-project TTS voice assignment.
# Source this from any TTS hook to get PROJECT_VOICE and PROJECT_RATE.
# Override with INWORLD_TTS_VOICE env var for manual control.

VOICES=(Alex Ashley Clive Craig Deborah Dennis Olivia Sarah Timothy Wendy)
RATES=(1.1)

PROJECT_DIR=$(git -C "$PWD" rev-parse --show-toplevel 2>/dev/null || echo "$PWD")
HASH=$(printf '%s' "$PROJECT_DIR" | md5sum | cut -c1-8)
HASH_NUM=$((16#$HASH))

PROJECT_VOICE="${INWORLD_TTS_VOICE:-${VOICES[$((HASH_NUM % ${#VOICES[@]}))]}}"
PROJECT_RATE="${RATES[$(( (HASH_NUM / ${#VOICES[@]}) % ${#RATES[@]} ))]}"
