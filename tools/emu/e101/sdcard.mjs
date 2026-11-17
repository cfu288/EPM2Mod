// Compatibility: the card of the om-emu fork's boot lab (src/boot/e101card.mjs), with buildFatImage(dir) of a host
// folder as the earlier driver had it.
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { OM_EMU_DIR } from './paths.mjs';
const imp = (p) => import(pathToFileURL(path.join(OM_EMU_DIR, 'emu', p)).href);
const card = await imp('src/boot/e101card.mjs');
const host = await imp('host/boot.mjs');
export const { listFat, attachCard } = card;
export function buildFatImage(dir, opts) { return card.buildFat16(dir ? host.folderTree(dir) : { entries: [] }, opts); }
