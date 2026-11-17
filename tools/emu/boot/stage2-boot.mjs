// stage2-boot.mjs [LABMS]: the boot report of the stock (or BLOCKS) firmware from its reset vector: the om-emu fork's
// `bin/boot.mjs report`. Exit 0 when both kernels run, Usr0..Usr4 finished and no fault happened.
import { runFork } from './forkcli.mjs';
const a = process.argv.slice(2);
runFork('report', a.length ? ['--ms', a[0]] : []);
