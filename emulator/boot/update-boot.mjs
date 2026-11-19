// update-boot.mjs [LABMS]: power on with OK held, the firmware-update path: the om-emu fork's `bin/boot.mjs update`.
// E101_CARD=<folder> gives the card (DCOLYMP/E1019999.BIN in it: "update file present"); NO_OK=1 a normal start;
// WATCH=hex:name,... more pcs to report.
import { runFork } from './forkcli.mjs';
const a = process.argv.slice(2);
runFork('update', a.length ? ['--ms', a[0]] : []);
