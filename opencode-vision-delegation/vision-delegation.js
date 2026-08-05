import { readFileSync } from "node:fs"
import { dirname, join } from "node:path"
import { fileURLToPath } from "node:url"

const PLUGIN_DIR = dirname(fileURLToPath(import.meta.url))
const VISION_FILE = join(PLUGIN_DIR, "..", "instructions", "vision.md")

let visionInstruction = null

function loadVisionInstruction() {
  if (visionInstruction === null) {
    const candidates = [process.env.OPENCODE_VISION_INSTRUCTION_FILE, VISION_FILE]
      .filter(Boolean)

    for (const file of candidates) {
      try {
        const text = readFileSync(file, "utf8").trim()
        if (text) {
          visionInstruction = text
          break
        }
      } catch {
        // try next candidate
      }
    }
    if (visionInstruction === null) visionInstruction = ""
  }
  return visionInstruction
}

function isDeepseek(model) {
  const providerID = model?.providerID ?? ""
  const id = model?.id ?? ""
  return /deepseek/i.test(`${providerID}/${id}`)
}

export const VisionDelegationPlugin = async () => {
  return {
    // Inject the vision-delegation instruction only when the active model
    // cannot see images. deepseek-v4-flash has no vision; gpt-5.6 / claude
    // do, and should not carry the extra prompt.
    "experimental.chat.system.transform": async (input, output) => {
      if (!isDeepseek(input.model)) return

      const instruction = loadVisionInstruction()
      if (!instruction) return

      output.system.push(instruction)
    },
  }
}

export default VisionDelegationPlugin
