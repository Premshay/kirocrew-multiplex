from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path


def _hook_module():
    path = Path(__file__).parents[1] / "scripts" / "multiplex_antigravity_hook.py"
    sys.path.insert(0, str(path.parent))
    try:
        spec = importlib.util.spec_from_file_location("multiplex_antigravity_hook", path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(path.parent))


def _payload(**updates):
    return {
        "conversationId": "conversation-123",
        "workspacePaths": ["/work/project"],
        "transcriptPath": "/state/transcript.jsonl",
        "modelName": "gemini-3-pro",
        **updates,
    }


def test_antigravity_hook_registers_first_invocation(monkeypatch) -> None:
    module = _hook_module()
    calls = []
    monkeypatch.setattr(
        module,
        "register_native_session",
        lambda *args, **kwargs: calls.append((args, kwargs)) or {"created": True},
    )
    events = []
    monkeypatch.setattr(module, "record_native_event", lambda *args: events.append(args))
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(_payload())))

    assert module.main(["invocation"]) == 0
    assert calls == [
        (
            ("antigravity", "conversation-123"),
            {
                "workspace_path": "/work/project",
                "model": "gemini-3-pro",
                "transcript_path": "/state/transcript.jsonl",
            },
        )
    ]
    assert events == [("antigravity", "conversation-123", "session_started")]


def test_antigravity_hook_marks_only_fully_idle_stop(monkeypatch) -> None:
    module = _hook_module()
    registrations = []
    monkeypatch.setattr(
        module,
        "register_native_session",
        lambda *args, **kwargs: registrations.append((args, kwargs)) or {"created": False},
    )
    events = []
    monkeypatch.setattr(module, "record_native_event", lambda *args: events.append(args))
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(_payload(fullyIdle=False))))

    assert module.main(["stop"]) == 0
    assert registrations == []
    assert events == []

    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(_payload(fullyIdle=True))))
    assert module.main(["stop"]) == 0
    assert events == [("antigravity", "conversation-123", "session_ended")]
