#!/usr/bin/env python3
"""Regenerate the skills index in README.md.

Scans top-level directories and builds an index grouped by type:
- Skills: dirs with a SKILL.md — `name`/`description` from its frontmatter.
- Hooks: other dirs with a README.md — description is the README's first
  paragraph after the title.

Rewrites the section of README.md between the SKILLS-INDEX markers.
Uses stdlib only.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"

START_MARKER = "<!-- SKILLS-INDEX:START -->"
END_MARKER = "<!-- SKILLS-INDEX:END -->"


def parse_frontmatter(text: str) -> dict:
    """Parse simple YAML frontmatter (scalars and folded/literal blocks)."""
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return {}
    fields: dict[str, object] = {}
    key = None
    for line in match.group(1).splitlines():
        m = re.match(r"^(\w[\w-]*):\s*(.*)$", line)
        if m:
            key, value = m.group(1), m.group(2).strip()
            if value in (">", "|", ">-", "|-", ">+", "|+"):
                fields[key] = []
            else:
                fields[key] = value
                key = None
        elif key and isinstance(fields.get(key), list) and line.strip():
            fields[key].append(line.strip())
    return {
        k: " ".join(v).strip() if isinstance(v, list) else v
        for k, v in fields.items()
    }


def first_paragraph(text: str) -> str:
    """First paragraph of body text after the title (headings skipped)."""
    para: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not para and (not stripped or stripped.startswith("#")):
            continue
        if not stripped:
            break
        para.append(stripped)
    return " ".join(para)


def build_index() -> str:
    skills: list[str] = []
    hooks: list[str] = []
    for d in sorted(ROOT.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        skill_md = d / "SKILL.md"
        readme = d / "README.md"
        if skill_md.exists():
            fm = parse_frontmatter(skill_md.read_text())
            name = fm.get("name") or d.name
            desc = fm.get("description") or "(no description)"
            skills.append(f"- **[{name}]({d.name}/SKILL.md)** — {desc}")
        elif readme.exists():
            desc = first_paragraph(readme.read_text()) or "(no description)"
            hooks.append(f"- **[{d.name}]({d.name}/README.md)** — {desc}")

    return "\n".join(
        [
            "### Skills",
            "",
            "\n".join(skills) if skills else "_No skills found._",
            "",
            "### Hooks",
            "",
            "\n".join(hooks) if hooks else "_No hooks found._",
        ]
    )


def main() -> int:
    readme = README.read_text()
    block = f"{START_MARKER}\n{build_index()}\n{END_MARKER}"

    pattern = re.compile(
        rf"{re.escape(START_MARKER)}.*?{re.escape(END_MARKER)}", re.DOTALL
    )
    if pattern.search(readme):
        updated = pattern.sub(lambda _: block, readme)
    else:
        updated = readme.rstrip() + f"\n\n## Skills\n\n{block}\n"

    if updated != readme:
        README.write_text(updated)
        print("README.md: skills index updated")
    else:
        print("README.md: skills index already up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
