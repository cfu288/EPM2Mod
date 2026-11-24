// touch_probe.mjs OUTDIR STEP...: the steps of af_probe.mjs (w:MS, key:NAME[:MS], shot:NAME, tag:HEX) plus
//   touch:X:Y[:tap]  arm a touch at (X, Y): at the next MAGNIFY key (so press it after this step) the GUI's handler
//             pressLvMagnifyKey 0x7ECDBBE7 is replaced by the touch handler 0x7ECDC22F on the same zoom context
//             (a1; x at +8, y at +12; with tap the event id +0 = 0x2000011, which adds touchTargetAf): a pad in lab RAM
//             `mov 0x7ECDC22F,a0; calls (a0); ret [a2],8` (the handler's own return)
//   tf        print the special AF frame of TAKE_FOCUS (TF = *(u32 *)0x60515FA8): active +54 enable, +56 mag,
//             +58 x, +60 y; requested +62 enable, +64 mag, +66 x, +68 y; af_type +12; and the clip state 0x60515E24..26
// and a log of each call on the path from a touch (or the MAGNIFY key) to the special AF frame:
// the GUI touch handler, moveZoomFrameTouch, OlyApi moveZoomFrame / touchTargetAf, CapThr setAfFrame /
// setMagnifyAfFrame, api_rec_Set_MagnifyAF_Frame and the TAKE_FOCUS setter.
// Run: E101_STATE=s.json emulator/emu-run IMAGE /abs/path/touch_probe.mjs OUTDIR STEP...
import fs from 'node:fs';
import path from 'node:path';
const E = path.join(process.env.EPM2_REPO, 'emulator/e101');
const { createBoot, backtrace } = await import(path.join(E, 'boot.mjs'));
const { screenshot } = await import(path.join(E, 'screen.mjs'));
const { KEYS, press, release } = await import(path.join(E, 'keys.mjs'));
const { R, PC, SP, PSW, D0, D1, A0, A1 } = await import(path.join(E, 'machine.mjs'));
const e = createBoot({ blocksDir: process.env.BLOCKS });
R[PC] = 0x7E421020 | 0; R[SP] = 0x47001FFC | 0; R[PSW] = 0;
const out = process.argv[2]; fs.mkdirSync(out, { recursive: true });
let step = 'boot';
const s16 = (v) => ((v & 0xFFFF) ^ 0x8000) - 0x8000;
const HOOKS = {
  0x7ECDC22F: 'gui touchStartZoomFrame/touchTargetAf',
  0x7ECDAFD4: 'gui moveZoomFrameTouch',
  0x7E98716A: 'OlyHfwOpeShoot::moveZoomFrame',
  0x7E98A0B9: 'OlyHfwOpeShoot::touchTargetAf',
  0x7EA1A708: 'CapThr setAfFrame',
  0x7EA1A8E5: 'CapThr setMagnifyAfFrame',
  0x7E68ACFE: 'api_rec_Set_MagnifyAF_Frame',
  0x7E5993D4: 'special frame request (d0 enable, d1 x, a0 y, a1 mag)',
  0x7E59356C: 'TakeFcs special_af setter',
};
for (const [pc, name] of Object.entries(HOOKS)) {
  e.hook(Number(pc), name, (lab) => {
    const bt = backtrace(lab, R[SP] >>> 0, 5).map((s) => s.replace(/^\[sp\+\w+\] /, '')).join(' < ');
    console.log(`[${step}] ${name}: d0=${R[D0] | 0} d1=${s16(R[D1])} a0=${s16(R[A0])} (0x${(R[A0] >>> 0).toString(16)}) a1=${R[A1] | 0} | ${bt}`);
  });
}
const PAD = [0xFC, 0xDC, 0x2F, 0xC2, 0xCD, 0x7E, 0xF0, 0xF0, 0xDF, 0x20, 0x08];
let armed = null;
e.hook(0x7ECDBBE7, 'pressLvMagnifyKey', () => {
  if (!armed) return;
  const ctx = R[A1] >>> 0, w32 = (a, v) => e.wr(a, [v & 255, (v >>> 8) & 255, (v >>> 16) & 255, (v >>> 24) & 255]);
  w32(ctx + 8, armed.x); w32(ctx + 12, armed.y); if (armed.tap) w32(ctx, 0x2000011);
  console.log(`[${step}] touch (${armed.x}, ${armed.y})${armed.tap ? ' tap' : ''} injected, ctx 0x${ctx.toString(16)}`);
  armed = null; e.wr(0x11A00, PAD); R[PC] = 0x11A00;
});
const run = (ms) => { const r = e.run({ maxLabMs: ms, maxMs: 600000 }); if (r.why !== 'labtime') { console.log('STOP', JSON.stringify(r)); process.exit(2); } };
const b = (a) => (e.r32(a & ~3) >>> (8 * (a & 3))) & 0xFF;
const h = (a) => s16(b(a) | (b(a + 1) << 8));
function tf() {
  const t = e.r32(0x60515FA8) >>> 0;
  if (!t) { console.log(`[${step}] TF null`); return; }
  console.log(`[${step}] TF 0x${t.toString(16)} af_type(+12)=${b(t + 12)} active: en=${b(t + 54)} mag=${h(t + 56)} x=${h(t + 58)} y=${h(t + 60)}`
    + ` | request: en=${b(t + 62)} mag=${h(t + 64)} x=${h(t + 66)} y=${h(t + 68)} | clip 0x60515E24=${b(0x60515E24)} x=${b(0x60515E25)} y=${b(0x60515E26)}`);
}
function tag(hex) {
  const t = parseInt(hex, 16), ent = 0x603A0E38 + 8 * (t >> 4), ptr = e.r32(ent + 4) >>> 0;
  const wide = (t & 0xF) === 0xA || (t & 0xF) === 0x2;
  let v = wide ? b(ptr) | (b(ptr + 1) << 8) : b(ptr);
  if ((t & 0xF) === 0xA && v & 0x8000) v -= 0x10000;
  console.log(`[${step}] tag 0x${t.toString(16)} = ${v}`);
}
run(Number(process.env.BOOTMS || 1500));
for (const s of process.argv.slice(3)) {
  step = s;
  const f = s.split(':');
  if (f[0] === 'w') run(Number(f[1]));
  else if (f[0] === 'key') { if (!KEYS[f[1]]) { console.log('unknown key', f[1]); process.exit(2); } press(e, f[1]); run(Number(f[2] || 120)); release(e, f[1]); run(400); }
  else if (f[0] === 'shot') screenshot(e, path.join(out, f[1] + '.png'));
  else if (f[0] === 'tag') tag(f[1]);
  else if (f[0] === 'tf') tf();
  else if (f[0] === 'touch') armed = { x: Number(f[1]), y: Number(f[2]), tap: f[3] === 'tap' };
  else { console.log('unknown step', s); process.exit(2); }
}
console.log('done at lab ms', (e.m.devices.clock.t / 1e6).toFixed(0), '| firmware errors', e.errLog.length);
