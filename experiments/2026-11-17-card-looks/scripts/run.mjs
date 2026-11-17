// The file-read probe in the boot lab: at the application's event loop (a task), after T ms, run probe.bin once
// (fopen "r", fread 512, fclose) with the task's registers saved, then put them back and go on.
import fs from 'node:fs';
const EMU = process.env.OM_EMU + '/emu';
const host = await import(EMU + '/host/boot.mjs');
const { createE101 } = await import(EMU + '/src/boot/e101.mjs');
const { buildFat16, listFat } = await import(EMU + '/src/boot/e101card.mjs');
const { R } = await import(EMU + '/src/core/cpu.mjs');
const fw = host.readBin(process.env.BIN);
const card = buildFat16(host.folderTree(process.env.CARD)).img;
const e = createE101({ rom: fw.rom, blocks: fw.blocks, card });
const probe = new Uint8Array(fs.readFileSync(process.env.PROBE));
const AT = Number(process.env.AT ?? 3000), START = 0x13000, END = 0x1305b, RES = 0x13400, BUF = 0x13800;
let saved = null, injected = false, done = null, t0 = 0;
e.wr(START, probe); e.wr(RES, new Uint8Array(16)); e.wr(BUF, new Uint8Array(512).fill(0xEE));
e.hook(0x7EBA752B, 'probe-inject', () => {
  if (injected || e.onCpu1 || e.labMs() < AT) return;
  injected = true; saved = Int32Array.from(R); t0 = e.labMs(); R[9] = START;
});
e.hook(END, 'probe-end', () => {
  done = { ms: (e.labMs() - t0).toFixed(1), handle: e.r32(RES), read: e.r32(RES + 4), fclose: e.r32(RES + 8), magic: e.r32(RES + 12).toString(16) };
  R.set(saved);
});
const { press, release } = await import(EMU + '/src/boot/e101keys.mjs');
e.run({ maxLabMs: AT, maxMs: 600000 });
press(e, 'INFO'); e.run({ maxLabMs: 120 }); release(e, 'INFO');        // a key: the event loop takes its event in its task
const r = e.run({ maxLabMs: 3000, maxMs: 600000 });
console.log('stop', JSON.stringify(r), 'lab ms', e.labMs().toFixed(0));
console.log('probe', JSON.stringify(done));
const want = new Uint8Array(fs.readFileSync(process.env.CARD + '/LOOKS.BIN')).subarray(0, 512), got = e.rd(BUF, 512);
let same = true; for (let i = 0; i < 512; i++) if (want[i] !== got[i]) { same = false; console.log('first difference at', i, want[i], got[i]); break; }
console.log('buffer equals the file\'s first 512 bytes:', same, '| head', String.fromCharCode(...got.subarray(0, 8)));
console.log('file task around the probe:', e.fileLog.filter((l) => parseFloat(l) >= t0 - 1).slice(0, 12).join(' ; '));
console.log('errors after the probe:', e.errLog.filter((l) => parseFloat(l) >= t0).join(' ; ') || 'none', '| refused MMIO', e.denied.length, '| CPU1', e.m.cores.state().parked ?? 'ok');
// the camera goes on: a key after the probe
press(e, 'MENU'); e.run({ maxLabMs: 120 }); release(e, 'MENU'); const r2 = e.run({ maxLabMs: 800 });
console.log('after the probe, MENU:', JSON.stringify(r2), '| events taken', e.evLog.length, '| card files unchanged:', listFat(e.card.img).map((f) => f.path + ' ' + f.size).join(', '));
