// E-PM2 peripheral models and register-level stand-ins. Each entry says what it returns and why (../boot/README.md lists them).
// A device is {read(addr, size) -> value | undefined, write(addr, value, size) -> true if handled}; undefined / false
// falls through to plain storage (a read returns what was last written, 0 when never written).
import { R, PC, h8 } from './machine.mjs';

export function installDevices(e) {
  // ---- 0x98E00000 system controller (om-emu calls it the SCPU interface)
  //  +0xA4 command word: the firmware writes 0x20041001 and waits until it reads 0 (0x7E425F44): reads 0 = done at once.
  //  +0x00 bit 1 set = the always-on domain kept its state (not a battery insertion); +0x48 wake factors, write-1-to-
  //  clear: bit 1 = factor 2 (0x7E45D2C3), which the table 0x7E73522C maps to event 0, the power lever (INFERRED);
  //  with +0x48 = 0 and +0x00 bit 1 clear the firmware takes factor 0 = battery insertion and runs the card
  //  firmware-update check instead of the normal start (VERIFIED in the emulator: "[usr]firmup").
  //  Ports +0x58 + 4k (k = 0..4): bit 31 is the input level (0x7E45D444 packs them into bits 0..4). UI_IN's group 1
  //  key table 0x7E735254 names them: port 0 key 0x0C (the ON/OFF button: wake factor 1 maps to event 12, which the
  //  fast start requires, "UiONFact"), port 1 key 0, port 2 key 0x1506, port 3 key 0x400, port 4 key 0x121C.
  //  e.ports holds the levels (bit k = port k). Default 0x08: port 3 high, which the fast start tests at 0x7E5026D0.
  e.ports = e.ports ?? 0x0C;                 // port 2 high: UI_IN key 0x1506 active = no card (0x7E5CC9DE: card presence is this key); port 3 high (quick-start check)
  //  +0x50: a pending bit per port whose level changed (write 1 to clear); IRQ 120 while any is set (ISR 0x7E45D5C7).
  //  e.setPorts(levels) changes the levels as the buttons would.
  const sys = { wake: e.wakeFactor ?? 0x1, pend: 0 };
  // RTC (S-RTC, MODEL of the registers the driver 0x7E467D17 uses; off unless E101_RTC is set, so the default runs stay as
  // they were): +0x98 seconds counter (read through the SRAM routine 0x47001220, written by 0x7E45D6CD), +0x9C bits 5..14
  // milliseconds (0x47001229), +0x00 bits 2..7 the "RTC initialised" marker 42 (0x7E45D756 / 0x7E45D73F; plain storage).
  // E101_RTC=<seconds> or an ISO date ("2026-11-14T12:00:00"): the clock is SET to that time at power-on and ticks with
  // lab time. The counter is Unix time, seconds since 1970-01-01 (VERIFIED by the driver's own conversion 0x7E508A6F). Without E101_RTC the counter is plain
  // storage (reads 0 = "clock not set": Y/M/D prompt, and the rows that need the clock are grey).
  let rtc = null;
  if (process.env.E101_RTC) {
    const s = process.env.E101_RTC, base = /^\d+$/.test(s) ? Number(s) : Math.floor(Date.parse(s + 'Z') / 1000);
    rtc = e.rtc = { base, t0: 0 }; e.store.set(0x98E00000, 42 << 2);
  }
  e.setPorts = (levels) => { sys.pend |= (e.ports ^ levels) & 0x1f; e.ports = levels; e.m.devices.intc.setLine(120, sys.pend !== 0); };
  e.mmio.set(0x98E, {
    read(a) {
      if (a === 0x98E000A4) return 0;
      if (a === 0x98E00000) return (e.store.get(0x98E00000) ?? 0) | 0x2;
      if (rtc && a === 0x98E00098) return (rtc.base + Math.floor((e.m.devices.clock.t - rtc.t0) / 1e9)) >>> 0;
      if (rtc && a === 0x98E0009C) return ((Math.floor(e.m.devices.clock.t / 1e6) % 1000) << 5) >>> 0;
      if (a === 0x98E00048) return sys.wake;
      if (a === 0x98E00050) return sys.pend;
      if (a >= 0x98E00058 && a <= 0x98E00068) return (((e.ports >>> ((a - 0x98E00058) >> 2)) & 1) << 31) >>> 0;
      return undefined;
    },
    write(a, v) {
      if (a === 0x98E00048) { sys.wake &= ~v; return true; }
      if (rtc && a === 0x98E00098) { rtc.base = v >>> 0; rtc.t0 = e.m.devices.clock.t; return true; }
      if (a === 0x98E00050) { sys.pend &= ~v; intc.setLine(120, sys.pend !== 0); return true; }
      return false;
    },
  });
  const intc = e.m.devices.intc;
  // ---- 0x98C00000 ADC (per_adc 0x7E45AB01..): +0x04 start / busy (bit 0 reads 0: a conversion is done at once),
  //  three completion groups {enable, status}: +0x10/+0x14 (polled mode), +0x18/+0x1C (IRQ mode, ISR 0x7E45B49D),
  //  +0x30/+0x34 (started by +0x28); a status is set by its start and cleared by writing 1; IRQ 117 = any enabled
  //  status. Results +0x3C.. (one word per input, read by 0x7E45B33C): e.adc[k], default 0x200 (FAKE values).
  e.adc = new Array(16).fill(0x200);
  e.adc[3] = 0x3FF;      // input 3 = the key ladder (UI_IN group 6, thresholds 0x22..0x2C2): 0x3FF = no key (0x200 reads as key 0x89 held)
  const adc = { en: [0, 0, 0], st: [0, 0, 0] };
  intc.drive(117);
  const adcLine = () => intc.setLine(117, adc.en.some((en, i) => (en & adc.st[i] & 1) !== 0));
  e.mmio.set(0x98C, {
    read(a) {
      const o = a - 0x98C00000;
      if (o === 0x04 || o === 0x28) return 0;
      if (o === 0x14) return adc.st[0]; if (o === 0x1C) return adc.st[1]; if (o === 0x34) return adc.st[2];
      if (o >= 0x3C && o < 0x7C) return e.adc[(o - 0x3C) >> 2];
      return undefined;
    },
    write(a, v) {
      const o = a - 0x98C00000;
      if (o === 0x04 && (v & 1)) { adc.st[0] = 1; adc.st[1] = 1; adcLine(); return true; }
      if (o === 0x28 && (v & 1)) { adc.st[2] = 1; adcLine(); return true; }
      if (o === 0x10) { adc.en[0] = v; adcLine(); return false; }
      if (o === 0x18) { adc.en[1] = v; adcLine(); return false; }
      if (o === 0x30) { adc.en[2] = v; adcLine(); return false; }
      if (o === 0x14) { adc.st[0] &= ~v; adcLine(); return true; }
      if (o === 0x1C) { adc.st[1] &= ~v; adcLine(); return true; }
      if (o === 0x34) { adc.st[2] &= ~v; adcLine(); return true; }
      return false;
    },
  });
  // ---- 0x99000000 SD host (TMIO-like core at +0x2000). No card model yet:
  //  +0x203C SD_INFO2 reads bit 13 set (the clock-divider-enable / bus idle flag the driver polls at 0x7E5CBE99).
  e.mmio.set(0x990, {
    read(a) { if (a === 0x9900203C) return (e.store.get(0x9900203C) ?? 0) | 0x2000; return undefined; },
    write(a, v) { return false; },
  });
  // ---- 0x9A900000 display controller ("VSC"): INTEN +0x0C, INTST +0x14 (write 1 to clear), as om-emu's kind-3 VSC.
  //  Bit 0 = frame (vsync) and bit 4 = line compare (the driver arms it at 0x7E6B77D6 and waits for it; om-emu's kind 3
  //  has the same bit): both set every 16.683 ms of lab time (59.94 Hz, FAKE timing source); IRQ 14 = INTST & INTEN.
  //  Everything else in the block is plain storage; the frame is composed by screen.mjs from these registers.
  const vsc = e.vsc = { inten: 0, intst: 0, next: 16683000, period: 16683000, frames: 0 };
  intc.drive(14); intc.drive(15);
  const vscLine = () => intc.setLine(14, (vsc.inten & vsc.intst) !== 0);
  e.m.devices.clock.add({ next: () => vsc.next, fire: (at) => { vsc.next = at + vsc.period; vsc.frames++; vsc.intst |= 0x11; vscLine(); if (e.onFrame) e.onFrame(vsc.frames); } });
  e.mmio.set(0x9A9, {
    read(a) { if (a === 0x9A90000C) return vsc.inten; if (a === 0x9A900014) return vsc.intst; return undefined; },
    write(a, v) {
      if (a === 0x9A90000C) { vsc.inten = v >>> 0; vscLine(); return true; }
      if (a === 0x9A900014) { vsc.intst &= ~v; vscLine(); return true; }
      // the 8-bit plane's palette has two banks, +0x400 and +0x600 (128 entries each); the firmware loads them in turn
      // (0x7E6B7B55). The composer uses the bank written last (INFERRED; the select register is not identified,
      // candidate +0x30 bit 4).
      if (a >= 0x9A900400 && a < 0x9A900800) vsc.palBank = a < 0x9A900600 ? 0x400 : 0x600;
      return false;
    },
  });
  // ---- 0x9A100000 GIO
  //  +0xF4..+0x100 deferred-call triggers (posts 0x7E45F14D.. write 1, the handlers 0x7E45F242.. write 0): bit 0 of
  //  word k is the level of IRQ 23 + k (the same unit as om-emu's "dpc" on later bodies).
  //  +0x10 + 12k (k = 0..14): one-shot timers {start, count, ..} (tables 0x7E4C6A40 / 0x7E4C6AF4; the soft-timer API
  //  0x7E4650A2 runs on them). Timers 0..9 share IRQ 17 with status +0xC4 (bit k, write 1 to clear) and enable +0xDC;
  //  timers 10..14 have IRQ 18..22 with status +0xC8.. and enable +0xE0.. (bit 0). The time of a timer is the
  //  microsecond value its set-up 0x7E462465(d0 = k, a0 -> {us, ..}) was given (observed there: the count register
  //  holds clock counts scaled from SYSCLK registers this machine does not model).
  const gt = e.gioTimers = { us: new Array(15).fill(1000), at: new Array(15).fill(Infinity), st: [0, 0, 0, 0, 0, 0], en: [0, 0, 0, 0, 0, 0] };
  for (let g = 0; g < 6; g++) intc.drive(17 + g);
  const gtLines = () => { for (let g = 0; g < 6; g++) intc.setLine(17 + g, (gt.st[g] & gt.en[g]) !== 0); };
  e.hook(0x7E462465, 'gio-timer-set', () => { const k = e.m.getRegs()[0] & 0xffff; if (k < 15) gt.us[k] = e.r32(e.m.getRegs()[4] >>> 0); });
  e.m.devices.clock.add({
    next: () => Math.min(...gt.at),
    fire: (at) => { for (let k = 0; k < 15; k++) if (gt.at[k] === at) { gt.at[k] = Infinity; if (k < 10) gt.st[0] |= 1 << k; else gt.st[k - 9] |= 1; } gtLines(); },
  });
  for (let k = 0; k < 4; k++) intc.drive(23 + k);
  e.mmio.set(0x9A1, {
    read(a) {
      const o = a - 0x9A100000;
      if (o >= 0xC4 && o <= 0xD8) return gt.st[(o - 0xC4) >> 2];
      if (o >= 0xDC && o <= 0xF0) return gt.en[(o - 0xDC) >> 2];
      // bit-search unit: a value written to +0x110 is answered at +0x108 with the index of its lowest set bit and at
      // +0x104 with the index of its highest set bit, 32 when no bit is set (0x7E45D9C8 / 0x7E45D9F1; the hardware
      // timer allocator 0x7E462557 gives every soft timer its own one-shot timer with it). INFERRED semantics.
      if (o === 0x108) { const v = e.store.get(0x9A100110) ?? 0; return v ? 31 - Math.clz32(v & -v) : 32; }
      if (o === 0x104) { const v = e.store.get(0x9A100110) ?? 0; return v ? 31 - Math.clz32(v) : 32; }
      return undefined;
    },
    write(a, v) {
      const o = a - 0x9A100000;
      if (o >= 0x10 && o < 0xC4 && (o - 0x10) % 12 === 0) {
        const k = (o - 0x10) / 12, clock = e.m.devices.clock;
        gt.at[k] = (v & 1) ? clock.t + Math.max(1, gt.us[k]) * 1000 : Infinity;
        return false;
      }
      if (o >= 0xC4 && o <= 0xD8) { gt.st[(o - 0xC4) >> 2] &= ~v; gtLines(); return true; }
      if (o >= 0xDC && o <= 0xF0) { gt.en[(o - 0xDC) >> 2] = v >>> 0; gtLines(); return true; }
      if (a >= 0x9A1000F4 && a <= 0x9A100100) { intc.setLine(23 + ((a - 0x9A1000F4) >> 2), (v & 1) !== 0); return false; }
      return false;
    },
  });
}
