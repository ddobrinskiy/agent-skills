---
name: manim-animation-explainer
description: >
  Use when building a Manim Community animated explainer video for a
  technical topic. Gives the three-level-depth structure
  (simple/technical/deep-dive) in one combined Scene, the 1080p60-final /
  LaTeX-available defaults, a self-contained project layout, the
  `pyproject.toml` + `render.sh` skeleton, and Manim gotchas (font
  substitution, frame bounds, verifying output before declaring done). Saves
  re-deriving the whole convention and system prerequisites from scratch.
---

# Manim Animation Explainer

How to build visual explainers for technical topics using
[Manim Community Edition](https://docs.manim.community/).

## Defaults — DO NOT DEVIATE without asking

1. **Three levels of depth**:
   - **Level 1 — Super simple**: analogy-driven, plain language, no jargon. Anyone audience.
   - **Level 2 — Technical**: components, interfaces, data structures, control flow. Engineer audience.
   - **Level 3 — Deep dive**: edge cases, protocol details, design rationale, gotchas. Domain-curious audience.
2. **One Scene class → one combined video.** Do NOT render three separate files and stitch with ffmpeg. Put all three levels inside a single `Scene.construct()`.
3. **Fullscreen header between levels.** Each level opens with a large `LEVEL N` card that fills the screen, then fades to the content. The header acts as the visual delimiter.
4. **1080p60 only** for final deliverable (`-qh`). Use `-ql` (480p15) for fast iteration while debugging; never ship `-ql` or `-qm`.
5. **Use LaTeX freely.** Math notation (`MathTex`, `Tex`) gives the 3Blue1Brown look and is part of the default toolbox. Requires MacTeX installed locally — see system prereqs below. Plain Pango `Text` is still right for labels and code blocks.
6. **Ground every claim** in a real source. Use WebSearch / WebFetch / context7. Cite sources in the file docstring.

## Project layout

Self-contained folder per explainer, named after the topic:

```
<topic>_manim_explainer/
├── README.md                  # short summary + sources
├── pyproject.toml             # uv-managed
├── .python-version            # pin to 3.12
├── .gitignore                 # ignore media/ .venv/ __pycache__/
├── <topic>_explainer.py       # one Scene class with three levels
└── render.sh                  # uv run manim -qh ...
```

## `pyproject.toml`

```toml
[project]
name = "<topic>-manim-explainer"
version = "0.1.0"
description = "Manim Community animation explaining <topic>."
requires-python = ">=3.12,<3.14"
dependencies = ["manim>=0.19,<0.21"]

[tool.uv]
package = false
```

## System prerequisites (macOS, one-time)

```bash
brew install cairo pango pkg-config ffmpeg
brew install --cask mactex-no-gui          # ~3 GB; provides latex/dvisvgm for MathTex/Tex
```

- `pkg-config` is required because `pycairo` builds from source on first install.
- MacTeX (no-gui variant) is ~3 GB and the cask installer requires sudo. The full `mactex` cask (~5 GB) adds GUI apps you don't need.
- Verify with `which latex && which dvisvgm` after install — both should resolve. You may need to `eval "$(/usr/libexec/path_helper)"` or open a new shell for `/Library/TeX/texbin` to land on PATH.

## Scene template (single combined video)

```python
"""<Topic> — visual explainer in three levels.

Sources:
- <primary spec URL>
- <secondary doc URL>
- ...

Render:
    uv run manim -ql <topic>_explainer.py FullExplainer    # preview
    uv run manim -qh <topic>_explainer.py FullExplainer    # final 1080p60
"""

from manim import (
    BOLD, DOWN, LEFT, RIGHT, UP, WHITE,
    FadeIn, FadeOut, LaggedStart, MathTex, Scene, Tex, Text, VGroup, Write,
)

# Consistent palette so colour itself carries actor identity across levels.
ACCENT_COLOR = "#FFD93D"   # yellow — titles, callouts
MUTED_COLOR  = "#9AA1A8"   # grey  — subtitles
WARN_COLOR   = "#FF6B6B"   # red   — problems / failure
GOOD_COLOR   = "#4FCB72"   # green — solutions / success
MONO_FONT    = "Menlo"     # macOS monospace; Pango falls back if missing


class FullExplainer(Scene):
    """<Topic> in three levels, delimited by fullscreen LEVEL cards."""

    def construct(self) -> None:
        self.opening()                                # 0. title card
        self.level_header(1, "The simple idea")
        self.level_1_simple()
        self.level_header(2, "How it actually works")
        self.level_2_technical()
        self.level_header(3, "Why it's designed this way")
        self.level_3_deep_dive()
        self.closing()

    # -- delimiters ---------------------------------------------------------
    def opening(self) -> None:
        title = Text("<Topic>", weight=BOLD, color=ACCENT_COLOR, font_size=72)
        subtitle = Text("a visual explainer", color=MUTED_COLOR, font_size=30)
        subtitle.next_to(title, DOWN, buff=0.4)
        self.play(Write(title), run_time=1.2)
        self.play(FadeIn(subtitle, shift=DOWN * 0.3))
        self.wait(1.2)
        self.play(FadeOut(VGroup(title, subtitle)))

    def level_header(self, n: int, blurb: str) -> None:
        """Fullscreen section divider. Big number, short blurb, then fade."""
        number = Text(f"LEVEL {n}", color=ACCENT_COLOR,
                      weight=BOLD, font_size=140)
        blurb_t = Text(blurb, color=WHITE, font_size=42)
        group = VGroup(number, blurb_t).arrange(DOWN, buff=0.7)
        self.play(FadeIn(number, shift=UP * 0.3), run_time=0.5)
        self.play(Write(blurb_t), run_time=0.8)
        self.wait(1.2)
        self.play(FadeOut(group))

    def closing(self) -> None:
        line = Text("That's it.", color=ACCENT_COLOR, weight=BOLD, font_size=44)
        self.play(Write(line), run_time=1.0)
        self.wait(2.0)
        self.play(FadeOut(line))

    # -- the three levels ---------------------------------------------------
    def level_1_simple(self) -> None:
        # plain-language analogy goes here
        ...

    def level_2_technical(self) -> None:
        # components, interfaces, control flow
        ...

    def level_3_deep_dive(self) -> None:
        # edge cases, design rationale
        ...
```

## `render.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
uv run manim -qh --disable_caching <topic>_explainer.py FullExplainer
echo "==> Output:"
/bin/ls -lh media/videos/<topic>_explainer/1080p60/FullExplainer.mp4
```

Quality flags (use only `-ql` or `-qh`):

| Flag | Resolution | FPS  | When         |
|------|------------|------|--------------|
| `-ql`| 854×480    | 15   | Fast iteration / debugging |
| `-qm`| 1280×720   | 30   | Don't use     |
| `-qh`| 1920×1080  | 60   | **Final deliverable** |
| `-qk`| 3840×2160  | 60   | Don't use unless explicitly asked |

## When to use `MathTex` / `Tex` vs `Text`

| Use                                  | Mobject       |
|--------------------------------------|---------------|
| Equations, summations, integrals     | `MathTex`     |
| Body prose with LaTeX commands       | `Tex`         |
| Labels, headers, callouts            | `Text` (Pango) — faster, no LaTeX round-trip |
| Source code (Solidity / Python / …)  | `Text` with `font=MONO_FONT` |

`MathTex` is slow on first render (LaTeX compile → dvi → svg). It caches, so subsequent renders are fast.

## Manim gotchas to remember

- **Pin `font=MONO_FONT` on any `Text` containing `→`, `×`, `·`, `±`, `Δ`, etc.** The default Pango font on macOS doesn't carry these glyphs natively, so Pango silently substitutes a *different* font for just those characters — visibly different baseline and stroke weight in the middle of an otherwise-uniform run. Menlo has them all. Either pass `font=MONO_FONT` explicitly, or rewrite the string to ASCII (`->` instead of `→`). The rule of thumb: if a `Text` contains anything outside basic Latin + punctuation, set `font=` explicitly. This applies to helpers too — `bullet()`, `two_line_box()`, etc. should accept a `font` kwarg.
- **Pango handles multi-line `Text`** via `\n`. Use a single `Text("line1\nline2\n...")` for code blocks — DO NOT build a `VGroup` of one-`Text`-per-line, because uneven character widths break vertical alignment in subtle ways.
- **`arrange(DOWN, aligned_edge=LEFT)`** aligns bounding-box left edges. Lines with leading spaces shift their visible content right, which is what you want for indented code.
- **Frame is ~14.22 × 8 units** (x: −7.11 to +7.11, y: −4 to +4). Anything past those bounds is clipped silently. Verify by sampling frames with `ffmpeg -ss <t> -i out.mp4 -frames:v 1 frame.png`.
- **Fade out before next scene**, even if you replace the whole canvas. Stale mobjects leak across transitions.
- **Use `.set_x(...)` not `.shift(LEFT * ...)`** when you want absolute placement — `shift` compounds, `set_x` is idempotent.
- **`Indicate`, `Flash`, `Circumscribe`** are good emphasis primitives. `LaggedStart` introduces bullet lists organically.
- **Reuse a palette** across all three levels so colour acts as actor/concept identity.

## Verifying output before declaring done

1. Render with `-ql --disable_caching` first.
2. `ffprobe -v error -show_entries format=duration -of csv=p=0 out.mp4` — confirm runtime is sensible.
3. `ffmpeg -ss <t> -i out.mp4 -frames:v 1 frame.png` at multiple `t` values to spot-check layout. **Layout bugs are invisible in Manim's logs.**
4. Look for: clipped text at frame edges, overlapping mobjects, stale mobjects leaking through transitions.
5. Only then run the final `-qh` render.
6. **Delete the debug artifacts** once `-qh` is good: `rm -rf media/videos/<topic>_explainer/480p15` (and `720p30` if you touched it). The 1080p60 mp4 is the only output that should remain in the workspace. `media/` is git-ignored so the user never sees these, but they pile up and eat disk on iteration.
