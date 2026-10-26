# agent-skills
Personal collection of LLM agent skills and instructions (Claude Code, etc.)

## Contents

<!-- SKILLS-INDEX:START -->
### Skills

- **[android-e2e-development](android-e2e-development/SKILL.md)** — Use when building or debugging an Android app and proving real end-to-end behavior on an emulator or physical device — build, install the exact APK, exercise the actual user journey, and record honest evidence. Also covers running regressions in an isolated, agent-owned emulator (explicit adb server/serial, resource limits, signing keys, camera scenes, IME checks) and the instrumentation-test traps that produce false passes.
- **[manim-animation-explainer](manim-animation-explainer/SKILL.md)** — Use when building a Manim Community animated explainer video for a technical topic. Gives the three-level-depth structure (simple/technical/deep-dive) in one combined Scene, the 1080p60-final / LaTeX-available defaults, a self-contained project layout, the `pyproject.toml` + `render.sh` skeleton, and Manim gotchas (font substitution, frame bounds, verifying output before declaring done). Saves re-deriving the whole convention and system prerequisites from scratch.
- **[scrape-via-recorded-client](scrape-via-recorded-client/SKILL.md)** — Use when you need repeated or programmatic access to a website's data and the current plan is "control a browser every time" (Playwright/Puppeteer/ browser-use). Record one real browsing session into a HAR file (network requests) or an MHTML snapshot (rendered DOM), reverse-engineer the underlying API or data shape from that recording, then write a small script or CLI that hits it directly. Turns a slow, expensive, flaky browser-automation loop into a fast, cheap, deterministic one. Trigger phrases: "build a CLI for this site", "scrape X repeatedly", "I don't want to drive a browser every time", "derive a client from this website".
- **[vision-delegation](vision-delegation/SKILL.md)** — Describes images, screenshots, diagrams, PDFs, and other visual content for text-only models. Use when you encounter visual files or image content and need to understand what they show. Requires a vision-capable `eyes` subagent — see the folder README for per-harness wiring.

### Hooks & extensions

- **[dbt-sibling-context-hook](dbt-sibling-context-hook/README.md)** — Cross-harness dbt sibling-context hooks for Claude Code, Codex, and OpenCode. Each adapter automatically loads the paired `.sql`/`.yml` model file under `etl/dbt_project/models/`, keeping SQL and YAML together in the agent's context.
- **[opencode-vision-delegation](opencode-vision-delegation/README.md)** — An [opencode](https://opencode.ai) plugin that makes a vision-less model (e.g. `deepseek-v4-flash`) automatically delegate anything visual to a vision-capable `eyes` subagent, without cluttering the prompt for models that can already see.
- **[pi-extensions](pi-extensions/README.md)** — Extensions for [pi](https://github.com/earendil-works/pi), a terminal coding agent. Each subfolder is one self-contained extension: drop the folder into `~/.pi/agent/extensions/` and pi discovers it on the next start.
<!-- SKILLS-INDEX:END -->
