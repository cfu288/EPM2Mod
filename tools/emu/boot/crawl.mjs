// crawl.mjs OUTDIR NAME ENTRY-STEP... : systematic menu crawl from one start screen (our code; drives the emulator in ../e101).
// ENTRY steps are play.mjs steps (w:MS, key:NAME, port:HEX, tilt:..); after them the crawler explores the screen it is on:
//   at each cursor position it writes OUTDIR/NAME-<i>.png, presses RIGHT (a changed screen is a child: explored the
//   same way under NAME-<i>.<j>, then MENU goes back), then DOWN, until the screen repeats (wrap) or does not change.
//   A screen is "the composed frame": equality is by the hash of the RGB frame. Nothing is ever confirmed with OK.
// env: DEPTH (max child depth, default 4), MAXLIST (max positions per screen, default 140), CHILDLIST (max positions in
//   screens at depth >= LISTDEPTH: default MAXLIST), E101_STATE (copied to OUTDIR/NAME.state.json first, never written back),
//   E101_CARD, E101_RTC as in play.mjs. Writes OUTDIR/NAME.log.json: [{name, hash, err, note}].
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const out = process.argv[2], NAME = process.argv[3];
fs.mkdirSync(out, { recursive: true });
if (process.env.E101_STATE) { const c = path.join(out, NAME + '.state.json'); fs.copyFileSync(process.env.E101_STATE, c); process.env.E101_STATE = c; }
const { createBoot } = await import('../e101/boot.mjs');
const { compose, png } = await import('../e101/screen.mjs');
const { KEYS, press, release } = await import('../e101/keys.mjs');
const { R, PC, SP, PSW } = await import('../e101/machine.mjs');
const e = createBoot({ blocksDir: process.env.BLOCKS });
R[PC] = 0x7E421020 | 0; R[SP] = 0x47001FFC | 0; R[PSW] = 0;
const DEPTH = Number(process.env.DEPTH ?? 4), MAXLIST = Number(process.env.MAXLIST ?? 140), MAXSHOTS = Number(process.env.MAXSHOTS ?? 4000);
const log = []; let shots = 0, keys = 0;
const run = (ms) => { const r = e.run({ maxLabMs: ms, maxMs: 3600000 }); if (r.why !== 'labtime') { log.push({ name: 'STOP', note: JSON.stringify(r) }); finish(2); } };
let frame = null;
const hash = () => { frame = compose(e); return crypto.createHash('sha1').update(frame.rgb).digest('hex').slice(0, 16); };
// wait until the frame is the same in two successive 100 ms looks (at least 300 ms, at most 2500 ms)
function settle() { run(200); let h = hash(); for (let t = 200; t < 2500; t += 100) { run(100); const h2 = hash(); if (h2 === h && t >= 300) return h; h = h2; } return h; }
function key(k) { keys++; press(e, k); run(120); release(e, k); return settle(); }
let errSeen = 0;
function save(name, h, note) {
  if (++shots > MAXSHOTS) { log.push({ name: 'LIMIT', note: 'MAXSHOTS' }); finish(3); }
  fs.writeFileSync(path.join(out, name + '.png'), png(frame.rgb, frame.w, frame.h));
  const err = e.errLog.slice(errSeen); errSeen = e.errLog.length;
  log.push({ name, hash: h, rom: e.videoRom ?? null, ...(err.length ? { err } : {}), ...(note ? { note } : {}) });
}
function finish(code) {
  fs.writeFileSync(path.join(out, NAME + '.log.json'), JSON.stringify(log, null, 0).replace(/\},\{/g, '},\n{'));
  console.log(`${NAME}: ${shots} screens, ${keys} keys, lab ms ${(e.m.devices.clock.t / 1e6).toFixed(0)}, firmware errors ${e.errLog.length}, notes ${log.filter((l) => l.note).map((l) => l.name + ':' + l.note).join(' | ').slice(0, 300)}`);
  process.exit(code);
}
class Desync extends Error {}
class Budget extends Error {}
const BUDGET = Number(process.env.BUDGET ?? 150), TOPMAX = Number(process.env.TOPMAX ?? 1000); let budgetLeft = BUDGET;
class LeftTo extends Error { constructor(h) { super('left'); this.h = h; } }
const p2 = (i) => String(i).padStart(2, '0');
// Leave a child screen: LEFT first (in a multi-field editor it moves back one field; in lists it goes back one level),
// then MENU. If the screen is then an ancestor's, LeftTo is thrown and the frame that owns that screen goes on from there.
function back(here, name, stack) {
  let h = key('LEFT'); if (h === here) return;
  h = key('MENU'); if (h === here) return;
  if (stack.includes(h)) { log.push({ name, note: 'leaving this screen went up more than one level' }); throw new LeftTo(h); }
  h = key('MENU'); if (h === here) { log.push({ name, note: 'back needed a second MENU' }); return; }
  if (stack.includes(h)) { log.push({ name, note: 'leaving this screen went up more than one level' }); throw new LeftTo(h); }
  log.push({ name, note: 'DESYNC: cannot get back' }); throw new Desync();
}
function explore(name, depth, stack) {
  let here = hash(); const first = here; const seen = new Map([[here, 0]]);
  let i = 0;
  for (; i < MAXLIST; i++) {
    const nm = `${name}.${p2(i)}`;
    if (depth === 0) budgetLeft = BUDGET; else if (--budgetLeft < 0) { log.push({ name: nm, note: 'BUDGET: the rest of this row\'s sub-screens was not walked' }); throw new Budget(); }
    save(nm, here);
    if (depth < DEPTH) {
      const h2 = key('RIGHT');
      if (h2 !== here) {
        if (seen.has(h2) || stack.includes(h2)) {
          log[log.length - 1].note = seen.has(h2) ? 'RIGHT moves inside the screen' : 'RIGHT goes to an ancestor';
          const h3 = key('LEFT'); if (h3 !== here) { if (stack.includes(h3) || stack.includes(h2)) throw new LeftTo(stack.includes(h3) ? h3 : h2); log.push({ name: nm, note: 'DESYNC after RIGHT/LEFT' }); throw new Desync(); }
        } else {
          try { explore(nm, depth + 1, [...stack, ...seen.keys()]); back(here, nm, stack); }
          catch (x) {
            if (x instanceof Budget && depth === 0) { let h = hash(); for (let k = 0; k < 8 && h !== here; k++) h = key('MENU'); if (h !== here) { log.push({ name: nm, note: 'DESYNC after BUDGET' }); throw new Desync(); } }
            else if (!(x instanceof LeftTo) || x.h !== here) throw x;
            else log.push({ name: nm, note: 'continued here after the child left more than one level' });
          }
        }
      }
    }
    const h4 = key('DOWN');
    if (h4 === here) { log.push({ name: nm, note: 'DOWN does nothing (end of list)' }); break; }
    if (seen.has(h4)) { if (seen.get(h4) !== 0) log.push({ name: nm, note: 'DOWN wraps to position ' + seen.get(h4) }); here = h4; break; }
    if (stack.includes(h4)) { log.push({ name: nm, note: 'DOWN leaves to an ancestor' }); throw new LeftTo(h4); }
    seen.set(h4, i + 1); here = h4;
    if (depth === 0 && i + 1 >= TOPMAX) { log.push({ name: nm, note: 'TOPMAX: this unit ends here (the next unit continues)' }); break; }
    if (i === MAXLIST - 2) log.push({ name, note: 'MAXLIST reached' });
  }
  // go back to the first position, so that the parent finds its screen unchanged
  for (let k = 0; here !== first && k < MAXLIST; k++) { const h = key('UP'); if (h === here) break; here = h; }
}
run(Number(process.env.BOOTMS || 1500));
for (const step of process.argv.slice(4)) {
  const f = step.split(':');
  if (f[0] === 'w') run(Number(f[1]));
  else if (f[0] === 'key') key(f[1]);
  else if (f[0] === 'port') e.setPorts(parseInt(f[1], 16));
  else if (f[0] === 'pin') e.pins.set(parseInt(f[1], 16), Number(f[2]));
  else if (f[0] === 'tilt') e.tilt = f[1] === 'off' ? null : [Number(f[1]), Number(f[2]), Number(f[3])];
  else if (f[0] === 'shot') { const h = hash(); save(`${NAME}-entry-${f[1]}`, h); }
  else { console.log('unknown step', step); process.exit(2); }
}
errSeen = 0;
try { explore(NAME, 0, []); } catch (x) { if (!(x instanceof Desync) && !(x instanceof LeftTo) && !(x instanceof Budget)) throw x; log.push({ name: NAME, note: 'UNIT ENDED EARLY' }); }
finish(0);
