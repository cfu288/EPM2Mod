"""Generator of the film-look patch specs.

The looks are data: ``looks/films.json`` says which film goes in which
art-filter menu entry, and ``looks/fits/*.npz`` holds the fitted values of each
film. This package turns that data into the three patch specs that the
firmware builds use. It needs numpy (``pip install epm2mod[looks]``).

Modules:
    slots: where each menu entry keeps its numbers in the firmware.
    films: the film list.
    generate: the patch specs.
"""
