Emulator checks of the Level Adjust build (NOTES.md section 12). Our scripts only: no om-emu file is here.

Copy the five files to <emulator work folder>/level-adjust/ (the work folder is ~/opt/om-emu-e101-boot-work, see
docs/feasibility.md, "The emulator") and run ./level-adjust/run-checks.sh there. They import the work folder's own
driver (e101/*.mjs) and use its audit/crawl.mjs and audit/state/. Screenshots and logs stay in that folder.

run-checks.sh     the checks a, c, d, e, ram and b, with the key scripts
trace-adjust.mjs  play.mjs with a trace of the calibration chain, a dump of the stored values, and a raw-sample
                  stand-in for the accelerometer (raw:X:Y:Z)
ramcheck.mjs      the row-state array and the bytes after it
crawl-all.sh      the audit's menu crawl for one image, output under level-adjust/crawl/
crawlcmp.py       crawl comparison that tolerates one more Custom Menu row
