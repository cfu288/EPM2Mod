# Debug Log

The camera writes what it does to a file on the card. Send the file with a bug report.

## Setup

Go to **MENU → Custom Menu → J**, press **DOWN** past Load Looks to **Debug Log**, select **On**, and press **OK**.

<img src="../images/ui/debug-log-list.png" width="320" alt="Debug Log with Off and On">
<img src="../images/ui/debug-log-on.png" width="320" alt="Debug Log reads On">

If the menu has no Custom Menu tab (gears icon), enable it in **Setup Menu → Menu Display**.

## Usage

With **On**, the camera adds to `EPM2LOG.BIN` in the top folder of the card each time you open a menu or playback, and
at power-off. To read the file on a computer: `uv run epm2mod log EPM2LOG.BIN --summary`
([the log format](../logging.md)).

## Limits

- **Off** is the default. With Off the camera writes no file and keeps no record after start-up.
- The file stops growing at 4 MiB. Delete it to go on.
- The row's texts are English in every menu language.
