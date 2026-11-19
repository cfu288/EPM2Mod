// Compatibility: the screen of the om-emu fork's boot lab (src/boot/e101screen.mjs compose, host/boot.mjs png).
// E101_ORDER=p4a,p4b,p8 (the planes from the bottom) as the earlier driver read it.
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { OM_EMU_DIR } from './paths.mjs';
const imp = (p) => import(pathToFileURL(path.join(OM_EMU_DIR, 'emu', p)).href);
const scr = await imp('src/boot/e101screen.mjs');
const host = await imp('host/boot.mjs');
const order = process.env.E101_ORDER ? process.env.E101_ORDER.split(',') : undefined;
export function compose(e, opts = {}) { return scr.compose(e, { ...(order ? { order } : {}), ...opts }); }
export function png(rgb, w, h) { return host.png({ rgb, w, h }); }
export function screenshot(e, file, opts) { const f = compose(e, opts); fs.writeFileSync(file, host.png(f)); return f.stats; }
