"""Read bounded metadata for native sessions Multiplex is allowed to show."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping


_MAX_PER_SOURCE = 40
_RECENT_WINDOW = timedelta(days=7)
_HEAD_BYTES = 64 * 1024
_TAIL_BYTES = 64 * 1024
_CODEX_PROCESS_START_TOLERANCE_MS = 60_000


def load_scope_roots(home: Path) -> list[Path]:
    """Return declared workspace roots, never falling back to ambient home-wide discovery."""
    roots: list[Path] = []
    config_file = home / ".kiro" / "crew" / "config.json"
    try:
        config = json.loads(config_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    workspaces = config.get("workspaces") if isinstance(config, dict) else None
    if not isinstance(workspaces, dict):
        return []
    for workspace in workspaces.values():
        if not isinstance(workspace, dict):
            continue
        candidate = workspace.get("dir")
        if isinstance(candidate, str) and Path(candidate).is_absolute():
            roots.append(Path(candidate))
    return roots


def load_managed_native_sessions(home: Path) -> dict[str, str]:
    """Map a provider's own session id to the KiroCrew session key that owns it.

    KiroCrew records the provider session id when it spawns a managed session,
    so a native transcript belonging to a dashboard slot is recognised from that
    recorded fact rather than inferred from titles, cwd or timestamps. An
    unreadable or malformed map yields no owners, which shows the native record
    rather than hiding a session.
    """
    path = home / ".kiro" / "crew" / "session_map.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    owned: dict[str, str] = {}
    for session_key, entry in raw.items():
        if not isinstance(entry, dict):
            continue
        sid = str(entry.get("sid") or "")
        if sid:
            owned[sid] = str(session_key)
    return owned


def _in_scope(cwd: str, roots: Iterable[Path]) -> bool:
    if not cwd:
        return False
    candidate = Path(cwd)
    return any(candidate == root or candidate.is_relative_to(root) for root in roots)


def _records(path: Path) -> list[dict[str, Any]]:
    """Read only transcript edges; a card must not turn into a transcript reader."""
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            head = handle.read(_HEAD_BYTES)
            handle.seek(max(0, size - _TAIL_BYTES))
            tail = handle.read()
    except OSError:
        return []

    parsed: list[dict[str, Any]] = []
    for index, chunk in enumerate((head, tail)):
        lines = chunk.splitlines()
        if index and size > _TAIL_BYTES and lines:
            lines = lines[1:]
        for raw in lines:
            try:
                record = json.loads(raw)
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            if isinstance(record, dict):
                parsed.append(record)
    return parsed


def _recent_files(root: Path, now: datetime, pattern: str = "**/*.jsonl") -> list[Path]:
    if not root.is_dir():
        return []
    cutoff = (now - _RECENT_WINDOW).timestamp()
    candidates: list[tuple[float, Path]] = []
    try:
        paths = root.glob(pattern)
        for path in paths:
            try:
                modified = path.stat().st_mtime
            except OSError:
                continue
            if modified >= cutoff:
                candidates.append((modified, path))
    except OSError:
        return []
    return [path for _, path in sorted(candidates, reverse=True)[:_MAX_PER_SOURCE]]


# Record types carrying the agent's own output. Claude nests tool calls and
# their results inside assistant/user records rather than emitting distinct
# types, so `assistant` is the only unambiguous agent-output marker — counting
# `user` would read the operator's typing as session activity. The metadata
# types (queue-operation, mode, last-prompt) are precisely what drift a file
# mtime away from real output.
_CLAUDE_OUTPUT_TYPES = frozenset({"assistant"})
_CODEX_OUTPUT_TYPES = frozenset({"response_item"})


def _process_start(proc_root: Path, pid: int) -> str:
    """Return Linux' process-start tick or nothing when the process is gone.

    A PID alone is recyclable. Claude's registry provides the kernel start tick,
    so require both facts before treating its session record as live.
    """
    try:
        stat = (proc_root / str(pid) / "stat").read_text(encoding="utf-8")
        fields = stat.rsplit(")", 1)[1].split()
    except (OSError, IndexError):
        return ""
    return fields[19] if len(fields) > 19 else ""


def _process_started_at_ms(proc_root: Path, pid: int) -> int | None:
    """Convert a Linux PID's start tick to epoch milliseconds when available."""
    ticks = _process_start(proc_root, pid)
    if not ticks.isdigit():
        return None
    try:
        boot_line = next(
            line for line in (proc_root / "stat").read_text(encoding="utf-8").splitlines()
            if line.startswith("btime ")
        )
        boot_seconds = int(boot_line.split()[1])
        clock_ticks = os.sysconf("SC_CLK_TCK")
    except (OSError, StopIteration, ValueError):
        return None
    if not isinstance(clock_ticks, int) or clock_ticks <= 0:
        return None
    return boot_seconds * 1000 + (int(ticks) * 1000 // clock_ticks)


def _iso_millis(value: object) -> str:
    """Project provider millisecond timestamps into the transcript timestamp shape."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return ""
    try:
        return datetime.fromtimestamp(value / 1000, UTC).isoformat().replace("+00:00", "Z")
    except (OverflowError, OSError, ValueError):
        return ""


def _runtime_card(
    *,
    source_type: str,
    native_id: str,
    cwd: str,
    title: str,
    evidence: str,
    catalog: str,
    execution: str,
    last_activity_at: str = "",
) -> dict[str, Any]:
    repo = Path(cwd).name or "workspace"
    agent = "Native Claude" if source_type == "claude" else "Native Codex"
    engine = "Claude Code" if source_type == "claude" else "Codex"
    return {
        "key": f"native:{source_type}:{native_id}",
        "title": f"{repo}: {title or f'{engine} session {native_id[:8]}'}",
        "agent": agent,
        "engine": engine,
        "model": "",
        "running": execution == "active",
        "native": True,
        "source_type": source_type,
        "native_session_id": native_id,
        "project_root": cwd,
        "last_activity_at": last_activity_at,
        "runtime_catalog": catalog,
        "runtime_execution": execution,
        "runtime_evidence": evidence,
    }


def _claude_runtime_sessions(
    home: Path, roots: Iterable[Path], proc_root: Path
) -> dict[str, dict[str, Any]]:
    """Read Claude's live PID registry, not its historical transcript directory."""
    sessions: dict[str, dict[str, Any]] = {}
    registry = home / ".claude" / "sessions"
    if not registry.is_dir():
        return sessions
    for path in registry.glob("*.json"):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(raw, dict):
            continue
        pid = raw.get("pid")
        native_id = str(raw.get("sessionId") or "")
        cwd = str(raw.get("cwd") or "")
        recorded_start = str(raw.get("procStart") or "")
        if (
            isinstance(pid, bool)
            or not isinstance(pid, int)
            or not native_id
            or not _in_scope(cwd, roots)
            or not recorded_start
            or _process_start(proc_root, pid) != recorded_start
        ):
            continue
        sessions[f"native:claude:{native_id}"] = _runtime_card(
            source_type="claude",
            native_id=native_id,
            cwd=cwd,
            title=str(raw.get("name") or ""),
            evidence="claude_session_registry",
            catalog="open",
            execution="active" if raw.get("status") == "busy" else "unknown",
            last_activity_at=_iso_millis(raw.get("statusUpdatedAt")),
        )
    return sessions


def _codex_runtime_sessions(
    home: Path, roots: Iterable[Path], proc_root: Path
) -> dict[str, dict[str, Any]]:
    """Read Codex's live child-process registry, which proves work not tab state."""
    path = home / ".codex" / "process_manager" / "chat_processes.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, list):
        return {}
    sessions: dict[str, dict[str, Any]] = {}
    for record in raw:
        if not isinstance(record, dict):
            continue
        pid = record.get("osPid")
        native_id = str(record.get("conversationId") or "")
        cwd = str(record.get("cwd") or "")
        recorded_start = record.get("startedAtMs")
        process_started_at = (
            _process_started_at_ms(proc_root, pid)
            if isinstance(pid, int) and not isinstance(pid, bool)
            else None
        )
        if (
            isinstance(pid, bool)
            or not isinstance(pid, int)
            or not native_id
            or not _in_scope(cwd, roots)
            or isinstance(recorded_start, bool)
            or not isinstance(recorded_start, int)
            or process_started_at is None
            or abs(process_started_at - recorded_start) > _CODEX_PROCESS_START_TOLERANCE_MS
        ):
            continue
        sessions[f"native:codex:{native_id}"] = _runtime_card(
            source_type="codex",
            native_id=native_id,
            cwd=cwd,
            title=str(record.get("chatTitle") or ""),
            evidence="codex_process_manager",
            catalog="observed",
            execution="active",
            last_activity_at=_iso_millis(record.get("updatedAtMs")),
        )
    return sessions


def discover_native_runtime_sessions(
    *, home: Path, roots: Iterable[Path], proc_root: Path = Path("/proc")
) -> dict[str, dict[str, Any]]:
    """Return provider sessions backed by a provider-owned live runtime record.

    Claude's registry establishes an open CLI session (and its busy/idle state).
    Codex's registry establishes only an executing child process, so it must not
    be projected as an open conversation after that process ends.
    """
    return {
        **_claude_runtime_sessions(home, roots, proc_root),
        **_codex_runtime_sessions(home, roots, proc_root),
    }


def _last_output_at(records: Iterable[dict[str, Any]], output_types: frozenset[str]) -> str:
    """Return the newest agent-output timestamp, or "" when none can be parsed.

    This mirrors the rule KiroCrew applies to its own slots: recency comes from
    the newest output record, never from file metadata. A transcript whose
    output records cannot be parsed leaves recency UNKNOWN — falling back to the
    mtime would reintroduce the drift this replaces, where a metadata-only write
    makes a long-idle session read as fresh.

    Sidechain records are excluded for the same reason KiroCrew excludes
    compaction notices: a subagent's output is not the parent's activity.

    Timestamps compare as strings because both providers emit the same
    UTC-suffixed ISO-8601 shape, so lexicographic order is chronological.
    """
    newest = ""
    for record in records:
        if record.get("type") not in output_types:
            continue
        if record.get("isSidechain") is True:
            continue
        stamp = record.get("timestamp")
        if isinstance(stamp, str) and stamp > newest:
            newest = stamp
    return newest


def _codex_session(path: Path, roots: Iterable[Path]) -> dict[str, Any] | None:
    native_id = cwd = model = ""
    records = _records(path)
    for record in records:
        if record.get("type") == "session_meta":
            payload = record.get("payload") or {}
            if isinstance(payload, dict):
                native_id = str(payload.get("id") or payload.get("session_id") or native_id)
                cwd = str(payload.get("cwd") or cwd)
        elif record.get("type") == "turn_context":
            payload = record.get("payload") or {}
            if isinstance(payload, dict):
                model = str(payload.get("model") or model)
                cwd = str(payload.get("cwd") or cwd)
    if not native_id or not _in_scope(cwd, roots):
        return None
    repo = Path(cwd).name or "workspace"
    return {
        "key": f"native:codex:{native_id}",
        "title": f"{repo}: Codex session {native_id[:8]}",
        "agent": "Native Codex",
        "engine": "Codex",
        "model": model,
        "running": False,
        "native": True,
        "source_type": "codex",
        "native_session_id": native_id,
        "project_root": cwd,
        "last_activity_at": _last_output_at(records, _CODEX_OUTPUT_TYPES),
    }


def _claude_session(path: Path, roots: Iterable[Path]) -> dict[str, Any] | None:
    native_id = cwd = title = model = ""
    records = _records(path)
    for record in records:
        if record.get("type") == "custom-title" and record.get("customTitle"):
            title = str(record["customTitle"])
        native_id = str(record.get("sessionId") or native_id)
        cwd = str(record.get("cwd") or cwd)
        message = record.get("message") or {}
        if isinstance(message, dict):
            model = str(message.get("model") or model)
    if not native_id or not _in_scope(cwd, roots):
        return None
    repo = Path(cwd).name or "workspace"
    return {
        "key": f"native:claude:{native_id}",
        "title": f"{repo}: {title or f'Claude session {native_id[:8]}'}",
        "agent": "Native Claude",
        "engine": "Claude Code",
        "model": model,
        "running": False,
        "native": True,
        "source_type": "claude",
        "native_session_id": native_id,
        "project_root": cwd,
        "last_activity_at": _last_output_at(records, _CLAUDE_OUTPUT_TYPES),
    }


def discover_native_sessions(
    *,
    home: Path | None = None,
    roots: Iterable[Path] | None = None,
    now: datetime | None = None,
    managed: Mapping[str, str] | None = None,
    proc_root: Path = Path("/proc"),
) -> list[dict[str, Any]]:
    """Return declared-scope Codex and Claude sessions in a common card shape.

    A session KiroCrew already manages is omitted: it is projected from its own
    dashboard slot, which carries the live checkpoint and an Open action, so
    emitting the native record too would show one conversation twice — once
    rich, once as a shadow that can never hold a checkpoint. Runtime-backed
    provider sessions are included even when no recent transcript file remains;
    transcript discovery otherwise supplies history only, never liveness.
    """
    home = home or Path.home()
    now = now or datetime.now(UTC)
    scope_roots = list(roots) if roots is not None else load_scope_roots(home)
    if not scope_roots:
        return []
    owned = load_managed_native_sessions(home) if managed is None else managed

    runtime_sessions = discover_native_runtime_sessions(
        home=home, roots=scope_roots, proc_root=proc_root
    )
    sessions = {
        key: record
        for key, record in runtime_sessions.items()
        if record["native_session_id"] not in owned
    }

    def add_transcript(record: dict[str, Any]) -> None:
        if record["native_session_id"] in owned:
            return
        runtime = sessions.get(record["key"])
        if runtime is None:
            sessions[record["key"]] = record
            return
        # Transcript metadata gives the human-facing title/model; the runtime
        # registry alone may establish execution or an open provider process.
        sessions[record["key"]] = {
            **runtime,
            **record,
            **{
                field: runtime[field]
                for field in (
                    "running",
                    "runtime_catalog",
                    "runtime_execution",
                    "runtime_evidence",
                )
                if field in runtime
            },
        }

    for path in _recent_files(home / ".codex" / "sessions", now):
        record = _codex_session(path, scope_roots)
        if record is not None:
            add_transcript(record)
    for path in _recent_files(home / ".claude" / "projects", now, "*/*.jsonl"):
        record = _claude_session(path, scope_roots)
        if record is not None:
            add_transcript(record)
    return sorted(sessions.values(), key=lambda item: item["last_activity_at"], reverse=True)
