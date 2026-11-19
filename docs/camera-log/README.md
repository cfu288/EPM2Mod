# Camera log

Every flash on real hardware gets a file here, `YYYY-MM-DD-BUILD.md`, with one row: what was flashed, the sha256, the lamp timings, and the result. Times are in UTC.

Body: Olympus PEN E-PM2. It was on body 1.6 and lens 1.1 before the first flash.

Each file holds one row of the table below, with these columns. Write the file before the flash (result: **Candidate, not flashed.**) and fill the result after it. `tools/freespace.py` and `epm2mod release` read every file of this folder.

| Date (UTC) | Build | sha256 | Result |
|---|---|---|---|
