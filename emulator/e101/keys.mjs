// Compatibility: the keys of the om-emu fork's boot lab (emulator/om-emu/emu/src/boot/e101keys.mjs).
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { OM_EMU_DIR } from './paths.mjs';
export const { KEYS, ADC_IDLE, press, release, pushSample, emitKey } = await import(pathToFileURL(path.join(OM_EMU_DIR, 'emu/src/boot/e101keys.mjs')).href);
