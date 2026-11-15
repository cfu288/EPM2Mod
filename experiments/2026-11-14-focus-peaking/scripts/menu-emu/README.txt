Emulator checks of the build peaking-menu (NOTES.md section 15).

These files are our drivers for the full-boot emulator. They are copies: the working copies are in the emulator
work folder, ~/opt/om-emu-e101-boot-work/peaking-menu/ (the emulator itself is not in this repository). They use
play.mjs, stage2-boot.mjs, audit/crawl.mjs, audit/state/pinned-*.json and level-adjust/ramcheck.mjs of that folder.

  run-checks.sh   a = boot report against the pinned build; c = screenshots of the row and its list; d = the value
                  over three restarts; ram = the row-state array; b = full menu crawls of both images and their
                  comparison; b0 = the shallow crawls (P without card, iAUTO, ART, movie)
  crawl-all.sh    all crawl units of one configuration for the named images, output under peaking-menu/crawl/
  crawlcmp.py     compares two crawls when one image has one more Custom Menu row (from the level-gauge work)
  tagpeek.mjs     play.mjs steps plus tag:LABEL = the stored value of prm tag 0x8971 (setting 458)

Images (from the repository root):
  python3 tools/oetool.py unpack build/peaking-gain-2x.BIN $SCRATCH/pinned2x
  python3 tools/oetool.py unpack build/peaking-menu.BIN    $SCRATCH/peakmenu
