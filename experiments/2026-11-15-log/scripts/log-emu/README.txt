Copies of the scripts that ran the emulator checks of the build debug-log (NOTES.md sections 6 and 7).
They run in the emulator work folder (~/opt/om-emu-e101-boot-work/log/), not here: they import that folder's
driver (e101/*.mjs) and use its env.sh, audit/crawl.mjs and audit/state/. No om-emu source is in this folder.

  logplay.mjs    play.mjs for the log checks: copies the card's root files back to the host folder (E101_CARD),
                 prints the ring headers (ring:), calls log_put from interrupt context (burst:N), writes records
                 into the CPU1 ring (cpu1:N), saves and seeds the ring RAM (save:, seed:), counts non-zero bytes
                 of the RAM gap (gap:), prints registers at a pc (PROBE=hex,hex) and the SD commands after a lab time (CARDTRACE=ms)
  run-checks.sh  checks a to h; outputs go to the same folder
  crawls.sh      shallow menu crawls of the pinned and the debug image and their compare (crawl-all.sh, crawlcmp.py)
  guitrace.mjs   prints the GUI's own trace lines with their callers (how the hook site of gui_state was found)
