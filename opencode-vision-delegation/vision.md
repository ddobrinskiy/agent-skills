# Vision delegation

Your current model (deepseek-v4-flash) cannot read images, screenshots, or
other visual content. Whenever a task involves anything visual, do NOT try to
interpret it yourself — delegate to the `eyes` subagent using the task tool.

## When to delegate

Use `eyes` for ANY of the following:

- A user attaches, pastes, or references an image, screenshot, photo, diagram,
  or scan
- A tool returns an image, screenshot, or rendered visual (e.g. Playwright
  screenshots, rendered charts, PDF pages)
- A file is a visual format (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.pdf`,
  `.svg`, `.icns`, `.heic`)
- A task requires describing, reading, or comparing visual content, or checking
  what something looks like

## How to use it

1. Read/locate the image file path (relative or absolute).
2. Call the task tool with `subagent_type: "eyes"`, telling it exactly which
   files to look at and what to report back.
3. Use the returned description to continue the task.

Never claim to have seen an image you could not process. If no `eyes` subagent
is available, say you cannot view the image and ask the user to describe it.
