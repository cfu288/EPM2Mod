"""Generator of the film-look patch specs.

The looks are data: ``data/films/films.json`` says which film goes in which
art-filter menu entry, and ``data/films/fits/*.npz`` holds the fitted values of each
film. This package turns that data into the three patch specs that the
firmware builds use.

Modules:
    slots: where each menu entry keeps its numbers in the firmware.
    films: the film list.
    generate: the patch specs. It needs numpy (``pip install epm2mod[looks]``).
    extra, mono: the specs of the film lists beyond the first seven.
    lookfile: the look file that the camera loads from the SD card
        (``docs/reference/look-file-format.md``). It does not need numpy.
    records: the film records that look files are packed from. It does not
        need numpy.
    lookpack: look records made from the fit files. It needs numpy.
"""
