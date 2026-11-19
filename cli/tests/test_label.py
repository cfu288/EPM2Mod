"""Tests of the build label on the Firmware screen, ``epm2mod.label``.

uv run python -m unittest discover -s cli/tests
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from support import ROOT  # noqa: E402

from epm2mod.builds import (  # noqa: E402
    BuildDescription,
    check_label_spec,
    description_from_json,
)
from epm2mod.errors import BuildError  # noqa: E402
from epm2mod.label import PLACEHOLDER, with_label  # noqa: E402
from epm2mod.paths import RepoPaths  # noqa: E402
from epm2mod.spec import BytesOp, load_spec  # noqa: E402

PATHS = RepoPaths(ROOT)
LABEL_SPEC = PATHS.relative(PATHS.label_spec)
SPEC = load_spec(PATHS.label_spec)


def text_of(spec: object) -> str:
    """Return the label spec's screen text."""
    ops = [op for op in spec.ops if isinstance(op, BytesOp) and "EPM2Mod".encode("utf-16-le") in op.new]  # type: ignore[attr-defined]
    return ops[0].new.decode("utf-16-le").rstrip("\x00")


class LabelTests(unittest.TestCase):
    def test_the_committed_spec_holds_the_placeholder(self) -> None:
        self.assertEqual(text_of(SPEC), f"%X.%X  EPM2Mod {PLACEHOLDER}")

    def test_the_label_replaces_the_placeholder_and_nothing_else(self) -> None:
        labelled = with_label(SPEC, "2026.11.19")
        self.assertEqual(text_of(labelled), "%X.%X  EPM2Mod 2026.11.19")
        changed = [i for i, (a, b) in enumerate(zip(SPEC.ops, labelled.ops)) if a != b]
        self.assertEqual(len(changed), 1)
        self.assertEqual(len(SPEC.ops[changed[0]].new), len(labelled.ops[changed[0]].new))  # type: ignore[union-attr]

    def test_the_same_label_gives_the_same_bytes(self) -> None:
        self.assertEqual(with_label(SPEC, "2026.12.31"), with_label(SPEC, "2026.12.31"))
        self.assertNotEqual(
            with_label(SPEC, "2026.12.31"), with_label(SPEC, "2026.11.19")
        )

    def test_a_malformed_label_is_refused(self) -> None:
        for bad in (
            "2026-11-19",
            "2026.13.01",
            "2026.02.30",
            "26.11.19",
            "2026.11.19 ",
        ):
            with self.subTest(bad), self.assertRaises(BuildError):
                with_label(SPEC, bad)


class DescriptionTests(unittest.TestCase):
    def test_a_label_needs_the_label_spec_and_the_spec_needs_a_label(self) -> None:
        with self.assertRaises(BuildError):
            check_label_spec(
                BuildDescription(
                    name="x",
                    what="x",
                    specs=("data/specs/lss-core.json",),
                    label="2026.11.19",
                    stock="x",
                ),
                LABEL_SPEC,
            )
        with self.assertRaises(BuildError):
            check_label_spec(
                BuildDescription(name="x", what="x", specs=(LABEL_SPEC,), stock="x"),
                LABEL_SPEC,
            )
        check_label_spec(
            BuildDescription(
                name="x", what="x", specs=(LABEL_SPEC,), label="2026.11.19", stock="x"
            ),
            LABEL_SPEC,
        )

    def test_the_label_goes_through_json(self) -> None:
        raw = {"what": "x", "stock": "x", "specs": [LABEL_SPEC], "label": "2026.11.19"}
        self.assertEqual(description_from_json("x", raw).to_json(), raw)


if __name__ == "__main__":
    unittest.main()
