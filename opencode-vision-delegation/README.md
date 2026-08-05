# opencode-vision-delegation

An [opencode](https://opencode.ai) plugin that makes a vision-less model (e.g.
`deepseek-v4-flash`) automatically delegate anything visual to a vision-capable
`eyes` subagent, without cluttering the prompt for models that can already see.

When the active model is deepseek, the plugin injects
[`vision.md`](vision.md) into the system prompt via the
`experimental.chat.system.transform` hook. That instruction tells the model to
delegate all image/screenshot/PDF/visual tasks to an `eyes` subagent through
the task tool. Models that can see images (gpt-5.6-luna, claude, …) never see
the extra prompt.

## Files

- **`vision-delegation.js`** — the opencode plugin (auto-discovered from
  `~/.config/opencode/plugins/`; no config entry needed).
- **`vision.md`** — the instruction text, loaded at runtime so you can edit it
  without touching the plugin. Override its location with
  `OPENCODE_VISION_INSTRUCTION_FILE`.

## Install

1. Copy both files into your opencode config:

   ```sh
   mkdir -p ~/.config/opencode/plugins ~/.config/opencode/instructions
   cp vision-delegation.js ~/.config/opencode/plugins/
   cp vision.md ~/.config/opencode/instructions/
   ```

   The plugin resolves `vision.md` as `../instructions/vision.md` relative to
   itself, so that layout is what it expects by default.

2. Define the `eyes` subagent in `opencode.json` (global
   `~/.config/opencode/opencode.json` or project `.opencode/opencode.json`):

   ```json
   {
     "agent": {
       "eyes": {
         "description": "Vision-capable subagent that reads and describes images, screenshots, diagrams, PDFs, and other visual content. Use as 'eyes' whenever the main model cannot see an image.",
         "mode": "subagent",
         "model": "openai/gpt-5.6-luna-fast",
         "temperature": 0.2,
         "permission": { "read": "allow", "edit": "deny", "bash": "deny" },
         "prompt": "You are 'eyes' - a vision specialist. Your job is to look at visual content and describe it precisely so that text-only models can understand it.\n\nWhen given image paths (screenshots, photos, diagrams, charts, PDF pages, etc.):\n1. Read every referenced file with the read tool.\n2. Describe the contents in detail: text shown (verbatim), UI elements and their positions, layout, colors, data/numbers in charts, and any notable details.\n3. Quote any visible text exactly, transcribe code/errors exactly, and state unambiguous values.\n4. Note anything ambiguous or unreadable rather than guessing.\n\nReturn a complete, structured description. Do not edit files or run commands."
       }
     }
   }
   ```

   Swap `openai/gpt-5.6-luna-fast` for any model you have that supports images.

3. Restart opencode. Then in a deepseek session, dropping in an image will
   trigger an `eyes` subagent run that reads and describes it.
