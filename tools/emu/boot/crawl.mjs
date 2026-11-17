// crawl.mjs OUTDIR NAME STEP...: the menu crawl from the screen the steps reach: the om-emu fork's `bin/boot.mjs crawl`
// (forkcli.mjs: the environment it takes, DEPTH, MAXLIST, ...)
import { runFork } from './forkcli.mjs';
runFork('crawl', process.argv.slice(2));
