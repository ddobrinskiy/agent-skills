#!/usr/bin/env bash
# Claude Code PostToolUse hook: auto-load a "sibling" file's content into
# context whenever its paired file is Read or Edited.
#
# Motivating case: a dbt model split across a `.sql` file (the transform) and
# a `.yml` file (description + tests). Agents routinely edit one half without
# even looking at the other, and the two silently drift out of sync. The same
# problem shows up anywhere a project splits one logical "thing" across two
# files: a source file + its test, a component + its story, an OpenAPI schema
# + its handler, a migration + its rollback. This hook makes the pairing
# non-optional: touch either file, and the other's content is injected into
# the agent's context automatically -- no reliance on the agent remembering,
# or on a skill/prompt happening to fire.
#
# ---------------------------------------------------------------------------
# Configuration (environment variables, all optional):
#
#   SIBLING_EXT_A     First extension of the pair, no dot.   Default: sql
#   SIBLING_EXT_B     Second extension of the pair, no dot.  Default: yml
#   SIBLING_DIR_SCOPE Path substring a file must contain to qualify.
#                     Leave unset/empty to match anywhere in the repo.
#                     Default: models  (matches typical dbt project layouts,
#                     e.g. .../dbt_project/models/..., .../models/staging/...)
#
# Example: pair Python modules with markdown docs, but only under docs/:
#   SIBLING_EXT_A=py SIBLING_EXT_B=md SIBLING_DIR_SCOPE=docs/
#
# Example: pair React components with their Storybook stories, anywhere:
#   SIBLING_EXT_A=tsx SIBLING_EXT_B=stories.tsx SIBLING_DIR_SCOPE=
#   (compound extensions like `.stories.tsx` work as long as EXT_B is the
#   FULL suffix after the shared basename -- see "Compound extensions" in
#   the README if your pair doesn't fit a plain swap.)
# ---------------------------------------------------------------------------

set -euo pipefail

# No jq -> no-op instead of erroring on every Read/Edit in the session.
command -v jq >/dev/null 2>&1 || exit 0

EXT_A="${SIBLING_EXT_A:-sql}"
EXT_B="${SIBLING_EXT_B:-yml}"
DIR_SCOPE="${SIBLING_DIR_SCOPE:-models}"

input=$(cat)
file_path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')
session_id=$(printf '%s' "$input" | jq -r '.session_id // "nosession"')

[[ -z "$file_path" ]] && exit 0

if [[ -n "$DIR_SCOPE" && "$file_path" != *"$DIR_SCOPE"* ]]; then
  exit 0
fi

case "$file_path" in
  *".$EXT_A") sibling="${file_path%".$EXT_A"}.$EXT_B" ;;
  *".$EXT_B") sibling="${file_path%".$EXT_B"}.$EXT_A" ;;
  *) exit 0 ;;
esac

# Sibling doesn't exist -> this file isn't actually part of a pair (e.g. a
# .yml with no matching .sql). Exit quietly; no hardcoded exclusion list
# needed, the filesystem is the source of truth.
[[ -f "$sibling" ]] || exit 0

# Canonical dedup key: always the EXT_A-side path, regardless of which side
# triggered the hook, so reading either half of the pair marks the same key.
case "$file_path" in
  *".$EXT_A") primary_path="$file_path" ;;
  *) primary_path="$sibling" ;;
esac

# Dedup per Claude Code session: without this, re-reading either file later
# in a long session would re-inject the full sibling content every time.
state_dir="${TMPDIR:-/tmp}/claude-sibling-context/$session_id"
mkdir -p "$state_dir"
marker="$state_dir/$(printf '%s' "$primary_path" | tr '/' '_')"

[[ -f "$marker" ]] && exit 0
touch "$marker"

sibling_content=$(cat "$sibling")
context=$(printf 'Sibling file (auto-loaded so the pair stays in sync): %s\n\n%s' "$sibling" "$sibling_content")

jq -n --arg ctx "$context" '{hookSpecificOutput: {hookEventName: "PostToolUse", additionalContext: $ctx}}'
