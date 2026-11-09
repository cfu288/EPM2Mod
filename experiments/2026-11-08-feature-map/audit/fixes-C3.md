# Fix pass C3 (2026-11-09)

Sources: `coverage/round3-review1.md` … `round3-review4.md`: the 4 CONTRADICTED verdicts (F011, F015/F016, F064), review 3's contradicted secondary claim C1, and every item in the "smaller errors", "side findings", "imprecise" and "other map defects" lists.

Method. Before each edit I re-checked the correction in block 0 of v1.6 (runtime = 0x7E421020 + offset) with `fwmap.py fn/range/str/xref/tasks`, `build/map/calls.tsv`, `functions.tsv`/`functions.txt`, raw word reads (`rd.py`, Python `-I`) and the D1 Ss handler table (`scratchpad/d1/gui-toolkit/ss/handlers.tsv`). Scratch: `/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad/fixC3/` (`rd.py`, `backup-modules.tsv`). Every changed line in the sections and the map carries "(C3 2026-11-09)". Old text is struck through (`~~…~~`), not deleted. modules.tsv has no comment column, so its 5 changed rows are not tagged (same as D2); they are listed in §1.6. I edited only sections 01, 02, 03, 08, 12, 13c, 13d, 13f, 14a, 14b, 14c, 14e, `docs/firmware-map.md` and `modules.tsv`. No git, no build, no network. Deep detail (Ss state names, HCI layer, AVPI classes, DPS parsers, etc.) is left to D3 (15a–15d).

**Counts.**
- **Applied:** 24 corrections in 31 log rows: 3 from the 4 CONTRADICTED verdicts (F015 and F016 share one claim), 1 from review 3's C1, 20 from the smaller-error/defect lists. They are on 31 tagged lines (01 1, 02 2, 03 5, 08 3, 12 1, 13c 4, 13d 3, 13f 1, 14a 2, 14b 2, 14c 2, 14e 1, firmware-map 4) and 5 modules.tsv rows.
- **Applied with different numbers than the review:** 6 (marked "≠ review" below).
- **Rejected:** 0.
- **Not applied (no map defect, or outside the brief):** 4 (§2).
- **Contradictions found** (review against the bytes): 5 (§3).

## 1. Applied

### 1.1 CONTRADICTED verdicts

| location | old | new | check done |
|---|---|---|---|
| 14b §1 table, cam_lens.c row (F011) | "~0x7E63E5xx–0x7E640857 … start not fixed" | ~0x7E640200–0x7E640857; code up to ~0x7E6401FF is still the imgdev driver | `fwmap fn 0x7E64015E`: callers 0x7E63E3FB/0x7E63E443 only, ← 0x7E63CF71/0x7E63D027 (calls.tsv); callee 0x7E63EB3F loads 0x8481 at 0x7E63EB92; error-code scan of 0x7E63C000–0x7E641000: last 0x0A17xxxx at 0x7E63E658, first 0x0A25xxxx at 0x7E640307, first 0x92xx at 0x7E640271; `IMGDEV_DRIVER`/`g_imgdev_driver` strings used by 0x7E63E4B2; the last fn before 0x7E640200 is 0x7E640186 (122 B, ← 0x7E63EC1E) |
| 03 §3 module table, rows cam_imgdev.c and cam_lens.c (F011) | imgdev 0x7E63BE39–0x7E63D0DD; CAMLNS "start not fixed" | + "driver part continues to ~0x7E6401FF"; cam_lens starts at ~0x7E640200 | same checks |
| 03 §7b SDET item (F015/F016) | "0x7E667400–0x7E675000 … **Inferred:** the detection algorithm library" | struck; 0x7E666EB9–~0x7E675000 is mainly the mdet motion-detection / AF-tracking library (TAKE AF, FCS_MOVIE); SDET reaches 2 of its functions; loader 0x7E674F44 inside | reachability over calls.tsv: from SDET 0x7E662000–0x7E666EB8 → 2 fns (0x7E6671C3, 0x7E673F91); from outside → 122; F015 0x7E668353 and F016 0x7E66B36A not reachable from SDET; 0x7E6682E6 ← 0x7E59BBD0/0x7E59BCD9 (coordinator's check confirmed); direct outside callers into the block include TAKE 0x7E592969…0x7E59BEF9 and 0x7E5E8044 (string `mdet` 0x7E7A1E6E); `block_trust` used by 0x7E666FE8; 0x7E674F44 has 15 distinct caller fns (playback, USB, art, BASIC, lens), none in TAKE. **≠ review:** the 2 SDET-reached fns are 0x7E6671C3 and 0x7E673F91, not "both via 0x7E673F91" |
| 03 open question 10 | "SDET: the algorithm block 0x7E667400–0x7E675000" | struck; points to §7b | as above |
| 14b §5 EMS1/EMS2 row | "← SDET algorithm block 0x7E66C9A8/0x7E66DA1D" | "← the mdet … library" | 0x7E66C9A8/0x7E66DA1D are in 0x7E666EB9–0x7E675000 and not among the 2 SDET-reached fns |
| firmware-map regions row 0x7E621020–0x7E6A1020 (F015/F016) | "EXP_MOVIE (AE), SDET (scene detection)" | + mdet library 0x7E666EB9–~0x7E675000 (TAKE AF, FCS_MOVIE, not SDET) | as above |
| 13d §1 row 0x7EDC15B0– (F064) | "…–~0x7EDE0000 … DPS GUI helpers 0x7EDCE9B9–0x7EDD07F9, the self-adjust UI 0x7EDD8–0x7EDDF" | end ~0x7EDE161C; focal-length page 0x7EDDAF6A–0x7EDDB050, language loader 0x7EDDBD50, self-adjust UI 0x7EDDBF31–0x7EDDD1E5, GuiTouch ~0x7EDDD21D–~0x7EDE161C (table 0x7EFED8F4, checkSlideAreaPos 0x7EDE13B4); DPS helpers ≥0x7EDD08D2 | `fwmap str 'GUI-SelfAdjust\|userGuiSelfAdjust'`: 15 user fns, 0x7EDDBF31…0x7EDDD1E5; word dump 0x7EFED8F4: 13 pointers 0x7EDE12C5, 0x7EDDDE22, 0x7EDDDF93 … 0x7EDDE967, then 0; `fwmap fn 0x7EDE13B4`: 35 callers 0x7EDDD22C–0x7EDE033E; `fwmap range 0x7EDE1400–`: getters to 0x7EDE15EE (47 B, ends 0x7EDE161C); `userGuiUsbConnectCallBack` used by 0x7EDE1D0A; `fwmap range 0x7EDD8000–`: `*FocalLength` strings in 0x7EDDAF6A/AFAF/AFFF, `getLanguageLoadResource` in 0x7EDDBD50. **≠ review:** GuiTouch end given as ~0x7EDE161C (last helper 0x7EDE15EE + 47 B) |
| 13d §1 row "~0x7EDE0000–0x7EE01FF5 menu pages" (F064) | start ~0x7EDE0000 | ~0x7EDE161D (after GuiTouch) | as above |

### 1.2 Review 3, contradicted secondary claim C1 (TSV owners)

| location | old | new | check done |
|---|---|---|---|
| 13c §4, new bullet "TSV caveat, next-class owners" (13c-event-ids.tsv itself is outside the brief) | TSV owner of 7591–7611 = "CmpSht_ShootingComponent_NEW (next class)"; 3613 = "Com_ManagersSubTransition (next class)" | 7591–7611 = `evTraCmpPly_*` play-component notifications (Cmp_PlayComponentBase observers); 3613 is created only in Cmp_PictBridgeComponent | TSV rows 7591–7611 all have that owner; ctor 0x7EB79E78 (7604) ← 0x7EB3DC6E, 0x7EB79F94 (7611) ← 0x7EB3DA61, 0x7EB79D60 (7597) ← 0x7EB3D9FB; observer ctors 0x7EB3DA46/0x7EB3DC53 ← 0x7EB0A5E7 only, and 0x7EB0A5E7 calls all 8 (0x7EB3DA46…0x7EB3DE8C); string `Cmp_PlaySingleComponentBase rcv [evTraCmpPly_NotifySelectDisplayExecuteEnd]` used by 0x7EB109D3; 3613 ctor 0x7EA69837 ← 0x7EAF2FE7, 0x7EAF51C3, 0x7EAF69EB, 0x7EAFBCD4, 0x7EAFBF48 (all in CmpPbr 0x7EAEEAEF–0x7EB015FE) |

### 1.3 Review 1, smaller errors

| location | old | new | check done |
|---|---|---|---|
| 02 §1 table, BC row | 0x7E53BAAD–0x7E542B4E | ≤0x7E53AEA9–0x7E542B4E | `fwmap fn`: BC init 0x7E53D90C (← Usr0 0x7E503DD4) calls 0x7E53AEA9; BC_MAIN 0x7E53D96D → 0x7E53DF10 → 0x7E53AEC5 → 0x7E53B456; 0x7E53B456: `cmp 2`/`cmp 255`, `add 2121548996 (0x7E7444C4),a1`, `jmp (a1)`; 0x7E53A9C8 is the `dbg` shell (U_SHELL words 0x7E732750/0x7E733360; 01 §3). **≠ review:** start ≤0x7E53AEA9, not ≤0x7E53AEC5 |
| 02 §1.9 LENS_FIRM_UP item | 4 steps cmd 0/3/4/5, errors 0x6608/0x6601/0x6604/0x6605 | + cmd 5 → 0x7E530171 (check; match → cmd 6 0x1006 → 0x7E53023E; mismatch → cmd 4 again, 3×, 0x6609; 0x6606); 0x7E53023E: packet index vs count 0x604F9394 → cmd 4 again or cmd 1 0x1001 → 0x7E53030A (errors 0x6607, 0x6602) | `fwmap fn --dis`: 0x7E530103 next = 2119369073 (0x7E530171), cmd 5/4101, error 26117; 0x7E530171 calls 0x7E5303E1, match → next 2119369278 (0x7E53023E), cmd 6/4102; mismatch → next 2119368963 (0x7E530103), cmd 4/4100, count 0x604F9398, error 26121 (0x6609); else error 26118 (0x6606); 0x7E53023E compares the index with `movhu (0x604F9394)`, then next 0x7E53030A (2119369482) with cmd 1/4097, or 0x7E530103 with cmd 4/4100; error 26119 (0x6607); 0x7E53030A error 26114 (0x6602) |
| firmware-map regions rows 0x7E621020– and 0x7E6A1020– | EXP_MOVIE in the first row; second row "Movie (`mov*.c`) …" | exp runs to ~0x7E6A93E4, past the first row; the second row starts with the exp tail, HDMI from 0x7E6A93E5 | `fwmap range 0x7E6A8000–0x7E6AA900`: last `[exp]:` string user 0x7E6A8D7A; small getters 0x7E6A8DCF–0x7E6A91BA; 0x7E6A93E5 uses `[HDMI-DRV]error: [hdmi]get heap error`. **≠ review:** review says HDMI starts at 0x7E6AA7CB; the first HDMI-DRV function is 0x7E6A93E5 |
| 03 overview bullet EXP_MOVIE | "about 0x7E68F000–0x7E6A0000" | 0x7E68F0DD–~0x7E6A93E4 | as above |
| 12 §1 bullet | `exp` module 0x7E68F0DD–0x7E6A9400 | –~0x7E6A93E4 | as above (0x7E6A93E5 is HDMI-DRV) |
| 01 §6 SYSFMEM modes | "**[I]** whether these map one-to-one" | help-text modes are hex (V for STL_Read 0x400); 0x103 not in the list, so completeness still open | `fwmap fn 0x7E4505A6`: only caller 0x7E4520F3, `cmp 1024,d0`, then `call 0x7E451D85` (strings `\nSTL_READ\n`, `nVol`); string `data_read_error. unknown mode!!` used by 0x7E4505A6; Usr2 0x7E505005 calls 0x7E451306 with d1 = 259 (0x103) |
| 13f §1 table, new row 0x7E45B67F–0x7E45CE11 | (gap between `per_adc` and ADCONV) | "not placed; holds 0x7E45BB10, async request/start with callback at +32; 21 callers" | `fwmap fn 0x7E45BB10`: 21 caller fns incl. 0x7E50B356, 0x7E45CE5B, 0x7E458A47, 0x7E45E27F; 0x7E50B356 stores 2119218980 (0x7E50B724) at (32,a3) then calls 0x7E45BB10. The review's "I²C health check" label was not checked and is not used |

### 1.4 Review 2, side findings

| location | old | new | check done |
|---|---|---|---|
| 13c §7 item, OlyHfwOpeLevel | 0x7E9782AF–0x7E97858C | –≥0x7E9786CE | `fwmap range`: 0x7E97858C = `OlyHfwOpeLevel::reset` (71 B); 0x7E9785D3 `Ope::startLevel` (252 B, ends 0x7E9786CE) calls 0x7E68EC99; small getters follow |
| 13c §4, new bullet "Tool caveat, DB split" | — | ctor/isTypeOf merge in the DB, 55 of 1,022 TSV rows | `fwmap fn 0x7EA465CD --dis`: ctor `ret` at 0x7EA465E4, `isTypeOf` (`cmp 27207`) 0x7EA465E7–0x7EA465F2 inside the DB fn (size 40); scan of 13c-event-ids.tsv against functions.tsv: 57 isTypeOf not a DB start, 55 of them inside the ctor's DB fn. **≠ review:** the review's "probably ~1,268 pairs" (I) is 55 |
| modules.tsv play_apical.c | 7e93be70–7e93c39b | 7e93bc2f–7e93c68a | `fwmap range 0x7E93BB00–`: `play_apical_check_edit_enable` 0x7E93BC2F … `play_apical_edit_make_exif_prm` 0x7E93C68A; next 0x7E93C78B is `play_beauty_*` |

### 1.5 Review 3, imprecise items I1–I6 (and F044/F045)

| location | old | new | check done |
|---|---|---|---|
| 13c §3 class hierarchy (I1) | "Cmp_PlayComponentBase (10) / play-edit bases 0x7EB2BB81 → 0x7EB1DA86 (16) / play-single base 0x7EB54718 (7)" | one chain 0x7EB0A5E7 → 0x7EB54718 → Cmp_IndxBase 0x7EB2BB81 → 0x7EB1DA86 → 16; 0x7EB2BB81 also ← 0x7EB01903/0x7EB172B0/0x7EB2EFD4 | `fwmap fn`: 0x7EB54718 calls 0x7EB0A5E7; 0x7EB2BB81 calls 0x7EB54718 (callers 0x7EB01903, 0x7EB172B0, 0x7EB1DA86, 0x7EB2EFD4); 0x7EB1DA86 calls 0x7EB2BB81 (16 callers); `Cmp_IndxBase idx_get_page_info` used by 0x7EB2BE79 |
| modules.tsv CmpPEvV, Cmp_PlayIndexComponentBase, CmpPLgh (I2, F043–F045) | last_fn 7eb298ca; 7eb2cc08–7eb2d259; last_fn 7eb353ea | last_fn 7eb2b6c8; 7eb2bb81–7eb2e7ff; last_fn 7eb38d5d | `fwmap range`: PEvV copies of the play-base methods run 0x7EB298CA…0x7EB2B698, `rcv Request` 0x7EB2B6C8 (1,209 B, ends 0x7EB2BB80), then ctor 0x7EB2BB81; IndxBase copies to `rcv Request` 0x7EB2E7FF (1,233 B, ends 0x7EB2ECCF), then CmpPli getInstance 0x7EB2ECD0; PLgh `rcv Request` 0x7EB38D5D (1,209 B, ends 0x7EB39215), then 0x7EB39216 = 59-B getInstance (callee 0x7EBA62DB, caller 0x7EB97098, same shape as 0x7EB2ECD0) before `Cmp_PlayMovieArchitecture` 0x7EB392F2. **≠ review:** PLgh ends at 0x7EB39215, not ~0x7EB392F1 |
| 14c §1.1 table header (I2) | "File (modules.tsv first_fn)" (shows the old CmpEAsp 0x7EAB9261 etc.) | "first_fn before D2; D2 has since moved these rows" | modules.tsv now has 7eab8802 (CmpEAsp), 7eb7d14b (MfAssist), 7e9ee544 (CapDpc) |
| 13d §4.4 DPS states (I3) | "DPS GUI helpers 0x7EDCE9B9–0x7EDD07F9" | –≥0x7EDD08D2 | `fwmap fn 0x7EDD07F9`: 218 B (moveCurrent strings); next fn 0x7EDD08D3 |
| 14e §3.1 (I4) | DC layer 0x7ECFE7B8–0x7ECFEF32, no accessor outside | + getPixelFormat 0x7ED36FC3 outside the range | `fwmap fn 0x7ED36FC3 --dis`: `cmp 0,a0`, copies (661,a0) byte and (628/632/636,a0) words out; callers 0x7ED2347A, 0x7ED243EA, both also call 0x7ECFE8FD |
| 14c §2.2 step 6 (I5) | 12067/timeout only | + 3346 → exit, 0x7EA7D5FE, re-enter state 7 (0x7EA7E081 → 0x7EA7E089) | `fwmap fn 0x7EA7E0CA --dis`: `mov 3346,d0`, isTypeOf, vt+212 exit, `call 0x7EA7D5FE`, `call 0x7EA7E081` (→ 0x7EA7E089); CmpPRec copy 0x7EB4C4FB also loads 3346 |
| 13d §4.4 state 17 (I6) | "17 = image selection (all arrow, zoom and long-press keys)" | 17 is the only state with arrow OFF/long-press and EXPANSION keys; arrow ON handlers in 4, 6, 7, 9–21 | D1 handlers.tsv, SS_DPS: UP/DOWN_ON in 4, 10–18; LEFT_ON in 6, 7, 9, 11–21; RIGHT_ON in 9, 11–13, 16, 17, 19, 20; *_LONG_ON, *_OFF and EXPANSION only in 17; state 20 LEFT_ON → 0x7EDA19EC |

### 1.6 Review 4, other map defects

| location | old | new | check done |
|---|---|---|---|
| 08 §1.1 DPS_MAIN row | "DPS XML library at 0x7F061020–0x7F068F9C" | in overlay A, ends 0x7F0645C0; red-eye 0x7F0645C1–0x7F0691C5 follows | `fwmap range 0x7F064500–`: 0x7F064584 (61 B) then 0x7F0645C1, 0x7F0646A0 (red-eye driver); `cipa.jp/dps` users 0x7F060CE2, 0x7F062C74 |
| firmware-map regions row overlay A | — | + DPS calls overlay-B helpers, so it needs overlay B too (load order not traced) | calls.tsv: overlay-A callers of 0x7F0879CD 26, 0x7F087BE5 18, 0x7F087BD1 28, 0x7F087BF9 14 |
| firmware-map regions row 0x7F06B000–0x7F0AB000 | one row "ADJ / … SPC" | 0x7F06B000–0x7F07FFFF = 0xFF; overlay B = 0x7F080000–0x7F0EB800 | `fwmap fn 0x7E505005 --dis`: bit 1 path `mov 0xBF080000,a0`, `mov 0x80F1F000,a1`, d0 = 0x7F0EB800 − 0x7F080000 = 0x6B800, d1 = 0x103, call 0x7E451306; byte scan: 0x7F06B000–0x7F07FFFF 99–100 % 0xFF, data again from 0x7F080000, 0xFF from 0x7F0EC000; `C3D_BRG_CPU0P` at 0x7F0D8B78 |
| 14a §2.1 internal-block table and §4 item 2 | "Shader/uniform back end (70 functions)" | back end; shader/uniform role inferred and partial; holds GL state-block creator 0x7EE133B3 | `fwmap fn 0x7EE133B3 --dis`: `mov (0x606A33E8)`, `mov 160,a0`, `calls (a1)`, store to 0x606A33E4; callees 0x7EE147FF, 0x7EE22793 (texture-internal block), 0x7EE09BB5, 0x7EE2843C …; caller 0x7EE0EDA7 |
| 08 §4 heading and "Dual core" item | "C3D … on CPU1"; "C3D (and the movie encoder) run on CPU1" | struck; C3D, C3D_UPDATE, C3D_EXE_BRIDGE and two bridges on CPU0, only C3D_EXE and two bridges on CPU1; which side renders is open | `fwmap.py tasks`: cpu 0 rows 0x0071 C3D 7f0a3e60, 0x0077, 0x007e, 0x808b, 0x808c; cpu 1 rows 0x1002 C3D_EXE 7f09dfd4, 0x900d, 0x900e; 0x7F0A3F5A (← C3D task) posts with OlyQeWr to `movhu (0x7E43EE2C)`; 0x7F0A3E2D creates that queue with name `C3D_BRG_CPU0P` |

## 2. Not applied

1. Review 2 side finding 4 (new links: abort_sound → AUD_MAIN, HCI dispatcher and builders, startLevel → slope API). These are additions, not map errors; left to the D3 deep dives. (The startLevel link is mentioned in the OpeLevel fix.)
2. Review 1/2/3/4 "Weakest areas" lists: not defects.
3. 08 §1.1 heading "(region 0x7F061020–0x7F0A1020)" is also stale against overlay B 0x7F080000–0x7F0EB800, but it is not in a review list; left unchanged.
4. Seen while checking, not in any list: modules.tsv `play_beauty.c` first_fn 7e93c80d, but `play_beauty_check_edit_enable` is at 0x7E93C78B; and the regions table has no row for 0x7F0EB800–0x7F1A0FE0 (0xFF, then the Usr1 copy 0x7F100000–0x7F119000). Not changed.

## 3. Contradictions found (review against the bytes)

1. **exp/HDMI boundary** (review 1, F020): the review puts the HDMI start at 0x7E6AA7CB. The first `[HDMI-DRV]` function is 0x7E6A93E5, so exp ends at ~0x7E6A93E4; section 12's 0x7E6A9400 was 27 bytes too far.
2. **CmpPLgh end** (review 3, F045): the review gives ~0x7EB392F1. 0x7EB39216 is the next class's getInstance, so PLgh ends at 0x7EB39215.
3. **DB ctor/isTypeOf merges** (review 2, side finding 2): the review estimates ~1,268 pairs (I). The count is 55 of 1,022 TSV rows.
4. **SDET-reached functions** (review 1, F015): the review says both go through 0x7E673F91. They are 0x7E6671C3 and 0x7E673F91.
5. **BC start** (review 1, F005): the review gives ≤0x7E53AEC5. The BC init 0x7E53D90C calls 0x7E53AEA9, so the start is ≤0x7E53AEA9 (a refinement, not a reversal).
