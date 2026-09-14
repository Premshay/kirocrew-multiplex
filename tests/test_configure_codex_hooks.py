from __future__ import annotations

import importlib.util
import tomllib
from pathlib import Path

import pytest


def _module():
    path = Path(__file__).parents[1] / "scripts" / "configure_multiplex_codex_hooks.py"
    spec = importlib.util.spec_from_file_location("configure_multiplex_codex_hooks", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_installer_is_idempotent_and_preserves_other_events():
    module = _module()
    original = "[[hooks.Stop]]\nmatcher = \".*\"\n"
    merged, changed = module.merge_hooks(original, tomllib.loads(original))

    assert changed
    parsed = tomllib.loads(merged)
    assert parsed["hooks"]["Stop"][0]["matcher"] == ".*"
    assert all(
        parsed["hooks"][event][0]["hooks"][0]["command"] == module.HOOK_COMMAND
        for event in module.HOOK_EVENTS
    )
    assert module.merge_hooks(merged, parsed) == (merged, False)


def test_installer_refuses_to_rewrite_an_existing_lifecycle_event():
    module = _module()
    original = """[[hooks.SessionStart]]
matcher = \".*\"
[[hooks.SessionStart.hooks]]
type = \"command\"
command = \"existing\"
"""

    with pytest.raises(ValueError, match="already defines SessionStart hooks"):
        module.merge_hooks(original, tomllib.loads(original))
