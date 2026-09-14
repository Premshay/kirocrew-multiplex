from __future__ import annotations

import json
import sys
import types
from datetime import UTC, datetime
from pathlib import Path

import pytest


BACKEND = Path(__file__).parents[1] / "backend"
package = types.ModuleType("multiplex_backend")
package.__path__ = [str(BACKEND)]
sys.modules.setdefault("multiplex_backend", package)

from multiplex_backend.external_sessions import (
    discover_native_runtime_sessions,
    discover_native_sessions,
    load_managed_native_sessions,
    load_scope_roots,
)


NOW = datetime(2026, 8, 9, 12, tzinfo=UTC)


def test_native_discovery_uses_kirocrew_workspaces_without_companion(tmp_path):
    workspace = tmp_path / "workspace"
    other = tmp_path / "other"
    home = tmp_path / "home"
    config = home / ".kiro" / "crew" / "config.json"
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps({"workspaces": {"project": {"dir": str(workspace)}}}))
    for directory, sid in ((workspace, "included"), (other, "excluded")):
        _write(home / ".codex" / "sessions" / f"{sid}.jsonl", [
            {"type": "session_meta", "payload": {"id": sid, "cwd": str(directory)}},
        ])

    sessions = discover_native_sessions(home=home, now=NOW)

    assert [session["key"] for session in sessions] == ["native:codex:included"]


def test_scope_ignores_personal_harness_and_keeps_declared_mounts(tmp_path):
    scope = tmp_path / ".config" / "agents-harness" / "observer-scope.yaml"
    scope.parent.mkdir(parents=True)
    scope.write_text("roots:\n  - /private/project\n")
    assert load_scope_roots(tmp_path) == []
    config = tmp_path / ".kiro" / "crew" / "config.json"
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps({"workspaces": {"mounted": {"dir": "/mnt/work/project"}}}))
    assert load_scope_roots(tmp_path) == [Path("/mnt/work/project")]


@pytest.mark.parametrize("payload", ["{", "[]", '{"workspaces": []}', '{"workspaces": {"invalid": null, "relative": {"dir": "project"}}}'])
def test_invalid_workspace_configuration_never_expands_scope(tmp_path, payload):
    config = tmp_path / ".kiro" / "crew" / "config.json"
    config.parent.mkdir(parents=True)
    config.write_text(payload)
    assert load_scope_roots(tmp_path) == []


def _write(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")
    timestamp = NOW.timestamp()
    path.touch()
    path.chmod(0o600)
    import os

    os.utime(path, (timestamp, timestamp))


def _live_proc(proc_root: Path, pid: int, start: str) -> None:
    proc = proc_root / str(pid)
    proc.mkdir(parents=True)
    # Fields after the command begin at stat field 3; field 22 is index 19.
    (proc / "stat").write_text(
        f"{pid} (provider) S " + "0 " * 18 + f"{start}\n", encoding="utf-8"
    )
    (proc_root / "stat").write_text("btime 1786530000\n", encoding="utf-8")


def test_discovers_scoped_codex_and_claude_sessions(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    home = tmp_path / "home"
    _write(home / ".codex" / "sessions" / "2026" / "08" / "09" / "rollout.jsonl", [
        {"type": "session_meta", "payload": {"id": "codex-123", "cwd": str(workspace)}},
        {"type": "turn_context", "payload": {"model": "gpt-5.6", "cwd": str(workspace)}},
    ])
    _write(home / ".claude" / "projects" / "workspace" / "claude-456.jsonl", [
        {"type": "user", "sessionId": "claude-456", "cwd": str(workspace)},
        {"type": "custom-title", "sessionId": "claude-456", "customTitle": "Review release"},
    ])

    sessions = discover_native_sessions(home=home, roots=[workspace], now=NOW)

    assert {session["key"] for session in sessions} == {"native:codex:codex-123", "native:claude:claude-456"}
    codex = next(session for session in sessions if session["source_type"] == "codex")
    assert codex["title"] == "workspace: Codex session codex-12"
    assert codex["model"] == "gpt-5.6"
    assert codex["project_root"] == str(workspace)
    claude = next(session for session in sessions if session["source_type"] == "claude")
    assert claude["title"] == "workspace: Review release"
    assert claude["project_root"] == str(workspace)


def test_ignores_native_sessions_outside_declared_scope(tmp_path):
    home = tmp_path / "home"
    observed = tmp_path / "observed"
    other = tmp_path / "other"
    observed.mkdir()
    other.mkdir()
    _write(home / ".codex" / "sessions" / "rollout.jsonl", [
        {"type": "session_meta", "payload": {"id": "outside", "cwd": str(other)}},
    ])

    assert discover_native_sessions(home=home, roots=[observed], now=NOW) == []


def test_ignores_claude_subagent_transcripts(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    home = tmp_path / "home"
    _write(home / ".claude" / "projects" / "workspace" / "main.jsonl", [
        {"type": "user", "sessionId": "main", "cwd": str(workspace)},
    ])
    _write(home / ".claude" / "projects" / "workspace" / "main" / "subagents" / "agent.jsonl", [
        {"type": "user", "sessionId": "subagent", "cwd": str(workspace)},
    ])

    sessions = discover_native_sessions(home=home, roots=[workspace], now=NOW)

    assert [session["key"] for session in sessions] == ["native:claude:main"]


def test_kirocrew_managed_sessions_are_suppressed(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    home = tmp_path / "home"
    _write(home / ".claude" / "projects" / "workspace" / "managed.jsonl", [
        {"type": "user", "sessionId": "managed-sid", "cwd": str(workspace)},
    ])
    _write(home / ".claude" / "projects" / "workspace" / "standalone.jsonl", [
        {"type": "user", "sessionId": "standalone-sid", "cwd": str(workspace)},
    ])

    sessions = discover_native_sessions(
        home=home,
        roots=[workspace],
        now=NOW,
        managed={"managed-sid": "dashboard:chat-10"},
    )

    assert [session["key"] for session in sessions] == ["native:claude:standalone-sid"]


def test_managed_owners_come_from_the_session_map(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    home = tmp_path / "home"
    _write(home / ".claude" / "projects" / "workspace" / "managed.jsonl", [
        {"type": "user", "sessionId": "managed-sid", "cwd": str(workspace)},
    ])
    session_map = home / ".kiro" / "crew" / "session_map.json"
    session_map.parent.mkdir(parents=True, exist_ok=True)
    session_map.write_text(
        json.dumps({
            "dashboard:chat-10": {
                "sid": "managed-sid",
                "provider": "claude_code",
                "cwd": str(workspace),
            }
        }),
        encoding="utf-8",
    )

    assert load_managed_native_sessions(home) == {"managed-sid": "dashboard:chat-10"}
    assert discover_native_sessions(home=home, roots=[workspace], now=NOW) == []


def test_unreadable_session_map_keeps_the_native_record(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    home = tmp_path / "home"
    _write(home / ".claude" / "projects" / "workspace" / "orphan.jsonl", [
        {"type": "user", "sessionId": "orphan-sid", "cwd": str(workspace)},
    ])
    session_map = home / ".kiro" / "crew" / "session_map.json"
    session_map.parent.mkdir(parents=True, exist_ok=True)
    session_map.write_text("{not json", encoding="utf-8")

    sessions = discover_native_sessions(home=home, roots=[workspace], now=NOW)

    assert [session["key"] for session in sessions] == ["native:claude:orphan-sid"]


def test_native_records_never_claim_running(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    home = tmp_path / "home"
    _write(home / ".claude" / "projects" / "workspace" / "fresh.jsonl", [
        {"type": "user", "sessionId": "fresh-sid", "cwd": str(workspace)},
    ])

    # Queried at the instant the transcript was written — the case the old
    # three-minute rule reported as running. No file fact establishes liveness.
    session = discover_native_sessions(home=home, roots=[workspace], now=NOW)[0]

    assert session["running"] is False


def test_duplicate_transcripts_do_not_require_runtime_fields(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    home = tmp_path / "home"
    for name in ("first", "second"):
        _write(
            home / ".codex" / "sessions" / f"{name}.jsonl",
            [
                {
                    "type": "session_meta",
                    "payload": {"id": "same-session", "cwd": str(workspace)},
                },
                {
                    "type": "turn_context",
                    "payload": {"model": "gpt-5.6", "cwd": str(workspace)},
                },
            ],
        )

    sessions = discover_native_sessions(home=home, roots=[workspace], now=NOW)

    assert [session["key"] for session in sessions] == ["native:codex:same-session"]
    assert sessions[0]["running"] is False
    assert "runtime_catalog" not in sessions[0]


def test_claude_pid_registry_proves_an_open_provider_session(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    home = tmp_path / "home"
    proc_root = tmp_path / "proc"
    _live_proc(proc_root, 741, "12345")
    registry = home / ".claude" / "sessions" / "741.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        json.dumps(
            {
                "pid": 741,
                "procStart": "12345",
                "sessionId": "claude-live",
                "cwd": str(workspace),
                "name": "Implement lifecycle contract",
                "status": "busy",
                "statusUpdatedAt": 1786530000000,
            }
        ),
        encoding="utf-8",
    )

    sessions = discover_native_runtime_sessions(
        home=home, roots=[workspace], proc_root=proc_root
    )

    assert sessions["native:claude:claude-live"]["runtime_catalog"] == "open"
    assert sessions["native:claude:claude-live"]["runtime_execution"] == "active"
    assert sessions["native:claude:claude-live"]["runtime_evidence"] == "claude_session_registry"


def test_claude_registry_rejects_a_reused_pid(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    home = tmp_path / "home"
    proc_root = tmp_path / "proc"
    _live_proc(proc_root, 741, "newer-process")
    registry = home / ".claude" / "sessions" / "741.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        json.dumps(
            {
                "pid": 741,
                "procStart": "old-process",
                "sessionId": "stale-session",
                "cwd": str(workspace),
            }
        ),
        encoding="utf-8",
    )

    assert discover_native_runtime_sessions(home=home, roots=[workspace], proc_root=proc_root) == {}


def test_codex_process_manager_proves_work_but_not_open_state(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    home = tmp_path / "home"
    proc_root = tmp_path / "proc"
    _live_proc(proc_root, 903, "0")
    registry = home / ".codex" / "process_manager" / "chat_processes.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        json.dumps(
            [
                {
                    "osPid": 903,
                    "conversationId": "codex-live",
                    "cwd": str(workspace),
                    "chatTitle": "Run verification",
                    "startedAtMs": 1786530000000,
                    "updatedAtMs": 1786530000000,
                }
            ]
        ),
        encoding="utf-8",
    )

    sessions = discover_native_runtime_sessions(
        home=home, roots=[workspace], proc_root=proc_root
    )

    assert sessions["native:codex:codex-live"]["runtime_catalog"] == "observed"
    assert sessions["native:codex:codex-live"]["runtime_execution"] == "active"
    assert sessions["native:codex:codex-live"]["runtime_evidence"] == "codex_process_manager"


def test_codex_process_manager_rejects_a_reused_pid(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    home = tmp_path / "home"
    proc_root = tmp_path / "proc"
    _live_proc(proc_root, 903, "10_000")
    registry = home / ".codex" / "process_manager" / "chat_processes.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        json.dumps(
            [{"osPid": 903, "conversationId": "stale", "cwd": str(workspace), "startedAtMs": 1786530000000}]
        ),
        encoding="utf-8",
    )

    assert discover_native_runtime_sessions(home=home, roots=[workspace], proc_root=proc_root) == {}


def test_recency_comes_from_the_newest_output_record(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    home = tmp_path / "home"
    _write(home / ".claude" / "projects" / "workspace" / "session.jsonl", [
        {"type": "user", "sessionId": "sid", "cwd": str(workspace)},
        {"type": "assistant", "sessionId": "sid", "timestamp": "2026-08-09T11:00:00.000Z"},
        {"type": "assistant", "sessionId": "sid", "timestamp": "2026-08-09T11:05:00.000Z"},
        # A metadata write lands later than any output; this is what drags an
        # mtime away from the moment the session last produced work.
        {"type": "queue-operation", "timestamp": "2026-08-09T11:55:00.000Z"},
    ])

    session = discover_native_sessions(home=home, roots=[workspace], now=NOW)[0]

    assert session["last_activity_at"] == "2026-08-09T11:05:00.000Z"


def test_sidechain_output_is_not_parent_activity(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    home = tmp_path / "home"
    _write(home / ".claude" / "projects" / "workspace" / "session.jsonl", [
        {"type": "user", "sessionId": "sid", "cwd": str(workspace)},
        {"type": "assistant", "sessionId": "sid", "timestamp": "2026-08-09T11:00:00.000Z"},
        {
            "type": "assistant",
            "sessionId": "sid",
            "timestamp": "2026-08-09T11:30:00.000Z",
            "isSidechain": True,
        },
    ])

    session = discover_native_sessions(home=home, roots=[workspace], now=NOW)[0]

    assert session["last_activity_at"] == "2026-08-09T11:00:00.000Z"


def test_recency_is_unknown_when_no_output_record_parses(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    home = tmp_path / "home"
    _write(home / ".claude" / "projects" / "workspace" / "metadata_only.jsonl", [
        {"type": "user", "sessionId": "sid", "cwd": str(workspace)},
        {"type": "queue-operation", "timestamp": "2026-08-09T11:55:00.000Z"},
        {"type": "mode"},
    ])

    session = discover_native_sessions(home=home, roots=[workspace], now=NOW)[0]

    # Unknown, never the file mtime: a metadata-only write must not read as
    # fresh output.
    assert session["last_activity_at"] == ""


def test_codex_recency_comes_from_response_items(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    home = tmp_path / "home"
    _write(home / ".codex" / "sessions" / "rollout.jsonl", [
        {"type": "session_meta", "payload": {"id": "codex-1", "cwd": str(workspace)}},
        {"type": "response_item", "timestamp": "2026-08-09T10:00:00.000Z"},
        {"type": "response_item", "timestamp": "2026-08-09T10:02:00.000Z"},
    ])

    session = discover_native_sessions(home=home, roots=[workspace], now=NOW)[0]

    assert session["last_activity_at"] == "2026-08-09T10:02:00.000Z"
    assert session["running"] is False
