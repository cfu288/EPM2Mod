#!/usr/bin/env python3
"""Check the documents that users read. The pre-commit hook runs this on staged files.

    python3 tools/doclint.py FILE.md ...     check the given files that are in scope
    python3 tools/doclint.py --all           check every file in scope
    python3 tools/doclint.py --selftest

Rules, and the files each one covers:

1. Simplified Technical English (tools/third_party/ste100/ste_lint.py), hard rules only:
   README.md, docs/install.md, docs/guide/*.md.
2. A heading has no punctuation (: ; , ! ? ( ) and dashes) and no full stop at its end:
   the files of rule 1, every other README.md outside experiments/, AGENTS.md, NOTICE.md,
   docs/conventions.md, docs/feasibility.md, docs/todo.md.
3. The root README.md is an index with the short install steps: at most 35 lines, and the only
   heading below the title is "## Install".
4. A guide is short and shows the screen: docs/guide/*.md has at most 40 lines and one or more
   pictures. docs/install.md has at most 45 lines.

Text that is not prose is left out of rule 1: code, generated blocks, comments, tables, links,
pictures and words in bold (names of buttons and menu entries, as the camera shows them).

Exit status 1 if a rule fails. Python standard library only.
"""
import fnmatch
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STE = os.path.join(ROOT, "tools", "third_party", "ste100", "ste_lint.py")
PROSE = ["README.md", "docs/install.md", "docs/guide/*.md"]
HEADINGS = PROSE + ["AGENTS.md", "NOTICE.md", "docs/conventions.md", "docs/feasibility.md", "docs/todo.md"]
ROOT_README_LINES = 35
ROOT_README_SECTIONS = {"## Install"}
MAX_LINES = {"docs/guide/*.md": 40, "docs/install.md": 45}
HEADING_PUNCTUATION = re.compile(r"[:;,!?()—–]|\.\s*$")


def matches(path, patterns):
    return any(fnmatch.fnmatch(path, p) for p in patterns)


def heading_scope(path):
    if matches(path, HEADINGS):
        return True
    return os.path.basename(path) == "README.md" and not path.startswith(("experiments/", "tools/third_party/"))


def in_scope(path):
    return path.endswith(".md") and (matches(path, PROSE) or heading_scope(path))


def prose_only(text):
    """Return text with everything that is not prose blanked. Line numbers stay the same."""
    def blank(match):
        return re.sub(r"[^\n]", " ", match.group(0))

    text = re.sub(r"<!-- BEGIN GENERATED: ([a-z-]+) -->.*?<!-- END GENERATED: \1 -->", blank, text, flags=re.S)
    text = re.sub(r"```.*?```", blank, text, flags=re.S)
    text = re.sub(r"<!--.*?-->", blank, text, flags=re.S)
    text = re.sub(r"<img[^>]*>|!\[[^\]]*\]\([^)]*\)", blank, text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", lambda m: m.group(1) + " " * (len(m.group(0)) - len(m.group(1))), text)
    text = re.sub(r"`[^`\n]*`", blank, text)
    text = re.sub(r"\*\*[^*\n]*\*\*", blank, text)
    lines = [" " * len(line) if line.lstrip().startswith(("|", "#")) else line for line in text.split("\n")]
    return "\n".join(lines)


def check(path, text):
    """Return the list of problems of one document, as text lines."""
    problems = []
    lines = text.split("\n")
    count = len(text.rstrip("\n").split("\n"))
    if matches(path, PROSE):
        done = subprocess.run([sys.executable, STE, "--disable", "passive-voice,present-perfect"],
                              input=prose_only(text), capture_output=True, text=True)
        for line in done.stdout.splitlines():
            if re.match(r"^(<stdin>|-)?:?\d+:\d+ ", line) or re.match(r"^\S*:\d+:\d+ ", line):
                problems.append("%s:%s" % (path, line.split(":", 1)[1] if line[0] in "<-" else line))
        if done.returncode not in (0, 1):
            problems.append("%s: the STE linter did not run: %s" % (path, done.stderr.strip()[-200:]))
    if heading_scope(path):
        fenced = False
        for number, line in enumerate(lines, 1):
            if line.startswith("```"):
                fenced = not fenced
            if fenced or not re.match(r"#{1,6} ", line):
                continue
            title = re.sub(r"`[^`]*`", "", line.lstrip("# "))
            if HEADING_PUNCTUATION.search(title):
                problems.append("%s:%d: heading with punctuation: %s" % (path, number, line.strip()))
    if path == "README.md":
        if count > ROOT_README_LINES:
            problems.append("README.md: %d lines. The root README is an index: at most %d lines. "
                            "Put the text in docs/guide/ or docs/." % (count, ROOT_README_LINES))
        if any(re.match(r"#{2,6} ", line) and line.strip() not in ROOT_README_SECTIONS for line in lines):
            problems.append("README.md: the root README has no sections below the title but: %s"
                            % ", ".join(sorted(ROOT_README_SECTIONS)))
    for pattern, limit in MAX_LINES.items():
        if fnmatch.fnmatch(path, pattern) and count > limit:
            problems.append("%s: %d lines, at most %d. Cut it." % (path, count, limit))
    if fnmatch.fnmatch(path, "docs/guide/*.md") and not re.search(r"<img |!\[", text):
        problems.append("%s: a guide needs one or more screenshots" % path)
    return problems


def selftest():
    good = "# Level gauge\n\nPress **INFO**. The bars show.\n\n<img src=\"x.png\">\n"
    assert check("docs/guide/x.md", good) == [], check("docs/guide/x.md", good)
    bad = "# Level gauge: how to (really) use it\n\nWe have received it; it works.\n"
    found = "\n".join(check("docs/guide/x.md", bad))
    for word in ("heading with punctuation", "semicolon", "screenshots"):
        assert word in found, (word, found)
    assert "at most" in "\n".join(check("README.md", "# T\n" + "x\n" * 40))
    assert "no sections" in "\n".join(check("README.md", "# T\n\n## More\n"))
    assert check("README.md", "# T\n\n## Install\n") == []
    table = "# T\n\n| a; b | c |\n\n<!-- BEGIN GENERATED: films -->\nx; y\n<!-- END GENERATED: films -->\n\n![p](q.png)\n"
    assert check("docs/guide/x.md", table) == [], check("docs/guide/x.md", table)
    assert check("experiments/x/README.md", bad) == [] and not in_scope("experiments/x/README.md")
    print("doclint selftest: ok")


def main(argv):
    if argv == ["--selftest"]:
        selftest()
        return 0
    if argv == ["--all"]:
        listed = subprocess.run(["git", "ls-files", "*.md"], cwd=ROOT, capture_output=True, text=True, check=True)
        argv = listed.stdout.split()
    problems = []
    for name in argv:
        path = os.path.relpath(os.path.abspath(name), ROOT).replace(os.sep, "/")
        full = os.path.join(ROOT, path)
        if in_scope(path) and os.path.isfile(full):
            with open(full, encoding="utf-8") as handle:
                problems += check(path, handle.read())
    for line in problems:
        print(line)
    if problems:
        print("doclint: %d problem(s). Rules: python3 tools/doclint.py --help" % len(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    if sys.argv[1:] in (["--help"], ["-h"]):
        print(__doc__)
        sys.exit(0)
    sys.exit(main(sys.argv[1:]))
