# agent-skills
Personal collection of LLM agent skills and instructions (Claude Code, etc.)

## Contents

<!-- SKILLS-INDEX:START -->
### Skills

- **[manim-animation-explainer](manim-animation-explainer/SKILL.md)** — Use when building a Manim Community animated explainer video for a technical topic. Gives the three-level-depth structure (simple/technical/deep-dive) in one combined Scene, the 1080p60-final / LaTeX-available defaults, a self-contained project layout, the `pyproject.toml` + `render.sh` skeleton, and Manim gotchas (font substitution, frame bounds, verifying output before declaring done). Saves re-deriving the whole convention and system prerequisites from scratch.
- **[scrape-via-recorded-client](scrape-via-recorded-client/SKILL.md)** — Use when you need repeated or programmatic access to a website's data and the current plan is "control a browser every time" (Playwright/Puppeteer/ browser-use). Record one real browsing session into a HAR file (network requests) or an MHTML snapshot (rendered DOM), reverse-engineer the underlying API or data shape from that recording, then write a small script or CLI that hits it directly. Turns a slow, expensive, flaky browser-automation loop into a fast, cheap, deterministic one. Trigger phrases: "build a CLI for this site", "scrape X repeatedly", "I don't want to drive a browser every time", "derive a client from this website".

### Hooks

- **[sibling-file-context-hook](sibling-file-context-hook/README.md)** — A `PostToolUse` + `UserPromptSubmit` hook for [Claude Code](https://claude.com/claude-code) that auto-injects a file's "sibling" into the agent's context whenever either half of the pair is read, edited, or `@`-mentioned in a prompt — so the agent never sees one half in isolation.
<!-- SKILLS-INDEX:END -->
