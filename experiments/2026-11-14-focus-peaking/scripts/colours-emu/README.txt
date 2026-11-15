Emulator checks of the build peaking-colours (NOTES.md section 16).

These files are our drivers for the full-boot emulator. They are copies: the working copies are in the emulator
work folder, ~/opt/om-emu-e101-boot-work/peaking-colours/ (the emulator itself is not in this repository). They use
play.mjs, stage2-boot.mjs, audit/crawl.mjs and audit/state/pinned-*.json of that folder, and ../menu-emu/crawlcmp.py.

  run-checks.sh   a = boot report against the pinned build; c = screenshots of the row and its list with the cursor
                  on each value; d = each of the five values over a restart; b0 = the shallow crawls of both images
                  (P without card, iAUTO, ART, movie) and their comparison
  crawl-all.sh    all crawl units of one configuration for the named images, output under peaking-colours/crawl/.
                  It has one unit more than ../menu-emu/crawl-all.sh: custA opens the lists of the rows of group A
  tagpeek.mjs     play.mjs steps plus tag:LABEL = the stored value of prm tag 0x8971 (setting 458)

Images (from the repository root):
  python3 tools/oetool.py unpack build/peaking-menu-names.BIN $SCRATCH/pc-pinned
  python3 tools/oetool.py unpack build/peaking-colours.BIN    $SCRATCH/pc-colours
