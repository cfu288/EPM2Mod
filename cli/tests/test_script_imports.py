"""The scripts outside the package (tools/, emulator/, gen/, web/scripts/, .github/scripts/, .githooks/) import only
what exists, and pyflakes finds no syntax error and no undefined name in them. The documents pass the writing rules.

No type check reads these scripts, so a module that is moved or removed leaves an import that fails only when the
script runs. This test finds each import that is not the standard library or a dependency of the workspace, and checks
that a file of that name is in the script's folder or a folder the scripts put on their path.

    uv run python -m unittest discover -s cli/tests
"""

import ast
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FOLDERS = ("tools/", "emulator/", "gen/", "web/scripts/", ".github/scripts/", ".githooks/")
#: The folders the scripts put on sys.path.
PATH = [ROOT / "tools", ROOT / "emulator", ROOT / "cli" / "src"]
#: The import names of the workspace's dependencies (pyproject.toml).
DEPENDENCIES = {"numpy", "scipy", "numba", "PIL", "rawpy", "matplotlib", "pyflakes", "cv2", "spektrafilm"}


def imports(source: str) -> set[str]:
    """Return the top-level names of the absolute imports in ``source``."""
    names = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module.split(".")[0])
    return names


#: pyflakes messages about tidiness. The scripts are research code: only what can stop a run fails the test.
TIDINESS = ("imported but unused", "assigned to but never used", "redefinition of unused")


def script_files() -> list[str]:
    """Return the Python scripts of FOLDERS that git holds: *.py, and the files without a suffix that start with a
    python line."""
    listed = subprocess.run(
        ["git", "ls-files", "--", *FOLDERS], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.split()
    found = []
    for name in listed:
        path = ROOT / name
        if name.startswith("emulator/om-emu") or not path.is_file():
            continue
        if name.endswith(".py") or (not path.suffix and path.read_bytes()[:40].startswith(b"#!/usr/bin/env python")):
            found.append(name)
    return found


class ScriptImportTests(unittest.TestCase):
    def test_pyflakes_finds_no_error(self) -> None:
        done = subprocess.run(
            [sys.executable, "-m", "pyflakes", *script_files()], cwd=ROOT, capture_output=True, text=True, check=False
        )
        self.assertNotIn("No module named pyflakes", done.stderr, "run: uv sync")
        lines = (done.stdout + done.stderr).splitlines()
        self.assertEqual([line for line in lines if not any(kind in line for kind in TIDINESS)], [])

    def test_the_documents_pass_the_writing_rules(self) -> None:
        done = subprocess.run(
            [sys.executable, ".githooks/doclint.py", "--all"], cwd=ROOT, capture_output=True, text=True, check=False
        )
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_every_local_import_has_a_file(self) -> None:
        scripts = [p for p in script_files() if p.endswith(".py")]
        self.assertTrue(scripts)
        missing = []
        for script in scripts:
            path = ROOT / script
            folders = [path.parent, *PATH]
            for name in imports(path.read_text(encoding="utf-8")):
                if name in sys.stdlib_module_names or name in DEPENDENCIES:
                    continue
                if not any((f / f"{name}.py").is_file() or (f / name / "__init__.py").is_file() for f in folders):
                    missing.append(f"{script}: import {name}")
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
