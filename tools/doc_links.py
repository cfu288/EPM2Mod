"""Tell the agent which other files repeat a fact when it edits one of them (a Claude Code PostToolUse hook).

    .claude/settings.json runs:  python3 tools/doc_links.py   (stdin: the hook's JSON)

Reads the edited file's path from the hook input, finds the groups of tools/doc_links.json that hold it (as truth or
as a copy), and prints a PostToolUse result whose additionalContext names the other files of each group. A group is
named once per session (state in the system temp folder), so repeated edits stay quiet. It never blocks and never
fails the tool call: on any problem it prints nothing.

    python3 tools/doc_links.py --file README.md      the same lookup without the hook, for a person
"""
from __future__ import annotations

import fnmatch
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "tools" / "doc_links.json"


def groups_for(rel: str, groups: list[dict]) -> list[tuple[dict, str]]:
    """The groups that hold the file rel (a path from the repository root), each with 'truth' or 'copy'."""
    found = []
    for group in groups:
        if any(fnmatch.fnmatch(rel, g) for g in group.get("truth", [])):
            found.append((group, "truth"))
        elif any(fnmatch.fnmatch(rel, g) for g in group.get("copies", [])):
            found.append((group, "copy"))
    return found


def message(rel: str, found: list[tuple[dict, str]]) -> str:
    """The note for the agent: per group, the fact and the other files to check."""
    lines = [f"Linked files for {rel} (tools/doc_links.json). Check whether this edit changes a fact they repeat:"]
    for group, role in found:
        others = [p for p in group.get("truth", []) + group.get("copies", []) if not fnmatch.fnmatch(rel, p)]
        lines.append(f"- {group['name']} ({'source of the fact' if role == 'truth' else 'a copy'}): {group['fact']}")
        lines.append(f"  also in: {', '.join(others)}")
        for step in group.get("regenerate", []):
            lines.append(f"  regenerate: {step}")
    lines.append("If a linked file still says the old thing, update it in the same change; if not, no action.")
    return "\n".join(lines)


def relative(path: str) -> str | None:
    """path as a path from the repository root, or None if it is outside the repository."""
    try:
        return Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return None


def first_time(session: str, names: list[str]) -> list[str]:
    """The group names not yet reported in this session; records them as reported."""
    state = Path(tempfile.gettempdir()) / f"epm2-doc-links-{session or 'none'}.json"
    try:
        seen = set(json.loads(state.read_text()))
    except (OSError, ValueError):
        seen = set()
    new = [n for n in names if n not in seen]
    try:
        state.write_text(json.dumps(sorted(seen | set(new))))
    except OSError:
        pass
    return new


def main() -> None:
    groups = json.loads(MAP.read_text())["groups"]
    if sys.argv[1:2] == ["--file"]:
        rel = relative(sys.argv[2]) or sys.argv[2]
        found = groups_for(rel, groups)
        print(message(rel, found) if found else f"{rel}: no linked files")
        return
    event = json.load(sys.stdin)
    tool_input = event.get("tool_input") or {}
    path = tool_input.get("file_path") or tool_input.get("notebook_path")
    rel = relative(path) if path else None
    if not rel:
        return
    found = groups_for(rel, groups)
    fresh = set(first_time(event.get("session_id", ""), [g["name"] for g, _ in found]))
    found = [(g, role) for g, role in found if g["name"] in fresh]
    if found:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": message(rel, found)}}))


if __name__ == "__main__":
    try:
        main()
    except Exception:  # a hook must never break an edit
        pass
