"""The scripts outside the package (tools/, emulator/, gen/, web/scripts/, .github/scripts/) import only what exists.

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
FOLDERS = ("tools/", "emulator/", "gen/", "web/scripts/", ".github/scripts/")
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


class ScriptImportTests(unittest.TestCase):
    def test_every_local_import_has_a_file(self) -> None:
        listed = subprocess.run(
            ["git", "ls-files", "--", *FOLDERS], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.split()
        scripts = [p for p in listed if p.endswith(".py") and not p.startswith("emulator/om-emu/")]
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
