# ART BKT in RAW Data Edit

ART BKT in RAW Data Edit develops one RAW photo in each film simulation you choose, in the camera, so you can compare
them side by side without a computer.

## Setup

Choose the film simulations once. Go to **MENU → SETUP → Shooting Menu 2 → Bracketing → ART BKT**, press **RIGHT**,
highlight **On** without pressing **OK**, and press **RIGHT** again.

<img src="../images/ui/art-bkt-bracketing.png" width="320" alt="The Bracketing screen with On highlighted for ART BKT">

The **ART BKT** screen lists the 12 ART entries under the names of your film simulations, then the Picture Modes. For
each row you want, press **RIGHT**, choose **On** or **Off**, and press **OK**. Press **MENU** to leave.

<img src="../images/ui/art-bkt-rows.png" width="320" alt="The ART BKT screen with Portra 400 and Velvia set to On">

## Usage

1. Set the Picture Mode you want as the reference, for example Natural.
2. Press the playback button, show a RAW photo, and press **OK**. Select **RAW Data Edit**, press **OK**, select
   **ART BKT**, and press **OK**.

   <img src="../images/ui/art-bkt-raw-edit.png" width="320" alt="RAW Data Edit with Current, Custom1, Custom2, ART BKT and No">
3. Select **Yes** and press **OK**. Wait until the camera asks **Reset** or **No**.
4. Select **No** and press **OK** to go back to playback.

You get one JPEG in the current Picture Mode, then one for each row that is On, in the order of the ART BKT screen.
Each JPEG records the name of its film simulation in its Image Description, so a photo viewer shows which is which.

## Limits

- A row set to the Olympus art filter Dramatic Tone, Key Line or Watercolor gives a JPEG with Natural's brightness and
  colors.

For implementation details, see the [notes](../../experiments/2026-11-24-artbkt-production/NOTES.md).
