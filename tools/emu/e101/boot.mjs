// E-PM2 boot stand-ins (each one listed in ../boot/README.md with what it returns and why).
import { E101, R, S, PC, SP, PSW, MDR, D0, D1, A0, A1, h8, Flash } from './machine.mjs';
import { sym, backtrace } from './sym.mjs';
import { installDevices } from './devices.mjs';
import { installOsd } from './osd.mjs';
import fs from 'node:fs';
import { buildFatImage, attachCard, listFat } from './sdcard.mjs';
export { listFat };
export { sym, backtrace };

// 0x7E44966C: the boot task after Usr0 (OlyTaSE 0x7E449621) drops to priority 16 and loops writing 8 to the CPU halt word 0x8040
const IDLE = [0x7E436825, 0x7E43683D, 0x7E44966C];
export function createBoot(opts) {
  const { blocksDir, verbose = false, faithfulLoad = true, stateFile = undefined } = opts;
  const e = new E101({ blocksDir });
  installDevices(e);
  installOsd(e);
  e.console = '';
  e.marks = [];
  const say = (s) => { if (verbose) process.stderr.write(s + '\n'); };
  // Only the part the (unknown) first-stage loader leaves in RAM is there at reset: 0x7E421020..0x7E430000.
  // Everything else is loaded by the firmware's own copies through the flash stand-ins below.
  if (faithfulLoad) {
    const z = new Uint8Array(0x100000), end = 0x7E421020 + e.rom.length;
    for (let a = 0x7E430000; a < end; a += z.length) e.wr(a, z.subarray(0, Math.min(z.length, end - a)));
  }
  // S-CONSOLE: the debug serial putchar 0x7E44B051(d0 = char): kept in e.console, never sent to a UART.
  e.hook(0x7E44B051, 'S-CONSOLE', () => { const c = R[D0] & 0xff; e.console += String.fromCharCode(c); if (verbose) process.stderr.write(String.fromCharCode(c)); e.ret(); });
  // boot marks 0x7E426511(a0 = tag): observed only
  e.hook(0x7E426511, 'boot-mark', () => { const t = e.cstr(R[A0] >>> 0, 8); e.marks.push([t, S.insns]); say(`[mark ${t}] @${S.insns}`); });
  // S-OSDFILL: the reset's memory clear 0x7E4213F7(d0 = start, d1 = end) uses the OSD engine's fill command;
  // stand-in: zero [start, end) (cached alias) and return.
  e.hook(0x7E4213F7, 'S-OSDFILL', () => {
    const a = ((R[D0] & 0x3FFFFFFF) | 0x40000000) >>> 0, b = ((R[D1] & 0x3FFFFFFF) | 0x40000000) >>> 0;
    say(`[osdfill ${h8(a)}..${h8(b)}]`);
    if (b > a && b - a < 0x10000000) { const z = new Uint8Array(0x10000); for (let p = a; p < b; p += z.length) e.wr(p, z.subarray(0, Math.min(z.length, b - p))); }
    e.ret();
  });
  // S-FLASHREAD0: the early flash reader 0x7E4217E6(d0 = volume, a0 = flash source, a1 = destination, d1 = size)
  e.hook(0x7E4217E6, 'S-FLASHREAD0', () => {
    const src = R[A0] >>> 0, dst = R[A1] >>> 0, n = R[D1] >>> 0;
    say(`[flashread0 vol ${R[D0]} ${h8(src)} -> ${h8(dst)} n=${h8(n)}]`);
    e.wr(dst, e.flash.read(src, n));
    e.ret(0);
  });
  // S-FLASHWRITE / S-FLASHERASE: the flash driver's two other primitives, WRITE 0x7E451B69(d0 = volume, a0 / a1 = flash
  // address and source buffer, d1 = size) and ERASE 0x7E4519C5(d0 = volume, a0 = flash address, d1 = size), next to the
  // reader S-FLASHREAD0. Natively they drive the flash chip through the BML layer and fail here (no chip: the settings
  // store then logs DBG_PRM_PROC_*_SAVE_ERR and nothing is kept). Stand-in: a flash device model at this seam: written
  // and erased ranges are kept in e.flash and read back by S-FLASHREAD0; both return 0. With a state file
  // (createBoot({stateFile}) or E101_STATE=path) the written ranges are loaded at start and saved by e.saveState(), so
  // the settings banks (0x400A0000.., user settings "MODE", "EEROM", "BKRAM") persist across runs.
  e.flashLog = []; e.flashWrites = [];
  const flashPut = (a, bytes) => { a = Flash.norm(a); e.flash.write(a, bytes); e.flashWrites.push([a, Buffer.from(bytes).toString('base64')]); e.flashDirty = true; };
  e.stateFile = stateFile ?? process.env.E101_STATE ?? null;
  // Power-off stand-in (FAKE): the camera saves the settings banks in its power-off sequence, which does not finish here
  // Instead e.saveState() also keeps the RAM images of the MODE and EEROM banks (0x60404674 and 0x603F4674,
  // 0x10000 bytes each), and the next start writes them back to RAM when the firmware's own boot-time bank save
  // 0x7E4580BD is first entered: that save compares RAM with flash and writes the bank with its own checksum.
  const RAMBANKS = [['mode', 0x60404674], ['eerom', 0x603F4674]];
  let st = null;
  if (e.stateFile && fs.existsSync(e.stateFile)) { st = JSON.parse(fs.readFileSync(e.stateFile, 'utf8')); for (const [a, b64] of st.flash) flashPut(a, new Uint8Array(Buffer.from(b64, 'base64'))); }
  e.flashDirty = false;
  let injected = false;
  e.hook(0x7E4580BD, 'bank-save', () => { if (injected) return; injected = true; e.bankSaveSeen = true; if (st && st.ram) for (const [k, a] of RAMBANKS) if (st.ram[k]) e.wr(a, new Uint8Array(Buffer.from(st.ram[k], 'base64'))); });
  e.saveState = () => {
    if (!e.stateFile) return false;
    // coalesce: replay the writes into 64 KiB pages
    const pages = new Map();
    for (const [a, b64] of e.flashWrites) { const d = Buffer.from(b64, 'base64'); for (let i = 0; i < d.length;) { const pa = ((a + i) & ~0xFFFF) >>> 0, off = (a + i) & 0xFFFF, n = Math.min(d.length - i, 0x10000 - off); if (!pages.has(pa)) pages.set(pa, Buffer.from(e.flash.read(pa, 0x10000))); i += n; } }
    for (const pa of pages.keys()) pages.set(pa, Buffer.from(e.flash.read(pa, 0x10000)));
    const ram = {}; if (e.bankSaveSeen && e.m.devices.clock.t > 100e6) for (const [k, a] of RAMBANKS) ram[k] = Buffer.from(e.rd(a, 0x10000)).toString('base64');
    fs.writeFileSync(e.stateFile, JSON.stringify({ flash: [...pages].map(([a, d]) => [a, d.toString('base64')]), ram: e.bankSaveSeen ? ram : (st && st.ram) }));
    e.flashDirty = false; return true;
  };
  if (!process.env.E101_NOFLASHWRITE) {
    e.hook(0x7E451B69, 'S-FLASHWRITE', () => {
      let dst = R[A0] >>> 0, src = R[A1] >>> 0; const n = R[D1] >>> 0;
      if (((src & 0x3FFFFFFF) | 0x40000000) < 0x48000000 && ((dst & 0x3FFFFFFF) | 0x40000000) >= 0x60000000) [dst, src] = [src, dst];
      if (e.flashLog.length < 400) e.flashLog.push(`${(e.m.devices.clock.t / 1e6).toFixed(1)} write ${h8(dst)} <- ${h8(src)} n=${h8(n)} from ${h8(R[MDR])}`);
      flashPut(dst, e.rd(src, n).slice());
      e.ret(0);
    });
    e.hook(0x7E4519C5, 'S-FLASHERASE', () => {
      const a = R[A0] >>> 0, n = R[D1] >>> 0;
      if (e.flashLog.length < 400) e.flashLog.push(`${(e.m.devices.clock.t / 1e6).toFixed(1)} erase ${h8(a)} n=${h8(n)} from ${h8(R[MDR])}`);
      if (n <= 0x1000000) flashPut(a, new Uint8Array(n).fill(0xFF));
      e.ret(0);
    });
  }
  // The kernel's idle loops (`bra self` at 0x7E436825 and 0x7E43683D, reached from the kernel start 0x7E432A3F when
  // no task is ready): CPU1 halts there until its bank presents an interrupt; CPU0 jumps lab time to the next event.
  const idle = () => {
    if (e.onCpu1) return;
    const clock = e.m.devices.clock, c1 = e.m.cores;
    e.idleHits = (e.idleHits || 0) + 1;
    if (S.irqReq) return;
    if (e.cpu1Started && c1.runnable()) { c1.turn(c1.quantum); clock.advance(clock.t + c1.quantum * e.nsPerInsn, false); return; }   // CPU1 is working: let it run, time moves
    if (e.onIdle && e.onIdle() === 'stop') return 'stop';
    const before = clock.t;
    clock.advance(clock.t + 50e6, true);                 // to the next timer event, at most 50 ms
    if (e.onTime) e.onTime(clock.t);
    e.idleNs = (e.idleNs || 0) + clock.t - before;
  };
  for (const pc of IDLE) e.hook(pc, 'idle', idle);
  // S-GIOIN: the GIO input read 0x7E46144E(d0 = pin id: type in bits 24..27, number in the low 16) returns e.pins'
  // level for a pin listed there (the buttons' pins of UI_IN's tables); every other pin is read natively from the
  // GIO registers (plain storage: 0 unless written).
  e.pins = new Map([[0x35, 1], [0x32, 1], [0x28, 1], [0x41, 1], [0x42, 1], [0x72, 1], [0x74, 1],
    [0x7D, 1], [0xA1, 1],
    [0xBE, Number(process.env.E101_CD ?? 1)]]);              // 0xBE (190) card detect: 1 = no card (0x7E5CC9C8); e.card (S-CARD) clears it   // 0x7D HDMI detect, 0xA1 video-out detect: 1 = not connected (the fast start 0x7E5026E6, 0x7E502753)
  e.pinReads = new Map(); e.noFast = process.env.E101_FAST ? false : true;
  e.hook(0x7E46144E, 'S-GIOIN', () => {
    const id = R[D0] >>> 0; e.pinReads.set(id, (e.pinReads.get(id) || 0) + 1);
    // S-NOFAST (e.noFast, default on): the quick start (USR_FAST_APP: lens set-up and live view before the application
    // is up) is declined the way the firmware itself declines it, "ErrLeOK": its read of the OK button's pin 0x35
    // at 0x7E5026FE returns 0 (held). The application then starts the camera on its normal path.
    if (e.noFast && id === 0x35 && (R[MDR] >>> 0) === 0x7E502705) { e.ret(0); return; }
    if (e.pins.has(id)) e.ret(e.pins.get(id));
  });
  // S-PWM: the two PWM requests to the PER_PCONT task (0x7E466435 and the duty setter 0x7E466448(d0 = percent), the
  // LCD backlight) wait for the PWM unit's completion (0x9A500000, IRQ 118), which is not modelled: both return 0.
  e.pwmDuty = null;
  e.hook(0x7E466435, 'S-PWM', () => { e.ret(0); });
  e.hook(0x7E466448, 'S-PWM-duty', () => { e.pwmDuty = R[D0] & 0xff; e.ret(0); });
  // S-BC: a transaction with the BC (the H8 stabiliser controller; 0x7E53E792(a0 = request {callback, .., u16
  // command at +8})) is answered at once: the request's callback is posted with result 0 and the reply bytes the
  // request holds are left as they are (zero). No H8 is modelled.
  e.bcLog = [];
  e.hook(0x7E53E792, 'S-BC', () => {
    const q = R[A0] >>> 0;
    e.bcLog.push(e.r16(q + 8).toString(16));
    e.post(e.r32(q), q, 0);
    e.ret(0);
  });
  // S-SDCMD: the SD card command exchange 0x7E5CEABB(a0 = host context, a1 = command record) starts a command on
  // the SD host (0x99002000) and waits for its interrupt. e.sdCmd(cmdRecordAddress) -> status serves it; the default
  // (no card model attached) returns 0x1402, an error, for every command: "no card answers".
  e.sdLog = [];
  e.sdCmd = null;
  e.hook(0x7E5CEABB, 'S-SDCMD', () => {
    const c = R[A1] >>> 0;
    if (e.sdLog.length < 200) e.sdLog.push(Buffer.from(e.rd(c, 96)).toString('hex'));
    const type = e.r16(c + 14);
    // no card model: host set-up records (type other than 3..5) succeed; a card command gets no response: 0x1405,
    // the driver's response-timeout code (it tests it after CMD8 at 0x7E5CCDC3)
    const st = e.sdCmd ? e.sdCmd(c, R[A0] >>> 0) : (type >= 3 && type <= 5 ? 0x1405 : 0);
    if (e.sdCmd) e.w16(c + 88, st);
    e.ret(st);
  });
  // S-CARD: with E101_CARD=<host folder> (or createBoot({cardDir})) an SD card model (e101/sdcard.mjs) is attached at
  // this seam, backed by a FAT16 image built from the folder, and the card-presence port (system-controller port 2)
  // is low = card inserted. e.card.img is the image (the firmware's writes land in it); E101_CARD_IMG=<file> uses and
  // rewrites an image file instead of building one.
  const cardDir = opts.cardDir ?? process.env.E101_CARD;
  if (cardDir || process.env.E101_CARD_IMG) {
    const f = process.env.E101_CARD_IMG;
    const img = f && fs.existsSync(f) ? fs.readFileSync(f) : buildFatImage(cardDir).img;
    attachCard(e, img);
    e.ports &= ~4;
    // The asynchronous users (block reads and writes with a completion callback, 0x7E5CD934) submit their record
    // straight to the driver's queue 0x7E5CE3E1(a0 = record) instead of the waiting exchange above: the same card model
    // serves it, and the record's callback (+8)(a0 = record, d0 = status) is posted as the host interrupt would call it.
    e.hook(0x7E5CE3E1, 'S-SDCMD-async', () => {
      const c = R[A0] >>> 0, st = e.sdCmd(c);
      if (e.sdLog.length < 200) e.sdLog.push(Buffer.from(e.rd(c, 96)).toString('hex'));
      e.w16(c + 88, st);
      const cb = e.r32(c + 8); if (cb) e.post(cb, c, st);
      e.ret(0);
    });
    e.saveCard = () => { if (f && e.card.dirty) fs.writeFileSync(f, e.card.img); };
  }
  // S-BATT: the battery classifier 0x7E53963A(d0 = ADC reading, d1) -> 0x100 / 0x200 / d1 compares the reading with
  // thresholds from the adjustment data, which this machine does not have. Stand-in: always 0x100, the class for which
  // the caller 0x7E53903C sets the level to 100 (the fast start otherwise stops with "ErrLeBat").
  e.hook(0x7E53963A, 'S-BATT', () => { e.ret(0x100); });
  // observer: the firmware's error log 0x7E426D4B(d0 = code, stack words = arguments)
  e.errLog = [];
  e.errSeen = new Map();
  e.hook(0x7E426D4B, 'errlog', () => { const k = `${R[D0] >>> 0}:${R[MDR] >>> 0}`, n = (e.errSeen.get(k) || 0) + 1; e.errSeen.set(k, n); if (n <= 3 && e.errLog.length < 500) e.errLog.push(`${(e.m.devices.clock.t / 1e6).toFixed(1)} ${e.onCpu1 ? 'c1 ' : ''}${h8(R[D0])} from ${sym(R[MDR])} args ${h8(e.r32((R[SP] >>> 0) + 4))} ${h8(e.r32((R[SP] >>> 0) + 8))}`); });
  // observer: the application's event loop (OXF thread loop 0x7EBA74BB): the id of each event taken (d0 at 0x7EBA752B)
  e.evLog = [];
  e.hook(0x7EBA752B, 'oxf-event', () => { if (e.evLog.length < 20000) e.evLog.push([e.m.devices.clock.t / 1e6, (R[D0] << 16) >> 16]); });
  // observers: the camera API's asynchronous calls: api_exec_start 0x7E67E493(d0 = funcno, d1 = event, a0 = packet)
  // and their completions api_exec_post 0x7E67E5BB
  e.apiLog = [];
  e.hook(0x7E67E493, 'api_exec_start', () => { if (e.apiLog.length < 5000) e.apiLog.push(`${(e.m.devices.clock.t / 1e6).toFixed(1)} start fn=${(R[D0] >>> 0).toString(16)} ev=${(R[D1] >>> 0).toString(16)} from ${(R[MDR] >>> 0).toString(16)}`); });
  e.hook(0x7E67E5BB, 'api_exec_post', () => { if (e.apiLog.length < 5000) e.apiLog.push(`${(e.m.devices.clock.t / 1e6).toFixed(1)} post d0=${(R[D0] >>> 0).toString(16)} d1=${(R[D1] >>> 0).toString(16)} from ${(R[MDR] >>> 0).toString(16)}`); });
  // observers: the file task FILECLBK: each command it takes (0x7E5C1B5B: the command word at (12,sp)) and each
  // result it replies (0x7E5C1B9F: d0)
  e.fileLog = [];
  e.hook(0x7E5C1B5B, 'fileclbk-cmd', () => { if (e.fileLog.length < 3000) e.fileLog.push(`${(e.m.devices.clock.t / 1e6).toFixed(1)} cmd ${h8(e.r32((R[SP] >>> 0) + 12))} ${h8(e.r32((R[SP] >>> 0) + 4))} ${h8(e.r32((R[SP] >>> 0) + 8))} ${h8(e.r32((R[SP] >>> 0) + 16))}`); });
  e.hook(0x7E5C1B9F, 'fileclbk-ret', () => { if (e.fileLog.length < 3000) e.fileLog.push(`${(e.m.devices.clock.t / 1e6).toFixed(1)}   -> ${(R[D0] & 0xffff).toString(16)}`); });
  // observer: the USR_FAST_APP log 0x7E503A6E(a0 = text)
  e.fastLog = [];
  e.hook(0x7E503A6E, 'usrfast-log', () => { e.fastLog.push(`${(e.m.devices.clock.t / 1e6).toFixed(1)} ${e.cstr(R[A0] >>> 0, 40)}`); });
  // S-DMA: the CPU's DMA channels (registers 0x8500.., driver: reserve 0x7E425FA8, start 0x7E426045(a0 = {src, dst,
  // length, .., u8 mode at +16, u8 at +17}), finish 0x7E42627B) copy .data at reset and serve three other callers.
  // The registers are plain RAM here (the driver then logs errors 0x19000C0x and copies nothing), so the three calls
  // are stood in: the transfer is done in the start call and each returns 0.
  e.dmaLog = [];
  e.hook(0x7E425FA8, 'S-DMA-reserve', () => { e.ret(0); });
  e.hook(0x7E426045, 'S-DMA', () => {
    const d = R[A0] >>> 0, src = e.r32(d), dst = e.r32(d + 4), len = e.r32(d + 8), mode = e.r8(d + 16), b17 = e.r8(d + 17);
    e.dmaLog.push({ src: h8(src), dst: h8(dst), len, mode, b17, pc: h8(R[MDR]) });
    if (len > 0 && len <= 0x4000000) e.wr(dst, mode === 2 ? new Uint8Array(len).fill(b17) : e.rd(src, len).slice());
    e.ret(0);
  });
  e.hook(0x7E42627B, 'S-DMA-finish', () => { e.ret(0); });
  // e.post(fn, a0, d0): have the firmware call fn(a0, d0) from interrupt context soon, through its own deferred-call
  // ring 0 (0x60415538: 32 entries {fn, a0, u16 d0}, head +384, tail +388; post 0x7E45F219, runner 0x7E45F2A2 from the
  // IRQ 23 handler 0x7E45F242). Used by stand-ins to deliver completions the way a driver's interrupt would.
  e.post = (fn, a0 = 0, d0 = 0) => {
    const ring = 0x60415538, head = (e.r32(ring + 384) + 1) & 31;
    if (head === e.r32(ring + 388)) throw new Error('e.post: the deferred-call ring is full');
    e.w32(ring + 384, head);
    e.w32(ring + head * 12, fn); e.w32(ring + head * 12 + 4, a0); e.w16(ring + head * 12 + 8, d0);
    e.store.set(0x9A1000F4, 1); e.m.devices.intc.setLine(23, true);
  };
  // S-IIC: the I2C layer's transfers (write 0x7E463275(d0 = ch, a0 = buf, d1 = len); read 0x7E4632AA(d0 = ch,
  // d1 = txlen, a0 = txbuf, a1 = rxbuf, (36,sp) = rxlen)) are served by e.i2c(ch, tx, rxlen) -> rx bytes; the layer's
  // own completion hooks (0x7E4632FF tx done, 0x7E463334 rx done) are then posted as the SIO interrupt would call them.
  e.i2cLog = [];
  e.i2cDev = (ch, tx, rxlen) => new Uint8Array(rxlen);       // default: every device reads 0
  const i2cAsync = (ch) => e.r16(0x60416374 + 2 * ch) === 1;
  e.hook(0x7E463275, 'S-IIC-write', () => {
    const ch = R[D0] & 0xff, len = R[D1] & 0xffff, tx = e.rd(R[A0] >>> 0, len).slice();
    e.i2cLog.push({ ch, tx: Buffer.from(tx).toString('hex'), pc: R[MDR] >>> 0 });
    e.i2cDev(ch, tx, 0);
    if (i2cAsync(ch)) { e.w16(0x6041637C + 4 * ch, 1); e.post(0x7E4632FF, 0, ch); } else e.w16(0x6041637C + 4 * ch, 0);
    e.ret(0);
  });
  e.hook(0x7E4632AA, 'S-IIC-read', () => {
    const ch = R[D0] & 0xff, txlen = R[D1] & 0xffff, rxlen = e.r32((R[SP] >>> 0) + 36) & 0xffff, rxbuf = R[A1] >>> 0;
    const tx = e.rd(R[A0] >>> 0, txlen).slice();
    const rx = e.i2cDev(ch, tx, rxlen);
    e.i2cLog.push({ ch, tx: Buffer.from(tx).toString('hex'), rx: Buffer.from(rx).toString('hex'), pc: R[MDR] >>> 0 });
    e.wr(rxbuf, rx);
    if (i2cAsync(ch)) { e.w16(0x6041637E + 4 * ch, 1); e.post(0x7E463334, 0, ch); } else e.w16(0x6041637E + 4 * ch, 0);
    e.ret(0);
  });
  // S-SIO: the SIO client transfer start 0x7E469CDF(a0 = request {u8 ch, u8 dir (1 write, 2 read), u8 txlen, u8 rxlen,
  // txbuf, rxbuf, tx callback or -1, its argument, rx callback}) used by the LCD panel, the lens, the BC (H8) and the
  // audio codec. The bytes go to e.sioDev(ch, tx, rxlen) -> rx; the driver's completion hooks (0x7E469D76 tx,
  // 0x7E469D93 rx) are then posted as the channel interrupt would call them.
  e.sioLog = [];
  e.sioDev = (ch, tx, rxlen) => new Uint8Array(rxlen);       // default: every device reads 0
  e.hook(0x7E469CDF, 'S-SIO', () => {
    const q = R[A0] >>> 0, ch = e.r8(q), dir = e.r8(q + 1), txlen = e.r8(q + 2), rxlen = e.r8(q + 3);
    const tx = (dir & 1) ? e.rd(e.r32(q + 4), txlen).slice() : new Uint8Array(0);
    const rx = (dir & 2) ? e.sioDev(ch, tx, rxlen) : new Uint8Array(0);
    if (e.sioLog.length < 4000) e.sioLog.push({ ch, dir, tx: Buffer.from(tx).toString('hex'), rx: Buffer.from(rx).toString('hex'), pc: (R[MDR] >>> 0).toString(16) });
    const txs = 0x60419FDC + 8 * ch, rxs = 0x6041A00C + 8 * ch;
    e.w32(txs, 0); e.w32(txs + 4, 0); e.w32(rxs, 0); e.w32(rxs + 4, 0);
    if (dir & 1) {
      const cb = e.r32(q + 12);
      if (cb !== 0xFFFFFFFF) { e.w32(txs, cb); e.w32(txs + 4, e.r32(q + 16)); }
      e.post(0x7E469D76, 0, ch);
    }
    if (dir & 2) { e.wr(e.r32(q + 8), rx); e.w32(rxs, e.r32(q + 20)); e.w32(rxs + 4, q); e.post(0x7E469D93, 0, ch); }
    e.ret(0);
  });
  // S-SIORAW: the raw SIO driver under the hot-shoe (external flash) protocol: tx start 0x7E468324(d0 = channel,
  // d1 = length, a0 = bytes) completes at once (the channel's tx callback 0x6041762C[ch] is posted); rx start
  // 0x7E4686E8 never completes: no device answers, and the firmware's own time-out ends the exchange ("no flash").
  e.sioRawLog = [];
  e.hook(0x7E468324, 'S-SIORAW-tx', () => {
    const ch = R[D0] & 0xff, len = R[D1] & 0xffff, tx = e.rd(R[A0] >>> 0, len).slice();
    if (e.sioRawLog.length < 500) e.sioRawLog.push(`${(e.m.devices.clock.t / 1e6).toFixed(1)} tx ch${ch} ${Buffer.from(tx).toString('hex')}`);
    const cb = e.r32(0x6041762C + 4 * ch); if (cb) e.post(cb, 0, ch);
    e.ret(0);
  });
  e.hook(0x7E4686E8, 'S-SIORAW-rx', () => { if (e.sioRawLog.length < 500) e.sioRawLog.push(`${(e.m.devices.clock.t / 1e6).toFixed(1)} rx ch${R[D0] & 0xff} len ${R[D1] & 0xffff}: no answer`); e.ret(0); });
  // S-CAM: requests to the mechanism sequencer "cam" (cam.c 0x7E628303(a0 = packet {u16 command, u8, u8 mode, ..,
  // +40 callback(a0 = packet, d0 = status), +52 caller context})). Commands 3..0x7F are answered "done, status 0"
  // through the packet's callback from interrupt context; the sequencer itself (shutter charge motor, magnets and
  // aperture through the H8, photo-interrupters) does not run. Command 7 (exposure values for the next live-view
  // frame) is answered one frame later. E101_CAM=1 lets the real sequencer run (it ends in "Damage 3b83" after 1.5 s:
  // the shutter mechanism never reports its position).
  e.camLog = [];
  if (!process.env.E101_CAM) e.hook(0x7E628303, 'S-CAM', () => {
    const p = R[A0] >>> 0, cmd = e.r16(p), cb = e.r32(p + 40);
    if (e.camLog.length < 300 && cmd !== 7) e.camLog.push(`${(e.m.devices.clock.t / 1e6).toFixed(1)} cmd ${cmd} b2=${e.r8(p + 2)} mode ${e.r8(p + 3)} from ${(R[MDR] >>> 0).toString(16)}`);
    if (cmd < 3 || cmd > 0x7f) return;
    if (cb) { if (cmd === 7) e.at(e.m.devices.clock.t / 1e6 + 16.683, () => e.post(cb, p, 0)); else e.post(cb, p, 0); }
    e.ret(0);
  });
  // S-TAKEAPI: camera API messages to the TAKE_FUNC task (queue 113) whose command is in e.takeFake are not sent.
  // The hook stands on api_exec_start's queue write 0x7E67E502 (OlyQeWr(d0 = queue, a0 -> {record, length}, d1 = time-out));
  // for a faked command the same call writes the reply a worker would send: the 12-byte record {u16 status = 0, ..,
  // u32 event, 0} to queue 6 (API_EVENT). Command 0x19 = api_tft_Start_Through (live view start): the application
  // believes live view runs; no sensor, IMG engine, AE / AF / WB or face detection is started. E101_TAKEFAKE=hex,hex
  // sets the list ("none" = nothing faked: the GUI then waits in startShootingService).
  e.takeFake = new Set((process.env.E101_TAKEFAKE ?? '19').split(',').filter((x) => x !== 'none').map((x) => parseInt(x, 16)));
  e.takeLog = [];
  // e.apiFake: the same for other modules, 'queue:command(hex)'. 80:5 = api_play_Play_Rom (PLAY_MAIN shows a ROM picture,
  // the menu's background, through the IMG engine): answered done, nothing is shown on the video plane. E101_APIFAKE sets the list.
  e.apiFake = new Set((process.env.E101_APIFAKE ?? '80:5,80:1').split(',').filter((x) => x !== 'none'));
  let takeSlot = 0;
  e.hook(0x7E68522D, 'play-rom-no', () => { e.romNo = R[D1] & 0xffff; });     // observer: api_play_Play_Rom(d0 = kind, d1 = ROM picture number)
  e.hook(0x7E67E502, 'S-TAKEAPI', () => {
    const sp = R[SP] >>> 0, m = e.r32(sp + 24), q = R[D0] & 0xffff, cmd = e.r32(m + 8), ev = e.r32(m + 4);
    const fake = (q === 113 && e.takeFake.has(cmd)) || e.apiFake.has(`${q}:${cmd.toString(16)}`);
    if (e.takeLog.length < 2000) e.takeLog.push(`${(e.m.devices.clock.t / 1e6).toFixed(1)} queue ${q} cmd ${cmd.toString(16)} event ${ev.toString(16)} data ${e.r32(m + 12).toString(16)} ${e.r32(m + 16).toString(16)}${fake ? ' FAKED' : ''}`);
    if (q === 80 && cmd === 5 && fake) e.videoRom = e.romNo; else if (q === 113 && cmd === 0x19) e.videoRom = null;
    if (!fake) return;
    const a = 0x00012000 + 16 * (takeSlot++ & 63);          // lab low RAM: the reply record
    e.w32(a, 0); e.w32(a + 4, ev); e.w32(a + 8, 0);
    e.w32(sp + 24, a); e.w32(sp + 28, 12); R[D0] = 6;
  });
  // S-IMG: a job of the IMG engine driver (0x7E544BB5 -> 0x7E545590(d0 = event flag, a0 = request {.., u16 result at
  // +104, u8 type at +194})) is prepared and started by the firmware (register writes go to plain storage), then waits
  // on its event flag for bit 1 = "finished" (the engine's interrupt), 1000 ms time-out (error 0x12010002). No IMG engine
  // is modelled: the wait at 0x7E5455BF is answered at once with "finished, result 0". No pixel is processed (the menu
  // background drawn by CapImg_ImagePlayer `Draw_Rectangle_Image_HandleArea` goes to the video plane, which is not
  // composed either). E101_IMG=1 disables.
  e.imgLog = [];
  if (!process.env.E101_IMG) e.hook(0x7E5455BF, 'S-IMG', () => {
    const sp = R[SP] >>> 0, req = R[A0 + 2] >>> 0;       // a2 = request
    if (e.imgLog.length < 500) e.imgLog.push(`${(e.m.devices.clock.t / 1e6).toFixed(1)} type ${e.r8(req + 194)}`);
    e.w32(sp + 12, 2); e.w16(req + 104, 0); R[D0] = 0; R[PC] = 0x7E5455C6 | 0;
  });
  // S-ACC (FAKE, off by default): the accelerometer read 0x7E4583BF(d0 = unit, a0 -> three s32 words x, y, z) used by
  // the PER_SLOPE task (level gauge). Natively it takes a sample from a ring (0x7E4585DC, write index 0x604148C0) that
  // the chip's sampling fills; no chip answers here, so the ring stays empty and the task sleeps 16 ms and retries for
  // ever (the gauge then shows its bars at rest). With e.tilt = [x, y, z] (play step `tilt:X:Y:Z`, E101_TILT=X,Y,Z;
  // 16384 = 1 g) the ring read answers "no sample" once (the firmware's own 16 ms sleep paces the loop) and "sample"
  // the next time, and at the function's exit 0x7E4584A4 the three output words are replaced by e.tilt, status 0.
  e.tilt = process.env.E101_TILT ? process.env.E101_TILT.split(',').map(Number) : null;
  let accPhase = 0;
  e.hook(0x7E4585DC, 'S-ACC-ring', () => { if (!e.tilt) return; accPhase ^= 1; e.ret(accPhase ? 1 : 0); });
  e.hook(0x7E4584A4, 'S-ACC-out', () => { if (!e.tilt) return; const a = R[A0 + 3] >>> 0; e.w32(a, e.tilt[0] | 0); e.w32(a + 4, e.tilt[1] | 0); e.w32(a + 8, e.tilt[2] | 0); R[D0 + 3] = 0; });
  // e.at(labMs, fn): run fn once when lab time reaches labMs (scripted inputs)
  e.sched = [];
  e.at = (ms, fn) => { e.sched.push([ms * 1e6, fn]); e.sched.sort((a, b) => a[0] - b[0]); };
  e.onTime = (t) => { while (e.sched.length && e.sched[0][0] <= t) e.sched.shift()[1](e); };
  // CPU1 release: the reset main stores CPU1's entry in 0x98D00140 and writes 1 to 0x988000F0 (0x7E4213C4..D9).
  e.wHooks.set(0x988000F0, (v) => {
    if (!(v & 1) || e.cpu1Started) return;
    const pc = e.store.get(0x98D00140) >>> 0;
    say(`[cpu1 released at ${h8(pc)}]`);
    e.m.cores.start(pc, 0, { stops: [...e.hooks.keys()].filter((p) => !IDLE.includes(p)), halts: IDLE,
      // CPU1's request loop (task at 0x7E44EB33, priority 15) only reads the request words 0x8FF0008C..0x8FF000AF:
      // CPU1 sleeps there until one changes or an interrupt arrives
      polls: [[0x7E44EB5B, 0x8FF0008C, 0x24]] });
    e.m.cores.onStop = (pc2, api) => e.cpu1Stop(pc2, api);
    e.m.cores.interleave = true;
    e.cpu1Started = true;
  });
  // the same pc hooks serve CPU1 (the cores' onStop runs with CPU1's registers selected)
  e.cpu1Stop = (pc, api) => {
    const h = e.hooks.get(pc >>> 0); if (!h) return 'step';
    h.count++; e.onCpu1 = true;
    try { h.fn(e, pc); } finally { e.onCpu1 = false; }
    return (R[PC] >>> 0) === (pc >>> 0) ? 'step' : 'go';
  };
  const fill = e.hooks.get(0x7E4213F7).fn;
  e.hook(0x7E426B5D, 'S-OSDFILL(cpu1)', fill);
  return e;
}

export function report(e, r) {
  const out = [];
  out.push(JSON.stringify(r) + ' ' + e.regs() + ' insns ' + S.insns);
  out.push('at ' + sym(R[PC]));
  out.push(...backtrace(e, R[SP]));
  const t = e.stderrTail(600); if (t) out.push(t);
  return out.join('\n');
}
export function seenReport(e, max = 60) {
  return [...e.seen.entries()].slice(-max).map(([k, v]) => `${k} n=${v.n} pc=${sym(v.pc)} v=${h8(v.v)} w=${v.w}`).join('\n');
}
