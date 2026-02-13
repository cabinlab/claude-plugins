#!/bin/bash
# PostToolUse hook — speaks "task complete" when a TaskUpdate sets status to completed.
# Speaks "all tasks finished" when all tasks in the session are done.
# No debounce — always plays.
set -euo pipefail

# Muted via /sound command
[[ -f /tmp/claude-tts-muted ]] && exit 0

INPUT=$(cat)

# Only fire for TaskUpdate
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')
if [[ "$TOOL_NAME" != "TaskUpdate" ]]; then
  exit 0
fi

# Only fire when status is set to completed
STATUS=$(echo "$INPUT" | jq -r '.tool_input.status // empty')
if [[ "$STATUS" != "completed" ]]; then
  exit 0
fi

if [[ -z "${INWORLD_API_KEY:-}" ]]; then
  exit 0
fi

# Check if all tasks in this session are now completed
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty')
TASK_DIR="${HOME}/.claude/tasks/${SESSION_ID}"
ALL_DONE=true
if [[ -d "$TASK_DIR" ]]; then
  for f in "$TASK_DIR"/*.json; do
    [[ -f "$f" ]] || continue
    TASK_STATUS=$(jq -r '.status // empty' "$f" 2>/dev/null)
    if [[ "$TASK_STATUS" == "pending" || "$TASK_STATUS" == "in_progress" ]]; then
      ALL_DONE=false
      break
    fi
  done
else
  ALL_DONE=false
fi

if [[ "$ALL_DONE" == "true" ]]; then
  MESSAGE="all tasks finished"
else
  MESSAGE="task complete"
fi

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
