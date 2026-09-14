#!/usr/bin/env python3
"""Inspect or opt in to the Multiplex lifecycle hooks for Codex."""

from __future__ import annotations

import argparse
import os
import shlex
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import Any


HOOK_COMMAND = f"{shlex.quote(sys.executable)} {shlex.quote(str(Path(__file__).with_name('multiplex_codex_hook.py')))}"
HOOK_EVENTS = ("SessionStart", "SubagentStart", "SubagentStop", "SessionEnd")


def config_path() -> Path:
    return Path(os.environ.get("CODEX_CONFIG_FILE", "~/.codex/config.toml")).expanduser()


def load_config(path: Path) -> tuple[str, dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return "", {}
    try:
        payload = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise ValueError(f"Codex config is not valid TOML: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError("Codex config must be a TOML table")
    return text, payload


def configured_commands(entries: Any) -> set[str]:
    if not isinstance(entries, list):
        raise ValueError("Codex lifecycle hooks must be lists")
    return {
        hook["command"]
        for entry in entries
        if isinstance(entry, dict)
        for hook in entry.get("hooks", [])
        if isinstance(entry.get("hooks", []), list)
        and isinstance(hook, dict)
        and isinstance(hook.get("command"), str)
    }


def hook_block(event: str) -> str:
    return "\n".join((
        f"[[hooks.{event}]]",
        'matcher = ".*"',
        f"[[hooks.{event}.hooks]]",
        'type = "command"',
        f"command = {HOOK_COMMAND!r}",
        "timeout = 5",
    ))


def merge_hooks(text: str, config: dict[str, Any]) -> tuple[str, bool]:
    hooks = config.get("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("Codex config hooks must be a TOML table")
    additions = []
    for event in HOOK_EVENTS:
        if event not in hooks:
            additions.append(hook_block(event))
            continue
        commands = configured_commands(hooks[event])
        if HOOK_COMMAND not in commands:
            raise ValueError(
                f"Codex config already defines {event} hooks; merge the Multiplex command manually"
            )
    if not additions:
        return text, False
    blocks = "\n\n".join(additions)
    candidate = f"{text.rstrip()}\n\n{blocks}\n"
    try:
        tomllib.loads(candidate)
    except tomllib.TOMLDecodeError as error:
        raise ValueError(f"Adding Multiplex hooks would make the Codex config invalid: {error}") from error
    return candidate, True


def save_config(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(text)
        temporary = Path(handle.name)
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write the missing hook entries")
    args = parser.parse_args()
    path = config_path()
    text, config = load_config(path)
    merged, changed = merge_hooks(text, config)
    if args.apply and changed:
        save_config(path, merged)
        print("Multiplex Codex hooks installed")
    elif changed:
        print("Multiplex Codex hooks are ready; rerun with --apply to install")
    else:
        print("Multiplex Codex hooks are already installed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
