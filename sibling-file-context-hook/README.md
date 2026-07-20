# Sibling-file context hook (Claude Code)

A `PostToolUse` hook for [Claude Code](https://claude.com/claude-code) that
auto-injects a file's "sibling" into the agent's context whenever either half
of the pair is read or edited — so the agent never sees one half in
isolation.

**Motivating case:** a dbt model split across `model.sql` (the transform) and
`model.yml` (description + column tests). Agents routinely edit the SQL
without checking whether the YAML tests/docs still match, or read the YAML
for context without opening the SQL — and the two drift apart. The same
problem shows up anywhere a project splits one logical "thing" across two
files: source + test, component + Storybook story, OpenAPI schema + handler,
migration + rollback. Telling the agent "always read both" in a prompt or
skill is guidance the agent can still skip. A hook makes it non-optional.

## Give this to your agent

Paste the following into Claude Code (or any coding agent that can read files,
edit JSON, and run shell commands) in the repo where you want this installed:

> Read `README.md` and `sibling-context-hook.sh` from
> `github.com/ddobrinskiy/agent-skills/sibling-file-context-hook`. Install the
> hook in this repo: copy the script to `.claude/hooks/sibling-context-hook.sh`
> (executable), merge the `PostToolUse` entry into `.claude/settings.json`
> (create it if missing, don't clobber existing hooks), figure out the right
> `SIBLING_EXT_A` / `SIBLING_EXT_B` / `SIBLING_DIR_SCOPE` values for our
> paired-file convention, and verify it end-to-end per the "Testing" section
> before reporting done.

The rest of this file is what the agent needs to actually do that.

## How it works

1. Claude Code fires a `PostToolUse` event after every `Read` or `Edit` tool
   call. The hook script gets the tool call as JSON on stdin (`tool_input`,
   `session_id`, ...).
2. The script checks whether the touched file's extension matches one side of
   a configured pair (default: `.sql` / `.yml`) and, optionally, that its path
   contains a configured directory substring (default: `models`). Anything
   else → silent no-op.
3. It computes the sibling path by swapping the extension. If that file
   doesn't exist on disk, it's not actually part of a pair (e.g. a `.yml` with
   no matching `.sql`) → silent no-op. No hardcoded exclusion list needed —
   the filesystem is the source of truth.
4. It dedupes per Claude Code session (a marker file under
   `${TMPDIR:-/tmp}/claude-sibling-context/<session_id>/`), so re-reading
   either file later in a long session doesn't re-dump the sibling's full
   content into context every time — only the first touch of a given pair
   does.
5. On a first touch, it emits:
   ```json
   {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "Sibling file (auto-loaded so the pair stays in sync): <path>\n\n<full file content>"}}
   ```
   Claude Code injects `additionalContext` straight into the agent's context —
   no extra tool call, no dependence on the agent choosing to go read it.

**Trade-off to know about:** this injects the *full* sibling content, not just
a pointer, because a pointer is a suggestion the agent can ignore — the whole
point is to make the pairing non-optional. For very large files this adds
real tokens to context on first touch; the per-session dedup keeps that to a
one-time cost per pair.

## Install

1. Copy `sibling-context-hook.sh` into your repo, e.g. `.claude/hooks/`, and
   make it executable: `chmod +x .claude/hooks/sibling-context-hook.sh`.
2. Merge this into your (repo-committed) `.claude/settings.json` — merge the
   `PostToolUse` array entry in, don't overwrite any hooks you already have:
   ```json
   {
     "hooks": {
       "PostToolUse": [
         {
           "matcher": "Read|Edit",
           "hooks": [
             {
               "type": "command",
               "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/sibling-context-hook.sh\""
             }
           ]
         }
       ]
     }
   }
   ```
   `$CLAUDE_PROJECT_DIR` is set by Claude Code to the repo root, so this works
   regardless of where the session's cwd is.
3. If `.claude/settings.json` already existed in this repo *before* your
   Claude Code session started, the change should take effect immediately
   (the settings watcher is already watching `.claude/`). If it's a brand-new
   file, or the hook doesn't seem to fire, open `/hooks` once to force a
   reload, or restart the session.
4. Requires `jq` on PATH. If it's missing the script no-ops instead of
   erroring on every Read/Edit — but the hook obviously won't do anything
   useful until it's installed.

### Configure for your project's pair

Set these as environment variables (e.g. exported in `.envrc`, or inlined
before the command in `settings.json`):

| Variable            | Meaning                                            | Default   |
|---------------------|-----------------------------------------------------|-----------|
| `SIBLING_EXT_A`      | first extension of the pair, no dot                 | `sql`     |
| `SIBLING_EXT_B`      | second extension of the pair, no dot                | `yml`     |
| `SIBLING_DIR_SCOPE`  | path substring a file must contain to qualify (empty = anywhere in the repo) | `models`  |

Examples:
- Python source + its markdown doc, scoped to `docs/`:
  `SIBLING_EXT_A=py SIBLING_EXT_B=md SIBLING_DIR_SCOPE=docs/`
- Any `.tf` + its README, anywhere in the repo:
  `SIBLING_EXT_A=tf SIBLING_EXT_B=md SIBLING_DIR_SCOPE=`

**Compound extensions** (e.g. `Component.tsx` + `Component.stories.tsx`, where
one side has an extra segment): the plain suffix-swap in the script assumes
both sides are `<shared-basename>.<ext>`. If your pair doesn't fit that shape,
edit the two `case` blocks in `sibling-context-hook.sh` (the extension-swap
and the dedup-key blocks) to compute the sibling path explicitly for your
naming scheme — the rest of the script (existence check, dedup, context
injection) doesn't need to change.

## Testing

Pipe-test the raw script before trusting it's wired up correctly — this
doesn't touch Claude Code at all, just exercises the script directly:

```bash
REPO="$(pwd)"
PAIR_A="$REPO/path/to/some_model.sql"   # pick any real .sql+.yml pair in your repo
SESSION="test-$$"

# First call: should print JSON with additionalContext containing the .yml content
echo "{\"session_id\":\"$SESSION\",\"tool_input\":{\"file_path\":\"$PAIR_A\"}}" \
  | bash .claude/hooks/sibling-context-hook.sh | jq .

# Second call, same session: should print nothing (dedup)
echo "{\"session_id\":\"$SESSION\",\"tool_input\":{\"file_path\":\"$PAIR_A\"}}" \
  | bash .claude/hooks/sibling-context-hook.sh
echo "exit code: $?"   # expect 0, no output

# Clean up the test session's dedup marker
rm -rf "${TMPDIR:-/tmp}/claude-sibling-context/$SESSION"
```

Then validate the JSON wiring in `settings.json`:

```bash
jq -e '.hooks.PostToolUse[] | select(.matcher == "Read|Edit")' .claude/settings.json
```

Finally, prove it fires for real inside a live Claude Code session: `Read` one
half of an actual pair in your repo and confirm a
`PostToolUse:Read hook additional context: ...` block with the sibling's
content shows up; re-read the same file and confirm it does *not* show up a
second time.
