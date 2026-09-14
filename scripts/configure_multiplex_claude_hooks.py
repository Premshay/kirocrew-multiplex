#!/usr/bin/env python3
"""Inspect or opt in to the Multiplex lifecycle hooks for Claude Code."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
import tempfile
from pathlib import Path
from typing import Any


HOOK_COMMAND = f"{shlex.quote(sys.executable)} {shlex.quote(str(Path(__file__).with_name('multiplex_claude_hook.py')))}"
HOOKS = {
    "SessionStart": "startup|resume|clear|compact",
    "SubagentStart": ".*",
    "SubagentStop": ".*",
    "SessionEnd": ".*",
}


def settings_path() -> Path:
    return Path(os.environ.get("CLAUDE_SETTINGS_FILE", "~/.claude/settings.json")).expanduser()


def load_settings(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    if not isinstance(payload, dict):
        raise ValueError("Claude settings must be a JSON object")
    return payload


def merge_hooks(settings: dict[str, Any]) -> bool:
    hooks = settings.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("Claude settings hooks must be an object")
    changed = False
    for event, matcher in HOOKS.items():
        entries = hooks.setdefault(event, [])
        if not isinstance(entries, list):
            raise ValueError(f"Claude settings {event} hooks must be a list")
        configured = any(
            isinstance(hook, dict) and hook.get("command") == HOOK_COMMAND
            for entry in entries if isinstance(entry, dict)
            for hook in entry.get("hooks", []) if isinstance(entry.get("hooks", []), list)
        )
        if configured:
            continue
        entries.append({"matcher": matcher, "hooks": [{"type": "command", "command": HOOK_COMMAND, "timeout": 5}]})
        changed = True
    return changed


def save_settings(path: Path, settings: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(settings, handle, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write the missing hook entries")
    args = parser.parse_args()
    path = settings_path()
    settings = load_settings(path)
    changed = merge_hooks(settings)
    if args.apply and changed:
        save_settings(path, settings)
        print("Multiplex Claude hooks installed")
    elif changed:
        print("Multiplex Claude hooks are ready; rerun with --apply to install")
    else:
        print("Multiplex Claude hooks are already installed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
