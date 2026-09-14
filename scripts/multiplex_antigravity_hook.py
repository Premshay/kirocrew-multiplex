#!/usr/bin/env python3
"""Register documented Antigravity hook identities with Multiplex."""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
from pathlib import Path
from typing import Any

from multiplex_checkpoint import record_native_event, register_native_session


_CONVERSATION_ID = re.compile(r"[A-Za-z0-9_.-]{1,160}\Z")
_DIAGNOSTICS = Path(
    os.environ.get(
        "MULTIPLEX_ANTIGRAVITY_DIAGNOSTICS",
        "~/.kiro/crew/apps/multiplex/antigravity-hook.log",
    )
).expanduser()


def _diagnostic(message: str) -> None:
    """Keep a bounded local reason when a hook intentionally publishes nothing."""
    try:
        _DIAGNOSTICS.parent.mkdir(parents=True, exist_ok=True)
        with _DIAGNOSTICS.open("a", encoding="utf-8") as handle:
            handle.write(f"{message[:500]}\n")
    except OSError:
        pass


def _identity(payload: dict[str, Any]) -> tuple[str, str, str, str] | None:
    conversation_id = payload.get("conversationId")
    workspaces = payload.get("workspacePaths")
    if not isinstance(conversation_id, str) or _CONVERSATION_ID.fullmatch(conversation_id) is None:
        _diagnostic("ignored hook payload without a valid conversationId")
        return None
    if not isinstance(workspaces, list) or len(workspaces) != 1:
        _diagnostic("ignored hook payload without exactly one declared workspace")
        return None
    workspace = workspaces[0]
    if not isinstance(workspace, str) or not Path(workspace).is_absolute():
        _diagnostic("ignored hook payload with an invalid workspace path")
        return None
    transcript = payload.get("transcriptPath")
    if transcript is not None and (
        not isinstance(transcript, str) or not Path(transcript).is_absolute()
    ):
        _diagnostic("ignored hook payload with an invalid transcript path")
        return None
    model = payload.get("modelName")
    return conversation_id, workspace, str(model or ""), str(transcript or "")


def _register(payload: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    identity = _identity(payload)
    if identity is None:
        return None
    conversation_id, workspace, model, transcript = identity
    result = register_native_session(
        "antigravity",
        conversation_id,
        workspace_path=workspace,
        model=model,
        transcript_path=transcript,
    )
    return conversation_id, result


def main(argv: list[str] | None = None) -> int:
    action = (argv or sys.argv[1:])[:1]
    if not action or action[0] not in {"invocation", "stop"}:
        _diagnostic("ignored hook invocation with no supported action")
        print("{}")
        return 0
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError("payload is not an object")
        if action[0] == "stop" and payload.get("fullyIdle") is not True:
            print("{}")
            return 0
        registered = _register(payload)
        if registered is None:
            print("{}")
            return 0
        conversation_id, registration = registered
        if action[0] == "stop":
            record_native_event("antigravity", conversation_id, "session_ended")
        elif registration.get("created") is True:
            record_native_event("antigravity", conversation_id, "session_started")
        elif registration.get("last_event") == "session_ended":
            record_native_event("antigravity", conversation_id, "session_resumed")
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        urllib.error.HTTPError,
        urllib.error.URLError,
    ) as exc:
        _diagnostic(f"hook publish failed: {exc}")
    print("{}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
