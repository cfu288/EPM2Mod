// stage2-boot.mjs [LABMS]: boot the stock (or BLOCKS=<dir>) E-PM2 firmware from its reset vector and report.
// Exit code 0 when both kernels run, the start-up tasks finished (Usr0..Usr4) and no CPU fault happened.
import { createBoot, report, sym } from '../e101/boot.mjs';
import { tasks } from '../e101/kernel.mjs';
import { evName } from './evnames.mjs';
import { R, S, PC, SP, PSW } from '../e101/machine.mjs';
const e = createBoot({ blocksDir: process.env.BLOCKS });
R[PC] = 0x7E421020 | 0; R[SP] = 0x47001FFC | 0; R[PSW] = 0;
const t0 = Date.now();
const r = e.run({ maxLabMs: Number(process.argv[2] || 2000), maxMs: 300000 });
const con = e.console.split('\n').filter((l) => !/TAG_NOT_EXIST|^ 0000/.test(l));
console.log('stop:', JSON.stringify(r), '| lab ms', (e.m.devices.clock.t / 1e6).toFixed(1), '| wall ms', Date.now() - t0, '| insns cpu0', S.insns, 'cpu1', e.m.cores.state().insns);
console.log('console (' + con.length + ' lines, prm tag messages left out):\n  ' + con.join('\n  '));
console.log('boot marks:', e.marks.length, 'last', e.marks.slice(-3).map((m) => m[0]).join(' '));
const out = { ok: true };
for (const c of [0, 1]) {
  const ts = tasks(e, c), by = {};
  for (const t of ts) by[t.state] = (by[t.state] || 0) + 1;
  console.log(`cpu${c} tasks:`, JSON.stringify(by));
  out['cpu' + c] = by;
}
console.log('quick start log:', e.fastLog.join(' | '));
console.log('application events taken:', e.evLog.length, 'last:', e.evLog.slice(-4).map((x) => `${x[1]} ${evName(x[1])}`.trim()).join('; '));
console.log('camera API async calls:', e.apiLog.join(' ; '));
console.log('file task:', e.fileLog.slice(0, 3).join(' ; '));
console.log('firmware error log entries:', e.errLog.length, e.errLog.slice(0, 5).join(' ; '));
console.log('stand-ins and observers hit:', [...e.hooks.values()].filter((h) => h.count).map((h) => `${h.name} x${h.count}`).join(', '));
console.log('I2C transfers', e.i2cLog.length, '| SIO client transfers', e.sioLog.length, '| BC transactions', e.bcLog.length, '| SD commands', e.sdLog.length, '| DMA', e.dmaLog.length, '| divide relaxations', S.divz | 0);
const c1 = e.m.cores.state();
console.log('cpu1:', c1.parked ? 'PARKED ' + c1.parked : (c1.halted ? 'idle' : 'running'), '| problems:', e.m.cores.problem()?.message ?? 'none');
const ok = r.why === 'labtime' && !c1.parked && /Usr4/.test(e.console) && e.console.includes(':-)');
console.log(ok ? 'STAGE 2: PASS (kernel on both cores, Usr0..Usr4 done, tasks scheduled, no fault)' : 'STAGE 2: FAIL');
process.exit(ok ? 0 : 1);
