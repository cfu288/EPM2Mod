// Stop with a message that names Node when it is older than package.json "engines" asks for.
import { readFileSync } from 'node:fs'

const want = JSON.parse(readFileSync(new URL('./package.json', import.meta.url), 'utf8')).engines.node.replace('>=', '')
const [major, minor] = want.split('.').map(Number)
const [haveMajor, haveMinor] = process.versions.node.split('.').map(Number)
if (haveMajor < major || (haveMajor === major && haveMinor < minor)) {
  console.error(
    `error: the web apps need Node ${want} or newer; this is Node ${process.versions.node}. Run the command through ../tools/node.sh, or: nvm use`,
  )
  process.exit(1)
}
