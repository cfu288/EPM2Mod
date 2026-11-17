// play.mjs OUTDIR STEP...: boot, then the scripted steps and screenshots: the om-emu fork's `bin/boot.mjs play`
// (third_party/om-emu/emu/bin/boot.mjs has the steps; forkcli.mjs the environment it takes from the earlier driver)
import { runFork } from './forkcli.mjs';
runFork('play', process.argv.slice(2));
