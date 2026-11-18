EPM2Mod: unofficial firmware for the Olympus PEN E-PM2
=====================================================

Start
  Mac:      double-click "Start (Mac).command".
            The first time, macOS blocks it. Open System Settings -> Privacy & Security,
            scroll down, select Open Anyway next to "Start (Mac).command", then Open.
  Windows:  double-click "Start (Windows).bat".
            If Windows protects your PC: More info, then Run anyway.
  Linux:    run ./start.sh in a terminal.

A page opens in your browser. It makes the firmware, adds film looks if you choose them,
and writes the files to your SD card or gives you a zip. Keep the window that opened with
it while you use the page; close that window to stop.

The first start downloads uv (a Python launcher) and Python 3.12 into the folder .uv here.
Each start downloads Olympus's firmware from OM Digital Solutions if it is not here yet.

Remove: delete this folder.

Project, help and how to go back to Olympus's firmware: https://github.com/cfu288/EPM2Mod
