#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Display local images in a dedicated Herdr pane, manually or after tool reads."""

import argparse
import fcntl
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCRIPT = Path(__file__).resolve()


def run(*args, timeout=5):
    return subprocess.run(
        args, check=True, capture_output=True, text=True, timeout=timeout
    )


def herdr(*args):
    output = run("herdr", "pane", *args).stdout
    return json.loads(output)["result"] if output.strip() else {}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".terminal-image-")
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def image_path(raw_path, cwd):
    if not isinstance(raw_path, str) or not raw_path:
        return None
    path = Path(raw_path).expanduser()
    path = (Path(cwd) / path).resolve() if not path.is_absolute() else path.resolve()
    if not path.is_file():
        return None
    mime = run("file", "--brief", "--mime-type", "--", str(path)).stdout.strip()
    return path if mime.startswith("image/") else None


def hook_image(event):
    if event.get("hook_event_name") != "PostToolUse":
        return None
    name = event.get("tool_name", "")
    arguments = event.get("tool_input", {})
    response = event.get("tool_response", {})
    if not isinstance(arguments, dict):
        return None
    if isinstance(response, dict) and (
        response.get("isError") or response.get("error")
    ):
        return None
    if name == "Read":
        if not isinstance(response, dict) or response.get("type") != "image":
            return None
        raw_path = arguments.get("file_path")
    elif re.search(r"(^|[.:])view_image$", name):
        if isinstance(response, str) and response.lower().startswith(
            ("error", "unable to")
        ):
            return None
        raw_path = arguments.get("path")
    else:
        return None
    return image_path(raw_path, event.get("cwd") or os.getcwd())


def show(path):
    if os.environ.get("HERDR_ENV") != "1":
        raise RuntimeError("run inside a Herdr pane")
    for tool in ("herdr", "chafa", "file", "uv"):
        if not shutil.which(tool):
            raise RuntimeError(f"required command is missing: {tool}")
    caller = herdr("current", "--current")["pane"]
    key = hashlib.sha256(caller["terminal_id"].encode()).hexdigest()[:24]
    base = Path(os.environ.get("XDG_RUNTIME_DIR") or Path.home() / ".cache")
    state = base / "herdr-image" / key
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (state / "lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        preview = None
        try:
            saved = json.loads((state / "pane.json").read_text())
            info = herdr("get", saved["pane_id"])["pane"]
            # Do not send shell commands into a pane the user has taken over.
            # A live viewer owns an advisory lock for its entire lifetime.
            with (state / "viewer.lock").open("a") as viewer_lock:
                try:
                    fcntl.flock(viewer_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    if info["terminal_id"] == saved["terminal_id"]:
                        preview = info
        except (OSError, ValueError, KeyError, subprocess.SubprocessError):
            pass
        write_json(state / "image.json", {"path": str(path), "request": time.time_ns()})
        if preview is not None:
            return preview["pane_id"]
        layout = herdr("layout", "--pane", caller["pane_id"])["layout"]
        rect = next(
            p["rect"] for p in layout["panes"] if p["pane_id"] == caller["pane_id"]
        )
        direction = "right" if rect["width"] >= rect["height"] * 2 else "down"
        preview = herdr(
            "split",
            "--pane",
            caller["pane_id"],
            "--direction",
            direction,
            "--cwd",
            str(Path.cwd()),
            "--no-focus",
        )["pane"]
        write_json(state / "pane.json", preview)
        herdr("rename", preview["pane_id"], "Image preview")
        command = shlex.join(
            [shutil.which("uv"), "run", "--script", str(SCRIPT), "--viewer", str(state)]
        )
        herdr("run", preview["pane_id"], command)
        # Wait only for startup; subsequent calls update the request file.
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            with (state / "viewer.lock").open("a") as viewer_lock:
                try:
                    fcntl.flock(viewer_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    return preview["pane_id"]
            time.sleep(0.05)
        raise RuntimeError(
            "preview viewer did not start; inspect the Image preview pane"
        )


def viewer(state):
    with (state / "viewer.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        previous = None
        while True:
            request = json.loads((state / "image.json").read_text())
            if request != previous:
                path = Path(request["path"])
                # Only this dedicated pane is cleared; no agent UI is touched.
                print("\033[2J\033[H", end="", flush=True)
                label = "".join(c for c in path.name if c.isprintable())
                print(label, flush=True)
                result = subprocess.run(
                    [
                        "chafa",
                        "--format",
                        "kitty",
                        "--probe",
                        "off",
                        "--passthrough",
                        "none",
                        "--animate",
                        "off",
                        "--",
                        str(path),
                    ],
                    check=False,
                )
                if result.returncode == 0:
                    write_json(state / "displayed.json", request)
                previous = request
            time.sleep(0.15)


def install(home):
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("uv is required")
    links = {
        home / ".agents/skills/terminal-image": SCRIPT.parent.parent,
        home / ".claude/skills/terminal-image": SCRIPT.parent.parent,
        home / ".local/bin/herdr-image": SCRIPT,
    }
    for path, target in links.items():
        if (path.exists() or path.is_symlink()) and not (
            path.is_symlink() and path.resolve() == target
        ):
            raise RuntimeError(f"refusing to replace existing path: {path}")
    command = shlex.join([uv, "run", "--script", str(SCRIPT), "--hook"])
    for path, matcher in (
        (home / ".claude/settings.json", "^Read$"),
        (home / ".codex/hooks.json", "(^|[.:])view_image$"),
    ):
        document = json.loads(path.read_text()) if path.exists() else {}
        hooks = document.setdefault("hooks", {}).setdefault("PostToolUse", [])
        # Remove only our own old handlers, retaining other handlers in a group.
        for group in hooks:
            group["hooks"] = [
                h
                for h in group.get("hooks", [])
                if not (
                    "terminal-image.py" in h.get("command", "")
                    and "--hook" in h["command"]
                )
            ]
        hooks[:] = [g for g in hooks if g.get("hooks")]
        hooks.append(
            {
                "matcher": matcher,
                "hooks": [
                    {
                        "type": "command",
                        "command": command,
                        "timeout": 15,
                    }
                ],
            }
        )
        write_json(path, document)
        print(f"Installed image-read hook: {path}")
    for path, target in links.items():
        if path.is_symlink() and path.resolve() == target:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.symlink_to(target, target_is_directory=target.is_dir())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--hook", action="store_true", help="read a PostToolUse JSON event on stdin"
    )
    mode.add_argument("--viewer", type=Path, metavar="STATE", help=argparse.SUPPRESS)
    mode.add_argument(
        "--install",
        action="store_true",
        help="merge user hooks and link this skill for both agents",
    )
    parser.add_argument("image", nargs="?")
    args = parser.parse_args()
    try:
        if args.hook:
            if os.environ.get("HERDR_ENV") != "1":
                return 0
            path = hook_image(json.load(sys.stdin))
            if path is not None:
                show(path)
        elif args.viewer:
            viewer(args.viewer)
        elif args.install:
            install(Path.home())
        elif args.image:
            path = image_path(args.image, os.getcwd())
            if path is None:
                raise RuntimeError("image is missing, unreadable, or not an image")
            print(show(path))
        else:
            parser.error("provide an image or --install")
        return 0
    except (
        OSError,
        ValueError,
        KeyError,
        RuntimeError,
        subprocess.SubprocessError,
    ) as error:
        print(f"terminal-image: {error}", file=sys.stderr)
        # A display failure must never prevent an agent from reading an image.
        return 0 if args.hook else 1
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
