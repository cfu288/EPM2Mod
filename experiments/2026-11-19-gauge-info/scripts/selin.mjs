// SETUP: the inputs of the layout selector 0x7ED99ABF at 0x7ED99B51: settings 28|455 (sp+16), 24 (sp+20), 324 (sp+24), 44 (sp+28); and the result.
const M = await import(process.env.EPM2_REPO + '/emulator/e101/machine.mjs');
const { R, SP, A3 } = M;
export default function (e) {
  let last = ''; const t = () => (e.m.devices.clock.t / 1e6).toFixed(0);
  let a3 = 0;
  e.hook(0x7ED99B51, 's-in', () => { const sp = R[SP] >>> 0; a3 = R[A3] >>> 0; globalThis.__in = `s28=${e.r32(sp + 16)} s24=${e.r32(sp + 20)} s324=${e.r32(sp + 24)} s44=${e.r32(sp + 28)}`; });
  e.hook(0x7ED99DF8, 's-out', () => { const s = `${globalThis.__in} -> layout ${e.r32(a3 + 764)} +760=${e.r32(a3 + 760)} group ${R[2]}`; if (s !== last) { console.log(t(), s); last = s; } });
}
