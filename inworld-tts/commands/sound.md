---
name: sound
description: Toggle TTS notifications on/off
---

Toggle TTS notifications on/off. Check if `/tmp/claude-tts-muted` exists:
- If it exists: remove it and tell the user "TTS unmuted"
- If it doesn't exist: create it with `touch /tmp/claude-tts-muted` and tell the user "TTS muted"

Use the Bash tool to check and toggle the file.
