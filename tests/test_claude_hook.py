from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path


def _hook_module():
    scripts = Path(__file__).parents[1] / "scripts"
    sys.path.insert(0, str(scripts))
    try:
        spec = importlib.util.spec_from_file_location("multiplex_claude_hook", scripts / "multiplex_claude_hook.py")
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(scripts))


def test_claude_hook_maps_session_and_subagent_lifecycle(monkeypatch):
    module = _hook_module()
    calls = []
    monkeypatch.setattr(module, "record_native_event", lambda *args: calls.append(args))
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({
        "hook_event_name": "SessionStart", "source": "resume", "session_id": "claude-123",
    })))

    assert module.main() == 0
    assert calls == [("claude", "claude-123", "session_resumed", "")]


def test_claude_hook_ignores_unrecognized_events(monkeypatch):
    module = _hook_module()
    calls = []
    monkeypatch.setattr(module, "record_native_event", lambda *args: calls.append(args))
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({
        "hook_event_name": "Stop", "session_id": "claude-123",
    })))

    assert module.main() == 0
    assert calls == []
