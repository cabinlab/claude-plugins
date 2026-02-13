#!/bin/bash
# SubagentStop hook — speaks "subtask complete" when a subagent finishes.
# No debounce — always plays.
set -euo pipefail

# Muted via /sound command
[[ -f /tmp/claude-tts-muted ]] && exit 0

INPUT=$(cat)

# Only fire for real subagents (background/plugin agents have empty agent_type)
AGENT_TYPE=$(echo "$INPUT" | jq -r '.agent_type // empty')
if [[ -z "$AGENT_TYPE" ]]; then
  exit 0
fi

if [[ -z "${INWORLD_API_KEY:-}" ]]; then
  exit 0
fi

MESSAGE="subtask complete"
source "$(dirname "$0")/tts-project-voice.sh"
source "$(dirname "$0")/play-audio.sh"
VOICE="$PROJECT_VOICE"
MODEL="${INWORLD_TTS_MODEL:-inworld-tts-1.5-max}"
CACHE_DIR="${HOME}/.cache/claude-tts"
mkdir -p "$CACHE_DIR"

HASH=$(printf '%s|%s|%s' "$MESSAGE" "$VOICE" "$PROJECT_RATE" | sha256sum | cut -d' ' -f1)
CACHED="${CACHE_DIR}/${HASH}.mp3"

if [[ -f "$CACHED" ]]; then
  play_audio "$CACHED"
  exit 0
fi

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

play_audio "$CACHED"

exit 0
