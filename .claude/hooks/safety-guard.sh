#!/usr/bin/env bash
set -euo pipefail

# Read the tool input from stdin
INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // ""')

# --- Bash command guard ---
if [ "$TOOL_NAME" = "Bash" ]; then
  cmd=$(echo "$INPUT" | jq -r '.tool_input.command // ""')

  deny_patterns=(
    'rm\s+-rf\s+/'              # rm -rf /
    'rm\s+-rf\s+~'              # rm -rf ~
    'rm\s+-rf\s+\.'             # rm -rf . or ./
    'rm\s+-rf\s+\*'             # rm -rf *
    'rm\s+-r\s+/'               # rm -r /
    'git\s+push\s+.*--force'    # git push --force
    'git\s+push\s+-f'           # git push -f
    'git\s+reset\s+--hard'      # git reset --hard
    'git\s+clean\s+-fd'         # git clean -fd (deletes untracked files)
    'git\s+remote\s+add'        # git remote add (exfiltration vector)
    'git\s+remote\s+set-url'    # git remote set-url
    'chmod\s+-R\s+777'          # chmod -R 777
    'mkfs\.'                    # mkfs (format disk)
    'dd\s+if='                  # dd (disk write)
    '>\s*/dev/sd'               # write to raw disk
    'curl.*\|\s*bash'           # curl | bash (remote code execution)
    'curl.*\|\s*sh'             # curl | sh
    'wget.*\|\s*bash'           # wget | bash
    'wget.*\|\s*sh'             # wget | sh
  )

  for pat in "${deny_patterns[@]}"; do
    if echo "$cmd" | grep -Eiq "$pat"; then
      jq -n \
        --arg reason "Blocked: matched dangerous pattern '$pat'. Use a safer alternative." \
        '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $reason}}'
      exit 0
    fi
  done
fi

# --- File edit guard: protect settings and hooks from self-modification ---
if [ "$TOOL_NAME" = "Edit" ] || [ "$TOOL_NAME" = "Write" ]; then
  file=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // ""')

  protected_patterns=(
    '\.claude/settings\.json'
    '\.claude/settings\.local\.json'
    '\.claude/hooks/'
    '\.env'
  )

  for pat in "${protected_patterns[@]}"; do
    if echo "$file" | grep -Eiq "$pat"; then
      jq -n \
        --arg reason "Blocked: cannot modify protected file '$file'." \
        '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $reason}}'
      exit 0
    fi
  done
fi

# Everything else: allow
exit 0
