#!/usr/bin/env bash
# OpenCode plugin hook: after a dbt model's .sql or .yml file is read,
# read the sibling file so SQL and YAML are never seen in isolation.
#
# The JavaScript plugin sends this standalone JSON protocol on stdin after a
# Read or resolved file attachment. This script has no dependency on another
# agent's settings, hooks, or environment variables.
set -euo pipefail

command -v jq >/dev/null 2>&1 || exit 0

input=$(cat)
file_path=$(printf '%s' "$input" | jq -r '.file_path // empty')
[[ -n "$file_path" ]] || exit 0

context=""

# Append the sibling's content for this tool invocation. The OpenCode plugin
# calls this script from a Read hook or attachment handler, so there is no
# model prompt and no per-session marker that could suppress a later Read.
add_sibling() {
  local file_path="$1" sibling sibling_content
  case "$file_path" in
    */etl/dbt_project/models/*.sql) sibling="${file_path%.sql}.yml" ;;
    */etl/dbt_project/models/*.yml) sibling="${file_path%.yml}.sql" ;;
    *) return ;;
  esac
  [[ -f "$sibling" ]] || return

  sibling_content=$(cat "$sibling")
  context+=$(printf 'dbt sibling file (auto-loaded so SQL and YAML stay in sync): %s\n\n%s\n\n' "$sibling" "$sibling_content")
}

add_sibling "$file_path"

[[ -z "$context" ]] && exit 0

jq -n --arg ctx "$context" '{additional_context: $ctx}'
