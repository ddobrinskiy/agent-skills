---
name: terminal-image
description: Display a local image in the user's terminal through Herdr, including remote server sessions viewed in Ghostty. Use for terminal image previews or configuring automatic previews of Claude and Codex image reads.
---

Display an image from the machine running Herdr:

```sh
uv run --script scripts/terminal-image.py /absolute/path/to/image.png
```

Resolve `scripts/terminal-image.py` relative to this skill's directory. Requires
`herdr`, `chafa`, and `uv` on PATH and `HERDR_ENV=1`.

The script creates one preview pane per calling pane, preserves focus, and
updates that preview on later calls. Kitty graphics travel through remote Herdr
to the laptop terminal; the image stays on the server. Tool runners need no
`/dev/tty`. Close the preview pane when finished; the next call recreates it.

Enable automatic previews for both agents:

```sh
uv run --script scripts/terminal-image.py --install
```

This merges `PostToolUse` hooks into Claude's user settings and Codex's
`hooks.json`, preserving existing hooks, and installs `~/.local/bin/herdr-image`.
Claude `Read` and Codex `view_image`
calls preview image files automatically; text reads and sessions outside Herdr
do nothing. Start a new agent session after installation. Codex may require
reviewing and trusting the new hook via `/hooks` before it runs.
