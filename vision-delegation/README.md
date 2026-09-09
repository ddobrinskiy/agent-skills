# vision-delegation

A portable skill for vision-less models: delegate anything visual (images,
screenshots, diagrams, PDFs) to a vision-capable `eyes` subagent instead of
hallucinating what the image shows. [`SKILL.md`](SKILL.md) is the
harness-agnostic instruction text; each harness below just needs the `eyes`
subagent defined.

## Files

- **`SKILL.md`** — the skill instruction (drop into your harness's skills dir).
- **`agents/eyes.md`** — the vision-specialist subagent definition
  (read-only, model swappable — pick any image-capable model you have).

## Required integrations

### pi (no extension needed)

The subagent tool is built in; only the agent definition is required:

```sh
cp agents/eyes.md ~/.pi/agent/agents/eyes.md
cp SKILL.md   ~/.pi/agent/skills/vision-delegation/SKILL.md
```

Swap `model: opencode-go/gpt-5.6-luna` in `agents/eyes.md` for any
image-capable model available in pi.

### opencode (plugin required)

opencode needs the plugin from the sibling folder
[`opencode-vision-delegation`](../opencode-vision-delegation) to inject the
instruction only for vision-less models (deepseek), plus the `eyes` agent in
`opencode.json` — see that folder's README for the full install. The
`vision.md` instruction it loads is an opencode-phrased variant of this
skill's text.

### Claude Code (no extension needed)

```sh
cp agents/eyes.md ~/.claude/agents/eyes.md
cp SKILL.md       ~/.claude/skills/vision-delegation/SKILL.md
```

The frontmatter format (name/description) matches Claude Code's skill and
subagent conventions; adjust `model:` in the agent file if needed.
