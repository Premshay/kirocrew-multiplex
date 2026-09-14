from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path


def test_codex_hook_maps_lifecycle(monkeypatch):
    path = Path(__file__).parents[1] / "scripts" / "multiplex_codex_hook.py"
    sys.path.insert(0, str(path.parent))
    try:
        spec = importlib.util.spec_from_file_location("multiplex_codex_hook", path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(path.parent))
    calls = []
    monkeypatch.setattr(module, "record_native_event", lambda *args: calls.append(args))
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({
        "hook_event_name": "SubagentStop", "session_id": "codex-123", "agent_type": "review",
    })))

    assert module.main() == 0
    assert calls == [("codex", "codex-123", "subagent_stopped", "review")]
