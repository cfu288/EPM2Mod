// E-PM2 (E101) machine on top of om-emu's CPU, memory, interrupt controller and timer.
// This file is our code. It imports om-emu from OM_EMU_DIR (paths.mjs: default build/om-emu, made by tools/emu/setup.sh) and adds:
//   - the flash view (the four container blocks at their flash addresses),
//   - a permissive MMIO layer with per-block device models (see devices.mjs),
//   - pc hooks (function-level stand-ins) and a run loop that moves lab time.
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
const { R, S } = cpu;
export { R, S };
export const D0 = 0, D1 = 1, D2 = 2, D3 = 3, A0 = 4, A1 = 5, A2 = 6, A3 = 7, SP = 8, PC = 9, PSW = 10, MDR = 11;

export const IMAGE_BASE = 0x7E421020;
export const h8 = (v) => '0x' + (v >>> 0).toString(16).padStart(8, '0');

// ---- container reader (the OE container: 32-byte header, payload, 32-byte trailer; see src/epm2mod/container.py).
// We take already unpacked payloads (tools/oetool.py unpack) to stay independent of the scrambling.
export function loadBlocks(dir) {
  const man = JSON.parse(fs.readFileSync(path.join(dir, 'manifest.json'), 'utf8'));
  return man.blocks.map((b) => {
    const header = Buffer.from(b.header, 'hex');
    return { file: b.file, addr: header.readUInt32LE(8), kind: header.readUInt16LE(20), header,
      payload: new Uint8Array(fs.readFileSync(path.join(dir, b.file))) };
  });
}

export class Flash {
  // segments: [{addr, data}] in the 0x40000000 flash address space (aliases 0x80000000, 0x00000000 high bits masked)
  constructor() { this.segs = []; this.reads = []; }
  add(addr, data, name) { this.segs.push({ addr: addr >>> 0, end: (addr >>> 0) + data.length, data, name }); }
  static norm(a) { return (((a >>> 0) & 0x3FFFFFFF) | 0x40000000) >>> 0; }
  read(addr, len) {
    const a = Flash.norm(addr), out = new Uint8Array(len).fill(0xFF);
    for (const s of this.segs) {
      const lo = Math.max(a, s.addr), hi = Math.min(a + len, s.end);
      if (lo < hi) out.set(s.data.subarray(lo - s.addr, hi - s.addr), lo - a);
    }
    return out;
  }
  write(addr, bytes) {
    const a = Flash.norm(addr);
    let done = 0;
    for (const s of this.segs) {
      const lo = Math.max(a, s.addr), hi = Math.min(a + bytes.length, s.end);
      if (lo < hi) { s.data.set(bytes.subarray(lo - a, hi - a), lo - s.addr); done += hi - lo; }
    }
    if (done < bytes.length) this.add(a, bytes.slice(), 'written');   // (coarse: a later read sees the newest segment last)
  }
}

export class E101 {
  constructor({ blocksDir, log = () => {}, cores = { second: 1, quantum: 2000, vectorPage2: 0x7E440000 } }) {
    this.log = log;
    this.blocks = loadBlocks(blocksDir);
    const rom = this.blocks[0].payload;
    this.rom = rom;
    this.m = machineMod.createMachine({ rom, insnLimit: 0, keepStderr: false, cores });
    this.flash = new Flash();
    for (const b of this.blocks) {
      const img = new Uint8Array(32 + b.payload.length);
      img.set(b.header, 0); img.set(b.payload, 32);
      this.flash.add(b.addr, img, b.file);
    }
    // on-chip SRAM 0x47000000 (kernel config, reset stack, SRAM code copy 0x47001000)
    mem.addRegion({ base: 0x47000000, size: 0x10000, kind: mem.K_RAM, off: mem.allocWindow(0x10000), name: 'e101.sram47' });
    // the cache purge reads 512 words at 0x28A00000 and 0x28A80000 (0x7E45DA9D): plain RAM, reads 0
    mem.addRegion({ base: 0x28A00000, size: 0x100000, kind: mem.K_RAM, off: mem.allocWindow(0x100000), name: 'e101.cache-purge' });
    this.hooks = new Map();          // pc -> { fn, name, count }
    this.mmio = new Map();           // block (addr >>> 20) -> device {read(off,size), write(off,value,size)}
    this.store = new Map();          // default MMIO storage: address -> u32 (word granular)
    this.seen = new Map();           // first-touch log: key -> count
    this.mmioLog = null;
    this.nsPerInsn = 4;              // lab time per instruction (CPU execution moves the lab clock by this much)
    this.slice = 20000;              // instructions between clock updates
    this.insnsAtClock = 0;
    mem.setStub({ read: (a, w, dbg) => this.mmioRead(a >>> 0, w, dbg), write: (a, v, w, dbg) => this.mmioWrite(a >>> 0, v, w, dbg) });
    // om-emu's strict SCPU-interface model sits at 0x98E00000 (the E-PM2's system controller): hand its page to our
    // permissive MMIO layer (plain storage unless devices.mjs models a register)
    this.takeOver(0x98E00000);
    S.relax = true;                  // E-PM2 code reads flags om-emu holds undefined (e.g. rol after udf04 at 0x7E5018FC)
    this.wHooks = new Map();         // exact MMIO address -> fn(value) on a CPU write
    const intc = this.m.devices.intc;
    intc.dset(0x008, 2);             // the lab's interrupt gate open at any pc (GATE_ANY)
    // GnICR request flags (0x8940 + 4 level, bit 4): the kernel polls them (0x7E43369F waits for the other CPU's kick),
    // so they follow what each core's controller bank presents. Core 0's system page is lab low RAM; core 1's its own.
    this.corePage = [mem.LOW_OFF, cores ? this.m.cores.ctx[cores.second].pages.get(0).rp : -1];
    intc.onMask = (core, mask) => {
      const off = this.corePage[core]; if (off < 0) return;
      for (let l = 0; l < 7; l++) { const o = off + 0x8940 + 4 * l; if (mask & (1 << l)) mem.U8[o] |= 0x10; else mem.U8[o] &= ~0x10; }
    };
    this.scratch = 0x00010000;       // ret pads in lab low RAM
    this.pads = new Map();
    this.stopReason = null;
  }
  // ---- memory helpers (debugger access: no side effects, no faults on RAM)
  rd(a, n) { const b = mem.dbgRead(a >>> 0, n); if (b === null) throw new Error('rd ' + h8(a)); return b; }
  r8(a) { return this.rd(a, 1)[0]; }
  r16(a) { const b = this.rd(a, 2); return b[0] | b[1] << 8; }
  r32(a) { const b = this.rd(a, 4); return (b[0] | b[1] << 8 | b[2] << 16 | b[3] << 24) >>> 0; }
  wr(a, bytes) { mem.dbgWrite(a >>> 0, bytes instanceof Uint8Array ? bytes : Uint8Array.from(bytes)); }
  w8(a, v) { this.wr(a, [v & 255]); }
  w16(a, v) { this.wr(a, [v & 255, (v >>> 8) & 255]); }
  w32(a, v) { this.wr(a, [v & 255, (v >>> 8) & 255, (v >>> 16) & 255, (v >>> 24) & 255]); }
  cstr(a, max = 256) {
    let s = '';
    for (let i = 0; i < max; i++) { let c; try { c = this.r8(a + i); } catch { break; } if (!c) break; s += String.fromCharCode(c); }
    return s;
  }
  // ---- MMIO
  takeOver(base) {
    const r = mem.findRegion(base); if (!r) throw new Error('takeOver: no region at ' + h8(base));
    r.dev = { read: (a, w, dbg) => this.mmioRead(a >>> 0, w, dbg), write: (a, v, w, dbg) => this.mmioWrite(a >>> 0, v, w, dbg) };
  }
  mmioRead(a, w, dbg) {
    const dev = this.mmio.get(a >>> 20);
    let v;
    if (dev) v = dev.read(a, w, dbg);
    if (v === undefined) {
      const word = this.store.get((a & ~3) >>> 0) ?? 0;
      v = w === 4 ? word : w === 2 ? (word >>> (8 * (a & 2))) & 0xffff : (word >>> (8 * (a & 3))) & 0xff;
      if (!dbg) this.touch('r', a, w, v, dev);
    }
    if (this.mmioLog && !dbg) this.mmioLog('r', a, w, v);
    return v;
  }
  mmioWrite(a, v, w, dbg) {
    if (dbg) return;
    if (this.mmioLog) this.mmioLog('w', a, w, v);
    const wh = this.wHooks.get(a); if (wh) wh(v >>> 0);
    const dev = this.mmio.get(a >>> 20);
    if (dev && dev.write(a, v, w) === true) return;
    const k = (a & ~3) >>> 0, old = this.store.get(k) ?? 0;
    const sh = 8 * (a & 3), mask = w === 4 ? 0xffffffff : w === 2 ? 0xffff << sh : 0xff << sh;
    this.store.set(k, ((old & ~mask) | ((v << sh) & mask)) >>> 0);
    this.touch('w', a, w, v, dev);
  }
  touch(dir, a, w, v, dev) {
    const key = `${dir} ${h8(a)}`;
    const n = this.seen.get(key);
    if (n === undefined) { this.seen.set(key, { n: 1, pc: R[PC] >>> 0, v: v >>> 0, w }); }
    else n.n++;
  }
  // ---- hooks
  hook(pc, name, fn) { this.hooks.set(pc >>> 0, { fn, name, count: 0 }); this.bpDirty = true; }
  unhook(pc) { this.hooks.delete(pc >>> 0); this.bpDirty = true; }
  // Return from the function whose entry the CPU stands at (a hook at a function's first instruction): through the
  // `ret`/`rets` that matches the call instruction that got here (the return address is in MDR).
  ret(d0, a0) {
    if (d0 !== undefined) R[D0] = d0 | 0;
    if (a0 !== undefined) R[A0] = a0 | 0;
    const ra = R[MDR] >>> 0, here = R[PC] >>> 0;
    let regs = -1, frame = 0;
    const b5 = this.rd(ra - 7, 7);
    const s16 = (lo, hi) => ((lo | hi << 8) << 16) >> 16;
    if (b5[2] === 0xCD && ((ra - 5 + s16(b5[3], b5[4])) >>> 0) === here) { regs = b5[5]; frame = b5[6]; }
    else if (b5[0] === 0xDD && ((ra - 7 + (b5[1] | b5[2] << 8 | b5[3] << 16 | b5[4] << 24)) >>> 0) === here) { regs = b5[5]; frame = b5[6]; }
    else if (b5[2] === 0xCD || b5[0] === 0xDD) {
      // a call whose target is not this pc (the hook stands inside the callee, or a tail jump got here): trust the 5-byte form first
      if (b5[2] === 0xCD) { regs = b5[5]; frame = b5[6]; } else { regs = b5[5]; frame = b5[6]; }
    }
    if (regs < 0) { R[PC] = this.pad('rets', [0xF0, 0xFC]); return; }       // reached by `calls`: plain rets
    R[PC] = this.pad(`ret${regs}_${frame}`, [0xDF, regs, frame]);
  }
  pad(key, bytes) {
    let a = this.pads.get(key);
    if (a === undefined) { a = this.scratch; this.scratch += 4; this.wr(a, bytes); this.pads.set(key, a); }
    return a;
  }
  syncBp() {
    if (!this.bpDirty) return;
    this.m.setBreakpoints([...this.hooks.keys()]); this.bpDirty = false;
    if (this.cpu1Started) this.m.cores.addStops([...this.hooks.keys()].filter((p) => !this.m.cores.ctx[1].halts.has(p)));
  }
  // ---- run: until `until()` is true, a fault, or maxInsns. Returns {why, pc}.
  run({ maxInsns = Infinity, until = null, maxMs = Infinity, maxLabMs = Infinity } = {}) {
    const m = this.m, clock = m.devices.clock;
    const i0 = S.insns, t0 = Date.now(), lab0 = clock.t; let iter = 0;
    this.stopReason = null;
    for (;;) {
      this.syncBp();
      if (S.insns - i0 >= maxInsns) return { why: 'limit', pc: R[PC] >>> 0 };
      if (this.stopReason) return { why: this.stopReason, pc: R[PC] >>> 0 };
      if (clock.t - lab0 >= maxLabMs * 1e6) return { why: 'labtime', pc: R[PC] >>> 0 };
      if ((++iter & 1023) === 0 && Date.now() - t0 > maxMs) return { why: 'maxMs', pc: R[PC] >>> 0 };
      const r = m.cont({ budget: this.slice });
      if (r === 'paused') m.halt();
      // lab time follows the instruction count
      const dn = S.insns - this.insnsAtClock;
      if (dn > 0) { this.insnsAtClock = S.insns; clock.advance(clock.t + dn * this.nsPerInsn, false); if (this.onTime) this.onTime(clock.t); }
      if (r === 'paused') {
        if (until && until()) return { why: 'until', pc: R[PC] >>> 0 };
        if (Date.now() - t0 > maxMs) return { why: 'maxMs', pc: R[PC] >>> 0 };
        continue;
      }
      const st = m.lastStop();
      if (st.kind === 'break') {
        const pc = R[PC] >>> 0, h = this.hooks.get(pc);
        if (!h) return { why: 'break', pc };
        h.count++;
        const act = h.fn(this, pc);
        if (act === 'stop') return { why: 'hook:' + h.name, pc };
        if ((R[PC] >>> 0) === pc) {            // the hook observed only: step over the instruction it stands on
          m.step();
          const s2 = m.lastStop();
          if (s2.kind === 'fault') return { why: 'fault', code: s2.code, pc: R[PC] >>> 0 };
        }
        continue;
      }
      if (st.kind === 'fault') return { why: 'fault', code: st.code, pc: R[PC] >>> 0 };
      return { why: st.kind, pc: R[PC] >>> 0 };
    }
  }
  idleSkip(ns) { const clock = this.m.devices.clock; clock.advance(clock.t + ns, true); }
  regs() {
    const n = ['d0', 'd1', 'd2', 'd3', 'a0', 'a1', 'a2', 'a3', 'sp', 'pc', 'psw', 'mdr', 'lir', 'lar'];
    return n.map((k, i) => `${k}=${(i === 10 ? R[i] & 0xffff : R[i] >>> 0).toString(16)}`).join(' ');
  }
  stderrTail(n = 800) { return this.m.stderrTail(n); }
}
