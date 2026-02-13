#!/bin/bash
# Cross-platform audio playback utility.
# Source this file then call: play_audio <file.mp3> [volume 0-100]
#
# Tries ffplay first (WSL/Linux), falls back to PowerShell mciSendString on Windows, afplay on macOS.

play_audio() {
  local file="$1"
  local volume="${2:-70}"

  [[ -f "$file" ]] || return 1

  # Prefer ffplay (WSL, Linux, or Windows with ffmpeg installed)
  if command -v ffplay &>/dev/null; then
    ffplay -nodisp -autoexit -loglevel quiet -volume "$volume" "$file" 2>/dev/null &
    wait $! 2>/dev/null || true
    return 0
  fi

  # Windows fallback: mciSendString via PowerShell P/Invoke
  if [[ "$OSTYPE" == msys* || "$OSTYPE" == mingw* || "$OSTYPE" == cygwin* ]]; then
    local win_path
    win_path=$(cygpath -w "$file" 2>/dev/null || echo "$file")
    local mci_vol=$(( volume * 10 ))

    powershell.exe -NoProfile -Command "
      Add-Type -MemberDefinition '
      [DllImport(\"winmm.dll\")]
      public static extern int mciSendStringA(string command, System.Text.StringBuilder returnString, int returnSize, System.IntPtr hwndCallback);
      ' -Name MCI -Namespace Win32
      \$sb = New-Object System.Text.StringBuilder 256
      \$null = [Win32.MCI]::mciSendStringA(\"open \`\"$win_path\`\" type mpegvideo alias tts\", \$sb, 256, [IntPtr]::Zero)
      \$null = [Win32.MCI]::mciSendStringA('setaudio tts volume to $mci_vol', \$sb, 256, [IntPtr]::Zero)
      \$null = [Win32.MCI]::mciSendStringA('play tts wait', \$sb, 256, [IntPtr]::Zero)
      \$null = [Win32.MCI]::mciSendStringA('close tts', \$sb, 256, [IntPtr]::Zero)
    " 2>/dev/null
    return 0
  fi

  # macOS fallback
  if command -v afplay &>/dev/null; then
    local vol_float
    vol_float=$(awk "BEGIN { printf \"%.2f\", $volume / 100 }")
    afplay -v "$vol_float" "$file" 2>/dev/null
    return 0
  fi

  return 1
}
