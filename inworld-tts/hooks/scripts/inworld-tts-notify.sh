#!/bin/bash
# Inworld TTS notification hook for Claude Code
# Caches audio by message hash — repeated messages play instantly.
#
# Required env vars:
#   INWORLD_API_KEY  - Base64-encoded Inworld API credentials
#
# Optional env vars:
#   INWORLD_TTS_VOICE  - Voice ID (overrides auto-assignment)
#   INWORLD_TTS_MODEL  - Model ID (default: "inworld-tts-1.5-max")
set -euo pipefail

# Muted via /sound command
[[ -f /tmp/claude-tts-muted ]] && exit 0

INPUT=$(cat)
MESSAGE=$(echo "$INPUT" | jq -r '.message // empty')

if [[ -z "$MESSAGE" ]]; then
  exit 0
fi

if [[ -z "${INWORLD_API_KEY:-}" ]]; then
  exit 0
fi

# Remap verbose messages to short phrases
if [[ "$MESSAGE" =~ "permission to use" ]]; then
  TOOL=$(echo "$MESSAGE" | sed -n 's/.*permission to use \(.*\)/\1/p' | tr '[:upper:]' '[:lower:]')
  MESSAGE="waiting to ${TOOL}"
elif [[ "$MESSAGE" =~ "waiting for" || "$MESSAGE" =~ "idle" || "$MESSAGE" =~ "input" ]]; then
  MESSAGE="coding stalled"
fi

# Debounce — skip if we played anything within the last 40 seconds
LAST_PLAY="/tmp/claude-tts-last"
NOW=$(date +%s)
if [[ -f "$LAST_PLAY" ]]; then
  LAST=$(cat "$LAST_PLAY")
  if (( NOW - LAST < 40 )); then
    exit 0
  fi
fi

source "$(dirname "$0")/tts-project-voice.sh"
VOICE="$PROJECT_VOICE"
MODEL="${INWORLD_TTS_MODEL:-inworld-tts-1.5-max}"
CACHE_DIR="${HOME}/.cache/claude-tts"
mkdir -p "$CACHE_DIR"

# Hash message+voice+rate for cache key
HASH=$(printf '%s|%s|%s' "$MESSAGE" "$VOICE" "$PROJECT_RATE" | sha256sum | cut -d' ' -f1)
CACHED="${CACHE_DIR}/${HASH}.mp3"

# Cache hit — play immediately
if [[ -f "$CACHED" ]]; then
  date +%s > "$LAST_PLAY"
  ffplay -nodisp -autoexit -loglevel quiet -volume 70 "$CACHED" 2>/dev/null &
  wait $! 2>/dev/null || true
  exit 0
fi

# Cache miss — synthesize via API
MESSAGE="${MESSAGE:0:2000}"

RESPONSE=$(curl -sf --max-time 10 \
  -X POST "https://api.inworld.ai/tts/v1/voice" \
  -H "Authorization: Basic $INWORLD_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -n \
    --arg text "$MESSAGE" \
    --arg voice "$VOICE" \
    --arg model "$MODEL" \
    --argjson rate "$PROJECT_RATE" \
    '{
      text: $text,
      voiceId: $voice,
      modelId: $model,
      audioConfig: { audioEncoding: "MP3", sampleRateHertz: 22050, speakingRate: ($rate | tonumber) }
    }')" 2>/dev/null) || exit 0

AUDIO=$(echo "$RESPONSE" | jq -r '.audioContent // empty')
if [[ -z "$AUDIO" ]]; then
  exit 0
fi

echo "$AUDIO" | base64 -d > "$CACHED"

date +%s > "$LAST_PLAY"
ffplay -nodisp -autoexit -loglevel quiet -volume 70 "$CACHED" 2>/dev/null &
wait $! 2>/dev/null || true

exit 0
