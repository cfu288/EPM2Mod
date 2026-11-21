"""The film simulations as data: the look file for the SD card and what it is packed from.

Modules:
    slots: where each menu entry keeps its numbers in the firmware.
    lookfile: the look file that the camera loads from the SD card
        (its format has its own document). It does not need numpy.
    records: the film records that look files are packed from. It does not
        need numpy.
    lookpack: look records made from the fit files. It needs numpy
        (``pip install epm2mod[looks]``).
"""
