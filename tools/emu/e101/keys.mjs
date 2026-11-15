// Key names -> how the E-PM2 body presents them (filled in as they are identified; see ../boot/README.md).
//   {pin: n}  a GIO input pin, pressed = level 0;  {adc: [channel, value]}  the key ladder's ADC value; {port: bit}
export const KEYS = {
  // GIO pins (UI_IN group 7, polled every 10 ms at 0x7E50C5F2; pressed = 0). VERIFIED by the GUI's reaction:
  OK: { pin: 0x35 },          // GUI event 0x01000016 / 17: opens the Live Guide in iAUTO
  PLAY: { pin: 0x28 },        // 0x0100001E / 1F: playback
  ERASE: { pin: 0x41 },       // 0x01000026 / 27: handler "deleteMultiExposure" (INFERRED: the erase key)
  CUSTOM1: { pin: 0x32 },     // key 0x1209, 0x01000022 / 23: a customisable key (`checkFuncDirectStart`): Fn or the movie button (which of the two is UNKNOWN)
  CUSTOM2: { pin: 0x42 },     // key 0x0B, 0x0100002E / 2F: the other customisable key (`checkFuncDirectStart`, isMediaAccess)
  // the key ladder on ADC input 3 (UI_IN group 6; thresholds 0x22, 0x64, 0xA8, 0xEF, 0x139, 0x18F, 0x1F2, 0x2C2):
  MAGNIFY: { adc: [3, 0x43] }, // key 0x0A, 0x01000042 / 43: `pressLvMagnifyKey` (zoom frame, then 10x) (VERIFIED by the GUI log)
  UP: { adc: [3, 0x86] },     // key 5, 0x01000006 / 07: an arrow ("checkModeDirectStart": nothing in iAUTO)
  DOWN: { adc: [3, 0xCB] },     // key 6, 0x0100000A / 0B: an arrow (a bar at the bottom of the screen)
  LEFT: { adc: [3, 0x114] },  // key 7, 0x0100000E / 0F: the AF target grid (INFERRED: the left arrow)
  RIGHT: { adc: [3, 0x164] },    // key 8, 0x01000012 / 13: an arrow (a bar at the bottom of the screen)
  INFO: { adc: [3, 0x1C0] },  // key 0x1205, 0x0100002A / 2B: `pressInfoKey`: the INFO button (VERIFIED by the GUI log and the display cycle)
  MENU: { adc: [3, 0x250] }, // key 0x89, 0x0100001A / 1B: MENU (VERIFIED: sub-app ShootingMenu, state 0x5700)
  POWER: { port: 0 },         // the ON/OFF button (system-controller port 0): power-off sequence; the settings banks are saved to flash
  S1: { pin: 0x72 }, S2: { pin: 0x74 },   // shutter half / full press (UI_IN group 2, keys 0x100 / 0x101)
  // experiments that produced no GUI event (MENU is not found yet; an earlier guess):
  X12: { ioe: [9, [0x00, 0x10]] }, E0B: { emit: [0x0B, 12] },
};
export const ADC_IDLE = 0x3FF;
// A ladder key: the ADC input 3 takes the key's value and the key-on line (GIO pin 0x5D, an edge interrupt registered
// by UI_IN at 0x7E50B40B) fires: its handler 0x7E50B50D(a0 = the ladder's table entry 0x7E7354CC) starts the ADC scan,
// which then repeats every 10 ms until the value says "no key". The handler is posted directly (the GIO pin interrupt
// unit is not modelled).
export function press(e, name) { const k = KEYS[name]; if (k.pin !== undefined) e.pins.set(k.pin, 0); if (k.adc) { e.adc[k.adc[0]] = k.adc[1]; e.post(0x7E50B50D, 0x7E7354CC, 0); } if (k.port !== undefined) e.setPorts(e.ports ^ (1 << k.port)); }
// UI_IN sample injection for the groups whose source is not modelled (the I/O expanders on I2C): the sample bytes are
// pushed the way the group's own completion would, 0x7E50AA1C(d0 = length, d1 = group, a0 = bytes), from interrupt
// context through a pad in lab low RAM (`mov group,d1 ; call 0x7E50AA1C,[],4 ; rets`).
let padN = 0;
export function pushSample(e, group, bytes) {
  const pad = 0x00011100 + 16 * (group & 15), data = 0x00011400 + 8 * (padN++ & 31), d = (0x7E50AA1C - (pad + 2)) | 0;
  e.wr(pad, [0x85, group, 0xDD, d & 255, (d >>> 8) & 255, (d >>> 16) & 255, (d >>> 24) & 255, 0x00, 0x04, 0xF0, 0xFC]);
  e.wr(data, bytes);
  e.post(pad, data, bytes.length);
}
// UI_IN event injection: the emitter 0x7E50A7AC(d0 = type << 24 | released << 16 | key id, d1 = index in its group),
// called from interrupt context through a pad (`mov event,d0 ; mov index,d1 ; call 0x7E50A7AC,[d2,d3,a2,a3],20 ; rets`).
// Used for keys whose electrical source is not identified (KEYS entries with `emit`).
let emitN = 0;
export function emitKey(e, key, index, released) {
  const pad = 0x00011800 + 32 * (emitN++ & 15), ev = (0x02000000 | (released ? 0x10000 : 0) | key) >>> 0, d = (0x7E50A7AC - (pad + 8)) | 0;
  e.wr(pad, [0xFC, 0xCC, ev & 255, (ev >>> 8) & 255, (ev >>> 16) & 255, (ev >>> 24) & 255, 0x85, index, 0xDD, d & 255, (d >>> 8) & 255, (d >>> 16) & 255, (d >>> 24) & 255, 0xF0, 0x14, 0xF0, 0xFC]);
  e.post(pad, 0, 0);
}
export function release(e, name) { const k = KEYS[name]; if (k.pin !== undefined) e.pins.set(k.pin, 1); if (k.adc) e.adc[k.adc[0]] = ADC_IDLE; if (k.port !== undefined) e.setPorts(e.ports ^ (1 << k.port));  if (k.ioe) pushSample(e, k.ioe[0], k.ioe[1].map(() => 0)); if (k.emit) emitKey(e, k.emit[0], k.emit[1], true); }
