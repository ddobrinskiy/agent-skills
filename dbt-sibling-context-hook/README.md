# dbt sibling context hooks

Cross-harness dbt sibling-context hooks for Claude Code, Codex, and OpenCode. Each adapter automatically loads the paired `.sql`/`.yml` model file under `etl/dbt_project/models/`, keeping SQL and YAML together in the agent's context.

Choose the adapter that matches the coding harness in use. The three adapters are independent; install only the one needed on a given machine. They do not change project files or require a project-specific configuration.

## Layout

```text
dbt-sibling-context-hook/
├── claude-code/
│   ├── dbt-sibling-context.sh
│   └── settings.fragment.json
├── codex/
│   ├── dbt-sibling-context.py
│   └── hooks.fragment.json
└── opencode/
    ├── dbt-sibling-context.js
    └── dbt-sibling-context.sh
```

All adapters recognize this pair layout:

```text
etl/dbt_project/models/orders.sql
etl/dbt_project/models/orders.yml
```

They quietly do nothing when the path is outside that directory or the paired file does not exist.

## Requirements

- Claude Code and OpenCode: `bash`, `jq`
- Codex: Python 3
- OpenCode: a Node.js runtime supplied by OpenCode

## Install

Set `BUNDLE` to the path where this directory is checked out before running the commands below:

```bash
BUNDLE=/path/to/agent-skills/dbt-sibling-context-hook
```

### Claude Code

This installs the hook system-wide for the current user. It handles `Read` and `Edit` tool events and also recognizes `@model.sql` / `@model.yml` references in submitted prompts.

```bash
mkdir -p "$HOME/.claude/hooks"
install -m 700 "$BUNDLE/claude-code/dbt-sibling-context.sh" \
  "$HOME/.claude/hooks/dbt-sibling-context.sh"
```

Merge both hook entries from [`settings.fragment.json`](claude-code/settings.fragment.json) into the existing top-level `hooks.PostToolUse` and `hooks.UserPromptSubmit` arrays in `~/.claude/settings.json`. Append the entries to those arrays and preserve any existing matchers or hooks. If the settings file does not exist, the fragment can be used as its initial contents.

Validate the resulting JSON before starting a new Claude Code session:

```bash
jq empty "$HOME/.claude/settings.json"
```

The settings command intentionally points at `$HOME/.claude/hooks/dbt-sibling-context.sh`, so the same installation works regardless of the project directory.

### Codex

This installs the Python hook in the user-level hooks directory:

```bash
mkdir -p "$HOME/.codex/hooks"
install -m 700 "$BUNDLE/codex/dbt-sibling-context.py" \
  "$HOME/.codex/hooks/dbt-sibling-context.py"
```

Merge the `PostToolUse` entry from [`hooks.fragment.json`](codex/hooks.fragment.json) into the top-level `hooks.PostToolUse` array in `~/.codex/hooks.json`. Preserve other hooks. The default entry watches completed `Bash` calls and skips commands that look write-oriented, so a model is not reloaded as pre-edit context after a mutation.

Prompt-time loading is available but disabled by default. To enable it, add this entry to the same top-level `hooks.UserPromptSubmit` array:

```json
{
  "hooks": [
    {
      "type": "command",
      "command": "CODEX_DBT_SIBLING_USER_PROMPT=true python3 ~/.codex/hooks/dbt-sibling-context.py",
      "statusMessage": "Loading dbt sibling context",
      "additionalContextLimit": 10000
    }
  ]
}
```

Validate the resulting JSON before starting a new Codex session:

```bash
jq empty "$HOME/.codex/hooks.json"
```

### OpenCode

OpenCode's adapter is a plugin plus a small shell helper. Install both files together in the user-level plugin directory so the plugin can find its helper beside itself:

```bash
mkdir -p "$HOME/.config/opencode/plugins"
install -m 644 "$BUNDLE/opencode/dbt-sibling-context.js" \
  "$HOME/.config/opencode/plugins/dbt-sibling-context.js"
install -m 755 "$BUNDLE/opencode/dbt-sibling-context.sh" \
  "$HOME/.config/opencode/plugins/dbt-sibling-context.sh"
```

Start a new OpenCode session after installing. The plugin handles both `Read` results and file attachments resolved from chat input.

## Verify an installation

Use a real model pair in a test repository. These checks should print context containing the sibling path and file contents:

```bash
REPO=/path/to/dbt-repository
MODEL="$REPO/etl/dbt_project/models/orders.sql"

jq -n --arg cwd "$REPO" --arg file "$MODEL" \
  '{hook_event_name:"PostToolUse",session_id:"install-check",cwd:$cwd,tool_input:{file_path:$file}}' \
  | bash "$BUNDLE/claude-code/dbt-sibling-context.sh"

jq -n --arg cwd "$REPO" --arg command "cat $MODEL" \
  '{hook_event_name:"PostToolUse",tool_name:"Bash",cwd:$cwd,tool_input:{command:$command}}' \
  | python3 "$BUNDLE/codex/dbt-sibling-context.py"

jq -n --arg file "$MODEL" '{file_path:$file}' \
  | bash "$BUNDLE/opencode/dbt-sibling-context.sh"
```

After the direct checks pass, read or attach the model through the installed harness and confirm that the paired file appears automatically. Start a fresh session if the harness caches settings or plugins.
