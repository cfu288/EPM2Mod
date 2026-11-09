# Audit fix pass (2026-11-09)

Every changed text carries "(audit 2026-11-09)". Before each edit I re-checked the correction against block 0 (`fwmap.py fn/str/range/tasks`, `disasm.py`, raw reads). Line numbers are the current ones. The sampled 05 claims moved down by 2 lines after `sample.json` was made, so 05-13/17/158/228 are now at lines 15/19/160/230. Backup of the files before the pass: `/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad/auditfix/backup/`.

**Counts.**
- 23 sampled claims fixed: 22 MINOR and 1 UNCHECKABLE. There were 0 WRONG.
- 2 errors from outside the sample fixed.
- 9 btst/mask sweep findings corrected, on 10 lines. 2 of them (02-162 ZOOM, 06-92) are sampled claims; the other 7 (8 lines) are new.
- Checker verdicts rejected: **0**. Two corrections were narrowed (04-152, 05-17), and one has an extra detail (02-162). See the notes after the table.

**Count error in REPORT.md and check-1.md.** check-1.md says "CORRECT 6, MINOR 6", but its table has 5 CORRECT and 7 MINOR. 02-162 and 02-171 are both MINOR, so section 02 is 4/2, not 5/1. The REPORT table also gives section 04 as 2 correct / 4 minor; check-2 has 3/3 (04-105, 04-133 and 04-224 are correct). The real totals are **25 correct, 22 minor, 0 wrong, 1 uncheckable** (REPORT says 26/21/0/1). REPORT.md is outside the files I may edit, so I did not change it.

## 1. Sampled claims and outside-sample errors

| claim/location | old text (short) | new text (short) | evidence |
|---|---|---|---|
| 01-11 · 01-platform.md:11 | "A `:` line … sends the input on to U_SHELL" | A bare `:` line toggles pass-through. While it is on, non-`:` lines go to U_SHELL and `:cmd` still runs in S_SHELL | 7E44E9F3 `cmp 58`, then CR/LF/NUL test, 7E44EA05 `a2 = 1 − a2`. With a2 ≠ 0: a `:` line → 7E44E82F (local), any other line → 7E4375AA(mbf (7E43EE3C), 256). With a2 = 0: 7E44EA54 local |
| 01-31 · 01-platform.md:31 | "entries 0–24 are 0x8085…0x80E0" | 0x8085–0x808D, 0x8058, 0x80AE, 0x8001, 0x8007, 0x80C0–0x80C3, 0x80D9–0x80E0 (not one run) | u16 read at 0x7E43E948: 25 values as listed, then 1, 2, 3… |
| 01-104 · 01-platform.md:104 | `usr fast` command | `usr fast log` command | 7E5023E2 `cmp 3,d0`; strcmp with "fast" (7E732CC6) and "log" (7E732CCB); then print "UsrFastAppDebug!" and call 7E503AA8 |
| 01-186 · 01-platform.md:186 | into 0xBC620000 | into 0xBC61DF00 | 7F05DF86 `fc df 00 df 61 bc` = mov 0xBC61DF00,a3 → (20,sp); 16384 at 7F05DF8E. The bytes for 0xBC620000 (`00 00 62 bc`) occur nowhere in block 0 |
| 01-196 · 01-platform.md:196 | PER_CCD_TEMP_MAIN (0x2D …), table 0x7E4C4FF8 | ID 0x2E, table 0x7E4C4DF8 | Raw record 0x7E4392B8 = {0x2e, 0, 0, 0x7e45dbb5, 0xb, 0x200, 0}. `fwmap tasks` gives 0x2D = PC_XXX. 7E45DCE5 `add 0x7E4C4DF8,a0`, index state·3 + event |
| 02-162 · 02-lens…:162 | "all … → reply" | adds: LENS_FOCUS_LIMIT does not reply | 7E532218 loop: OlyQeRd((7E43ED24)) → 7E532240 → `bra`. No OlyQeWr. The handler's helper 7E53232C posts cmd 258/259 to the shared queue (7E43ED8C) through 7E50689F (Oimf qwrite). That is a notice, not a reply to the sender |
| 02-162 · 02-lens…:162 (ZOOM) | "waits event bit 2" | mask 0x02 = bit 1, `btst 2` | 7E538DCD `f8 ec 02` btst 2,d0 |
| 02-171 · 02-lens…:171 | `src` 1=AC 2=BAT | `get_src`/`set_src` ("1=AC, 2=BAT") | Strings 7E743BE1 get_src, 7E743BE9 set_src, 7E743BF4 "1=AC, 2=BAT\n", used by 7E539672. There is no plain `src` command |
| 03-92 · 03-camera…:92 | 0x7E656B1D–0x7E656F6F | 0x7E656B1D–~0x7E65DA2A | "cam_still_func.c" (7E7BE2B6) is used by functions up to 7E65D5E7. The reporter 7E65D9A6 (133 B) ends at 7E65DA2A, and 7E65DA2B (live bulb) follows |
| 03-98 · 03-camera…:98 | filter 0x7E656D64 / 0x7E65DA2B; else "NOT SUPPORT" | dispatchers 0x7E656EEB / 0x7E65DC34. Other commands get error 0x3C11. 0x7E656D64/0x7E65DA2B are name lookups | 7E656D64: cmp 7/80 → string → strcpy 7E500DE9, ret. 7E656F06 `cmp 7`, 7E656F48 `cmp 80`, else 7E656F56 `mov 15377`. 7E65DC4F `cmp 7`, else 7E65DC95 `mov 15377` |
| 03-281 · 03-camera…:281 | `art_frame_*` 0x7E721294… | 0x7E7209BD–0x7E721619 | `fwmap range`: 7E7209BD art_frame_get_jpeg_revision (ART_FRAME_MOVIE_SD) … 7E721294 get_res_ID … 7E721619 art_frame_free |
| 04-71 · 04-movie.md:71 | "adds 600 to (552) each second … **Verified.**" | Runs only when 0x605B1FA2 == 1. Mode 106 sets (552) = (96)/fps × 600. "Each second" is now **inferred** | 7E6EDFAA–B5 `movbu (605b1fa2)`, `cmp 1`, bne ret. 7E6EDFBF `cmp 106` → divu, `udfu01 600`, store (552). Else 7E6EDFDD `add 600`. 7E6EDFF5 0x04070100 |
| 04-139 · 04-movie.md:139 | 0x7E6EF3D6 / 5E7 / 7F7 (merged states) | idle 3D3, aud_wait 3ED, first_frame 507, record_normal 5E2, userstop 7F2, userstop_for_edit 89E, finish_1 958, do_nothing 9A7, finish_2 9BD, errorstop A79, fullstop A99 | Each new address occurs as an LE32 immediate (e.g. 7E6EF5BB → 5E2, 7E6EF36F → 89E). The old 3D6/5E7/7F7 occur nowhere. `movm` prologues at 5E2/7F2/89E |
| 04-152 · 04-movie.md:152 | "art effects … applied to the first frame" (under Verified) | Strings verified. Branch tests listed. Meaning relabelled **inferred**; "1st" is more likely a first pass | 7E6C6A8D `movbu (a07507cc)`, `cmp 73`/`cmp 82` → "toyphoto". 7E6C6AA7 `mov (605b0394)`, `cmp 0` → "filter", else "simple & Frame". `SIMPLE_1ST` string at 7E7FE711 (fn 7E6CCBE1) |
| 05-13 · 05-playback…:15 | 0x7E8F904F–0x7E8F926E | 0x7E8F9031–0x7E8F926E (init 0x7E8F9031, task entry 0x7E8F904F) | 7E8F9031 clears 8 words at 0x605C22F8 and the byte 0x605C2318. Its caller is 7E504AF9 |
| 05-17 · 05-playback…:19 | 0x7E91D000–0x7E937FFF | ~0x7E91D279–~0x7E937CDD, with Olympus code at both edges and inside | 7E91CD59 (iAP, 1312 B) ends at 7E91D278. 7E937CDE is called by obex_acpl 7E93902C/7E93915B. 7E923B0F uses BT_CliCallback/`OLYMPUS BlueSDK a4`; 7E923C93 uses OLYMPUS_TST_OBJ |
| 05-158 · 05-playback…:160 | "plays HOGE.WAV, records, or changes the volume" | plays HOGE.WAV at volume work_info (action 2; > 10 → logged and clamped to 10), or records at 48 kHz (action 3); no volume action | 7E9503AA–B8 `cmp 2/3/1/16`. 7E9503BF `cmp 10` → logs 7EBBFC49/7EBBFC62, `mov 10,a2` → 7E95040A. 7E9502D8 sleep 10000, 7E950360 `udf00 1000` |
| 05-228 · 05-playback…:230 | "calls 27 functions" | 28 command functions: 27 Write_RAM chunks + Launch_RAM 0x7E912680 | `fwmap fn 7E9126CC --dis`: 28 distinct chunk callees (7E904B2E … 7E911EFD, 7E912680), each followed by 7E912CEE |
| 06-92 · 06-app…:92 | "bit 14 of the interval state" | mask 0x0E (bits 1–3; `btst 14`) of 0x602B0CDC, plus a RecView/recording check (0x7E969A6A) | 7E969C5B `f8 ec 0e`. 7E969C45 call 7E969A6A, `cmp 1` → "…false for RecView or Recording" (7EBCE36D). 7E96998B returns (602B0CDC) |
| 07-272 · 07-gui…:272 | 0x7EDA6D93 | 0x7EDA9D03 (F/W string loaded at 0x7EDAA63F) | 7EDA6D93 only uses "SsMenuLv_StartAnimation FAIL". "F/W Version up start" 7EFD43F2 is used by fn 7EDA9D03. 7EDAA626 `cmp 43` → 7EDC5C47(11, 12) → 7EDAA63F |
| 07-275 · 07-gui…:275 | "normal Custom Menu J item" (in a verified row) | Strings verified. The Custom Menu J placement is labelled **inferred** (A–J item lists not decoded) | Checker 4: string id 207 appears only in the generic label builder 7ED4CEE0, and no item list exists under J (175). I found nothing that contradicts this |
| 08-17 · 08-conn…:17 | ops 0x9117 and 0x9119–0x9125 | 0x9117, 0x9119, 0x911C, 0x9120–0x9125 (0x911A/B, 0x911D–F not registered) | Builders 7F089754 and 7F089BFA load 0x911C, 9121, 9122, 9123, 9117, 9120, 9119, 9124, 9125. No `mov` of 0x911A/B/D/E/F exists anywhere in functions.txt |
| 08-59 · 08-conn…:59 | TEST_PACKET at 0x7F0D7C61 | at 0x7F0D7C58; the last byte is E7, where the spec has 7E | 7F09BE10 `mov 53,d1; mov 0x7F0D7C58,a0`. Bytes: 00×9, AA×8, EE×8, FE, FF×11, 7F BF DF EF F7 FB FD FC 7E BF DF EF F7 FB FD **E7** |
| REPORT (outside) · 01-platform.md:33 | records follow from 0x1C488 | from 0x1C490 (first id 0x9004) | Block words: 0x1C480 = 0xA07678D0, 0x1C484–0x1C48F = 0, 0x1C490 = {0x9004, 0, 0, 0x7E506659, 0xC, 0x800, …}. The 0x1001 record is at 0x1C5E0 = 0x1C490 + 12·28 |
| REPORT (outside) · 07-gui…:262 | Warnings "in 0x7EDA6D93 (shared with the Version screen)" | in 0x7EDB0847 (`[GUI Warning]`) and 0x7EDC25D4 (`Warning_Viewer`) | `fwmap str`: 7EFD4990 `[GUI Warning]:…` → 7EDB0847. 7EFDA2BC/7EFDA2E8 `Warning_Viewer::Update…` → 7EDC25D4. "Shared with the Version screen" came from the wrong address, so I removed it |

**Corrections narrowed or extended. None of these reverses a checker verdict.**
- **04-152.** The checker calls 73 and 82 "the Pin Hole filter codes". Section 09 confirms 73 as a Pin Hole effect code (73/106/108). Nothing in sections 01–10 identifies 82. The fix says "82 is not identified".
- **05-17.** The checker gives the start as "0x7E91D279/0x7E91D29F". I used "~0x7E91D279", the first byte after the iAP function. Both bounds are marked approximate.
- **02-162.** I added that LENS_FOCUS_LIMIT's handler does post messages (cmd 258/259 to queue 0x7E43ED8C). That queue is shared by many lens functions, so the post is not a reply. Only "does not reply" went into the section text.
- **01-47** (CORRECT, not edited). The checker cites the raw record at 0x7E43D5F8. The record actually starts at 0x7E43D600 (block 0x1C5E0); 0x7E43D5F8 is 8 bytes before it. The verdict stands.

**Same errors repeated elsewhere. Not edited, because the brief limits the fix to the cited lines.**
- docs/firmware-map.md:140 and sections/10e-connectivity.md:197 both repeat the 08-17 range "0x9119–0x9125".

## 2. btst / mask sweep

On MN103, `btst imm,Dn`, `btst imm,(abs)`, `bset imm,(abs)` and `bclr imm,(abs)` all take imm as a **mask**. I searched sections 01–10f (including 09, 09a and 09b) and docs/firmware-map.md for every "bit"/"bits"/"bitN" claim (80 lines). For each claim derived from code, I read the instruction at the cited address. Claims that come from help strings or data tables are listed at the end.

**Corrected: the operand was read as a bit number (9 findings, 10 lines).**

| location | instruction | old | new |
|---|---|---|---|
| 02-lens…:162 (ZOOM, claim 02-162) | 7E538DCD `btst 2,d0` | event bit 2 | mask 0x02 = bit 1 |
| 06-app…:92 (claim 06-92) | 7E969C5B `btst 14,d0` (`f8 ec 0e`) | bit 14 | mask 0x0E = bits 1–3 |
| 01-platform.md:165 | 7F084358 `btst 2,d0` on (8,a2) | "system" flag bit 2 | bit 1 (mask 0x02). Now agrees with 10f:74 "(8,a2) & 2" |
| 05-playback…:224 | 7E923FDB `btst 1,d0` / 7E923FE7 `btst 2,d0` on (602AEE98) | bit 1 → 7E923B0F; bit 2 → stub | bit 0 → 7E923B0F; bit 1 → stub (7E923723 = `retf`) |
| 10d-playback.md:118 | 7E679911 `btst 1,d1` | tests bit 1 | tests bit 0 (mask 0x01) |
| 04-movie.md:197 | 7E6DD115/11E/127 `bset 1/2/4,(602adfb8)` (imm bytes 01/02/04) | sets bit 1/2/4 | sets mask 0x01/0x02/0x04 = bits 0/1/2 |
| 03-camera…:310 | 7E6B3AEA/7E6B3AFC `mov 16,d1` → set-flag 7E449083/7E449030 | sets bit 16 | sets pattern 0x10 = bit 4 |
| 02-lens…:150 | 7E880D12 `cmp d3(=1)`, 7E880D20 `cmp 2`, 7E880D71 `cmp 4`, 7E880DBB `cmp 8` on the flag pattern | bit1/bit2/bit4/bit8 | pattern 0x1/0x2/0x4/0x8 (bits 0–3; exact compares) |
| 10b-shooting-modes.md:92 and :176 | 7E5226EA `or 64,d2` | "Bit 64" / "lens status bit 64" | bit 0x40 (bit 6). The neighbouring "0x604F67AC bit 0x200000" is correct (`btst 2097152` = mask 0x200000) |

The last four rows are not `btst`, but they make the same mistake: a mask value written as a bit number. The 02:150 and 10b rows are wording fixes, since the values were right but read as bit numbers.

**Checked and found correct (code-derived).**
- 01:9 and docs/firmware-map.md:14. CPU in bits 12–14: 7E430792 `and 28672` (0x7000), `asr 12`. Index: 7E43074F `and 4095`.
- 01:33. IDs with bit 12 set: the record ids 0x9004… are data values (0x1000 set).
- 01:54. OlyTaSt `id & 0x1000`: 7E449543 `mov 4096,d0; and d0,d1`.
- 01:71, 84, 85, 251, 260 and 10f:16, 18, 91, 98. Usr2 bits 0, 1 and 24: 7E505020 `btst 1`, 7E50509F `btst 2`, 7E50511E `mov 16777216` + `and`.
- 01:89–100. USR_FAST_APP table 0x01…0x80: 7E50216D–7E50227F `btst 1/2/4/8/16/32/128/64`, which match the hex masks.
- 01:201. UI_IN bit 0x01 / 0x02: 7E509024 `btst 1`, 7E509045 `btst 2`.
- 03:232. ctx+84 bit 28: 7E7223DF `mov 268435456` (0x10000000) + `and`.
- 05:156. AUD_BRIDGE_LITE bits 0–3, 4–7 and 8–11: 7E94DCA7 `and 15`, 7E94DCBA `and 240`, 7E94DCCB `and 3840`.
- 05:158. AUD_COPY_DATA masks 0x30 / 0x03: `btst 48` / `btst 3` (claim 05-156, checked CORRECT).
- 05:271. SERV flag bits 0x01 / 0x10: written as masks (wait pattern 0x11).
- 05:283. EFFECT_EXE 0x8…0x200, with 0x100/0x200 split by flags at 0x605C22D8: 7E8F6A8D–AD `cmp`, 7E8F6AEF `btst 2,(605c22d8)`, 7E8F6B08 `btst 8,(605c22d8)`. The text gives no bit numbers for these.
- 07:36–42. `tag&7` / `tag&8`: 7E457DE1 `btst 8`, 7E457DE6 `and 7`.
- 10b:92. 0x604F67AC bit 0x200000: 7E5226E1 `btst 2097152`.
- 10c:166. "with bit 0 set": 7E6CC042 `and 1,d3` on the d0 argument. The record-path callers pass d0 = 1 (e.g. 7E6EDDE6, 7E6EF13A, 7E6F0BAC).
- 10e:45–64, 208, 10:56, 111 and docs/firmware-map.md:145. edev bit *i* / "Cube" bit 4: 7E50BC87–8D `mov 1,d0; asl d2,d0; or`, a real bit index (1 << i).
- 10f:74. "(8,a2) & 2": 7F084358 `btst 2`.

**Not code-derived (help strings or data tables), so not affected.** 01:163 and 07:81 (`psave/pload <bit0 …>` help), 03:58 (factor table in hex), 03:101/103 and 10a:143 (`cam still` help: "bit1 : fpn" 7E7AC789, "bit3 : antishock" 7E7AC74C), 02:104 (found-mask values in hex), and the bit widths/bitrates in 02, 04, 05, 07, 08 and 09a.

**docs/firmware-map.md.** It has no "bit" claim that reads a btst/and operand as a bit number. Lines 14 and 145 are correct (see above). Line 169, `(id & 0x7FFF) − 1`, is a mask formula, not a bit claim, and matches `tools/fwmap.py`. No edits were made to this file.

**Sweep totals.**
- Found: 25 code-derived bit-claim groups checked (9 corrected + 16 correct, as listed above).
- Corrected: 9 findings on 10 lines. 5 are `btst`; 4 are bset/set_flg/cmp/or wording of the same kind.
- Found correct: 16 groups.
