# Camera test sheet: artbkt (2026-11-26)

One flash for every item that only the camera can show (`plan.md` sections 1.3 and 2.1, `NOTES.md` section 3):
n = 0, 1, 3 and 12 with a Picture Mode row; Busy and its keys; a card that fills up; power-off during Busy; a
RAW+JPEG source; a RAW shot in ART mode; Dramatic Tone, Key Line and Watercolor; each JPEG's film name; and that
nothing else changed. The Debug Log is On for the whole test.

Build `data/builds/artbkt.json` (the pinned film-tables-fix with ART BKT, label 2026.11.29), sha256
`dc1e31898fb0bc0a75c8a54d40a3cd25aa751dc104e1eeee0752ea7ce1afddd0`. On this host: `build/artbkt.BIN`, and the look pack
`build/artbkt-card/EPM2LOOK.BIN` (sha256 `7b82124e415f624ecda0396aa8b8c1589bcdc9cfdf0c1be56cc937da5c25e451`:
ART 1 Portra 400, ART 2 Velvia, ART 5 Double-X, Olympus's filters in the other entries). Menu paths: the camera
manual (p. 28, 39, 61-63, 65, 100) and the emulator's screens of this build.

## Card (on the Mac, card in, mounted at /Volumes/Untitled)

1. Empty the photo folder and the log, then copy the test RAW and the look pack:

   ```
   rm -f /Volumes/Untitled/DCIM/100OLYMP/* /Volumes/Untitled/EPM2LOG.BIN
   mkdir -p /Volumes/Untitled/DCIM/100OLYMP
   scp USER@HOST:/path/to/epm2-tools/experiments/2026-11-09-film-portra/testraw/PB130001.ORF /Volumes/Untitled/DCIM/100OLYMP/PB130001.ORF
   scp USER@HOST:/path/to/epm2-tools/build/artbkt-card/EPM2LOOK.BIN /Volumes/Untitled/EPM2LOOK.BIN
   ```

2. Flash (the command ejects the card):

   ```
   epm2flash artbkt dc1e31898fb0bc0a75c8a54d40a3cd25aa751dc104e1eeee0752ea7ce1afddd0
   ```

   Go back:

   ```
   epm2flash film-tables-fix e029facb38569880c0cec4c16b0f295ca2a96214ed75900fe00585f6b0cedd28
   ```

3. Card in the camera, camera off. Hold **OK** and **ON/OFF** together; let go when the orange lamp lights. Wait
   for it to blink, then switch off and on.

## Set-up on the camera

4. MENU → RIGHT to **SETUP** → OK. In the tab column (left), UP or DOWN to the tab whose title reads **Setup Menu**
   → RIGHT → UP or DOWN to **Firmware** → RIGHT. Body reads **1.6  EPM2Mod 2026.11.29**. MENU until the live view
   shows.
5. MENU → RIGHT to **SETUP** → OK. Tab **Custom Menu** → RIGHT → UP or DOWN to **J** → RIGHT → **Debug Log** →
   RIGHT → **On** → OK. MENU until the live view shows.
6. MENU → RIGHT to **SETUP** → OK. Tab **Custom Menu** → RIGHT → **J** → RIGHT → **Load Looks** → RIGHT → **Load**
   → OK. The row reads **Loaded**. MENU until the live view shows.
7. P mode: MENU, LEFT or RIGHT to **P** (the text reads "Sets the Aperture and Shutter Speed Automatically"), OK.
   Press OK (live control); UP or DOWN to the Picture Mode item; LEFT or RIGHT to **Natural** (the text reads
   Natural); OK. In the same way set the image quality item to **LN**.

**Rows** (used in each part): MENU → RIGHT to **SETUP** → OK. Tab **Shooting Menu 2** → RIGHT → DOWN to
**Bracketing** → RIGHT. Screen **Bracketing**: DOWN to **ART BKT** → RIGHT → DOWN to **On** (do not press OK) →
RIGHT. Screen **ART BKT**: 19 rows, Portra 400 … Watercolor, then i-Enhance, Vivid, Natural, Muted, Portrait,
Monotone, Custom; each reads On or Off. To change a row: RIGHT, UP to **Off** or DOWN to **On**, OK. To leave: MENU
(the Off / On panel of Bracketing stays open), MENU (the panel closes; ART BKT reads `--`), MENU until the live view
shows.

**Run** (used in each part): ▶. LEFT or RIGHT to the RAW the part names. OK → menu **RAW** (for a RAW+JPEG pair:
**RAW/JPEG**) → **RAW Data Edit** → OK → screen **RAW Data Edit**: Current, Custom1, Custom2, ART BKT, No → DOWN to
**ART BKT** → OK → the preview with **Yes** / **No** → **Yes** → OK → **Busy** → **Reset** / **No** → **No** → OK.

**PM check** (after each part): press the shutter button halfway, then OK; UP or DOWN to the Picture Mode item; the
text reads **Natural**. Press the shutter button halfway to leave.

## Part 1: 12 entries (n = 12, film names, time)

8. Rows: 1-12 **On**, 13-19 **Off**. Rows 1, 2 and 5 read Portra 400, Velvia, Double-X. Leave as written; Bracketing
   shows ART BKT `--`.
9. Run on **PB130001**. Note the seconds from Yes to Reset / No. Press nothing during Busy. PM check.

## Part 2: n = 3 with a Picture Mode row, keys during Busy

10. Rows: only **Velvia** (row 2), **Pin Hole** (row 6) and **Monotone** (row 18) On.
11. Run on **PB130001**; during Busy press MENU once, then ▶ once. Note what each did. PM check.

## Part 3: n = 1 with Reset, and n = 0

12. Rows: only **Watercolor** (row 12) On.
13. Run on **PB130001**, but at **Reset** / **No** choose **Reset** → OK: the RAW Data Edit list shows again
    (5 rows). MENU, MENU to playback. PM check.
14. Rows: every row **Off**. Run on **PB130001**. Note whether one JPEG is made. PM check.

## Part 4: a RAW+JPEG shot in ART mode, Dramatic Tone, Key Line, Watercolor

15. MENU, LEFT to **ART**, OK. In the art filter menu choose **10 Dramatic Tone**, OK. Live control: image quality
    **LF+RAW**. Shoot a coloured scene (shot D). Keep the camera still for shots D, K and W.
16. Press OK: the art filter menu shows (manual p. 28). Choose **11 Key Line**, OK. Shoot (shot K).
17. Press OK; choose **12 Watercolor**, OK. Shoot (shot W).
18. MENU, RIGHT to **P**, OK. Picture Mode **Natural**, image quality **LN** (step 7).
19. Rows: only **Dramatic Tone** (row 10), **Key Line** (row 11), **Watercolor** (row 12) On.
20. Run on shot W's RAW: the menu title reads **RAW/JPEG** and lists RAW Data Edit and JPEG Edit. PM check.

## Part 5: RAW Data Edit → Current and Custom1 of a RAW shot in a film simulation

21. Live control: Picture Mode **ART 1** (the text reads Portra 400), image quality **LF+RAW**. Shoot (shot F).
22. Picture Mode **Natural**, image quality **LN** (step 7).
23. ▶, shot F. OK → **RAW Data Edit** → OK → **Current** → OK → **Yes** → OK → **No** → OK.
24. ▶, shot F. OK → **RAW Data Edit** → OK → **Custom1** → OK. If a settings screen shows, press OK. **Yes** → OK →
    **No** → OK.

## Part 6: power-off during Busy

25. Rows: 1-12 **On**. Run on **PB130001**, and about 8 seconds after Yes (the third JPEG) switch the camera off.
26. Switch on. PM check: note the Picture Mode. ▶: note the last JPEG; it must open.

## Part 7: a card that fills up, and the rest of the camera

27. MENU, switch off, card out. On the Mac, card in:

    ```
    df -m /Volumes/Untitled
    ```

    N = the Available number minus 20. Then, with that number in place of N:

    ```
    dd if=/dev/zero of=/Volumes/Untitled/FILLER.BIN bs=1048576 count=N
    diskutil eject /Volumes/Untitled
    ```

28. Card in the camera, switch on. Rows: 1-12 **On** (as left by part 6). Run on **PB130001**. Note the message and
    when it shows. PM check.
29. Focus peaking: live control, the AF mode item → **MF**; turn the focus ring: the peaking lines show. AF mode back
    to **S-AF**. Shoot one JPEG in P (shot P).
30. MENU, switch off, card out. On the Mac, card in:

    ```
    rm /Volumes/Untitled/FILLER.BIN
    ssh USER@HOST mkdir -p /path/to/epm2-tools/build/fw-test/artbkt-prod
    scp -r /Volumes/Untitled/DCIM/100OLYMP /Volumes/Untitled/EPM2LOG.BIN USER@HOST:/path/to/epm2-tools/build/fw-test/artbkt-prod/
    diskutil eject /Volumes/Untitled
    ```

On this host (the agent runs these):
`exiftool -FileName -DateTimeOriginal -ArtFilter -PictureMode -ImageDescription build/fw-test/artbkt-prod/100OLYMP/*`
and `uv run epm2mod log build/fw-test/artbkt-prod/EPM2LOG.BIN --json > build/fw-test/artbkt-prod/log.json`.

## Expected, and what other results mean

| Part | Expected | Other results |
|---|---|---|
| 4-7 | Firmware 1.6  EPM2Mod 2026.11.29; Debug Log On; Loaded | Another label = another build on the camera: flash again |
| 1 | 13 JPEGs in this order: Natural, Portra 400, Velvia, Pale&Light Color, Light Tone, Double-X, Pin Hole, Diorama, Cross Process, Gentle Sepia, Dramatic Tone, Key Line, Watercolor; each looks like its film simulation or filter; about 35 s; Picture Mode Natural after | 4 rows in the list = old firmware. 1 JPEG = the loop did not go on. The same look in all = the Picture Mode does not reach the development. Another Picture Mode after = the restore failed. A freeze or restart: note the frame; the Debug Log has the last event |
| 2 | 4 JPEGs: Natural, Velvia, Pin Hole, Monotone. MENU and ▶ during Busy do nothing | A key that stops the run or freezes the camera: note it (the guide states it) |
| 3 | n = 1: 2 JPEGs (Natural, Watercolor); Reset shows the 5-row list. n = 0: 1 JPEG (Natural) | n = 0 with no JPEG and the list staying also passes; the guide states what happened |
| 4 | Shots D, K, W: an ORF and a JPEG each. The menu reads RAW/JPEG with both edits. 4 JPEGs from W's RAW: Natural, Dramatic Tone, Key Line, Watercolor; each filter frame looks like shot D, K or W's JPEG | A filter frame with Natural's look = the filter does not act in RAW Data Edit: blocking (A4). A different look from the capture: note it for the guide |
| 5 | Current: 1 JPEG with Natural's look, ImageDescription OLYMPUS DIGITAL CAMERA. Custom1: 1 JPEG, ImageDescription Portra 400 (the RAW's text, as stock) | Portra 400 on the Current JPEG = the fix does not act on the camera |
| 6 | After the restart: Picture Mode Natural; the last JPEG opens | Another Picture Mode (the frame's entry) = the run needs a restore at start: a fix and a second flash |
| 7 | Fewer than 13 new JPEGs, the Card Full message (manual p. 100: "The card is full"), Picture Mode Natural, the camera works on; the peaking lines show; shot P is a normal JPEG | A freeze or a JPEG that does not open = blocking |
| EXIF | ArtFilter: the filter's name on Olympus frames, Off on Natural and film frames. ImageDescription: OLYMPUS DIGITAL CAMERA on Natural and Olympus frames, the film's name (Portra 400, Velvia, Double-X) on film frames | The RAW's text (OLYMPUS DIGITAL CAMERA) on a film frame = the fix does not act |
| Log | One work-buffer switch per frame; the record times give the time per JPEG (about 2.7 s) | |
