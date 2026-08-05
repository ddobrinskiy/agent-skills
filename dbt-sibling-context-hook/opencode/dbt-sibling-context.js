import { randomUUID } from "node:crypto"
import { spawn } from "node:child_process"
import { existsSync } from "node:fs"
import { dirname, isAbsolute, resolve } from "node:path"
import { fileURLToPath } from "node:url"

const PLUGIN_DIR = dirname(fileURLToPath(import.meta.url))
const SIBLING_HOOK = resolve(PLUGIN_DIR, "dbt-sibling-context.sh")

function asAbsolutePath(value, worktree) {
  if (typeof value !== "string" || value.length === 0 || value.startsWith("data:")) return null

  try {
    if (value.startsWith("file:")) return fileURLToPath(new URL(value))
  } catch {
    return null
  }

  return isAbsolute(value) ? value : resolve(worktree, value)
}

function isDbtModelPath(filePath, worktree) {
  if (!filePath) return false

  const modelsRoot = `${resolve(worktree, "etl", "dbt_project", "models")}/`
  const normalized = resolve(filePath)
  return (
    normalized.startsWith(modelsRoot) &&
    (normalized.endsWith(".sql") || normalized.endsWith(".yml"))
  )
}

function filePathFromPart(part, worktree) {
  if (!part || part.type !== "file") return null
  return asAbsolutePath(part.source?.path ?? part.url ?? part.filename, worktree)
}

function runSiblingHook({ cwd, filePath }) {
  if (!existsSync(SIBLING_HOOK)) return Promise.resolve(null)

  return new Promise((resolveHook) => {
    let stdout = ""

    const child = spawn("bash", [SIBLING_HOOK], {
      cwd,
      env: { ...process.env },
      stdio: ["pipe", "pipe", "ignore"],
    })

    child.stdout.setEncoding("utf8")
    child.stdout.on("data", (chunk) => {
      stdout += chunk
    })
    child.on("error", () => resolveHook(null))
    child.on("close", (code) => {
      if (code !== 0 || !stdout.trim()) {
        resolveHook(null)
        return
      }

      try {
        const result = JSON.parse(stdout)
        resolveHook(result?.additional_context ? result : null)
      } catch {
        resolveHook(null)
      }
    })

    child.stdin.end(
      JSON.stringify({
        cwd,
        ...(filePath ? { file_path: filePath } : {}),
      }),
    )
  })
}

function contextFromResult(result) {
  return result?.additional_context ?? ""
}

function appendSyntheticContext(input, output, context) {
  if (!context) return

  output.parts.push({
    id: `prt_${randomUUID()}`,
    sessionID: input.sessionID,
    messageID: output.message.id,
    type: "text",
    text: context,
    synthetic: true,
  })
}

export const DbtSiblingContextPlugin = async ({ worktree, directory }) => {
  const projectRoot = worktree ?? directory
  const promptCwd = directory ?? projectRoot

  if (!projectRoot) return {}

  return {
    // @file and --file inputs are resolved into file parts before OpenCode
    // calls a model. There is no Read tool event for those attachments, so
    // load their siblings here without asking the model to read anything.
    "chat.message": async (input, output) => {
      if (input.agent === "title") return

      const filePaths = [
        ...new Set(
          output.parts
            .map((part) => filePathFromPart(part, projectRoot))
            .filter((filePath) => isDbtModelPath(filePath, projectRoot)),
        ),
      ]
      if (filePaths.length === 0) return

      const contexts = await Promise.all(
        filePaths.map(async (filePath) =>
          contextFromResult(await runSiblingHook({ cwd: promptCwd, filePath })),
        ),
      )
      appendSyntheticContext(input, output, contexts.filter(Boolean).join("\n"))
    },

    // OpenCode has no supported plugin API for enqueueing a second built-in
    // Read. The sibling is read here and appended to the completed tool output;
    // this is automatic and does not depend on a model prompt.
    "tool.execute.after": async (input, output) => {
      const tool = String(input.tool ?? "").toLowerCase()
      if (tool !== "read") return

      const rawPath = input.args?.filePath ?? input.args?.path
      const filePath = asAbsolutePath(rawPath, projectRoot)
      if (!isDbtModelPath(filePath, projectRoot)) return

      const result = await runSiblingHook({
        cwd: promptCwd,
        filePath,
      })
      const context = contextFromResult(result)
      if (!context) return

      output.output = output.output ? `${output.output}\n\n${context}` : context
    },
  }
}

export default DbtSiblingContextPlugin
