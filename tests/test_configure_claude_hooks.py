from __future__ import annotations

import importlib.util
from pathlib import Path


def _module():
    path = Path(__file__).parents[1] / "scripts" / "configure_multiplex_claude_hooks.py"
    spec = importlib.util.spec_from_file_location("configure_multiplex_claude_hooks", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_merge_preserves_existing_claude_hooks_and_is_idempotent():
    module = _module()
    settings = {"hooks": {"SessionStart": [{"hooks": [{"command": "existing"}]}]}}

    assert module.merge_hooks(settings)
    assert settings["hooks"]["SessionStart"][0]["hooks"][0]["command"] == "existing"
    assert not module.merge_hooks(settings)
