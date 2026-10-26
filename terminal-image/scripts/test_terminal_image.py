"""Behavior checks: filtering, preserving hooks, safe paths, and preview reuse."""

import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "terminal_image", Path(__file__).with_name("terminal-image.py")
)
image = importlib.util.module_from_spec(spec)
spec.loader.exec_module(image)


class ImageTests(unittest.TestCase):
    def test_only_image_read_events(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "no extension"
            path.write_bytes(
                bytes.fromhex(
                    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
                )
            )
            text = Path(directory) / "pretend.png"
            text.write_text("ordinary text")
            event = {
                "hook_event_name": "PostToolUse",
                "tool_name": "Read",
                "cwd": directory,
                "tool_input": {"file_path": path.name},
                "tool_response": {"type": "image"},
            }
            self.assertEqual(image.hook_image(event), path)
            event["tool_response"] = {"type": "text"}
            self.assertIsNone(image.hook_image(event))
            event.update(
                tool_name="view_image", tool_input={"path": path.name}, tool_response={}
            )
            self.assertEqual(image.hook_image(event), path)
            event["tool_input"] = {"path": str(text)}
            self.assertIsNone(image.hook_image(event))
            event["tool_input"] = {"path": str(path)}
            event["tool_response"] = {"isError": True}
            self.assertIsNone(image.hook_image(event))
            event.update(tool_name="Bash", tool_response={})
            self.assertIsNone(image.hook_image(event))

    def test_install_preserves_other_hooks_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            path = home / ".claude/settings.json"
            path.parent.mkdir()
            original = {
                "model": "keep-me",
                "hooks": {
                    "SessionStart": [
                        {
                            "hooks": [
                                {"type": "command", "command": "existing-session-hook"},
                            ]
                        }
                    ],
                    "PostToolUse": [
                        {
                            "matcher": "Read",
                            "hooks": [
                                {"type": "command", "command": "existing-read-hook"},
                            ],
                        }
                    ],
                },
            }
            path.write_text(json.dumps(original))
            image.install(home)
            first = json.loads(path.read_text())
            image.install(home)
            self.assertEqual(first, json.loads(path.read_text()))
            self.assertEqual(first["model"], original["model"])
            self.assertEqual(
                first["hooks"]["SessionStart"], original["hooks"]["SessionStart"]
            )
            self.assertIn(
                original["hooks"]["PostToolUse"][0], first["hooks"]["PostToolUse"]
            )
            self.assertTrue((home / ".agents/skills/terminal-image/SKILL.md").is_file())

    def test_outside_herdr_does_not_read_stdin_or_touch_panes(self):
        env = dict(os.environ, HERDR_ENV="0")
        result = subprocess.run(
            ["uv", "run", "--script", str(image.SCRIPT), "--hook"],
            check=False,
            input="invalid JSON",
            text=True,
            capture_output=True,
            env=env,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

    def test_hook_display_errors_are_nonblocking(self):
        event = {
            "hook_event_name": "PostToolUse",
            "tool_name": "view_image",
            "tool_input": {"path": "/missing.png"},
        }
        result = subprocess.run(
            ["uv", "run", "--script", str(image.SCRIPT), "--hook"],
            check=False,
            input=json.dumps(event),
            text=True,
            capture_output=True,
            env=dict(os.environ, HERDR_ENV="1"),
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
