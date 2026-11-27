# Spot Metering

Spot metering reads the light where you focus, so a subject away from the center of the frame is exposed correctly
without recomposing.

## Setup

Go to **MENU → SETUP → Custom Menu → E. Exp/▣/ISO → Spot Metering**, press **RIGHT**, select **Spot**,
**Spot Hilight** or **Spot Shadow** with **UP/DOWN**, press **RIGHT**, choose **On**, and press **OK**.

<img src="../images/ui/spot-metering-row.png" width="320" alt="Custom Menu E with the Spot Metering row">
<img src="../images/ui/spot-metering-page.png" width="320" alt="The Spot Metering page with Spot, Spot Hilight and Spot Shadow">
<img src="../images/ui/spot-metering-list.png" width="320" alt="The Off and On choices of the Spot row">

If the menu has no Custom Menu tab (gears icon), enable it in **MENU → SETUP → Setup Menu (wrench tab) → Menu Display**.

## Usage

1. Set the metering mode: press **OK**, then in the right column choose the metering item and select **Spot**,
   **Spot Hilight** or **Spot Shadow**. Its row on the Spot Metering page must be **On**.
2. Choose where to meter:
   - **Tap the subject** on the screen: the spot moves to the point you tap.
   - Or press **LEFT** and move a single AF target with the arrow keys: the spot moves with the target.

A mode whose row is **Off** (the default) meters at the center of the frame.

## Limits

- In **All Targets** with no point tapped, the camera meters at the center of the frame.
- Faces are ignored: with **Face Priority** on, the camera meters at the AF point, not at the face.
- The row is grayed out in **iAUTO**.
- The **Spot Metering** row's name is English in every menu language.

For implementation details, see the [notes](../../experiments/2026-11-24-af-spot-metering/NOTES.md).
