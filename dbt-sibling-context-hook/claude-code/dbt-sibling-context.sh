#!/usr/bin/env bash
# System-wide Claude Code hook (PostToolUse: Read|Edit and UserPromptSubmit):
# when a dbt model's .sql or .yml file is referenced under
# etl/dbt_project/models/, inject its paired sibling so SQL and YAML are never
# seen in isolation.
#
# The hook is deliberately project-agnostic. Claude passes the current working
# directory in the event payload, so relative tool paths and @-mentions work
# in any repository that follows the standard dbt layout.
set -euo pipefail

command -v jq >/dev/null 2>&1 || exit 0

input=$(cat)
hook_event=$(printf '%s' "$input" | jq -r '.hook_event_name // empty')
session_id=$(printf '%s' "$input" | jq -r '.session_id // "nosession"')
payload_cwd=$(printf '%s' "$input" | jq -r '.cwd // empty')

case "$hook_event" in
  UserPromptSubmit|PostToolUse) ;;
  *) exit 0 ;;
esac

if [[ -z "$payload_cwd" ]]; then
  payload_cwd="${CLAUDE_PROJECT_DIR:-$PWD}"
fi

safe_session_id=$(printf '%s' "$session_id" | tr -c '[:alnum:]_.-' '_')
state_dir="${TMPDIR:-/tmp}/claude-dbt-sibling/$safe_session_id"
mkdir -p "$state_dir"

context=""

# Append the paired file once per session per model. The SQL path is the
# identity for both directions, so reading foo.sql and then foo.yml produces
# one sibling block rather than two.
add_sibling() {
  local file_path="$1" sibling sql_path marker sibling_content

  [[ -n "$file_path" ]] || return
  [[ "$file_path" != data:* ]] || return

  if [[ "$file_path" != /* ]]; then
    file_path="$payload_cwd/${file_path#./}"
  fi

  case "$file_path" in
    */etl/dbt_project/models/*.sql)
      sibling="${file_path%.sql}.yml"
      sql_path="$file_path"
      ;;
    */etl/dbt_project/models/*.yml)
      sibling="${file_path%.yml}.sql"
      sql_path="$sibling"
      ;;
    *) return ;;
  esac

  [[ -f "$sibling" ]] || return
  sibling_content=$(cat "$sibling") || return

  marker="$state_dir/$(printf '%s' "$sql_path" | tr '/:' '__')"
  # A no-clobber create makes duplicate PostToolUse hooks harmless when
  # Claude runs several file reads concurrently.
  if ! (set -C; : > "$marker") 2>/dev/null; then
    return
  fi

  context+=$(printf 'dbt sibling file (auto-loaded so SQL and YAML stay in sync): %s\n\n%s\n\n' "$sibling" "$sibling_content")
}

if [[ "$hook_event" == "UserPromptSubmit" ]]; then
  prompt=$(printf '%s' "$input" | jq -r '.prompt // empty')
  while IFS= read -r mention; do
    [[ -z "$mention" ]] && continue
    add_sibling "${mention#@}"
  done < <(grep -oE '@[^[:space:]]+\.(sql|yml)' <<< "$prompt" || true)
else
  file_path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // .tool_input.path // empty')
  add_sibling "$file_path"
fi

[[ -z "$context" ]] && exit 0

jq -n --arg ctx "$context" --arg event "$hook_event" \
  '{hookSpecificOutput: {hookEventName: $event, additionalContext: $ctx}}'
