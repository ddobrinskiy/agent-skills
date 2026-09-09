---
name: vision-delegation
description: >
  Describes images, screenshots, diagrams, PDFs, and other visual content for
  text-only models. Use when you encounter visual files or image content and
  need to understand what they show. Requires a vision-capable `eyes`
  subagent — see the folder README for per-harness wiring.
---

# Vision Delegation

If your current model cannot read images, screenshots, or other visual
content, do NOT try to interpret them yourself — delegate anything visual to
the vision-capable `eyes` subagent.

## When to delegate

Use `eyes` for ANY of the following:

- A user attaches, pastes, or references an image, screenshot, photo,
  diagram, or scan
- A tool returns an image, screenshot, or rendered visual (e.g. Playwright
  screenshots, rendered charts, PDF pages)
- A file is a visual format (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`,
  `.pdf`, `.svg`, `.icns`, `.heic`)
- A task requires describing, reading, or comparing visual content, or
  checking what something looks like

## How to use it

1. Read/locate the image file path (relative or absolute).
2. Spawn the `eyes` subagent with the subagent/task tool, telling it exactly
   which files to look at and what to report back.
3. Use the returned description to continue the task.

Never claim to have seen an image you could not process. If no `eyes`
subagent is available, say you cannot view the image and ask the user to
describe it.

## Wiring per harness

The skill text is harness-agnostic; the `eyes` subagent must exist. See
[README.md](README.md) for the pi, opencode, and Claude Code setup.
