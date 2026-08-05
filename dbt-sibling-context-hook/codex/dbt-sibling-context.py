#!/usr/bin/env python3
"""Add the matching dbt SQL/YAML file to Codex's tool context.

Codex's current PostToolUse hook path observes Bash tool calls.  The hook
therefore finds dbt model paths in the completed shell command, reads the
matching sibling, and returns it as model-visible additional context.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path


MODEL_MARKER = "etl/dbt_project/models/"
MODEL_SUFFIXES = (".sql", ".yml")
TRAILING_COMMAND_CHARS = ",;|&)]}>"
USER_PROMPT_FEATURE_FLAG = "CODEX_DBT_SIBLING_USER_PROMPT"


def git_root(cwd: Path) -> Path | None:
    """Return the repository root for the hook's session directory."""

    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
            capture_output=True,
            check=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    root = result.stdout.strip()
    return Path(root).resolve() if root else None


def model_root(root: Path | None) -> Path | None:
    if root is None:
        return None
    return (root / MODEL_MARKER.rstrip("/")).resolve()


def suffix_end(value: str) -> int | None:
    """Find the end of a model filename inside a shell token."""

    matches = [value.rfind(suffix) + len(suffix) for suffix in MODEL_SUFFIXES]
    end = max((match for match in matches if match > len(MODEL_MARKER)), default=0)
    return end or None


def candidate_from_token(token: str, cwd: Path, root: Path | None) -> list[Path]:
    """Resolve model paths embedded in one shell token."""

    token = token.strip(TRAILING_COMMAND_CHARS)
    marker_index = token.find(MODEL_MARKER)
    candidates: list[Path] = []

    if marker_index >= 0:
        end = suffix_end(token[marker_index:])
        if end is None:
            return candidates

        model_path = token[marker_index : marker_index + end]
        prefix = token[:marker_index]

        # Preserve an absolute path when the token contains one.  Otherwise,
        # resolve the repository-relative dbt path from the session root.
        if prefix.startswith("/") and root is not None:
            candidates.append(Path(prefix + model_path))
        elif root is not None:
            candidates.append(root / model_path)
        candidates.append(cwd / model_path)
        return candidates

    if not token.endswith(MODEL_SUFFIXES):
        return candidates

    # This covers commands run from the repository root as well as commands
    # run from inside etl/dbt_project/models itself.
    if root is not None:
        candidates.append(root / MODEL_MARKER / token.lstrip("./"))
    candidates.append(cwd / token)
    return candidates


def command_tokens(command: str) -> list[str]:
    try:
        return shlex.split(command, posix=True)
    except ValueError:
        # An incomplete quote should not make the hook fail.  The fallback is
        # enough for ordinary unquoted model paths.
        return command.split()


def is_write_oriented(command: str) -> bool:
    """Avoid adding pre-edit context after shell commands that mutate files."""

    lowered = command.lower()

    if "apply_patch" in lowered:
        return True

    if re.search(
        r"(?:^|[;&|]\s*)(?:sudo\s+)?"
        r"(?:rm|mv|cp|install|touch|truncate|chmod|chown|ln|tee|"
        r"git\s+(?:checkout|restore|apply))\b",
        lowered,
    ):
        return True

    if re.search(r"\b(?:sed|perl)\b[^\n;&|]*\s-i(?:[A-Za-z]*)?(?:\s|$)", lowered):
        return True

    # Redirection to a dbt model is a write, while redirection from one is a
    # read.  Restrict this check to model-looking destinations.
    if re.search(
        rf"(?:>>?|\btee\b\s+)[^\n;&|]*{re.escape(MODEL_MARKER)}[^\n;&|]*"
        rf"(?:\.sql|\.yml)\b",
        lowered,
    ):
        return True

    return False


def existing_model_paths(command: str, cwd: Path) -> list[Path]:
    root = git_root(cwd)
    paths: list[Path] = []

    for token in command_tokens(command):
        # Handle common --file=/path and key=/path forms without attempting to
        # interpret arbitrary shell syntax.
        token_variants = [token]
        if "=" in token:
            token_variants.append(token.split("=", 1)[1])

        for variant in token_variants:
            for candidate in candidate_from_token(variant, cwd, root):
                try:
                    resolved = candidate.expanduser().resolve()
                except OSError:
                    continue

                if not resolved.is_file() or resolved.suffix not in MODEL_SUFFIXES:
                    continue

                root_for_check = model_root(root)
                if root_for_check is not None:
                    try:
                        resolved.relative_to(root_for_check)
                    except ValueError:
                        continue
                elif MODEL_MARKER not in resolved.as_posix():
                    continue

                if resolved not in paths:
                    paths.append(resolved)

    return paths


def sibling_for(path: Path) -> Path:
    suffix = ".yml" if path.suffix == ".sql" else ".sql"
    return path.with_suffix(suffix)


def context_for(paths: list[Path]) -> str:
    blocks: list[str] = []
    siblings: set[Path] = set()
    targets = set(paths)

    for path in paths:
        sibling = sibling_for(path)
        if sibling in siblings or sibling in targets or not sibling.is_file():
            continue
        siblings.add(sibling)

        try:
            content = sibling.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        blocks.append(
            "dbt sibling file (auto-loaded so SQL and YAML stay in sync): "
            f"{sibling}\n\n{content}\n"
        )

    return "\n".join(blocks)


def emit_context(event_name: str, context: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": event_name,
                    "additionalContext": context,
                }
            },
            ensure_ascii=False,
        )
    )


def user_prompt_hook_enabled() -> bool:
    """Keep prompt-time loading opt-in; PostToolUse remains the default."""

    return os.environ.get(USER_PROMPT_FEATURE_FLAG, "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError, TypeError):
        return 0

    event_name = payload.get("hook_event_name")
    if event_name == "PostToolUse":
        if payload.get("tool_name") != "Bash":
            return 0
        tool_input = payload.get("tool_input")
        command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
        if not isinstance(command, str) or not command.strip() or is_write_oriented(command):
            return 0
    elif event_name == "UserPromptSubmit":
        if not user_prompt_hook_enabled():
            return 0
        command = payload.get("prompt", "")
        if not isinstance(command, str) or not command.strip():
            return 0
    else:
        return 0

    if ".sql" not in command and ".yml" not in command:
        return 0

    raw_cwd = payload.get("cwd")
    cwd = Path(raw_cwd if isinstance(raw_cwd, str) and raw_cwd else os.getcwd())
    try:
        cwd = cwd.expanduser().resolve()
    except OSError:
        return 0

    context = context_for(existing_model_paths(command, cwd))
    if not context:
        return 0

    emit_context(event_name, context)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
