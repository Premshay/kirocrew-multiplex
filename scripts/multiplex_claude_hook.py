#!/usr/bin/env python3
"""Publish Claude Code lifecycle milestones to the Multiplex native-event bridge."""

from __future__ import annotations

import json
import sys
import urllib.error
from typing import Any

from multiplex_checkpoint import record_native_event


_EVENTS = {
    "SessionStart": {
        "startup": "session_started",
        "resume": "session_resumed",
        "clear": "session_resumed",
        "compact": "session_resumed",
    },
    "SubagentStart": "subagent_started",
    "SubagentStop": "subagent_stopped",
    "SessionEnd": "session_ended",
}


def _event(payload: dict[str, Any]) -> tuple[str, str] | None:
    event_name = payload.get("hook_event_name")
    mapping = _EVENTS.get(event_name)
    if isinstance(mapping, dict):
        event = mapping.get(payload.get("source"))
        return (event, "") if event else None
    if not isinstance(mapping, str):
        return None
    detail_key = "agent_type" if event_name.startswith("Subagent") else "reason"
    detail = str(payload.get(detail_key) or "")[:80]
    return mapping, detail


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return 0
    if not isinstance(payload, dict):
        return 0
    session_id = payload.get("session_id")
    event = _event(payload)
    if not isinstance(session_id, str) or not session_id or event is None:
        return 0
    try:
        record_native_event("claude", session_id, *event)
    except (OSError, ValueError, json.JSONDecodeError, urllib.error.HTTPError, urllib.error.URLError):
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
