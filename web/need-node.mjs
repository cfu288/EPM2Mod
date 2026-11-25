// Stop with a message that names Node when it is not the version of ../.nvmrc, the one place that names it.
import { readFileSync } from 'node:fs'

const want = readFileSync(new URL('../.nvmrc', import.meta.url), 'utf8')
  .trim()
  .replace(/^v/, '')
if (process.versions.node !== want) {
  console.error(
    `error: the web apps need Node ${want} (.nvmrc); this is Node ${process.versions.node}. Run the command through ../tools/node.sh, or: nvm use`,
  )
  process.exit(1)
}
