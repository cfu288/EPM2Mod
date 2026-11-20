// rawedit.mjs STEP...: play.mjs-like steps (w:MS, key:NAME[:MS], shot:NAME) with pc hooks on the RAW Data Edit path.
// Env: as play.mjs, plus SHOTS (out dir) and PLAIN=hex,hex,... (declare those I/O blocks as plain storage; a scratch stand-in, not a hardware model).
import fs from 'node:fs';
const ROOT = new URL('../../../emulator/e101/', import.meta.url).href;
const { createBoot } = await import(ROOT + 'boot.mjs');
const { KEYS, press, release } = await import(ROOT + 'keys.mjs');
const { screenshot } = await import(ROOT + 'screen.mjs');
const { R, PC, SP, PSW } = await import(ROOT + 'machine.mjs');
const e = createBoot({ blocksDir: process.env.BLOCKS });
for (const b of (process.env.PLAIN || '').split(',').filter(Boolean)) e.block(parseInt(b, 16), 'scratch plain ' + b);
R[PC] = 0x7E421020 | 0; R[SP] = 0x47001FFC | 0; R[PSW] = 0;
const ms = () => Number((e.m.devices.clock.t / 1e6).toFixed(1));
const H = {
  0x7EB0C240: 'app_select_execute_prep_edit_raw', 0x7EB0E1D5: 'rawedit_change_mode', 0x7EB0E373: 'rawedit_restore_mode',
  0x7EACF352: 'ERaw createActiveRelations', 0x7EAD0163: 'ERaw state_start_current_mode', 0x7EAD025D: 'ERaw state_start_custom_edit',
  0x7EAD1687: 'ERaw start_current_mode_edit', 0x7EAD2633: 'ERaw preview_current_start', 0x7EAD278D: 'ERaw preview_current',
  0x7EACFD75: 'ERaw state_preview', 0x7EACF5D6: 'ERaw check_execute_edit_raw', 0x7EAD1D17: 'ERaw save_start',
  0x7EAD1AE1: 'ERaw save_current_start', 0x7EAD1BB6: 'ERaw save_current', 0x7EAD006F: 'ERaw state_save',
  0x7EACFA70: 'ERaw edit_raw_exe_end', 0x7EACFC3F: 'ERaw state_end_edit', 0x7EACF574: 'ERaw callback_progress',
  0x7EAD3430: 'ERaw end_current_mode_edit', 0x7EAD37C2: 'ERaw can_raw_start', 0x7EAD203B: 'ERaw choice (null transition)',
  0x7EDF795E: 'page 620/621 slot29 (OlyApiEditRaw call)', 0x7EDF7F60: 'RawEditProcessCallback',
  0x7E686A77: 'api_play_EditRaw_PlayPicture', 0x7E6839C8: 'api_picfile_EditRaw_Create_PictureFile', 0x7E68E29C: 'api_tft_Draw_Image_EditRaw',
  0x7EA0A72C: 'CapImg make_image_edit_raw', 0x7E9F45DE: 'app_background_raw_edit_preview',
  0x7E940F1A: 'play_edit_raw_main', 0x7E940F77: 'play_edit_raw_edit', 0x7E94113F: 'play_edit_raw_set_exif_default',
  0x7E948E4F: 'play_rec_raw_edit', 0x7E944DB9: 'play_img_encode_jpeg', 0x7E9436E8: 'play_file_create_file',
  0x7E94AE4B: 'play_save', 0x7E94B011: 'play_save_raw', 0x7E948E05: 'play progress', 0x7E94470C: 'play resize (0x7E94470C)',
  0x7E55776E: 'IMG engine regs (0x7E55776E)', 0x7EACFDFA: 'preview: calls (a2) raw load', 0x7EACFDFE: 'preview: (a2) returned', 0x7EACFE0B: 'preview: calls (a1)', 0x7EACFE10: 'preview: (a1) returned', 0x7EACFE15: 'SUCCESS RAW LOAD', 0x7EACFF5E: 'ERR RAW LOAD a', 0x7EACFFC0: 'ERR RAW LOAD b', 0x7E94764F: 'play_load_raw_raw_header_check', 0x7E947719: 'play_load_raw_load_prim_raw', 0x7E947746: 'lpr a', 0x7E94776D: 'lpr dcfcheck', 0x7E947793: 'lpr 9479ef', 0x7E9477CD: 'lpr c22', 0x7E9477F0: 'lpr c81', 0x7E947833: 'lpr dbe', 0x7E947859: 'lpr 983', 0x7E947877: 'lpr 578c60', 0x7E947888: 'lpr out', 0x7E947CBA: 'rp 941625', 0x7E947CC5: 'rp 9416b6', 0x7E947CCF: 'rp 941517', 0x7E947CFE: 'rp 9435e7 (file read?)', 0x7E947D03: 'rp 9435e7 returned', 0x7E947D61: 'rp 93d10f', 0x7E947D83: 'rp errlog',
};
const seen = [];
for (const [a, n] of Object.entries(H)) e.hook(Number(a), n, () => { const s = `${ms()} ${n}${n === 'play progress' ? ' d0=' + (R[0] >>> 0) : ''}`; if (seen.length < 400) seen.push(s); console.log('HIT', s); });
const fin = (why) => {
  console.log(JSON.stringify({ end: why, ms: ms(), pc: (R[PC] >>> 0).toString(16), denied: (e.denied || []).slice(0, 8).map((d) => d.map((x) => typeof x === 'number' ? (x >>> 0).toString(16) : x)),
    errlog: e.errLog.slice(-6), problem: e.m.cores.problem()?.message ?? 'none' }));
};
const run = (t) => {
  const r = e.run({ maxLabMs: t, maxMs: 900000 });
  if (r.why !== 'labtime') { fin(r); process.exit(2); }
};
run(Number(process.env.BOOTMS || 1500));
for (const step of process.argv.slice(2)) {
  const f = step.split(':');
  console.log('STEP', step, ms());
  if (f[0] === 'w') run(Number(f[1]));
  else if (f[0] === 'key') { if (!KEYS[f[1]]) { console.log('unknown key', f[1]); process.exit(2); } press(e, f[1]); run(Number(f[2] || 120)); release(e, f[1]); run(400); }
  else if (f[0] === 'shot') { fs.mkdirSync(process.env.SHOTS, { recursive: true }); screenshot(e, `${process.env.SHOTS}/${f[1]}.png`); }
  else { console.log('unknown step', step); process.exit(2); }
}
console.log('card', e.card?.reads, e.card?.writes, JSON.stringify([...(e.card?.unknown ?? [])])); fin('done');
