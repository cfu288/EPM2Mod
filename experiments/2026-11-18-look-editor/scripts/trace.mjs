// trace.mjs STEP...: who touches the candidate settings, in the emulator.
//   emulator/emu-run IMAGE $PWD/experiments/2026-11-18-look-editor/scripts/trace.mjs STEP...
// Steps: w:MS, key:NAME[:MS], poke:VALUE (write VALUE into every candidate's stored value, RAM only), dump.
// Logs every call of the prm getter/setter with a candidate tag, of Get/Set_CameraInfo (current, user, bank, W)
// and of the mode controller's get/set and the GUI's getSetting/setSetting with a candidate id (caller = mdr).
// Polls every candidate's stored bytes every 20 ms of lab time and logs each change with the lab time.
import path from 'node:path';
const E = path.join(process.env.EPM2_REPO, 'emulator/e101');
const { createBoot } = await import(path.join(E, 'boot.mjs'));
const { KEYS, press, release } = await import(path.join(E, 'keys.mjs'));
const { R, PC, SP, PSW } = await import(path.join(E, 'machine.mjs'));
const { backtrace } = await import(path.join(E, 'sym.mjs'));
const BT = Number(process.env.BTTAG || 0); let btn = 0;
const C = (process.env.CANDS || '').split(' ').filter(Boolean).map((s) => { const [id, tag, ty] = s.split(':'); return { id: +id, tag: parseInt(tag, 16), ty }; });
const ids = new Map(C.map((c) => [c.id, c])), tags = new Map(C.map((c) => [c.tag, c]));
const e = createBoot({ blocksDir: process.env.BLOCKS });
R[PC] = 0x7E421020 | 0; R[SP] = 0x47001FFC | 0; R[PSW] = 0;
const ms = () => Number((e.m.devices.clock.t / 1e6).toFixed(1));
const seen = new Map();
const note = (k) => { const n = (seen.get(k) || 0) + 1; seen.set(k, n); if (n <= 3) console.log(ms(), k, n === 3 ? '(further ones counted only)' : ''); };
const mdr = () => '0x' + (R[11] >>> 0).toString(16);
const byTag = { 0x7E457C75: 'prm_get', 0x7E457CED: 'prm_set', 0x7E6803BC: 'prm_get2' };
for (const [pc, n] of Object.entries(byTag)) e.hook(+pc, n, () => { const t = R[0] & 0xFFFF; if (BT && t === BT && n === 'prm_set' && btn++ < 4) console.log(ms(), 'BT', backtrace(e, R[SP], 10).join(' | ')); if (tags.has(t)) note(`${n} tag=0x${t.toString(16)} idx=${R[0] >>> 16} from ${mdr()}`); });
const byId = { 0x7E67F822: 'GetInfo', 0x7E67F882: 'SetInfo', 0x7E67FC52: 'GetUser', 0x7E67FC78: 'SetUser', 0x7E67FBFD: 'GetBank', 0x7E67FC26: 'SetBank', 0x7E67FCB8: 'GetW', 0x7E67FD72: 'SetW', 0x7E6FEA5F: 'mcon_get', 0x7E6FEAE0: 'mcon_set', 0x7EE01D38: 'gui_get', 0x7EE01D4E: 'gui_set', 0x7E6FF3ED: 'mcon_wr', 0x7E6FF46F: 'mcon_wr2', 0x7E6FF4C7: 'mcon_wr3', 0x7E6FF507: 'mcon_wr4', 0x7E6FF56D: 'mcon_wr5', 0x7E6FCC72: 'set_simple', 0x7E6FCC91: 'get_simple' };
// SWAP=699:447:14,700:37:14 turns the stock Set_CameraInfo_Simple(699, v) into Set_CameraInfo_Simple(447, 14), as the menu would set it
const SW = new Map((process.env.SWAP || '').split(',').filter(Boolean).map((s) => { const [a, b, v] = s.split(':').map(Number); return [a, [b, v]]; }));
const GS = (process.env.GUISWAP || '').split(':').map(Number); let gsDone = false;
e.hook(0x7EE01D4E, 'gui_set_swap', () => { const i = R[0] & 0xFFFF; if (process.env.GUILOGALL) console.log(ms(), `gui_set(${i}, ${R[1]}) from ${mdr()}`); if (GS.length === 3 && i === GS[0] && !gsDone) { gsDone = true; console.log(ms(), `swap gui_set(${i}, ${R[1]}) -> (${GS[1]}, ${GS[2]})`); R[0] = GS[1]; R[1] = GS[2]; } else if (ids.has(i)) note(`gui_set id=${i} d1=${R[1]} from ${mdr()}`); });
e.hook(0x7E6FCC72, 'set_simple_swap', () => { const i = R[0] & 0xFFFF; if (SW.has(i)) { const [b, v] = SW.get(i); console.log(ms(), `swap set_simple(${i}, ${R[1]}) -> (${b}, ${v})`); R[0] = b; R[1] = v; } else if (ids.has(i)) note(`set_simple id=${i} d1=${R[1]} from ${mdr()}`); });
for (const [pc, n] of Object.entries(byId).filter(([pc]) => +pc !== 0x7E6FCC72 && +pc !== 0x7EE01D4E)) e.hook(+pc, n, () => { const i = R[0] & 0xFFFF; if (ids.has(i)) note(`${n} id=${i} d1=${R[1]} from ${mdr()}`); });
const b8 = (a) => (e.r32(a & ~3) >>> (8 * (a & 3))) & 0xFF;
const size = { u8: 1, s8: 1, u16: 2, s16: 2, u32: 4 };
function where(c) { const ent = 0x603A0E38 + 8 * (c.tag >> 4); return e.r32(ent + 4) >>> 0; }
const uaddr = (c) => where({ tag: 0x8B54 }) + 4 * c.id;
const uval = (c) => e.r32(uaddr(c)) >>> 0;
function val(c) { const a = where(c), n = size[c.ty] || 1; let v = 0; for (let k = 0; k < n; k++) v |= b8(a + k) << (8 * k); return v >>> 0; }
const last = new Map();
function poll(tagline) { for (const c of C) { const v = val(c); if (last.has(c.id) && last.get(c.id) !== v) console.log(ms(), `CHANGE id=${c.id} tag=0x${c.tag.toString(16)} ${last.get(c.id)} -> ${v}${tagline || ''}`); last.set(c.id, v); } }
const run = (t) => { for (let left = t; left > 0; left -= 20) { const r = e.run({ maxLabMs: Math.min(20, left), maxMs: 900000 }); if (r.why !== 'labtime') { console.log('stop', JSON.stringify(r)); process.exit(2); } poll(); } };
// first chunk: poll from the first ms on (the RAM index is filled early; before that the reads give garbage)
run(Number(process.env.BOOTMS || 2500));
console.log(ms(), 'after boot:', C.map((c) => `${c.id}=${val(c)}@0x${where(c).toString(16)}`).join(' '));
for (const step of process.argv.slice(2)) {
  const f = step.split(':');
  if (f[0] === 'w') run(Number(f[1]));
  else if (f[0] === 'key') { press(e, f[1]); run(Number(f[2] || 120)); release(e, f[1]); run(400); }
  else if (f[0] === 'poke') { for (const c of C) { const a = where(c), v = +f[1]; for (let k = 0; k < (size[c.ty] || 1); k++) e.w8(a + k, (v >>> (8 * k)) & 255); } if (f[2] === 'user') for (const c of C) e.w32(uaddr(c), +f[1]); poll(' (poke)'); console.log(ms(), 'poked', f[1], f[2] || 'current only'); }
  else if (f[0] === 'udump') console.log(ms(), 'user plane:', C.map((c) => `${c.id}=${uval(c)}`).join(' '));
  else if (f[0] === 'dump') console.log(ms(), 'values:', C.map((c) => `${c.id}=${val(c)}`).join(' '));
  else { console.log('bad step', step); process.exit(2); }
}
run(300);
console.log(ms(), 'end values:', C.map((c) => `${c.id}=${val(c)}`).join(' '));
if (process.env.SAVE && e.saveState()) console.log('state saved');
console.log('counts', JSON.stringify([...seen.entries()].sort()));
console.log('end', ms(), 'errors', JSON.stringify(e.errLog.slice(-3)));
