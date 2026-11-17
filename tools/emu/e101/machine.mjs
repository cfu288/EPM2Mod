// Compatibility for the scripts of this repository: the names the earlier drivers exported, now from the om-emu
// fork's boot lab (third_party/om-emu/emu/src/boot/). New code imports from there directly.
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { OM_EMU_DIR } from './paths.mjs';
export { OM_EMU_DIR };
process.env.OM_EMU_MODEL = 'E101';
const imp = (p) => import(pathToFileURL(path.join(OM_EMU_DIR, 'emu', p)).href);
export const machineMod = await imp('src/machine.mjs');
export const mem = await imp('src/core/mem.mjs');
export const cpu = await imp('src/core/cpu.mjs');
export const interp = await imp('src/core/interp.mjs');
const lab = await imp('src/boot/bootlab.mjs');
const flash = await imp('src/boot/flash.mjs');
export const { R, S, PC, SP, PSW, MDR, D0, D1, D2, D3, A0, A1, A2, A3, h8, BootLab } = lab;
export const E101 = lab.BootLab;
export const Flash = flash.FlashView;
export const IMAGE_BASE = 0x7E421020;
// A folder that tools/oetool.py unpack made (manifest.json and one file per block) as the boot lab's blocks
export function loadBlocks(dir) {
  const man = JSON.parse(fs.readFileSync(path.join(dir, 'manifest.json'), 'utf8'));
  return man.blocks.map((b) => {
    const head = new Uint8Array(Buffer.from(b.header, 'hex'));
    return { block: { load: Buffer.from(head).readUInt32LE(8), flags: Buffer.from(head).readUInt16LE(20) }, head, data: new Uint8Array(fs.readFileSync(path.join(dir, b.file))), name: b.file };
  });
}
