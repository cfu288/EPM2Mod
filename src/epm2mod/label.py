"""The build label on the camera's Firmware screen: "Body : 1.6  EPM2Mod 2026.11.19".

A build description with a ``label`` (``YYYY.MM.DD``) lists the project's label spec (``RepoPaths.label_spec``). That
spec holds the screen's edits and its text with the placeholder date
``0000.00.00``; ``with_label`` returns it with the label written in place. The
text has a fixed length, so the free-space check of the committed spec covers
every label, and the same label always gives the same bytes.
"""

from __future__ import annotations

import datetime
import re
from dataclasses import replace

from .errors import BuildError
from .spec import BytesOp, PatchSpec

#: The date in the committed spec's text that the label replaces.
PLACEHOLDER = "0000.00.00"

_LABEL = re.compile(r"\d{4}\.\d{2}\.\d{2}")


def check_label(label: object, where: str) -> str:
    """Return ``label`` if it is a real date written ``YYYY.MM.DD``.

    Raises:
        BuildError: if it is not.
    """
    if not isinstance(label, str) or not _LABEL.fullmatch(label):
        raise BuildError(f"{where}: 'label' must be a date written YYYY.MM.DD")
    try:
        datetime.date.fromisoformat(label.replace(".", "-"))
    except ValueError:
        raise BuildError(f"{where}: 'label' {label} is not a real date") from None
    return label


def with_label(spec: PatchSpec, label: str) -> PatchSpec:
    """Return the label spec with ``label`` written over the placeholder.

    Raises:
        BuildError: if the label is malformed, or the spec does not hold the
            placeholder exactly once.
    """
    check_label(label, spec.name)
    old, new = PLACEHOLDER.encode("utf-16-le"), label.encode("utf-16-le")
    found = [
        (i, op)
        for i, op in enumerate(spec.ops)
        if isinstance(op, BytesOp) and old in op.new
    ]
    if len(found) != 1 or found[0][1].new.count(old) != 1:
        raise BuildError(
            f"{spec.name}: the placeholder {PLACEHOLDER} must be there once"
        )
    index, op = found[0]
    ops = list(spec.ops)
    ops[index] = replace(op, new=op.new.replace(old, new))
    return replace(spec, ops=tuple(ops))
