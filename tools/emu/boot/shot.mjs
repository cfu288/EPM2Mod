// shot.mjs LABMS OUT.png: boot, run LABMS of lab time, write a screenshot (720 x 480) of the composed OSD planes
import { createBoot } from '../e101/boot.mjs';
import { screenshot } from '../e101/screen.mjs';
import { R, PC, SP, PSW } from '../e101/machine.mjs';
const e = createBoot({ blocksDir: process.env.BLOCKS });
if (process.env.SETUP) (await import(process.env.SETUP)).default(e);
R[PC] = 0x7E421020 | 0; R[SP] = 0x47001FFC | 0; R[PSW] = 0;
console.log(JSON.stringify(e.run({ maxLabMs: Number(process.argv[2]), maxMs: 300000 })));
console.log('osd runs', e.osd.runs, 'cmds', e.osd.cmds, 'bitmaps', e.osd.bitmaps, 'notes', e.osd.log.slice(0, 8));
console.log('planes drawn pixels', JSON.stringify(screenshot(e, process.argv[3])), '->', process.argv[3]);
