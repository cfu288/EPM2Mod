// shot.mjs LABMS OUT.png: boot, run LABMS of lab time, write one screenshot: the om-emu fork's `bin/boot.mjs play` with
// --boot-ms LABMS and the step shot:NAME into OUT.png's folder
import path from 'node:path';
import { runFork } from './forkcli.mjs';
const [ms, file] = process.argv.slice(2);
process.env.BOOTMS = ms;
runFork('play', [path.dirname(path.resolve(file)), `shot:${path.basename(file, '.png')}`]);
