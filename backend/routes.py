"""Authenticated, app-scoped checkpoint routes for Multiplex."""

from __future__ import annotations

import asyncio
import json
import importlib.util
import logging
import re
import sys
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aiohttp import web
from kiro_crew.autonudge import get_instance
from kiro_crew.apps.context import AppContext
from kiro_crew.apps.route_registry import AppRoute

logger = logging.getLogger(__name__)


def _load_native_session_adapter():
    """External app route modules are loaded without a package context."""
    source = Path(__file__).with_name("external_sessions.py")
    spec = importlib.util.spec_from_file_location(
        "_multiplex_external_sessions", source
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("native session adapter could not be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_native_session_adapter = _load_native_session_adapter()
discover_native_sessions = _native_session_adapter.discover_native_sessions
load_scope_roots = _native_session_adapter.load_scope_roots


def _load_session_presence():
    """Load the app-local presence contract without relying on package installation."""
    source = Path(__file__).with_name("session_presence.py")
    spec = importlib.util.spec_from_file_location("_multiplex_session_presence", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("session presence adapter could not be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


session_presence = _load_session_presence()


_MAX_CHECKPOINTS = 200
_MAX_REGISTERED_NATIVE_SESSIONS = 200
_MAX_TRACKED_NATIVE_SESSIONS = 200
_MAX_MAIN_ITEMS = 4
_MAX_TRAIL_ITEMS = 7
_MAX_BASIS_RECORDS = 8
_ALLOWED_STATES = frozenset(
    {"unattended", "active", "awaiting_attention", "paused", "failed"}
)
_ALLOWED_ATTENTION = frozenset({"none", "unassigned", "claimed", "resolved"})
# What an attention entry is ABOUT. "decision" marks one a reader must not treat
# as settled by its presence alone — it is raised, owned and resolved through the
# same claimed/resolved lifecycle as any other attention, deliberately: that
# handoff is the part of this contract that works, and a material decision has
# the same shape. A second parallel lifecycle would be a thing to justify, not
# assume.
_ALLOWED_ATTENTION_KINDS = frozenset({"none", "decision"})
_ALLOWED_SOURCE_KINDS = frozenset({"observed", "asserted", "relayed"})
_ALLOWED_BASIS_KINDS = frozenset(
    {"commit", "channel_message", "canonical_record"}
)
_ALLOWED_PROGRESS_KINDS = frozenset({"none", "plan", "goal"})
_NATIVE_SOURCES = frozenset({"antigravity", "claude", "codex"})
_REGISTERABLE_NATIVE_SOURCES = frozenset({"antigravity"})
_NATIVE_EVENT_STATES = {
    "session_started": "active",
    "session_resumed": "active",
    "subagent_started": "active",
    "subagent_stopped": "active",
    "session_ended": "unattended",
}
_WORKFLOW_STATUSES = frozenset({"running", "finished", "failed", "cancelled"})
_MAX_WORKFLOW_RUNS = 200
_STORE_LOCK = threading.Lock()
_STORE_KEY = "checkpoints"
_NATIVE_SESSION_KEY = re.compile(
    r"^native:(antigravity|claude|codex):([A-Za-z0-9_.-]{1,160})$"
)


def _empty_store() -> dict[str, Any]:
    return {
        "schema_version": 3,
        "checkpoints": {},
        "registered_native_sessions": {},
        "tracked_native_sessions": {},
    }


def _require_user(request: web.Request) -> None:
    if request.get("user") is None:
        raise web.HTTPUnauthorized(text="dashboard authentication required")


def _require_multiplex_producer(request: web.Request) -> None:
    _require_user(request)
    if request.get("app") != "multiplex":
        raise web.HTTPForbidden(text="a Multiplex app credential is required")


def _storage(ctx: AppContext):
    if ctx.storage is None:
        raise web.HTTPServiceUnavailable(text="checkpoint storage is unavailable")
    return ctx.storage


def _read_store(ctx: AppContext) -> dict[str, Any]:
    payload = _storage(ctx).get(_STORE_KEY)
    if payload is None:
        return _empty_store()
    if not isinstance(payload, dict) or not isinstance(
        payload.get("checkpoints"), dict
    ):
        raise web.HTTPServiceUnavailable(
            text="checkpoint storage has an unsupported format"
        )
    return payload


def _make_room_for_checkpoint(checkpoints: dict[str, Any], session_key: str) -> None:
    """Drop the least recently updated checkpoints so a new key can be stored.

    The cap bounds the store; it was never meant to close it. Every key names one
    session and sessions are disposable, so a store that only grows reaches the
    cap once and then refuses every session started after it -- observed between
    2026-09-06 and 2026-09-10, when the store sat at exactly _MAX_CHECKPOINTS and
    no session could record anything at all. Evicting keeps both the bound and
    the ability to write.

    An entry with no ``updated_at`` sorts first: it predates the field, so it is
    the oldest thing present rather than the newest.
    """
    if session_key in checkpoints or len(checkpoints) < _MAX_CHECKPOINTS:
        return
    oldest_first = sorted(
        checkpoints,
        key=lambda key: str((checkpoints[key] or {}).get("updated_at") or ""),
    )
    for key in oldest_first:
        if len(checkpoints) < _MAX_CHECKPOINTS:
            break
        checkpoints.pop(key, None)
        logger.info("Evicted checkpoint %s to admit %s", key, session_key)


def _native_key(source: str, native_id: str) -> str:
    if source not in _NATIVE_SOURCES or not re.fullmatch(
        r"[A-Za-z0-9_.-]{1,160}", native_id
    ):
        raise web.HTTPBadRequest(text="native session identity is invalid")
    return f"native:{source}:{native_id}"


def _optional_absolute_path(value: Any, field: str) -> str:
    if value is None or value == "":
        return ""
    path = _required_text(value, field, 1_000)
    if not Path(path).is_absolute():
        raise ValueError(f"{field} must be absolute")
    return str(Path(path).resolve(strict=False))


def _path_is_in_scope(path: str) -> bool:
    candidate = Path(path)
    for root in load_scope_roots(Path.home()):
        resolved_root = root.resolve(strict=False)
        if candidate == resolved_root or candidate.is_relative_to(resolved_root):
            return True
    return False


def _registered_native_sessions(store: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Load only validated provider records explicitly registered by an app producer."""
    raw = store.get("registered_native_sessions")
    if not isinstance(raw, dict):
        return {}
    sessions: dict[str, dict[str, Any]] = {}
    for key, record in raw.items():
        match = _NATIVE_SESSION_KEY.fullmatch(key) if isinstance(key, str) else None
        if match is None or match.group(1) not in _REGISTERABLE_NATIVE_SOURCES:
            continue
        if not isinstance(record, dict):
            continue
        project_root = record.get("project_root")
        if not isinstance(project_root, str) or not Path(project_root).is_absolute():
            continue
        sessions[key] = {
            "key": key,
            "title": str(record.get("title") or "")[:500],
            "agent": "Native Antigravity",
            "engine": "Antigravity (Gemini)",
            "model": str(record.get("model") or "")[:500],
            "native": True,
            "running": False,
            "source_type": "antigravity",
            "native_session_id": match.group(2),
            "project_root": project_root,
            "transcript_path": str(record.get("transcript_path") or "")[:1_000],
            "last_activity_at": str(record.get("last_seen_at") or ""),
            "runtime_catalog": "observed",
            "runtime_execution": "unknown",
            "runtime_evidence": "antigravity_hook",
        }
    return sessions


def _available_native_sessions(
    store: dict[str, Any], discovered: list[dict[str, Any]] | None = None
) -> list[dict[str, Any]]:
    """Join discovered and registered sessions without allowing registration to overwrite runtime facts.

    ``discovered`` lets an async caller perform the sweep off the event loop and
    hand the result in. That sweep globs two session trees and reads the head
    and tail of every recent transcript; run inline it has outrun the gateway's
    30s loop-stall threshold and the watchdog killed the process, three times on
    2026-08-31. It is a parameter rather than a cache because a session that
    ends must leave the card on the next request, not one window later.
    """
    sessions = {
        str(session.get("key")): session
        for session in (discover_native_sessions() if discovered is None else discovered)
        if isinstance(session, dict) and isinstance(session.get("key"), str)
    }
    for key, session in _registered_native_sessions(store).items():
        sessions.setdefault(key, session)
    return list(sessions.values())


def _registered_native_record(
    source: str, native_id: str, payload: dict[str, Any]
) -> dict[str, str]:
    if source not in _REGISTERABLE_NATIVE_SOURCES:
        raise web.HTTPNotFound(text="native source does not support registration")
    workspace = _optional_absolute_path(payload.get("workspace_path"), "workspace_path")
    if not workspace:
        raise ValueError("workspace_path is required")
    if not _path_is_in_scope(workspace):
        raise ValueError("workspace_path is outside declared scope")
    title = _optional_text(payload.get("title"), "title", 500)
    model = _optional_text(payload.get("model"), "model", 500)
    transcript = _optional_absolute_path(payload.get("transcript_path"), "transcript_path")
    return {
        "key": _native_key(source, native_id),
        "title": title or f"{Path(workspace).name}: Antigravity session {native_id[:8]}",
        "model": model,
        "project_root": workspace,
        "transcript_path": transcript,
        "last_seen_at": datetime.now(UTC).isoformat(),
    }


def _tracked_native_sessions(store: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Return validated operator-tracked native cards from app-owned storage."""
    raw = store.get("tracked_native_sessions")
    if not isinstance(raw, dict):
        return {}
    tracked: dict[str, dict[str, str]] = {}
    for key, record in raw.items():
        if not isinstance(key, str) or _NATIVE_SESSION_KEY.fullmatch(key) is None:
            continue
        if not isinstance(record, dict):
            continue
        tracked[key] = {
            field: value[:500]
            for field, value in record.items()
            if field
            in {
                "key",
                "title",
                "agent",
                "engine",
                "model",
                "source_type",
                "native_session_id",
                "project_root",
                "last_activity_at",
                "tracked_at",
                "tracked_by",
            }
            and isinstance(value, str)
        }
    return tracked


def _native_snapshot(session: dict[str, Any], *, viewer: str = "") -> dict[str, str]:
    """Keep only card metadata when a user elects to retain a native session."""
    key = session.get("key")
    if not isinstance(key, str) or _NATIVE_SESSION_KEY.fullmatch(key) is None:
        raise ValueError("unknown native session")
    snapshot = {
        field: str(session.get(field) or "")[:500]
        for field in (
            "key",
            "title",
            "agent",
            "engine",
            "model",
            "source_type",
            "native_session_id",
            "project_root",
            "last_activity_at",
        )
    }
    snapshot["tracked_at"] = datetime.now(UTC).isoformat()
    snapshot["tracked_by"] = viewer[:120]
    return snapshot


def _native_sessions_with_tracking(
    native_sessions: list[dict[str, Any]], store: dict[str, Any]
) -> list[dict[str, Any]]:
    """Merge observed native cards with explicit retention, never inferred openness."""
    tracked = _tracked_native_sessions(store)
    sessions: dict[str, dict[str, Any]] = {}
    for session in native_sessions:
        key = session.get("key")
        if not isinstance(key, str):
            continue
        sessions[key] = {**session, "tracked": key in tracked}
    for key, snapshot in tracked.items():
        if key in sessions:
            continue
        source_type = snapshot.get("source_type")
        native_id = snapshot.get("native_session_id")
        if source_type not in _NATIVE_SOURCES or not native_id:
            continue
        sessions[key] = {
            **snapshot,
            "key": key,
            "native": True,
            "running": False,
            "tracked": True,
        }
    return sorted(sessions.values(), key=lambda item: item.get("last_activity_at", ""), reverse=True)


def _required_text(value: Any, field: str, limit: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field} is required")
    if len(normalized) > limit:
        raise ValueError(f"{field} exceeds {limit} characters")
    return normalized


def _optional_text(value: Any, field: str, limit: int) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    normalized = value.strip()
    if len(normalized) > limit:
        raise ValueError(f"{field} exceeds {limit} characters")
    return normalized


def _string_list(value: Any, field: str, *, limit: int, item_limit: int) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > limit:
        raise ValueError(f"{field} must contain at most {limit} strings")
    return [_required_text(item, field, item_limit) for item in value]


def _basis(value: Any) -> list[dict[str, str]]:
    """Validate re-readable claim evidence without resolving it at ingest."""
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > _MAX_BASIS_RECORDS:
        raise ValueError(f"basis must contain at most {_MAX_BASIS_RECORDS} records")
    records: list[dict[str, str]] = []
    for raw in value:
        if not isinstance(raw, dict):
            raise ValueError("basis records must be objects")
        kind = _required_text(raw.get("kind"), "basis.kind", 32)
        if kind not in _ALLOWED_BASIS_KINDS:
            raise ValueError("basis.kind is not supported")
        records.append(
            {
                "kind": kind,
                "ref": _required_text(raw.get("ref"), "basis.ref", 200),
            }
        )
    return records


def _session_timeline(value: Any) -> list[dict[str, str]]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > _MAX_TRAIL_ITEMS:
        raise ValueError(
            f"session_timeline must contain at most {_MAX_TRAIL_ITEMS} entries"
        )
    entries: list[dict[str, str]] = []
    for raw in value:
        if not isinstance(raw, dict):
            raise ValueError("session_timeline entries must be objects")
        entries.append(
            {
                "text": _required_text(raw.get("text"), "session_timeline.text", 220),
                "source": _optional_text(
                    raw.get("source"), "session_timeline.source", 48
                ),
                "timestamp": _optional_text(
                    raw.get("timestamp"), "session_timeline.timestamp", 64
                ),
            }
        )
    return entries


def _progress(value: Any) -> dict[str, Any]:
    if value is None:
        return {"kind": "none", "completed": 0, "total": 0, "label": ""}
    if not isinstance(value, dict):
        raise ValueError("progress must be an object")
    kind = _required_text(value.get("kind", "none"), "progress.kind", 16)
    if kind not in _ALLOWED_PROGRESS_KINDS:
        raise ValueError("progress.kind is not supported")
    completed = value.get("completed", 0)
    total = value.get("total", 0)
    if not isinstance(completed, int) or isinstance(completed, bool) or completed < 0:
        raise ValueError("progress.completed must be a non-negative integer")
    if not isinstance(total, int) or isinstance(total, bool) or total < 0:
        raise ValueError("progress.total must be a non-negative integer")
    if kind == "none" and (completed or total):
        raise ValueError("progress.kind none cannot have progress counts")
    if kind != "none" and (not total or completed > total):
        raise ValueError("progress must have a total no smaller than completed")
    return {
        "kind": kind,
        "completed": completed,
        "total": total,
        "label": _optional_text(value.get("label"), "progress.label", 160),
    }


def _validate_checkpoint(session_key: str, raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("checkpoint must be an object")
    if not session_key or len(session_key) > 256 or "\x00" in session_key:
        raise ValueError("session key is invalid")
    state = _required_text(raw.get("state"), "state", 32)
    if state not in _ALLOWED_STATES:
        raise ValueError("state is not supported")
    attention_raw = raw.get("attention") or {}
    if not isinstance(attention_raw, dict):
        raise ValueError("attention must be an object")
    attention_status = _required_text(
        attention_raw.get("status", "none"), "attention.status", 32
    )
    if attention_status not in _ALLOWED_ATTENTION:
        raise ValueError("attention.status is not supported")
    if attention_status in {"claimed", "resolved"}:
        raise ValueError("attention claims use the dedicated action endpoint")
    attention_kind = _required_text(
        attention_raw.get("kind", "none"), "attention.kind", 16
    )
    if attention_kind not in _ALLOWED_ATTENTION_KINDS:
        raise ValueError("attention.kind is not supported")
    decision_key = _optional_text(
        attention_raw.get("decision_key"), "attention.decision_key", 120
    )
    # A key on a non-decision entry names nothing and nothing would ever read it.
    # Rejecting is louder than dropping: the writer meant something by it.
    if decision_key and attention_kind != "decision":
        raise ValueError("attention.decision_key requires attention.kind 'decision'")
    source_kind = _required_text(
        raw.get("source_kind", "asserted"), "source_kind", 16
    )
    if source_kind not in _ALLOWED_SOURCE_KINDS:
        raise ValueError("source_kind is not supported")
    basis = _basis(raw.get("basis"))
    return {
        "session_key": session_key,
        "role": _required_text(raw.get("role"), "role", 120),
        "identity": _required_text(raw.get("identity"), "identity", 240),
        "engine": _optional_text(raw.get("engine"), "engine", 120),
        "model": _optional_text(raw.get("model"), "model", 120),
        "state": state,
        "goal": _optional_text(raw.get("goal"), "goal", 240),
        "next_action": _optional_text(raw.get("next_action"), "next_action", 160),
        "summary": _required_text(raw.get("summary"), "summary", 900),
        "main_items": _string_list(
            raw.get("main_items"), "main_items", limit=_MAX_MAIN_ITEMS, item_limit=160
        ),
        "trail": _string_list(
            raw.get("trail"), "trail", limit=_MAX_TRAIL_ITEMS, item_limit=220
        ),
        "session_timeline": _session_timeline(raw.get("session_timeline")),
        "progress": _progress(raw.get("progress")),
        "decision": _optional_text(raw.get("decision"), "decision", 360),
        "blocker": _optional_text(raw.get("blocker"), "blocker", 360),
        "canonical_record": _optional_text(
            raw.get("canonical_record"), "canonical_record", 500
        ),
        "changed_since_checkpoint": _string_list(
            raw.get("changed_since_checkpoint"),
            "changed_since_checkpoint",
            limit=12,
            item_limit=240,
        ),
        "source_links": _string_list(
            raw.get("source_links"), "source_links", limit=12, item_limit=500
        ),
        # This is server arrival time, not an assertion about when the writer
        # observed its evidence. Client input is deliberately ignored.
        "recorded_at": datetime.now(UTC).isoformat(),
        "source_kind": source_kind,
        "basis": basis,
        "attention": {
            "status": attention_status,
            "kind": attention_kind,
            "decision_key": decision_key,
            "claimed_by": "",
            "disposition": "",
        },
        "updated_at": datetime.now(UTC).isoformat(),
    }


def _changed_path_overlaps(checkpoints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Index exact path matches without inferring who changed or owns them.

    A checkpoint replaces its complete changed-path list atomically, so the
    index is deliberately not a chronology or a resolution signal.  The UI
    narrows these candidates to live cards before displaying anything.
    """
    sessions_by_path: dict[str, set[str]] = {}
    for checkpoint in checkpoints:
        session_key = checkpoint.get("session_key")
        if not isinstance(session_key, str) or not session_key:
            continue
        paths = checkpoint.get("changed_since_checkpoint")
        if not isinstance(paths, list):
            continue
        seen_paths: set[str] = set()
        for path in paths:
            if not isinstance(path, str) or not path or path in seen_paths:
                continue
            seen_paths.add(path)
            sessions_by_path.setdefault(path, set()).add(session_key)
    return [
        {"path": path, "session_keys": sorted(session_keys)}
        for path, session_keys in sorted(sessions_by_path.items())
        if len(session_keys) > 1
    ]


async def _list_checkpoints(request: web.Request, ctx: AppContext) -> web.Response:
    _require_user(request)
    with _STORE_LOCK:
        checkpoints = _read_store(ctx)["checkpoints"]
        ordered = sorted(
            checkpoints.values(),
            key=lambda record: record.get("updated_at", ""),
            reverse=True,
        )
    return web.json_response(
        {
            "checkpoints": [_checkpoint_view(record, request) for record in ordered],
            "changed_path_overlaps": _changed_path_overlaps(ordered),
        }
    )


async def _get_checkpoint(request: web.Request, ctx: AppContext) -> web.Response:
    _require_user(request)
    session_key = request.match_info["session_key"]
    with _STORE_LOCK:
        checkpoint = _read_store(ctx)["checkpoints"].get(session_key)
    if checkpoint is None:
        raise web.HTTPNotFound(text="checkpoint not found")
    return web.json_response({"checkpoint": _checkpoint_view(checkpoint, request)})


async def _put_checkpoint(request: web.Request, ctx: AppContext) -> web.Response:
    _require_user(request)
    session_key = request.match_info["session_key"]
    try:
        checkpoint = _validate_checkpoint(session_key, await request.json())
    except (json.JSONDecodeError, ValueError) as exc:
        raise web.HTTPBadRequest(text=str(exc)) from exc
    with _STORE_LOCK:
        store = _read_store(ctx)
        checkpoints = store["checkpoints"]
        _make_room_for_checkpoint(checkpoints, session_key)
        existing = checkpoints.get(session_key)
        existing_attention = (
            existing.get("attention") if isinstance(existing, dict) else None
        )
        if isinstance(existing_attention, dict) and existing_attention.get(
            "status"
        ) in {"claimed", "resolved"}:
            checkpoint["attention"] = existing_attention
        checkpoints[session_key] = checkpoint
        _storage(ctx).set(_STORE_KEY, store)
    return web.json_response({"checkpoint": checkpoint})


def _attention_state(checkpoint: dict[str, Any]) -> dict[str, str]:
    raw = checkpoint.get("attention")
    if not isinstance(raw, dict):
        raw = {}
    status = raw.get("status")
    if status not in _ALLOWED_ATTENTION:
        status = "none"
    # Checkpoints stored before attention carried a kind have neither key. They
    # read as an ordinary attention entry rather than being backfilled into a
    # decision they never declared.
    kind = raw.get("kind")
    if kind not in _ALLOWED_ATTENTION_KINDS:
        kind = "none"
    return {
        "status": status,
        "kind": kind,
        "decision_key": str(raw.get("decision_key") or "")[:120],
        "claimed_by": str(raw.get("claimed_by") or "")[:120],
        "claimed_at": str(raw.get("claimed_at") or "")[:64],
        "disposition": str(raw.get("disposition") or "")[:360],
        "resolved_by": str(raw.get("resolved_by") or "")[:120],
        "resolved_at": str(raw.get("resolved_at") or "")[:64],
    }


def _attention_transition(previous: dict[str, str], **fields: str) -> dict[str, str]:
    """Build the next attention dict, carrying the entry's identity across.

    Every transition rewrites this dict wholesale, so anything not named at the
    call site is dropped. ``kind`` and ``decision_key`` describe WHAT the entry
    is about and have to outlive a change in WHO owns it: a decision that loses
    its key the moment someone claims it stops being the decision anyone was
    tracking, which defeats putting decisions on this lifecycle at all. Routing
    every transition through here is what stops a fourth one from forgetting.
    """
    return {
        "kind": previous["kind"],
        "decision_key": previous["decision_key"],
        **fields,
    }


def _attention_conflict(checkpoint: dict[str, Any]) -> web.Response:
    return web.json_response(
        {"error": "attention is not available", "checkpoint": checkpoint}, status=409
    )


def _checkpoint_view(
    checkpoint: dict[str, Any], request: web.Request
) -> dict[str, Any]:
    """Add viewer-specific attention actions without persisting viewer state."""
    viewer = str(request.get("user") or "").strip()
    attention = _attention_state(checkpoint)
    claimed_by_viewer = (
        attention["status"] == "claimed" and attention["claimed_by"] == viewer
    )
    attention["can_claim"] = attention["status"] == "unassigned"
    attention["can_release"] = claimed_by_viewer
    attention["can_resolve"] = claimed_by_viewer
    return {**checkpoint, "attention": attention}


async def _post_attention_claim(request: web.Request, ctx: AppContext) -> web.Response:
    _require_user(request)
    session_key = request.match_info["session_key"]
    claimant = str(request["user"]).strip()
    if not claimant:
        raise web.HTTPUnauthorized(text="dashboard user identity is unavailable")
    with _STORE_LOCK:
        store = _read_store(ctx)
        checkpoint = store["checkpoints"].get(session_key)
        if checkpoint is None:
            raise web.HTTPNotFound(text="checkpoint not found")
        attention = _attention_state(checkpoint)
        if attention["status"] != "unassigned":
            return _attention_conflict(checkpoint)
        checkpoint["attention"] = _attention_transition(
            attention,
            status="claimed",
            claimed_by=claimant[:120],
            claimed_at=datetime.now(UTC).isoformat(),
            disposition="",
            resolved_by="",
            resolved_at="",
        )
        checkpoint["updated_at"] = datetime.now(UTC).isoformat()
        _storage(ctx).set(_STORE_KEY, store)
    return web.json_response({"checkpoint": checkpoint})


async def _post_attention_release(
    request: web.Request, ctx: AppContext
) -> web.Response:
    _require_user(request)
    session_key = request.match_info["session_key"]
    claimant = str(request["user"]).strip()
    with _STORE_LOCK:
        store = _read_store(ctx)
        checkpoint = store["checkpoints"].get(session_key)
        if checkpoint is None:
            raise web.HTTPNotFound(text="checkpoint not found")
        attention = _attention_state(checkpoint)
        if attention["status"] != "claimed":
            return _attention_conflict(checkpoint)
        if attention["claimed_by"] != claimant:
            raise web.HTTPForbidden(text="only the claimant may release attention")
        checkpoint["attention"] = _attention_transition(
            attention,
            status="unassigned",
            claimed_by="",
            claimed_at="",
            disposition="",
            resolved_by="",
            resolved_at="",
        )
        checkpoint["updated_at"] = datetime.now(UTC).isoformat()
        _storage(ctx).set(_STORE_KEY, store)
    return web.json_response({"checkpoint": checkpoint})


async def _post_attention_resolve(
    request: web.Request, ctx: AppContext
) -> web.Response:
    _require_user(request)
    session_key = request.match_info["session_key"]
    claimant = str(request["user"]).strip()
    try:
        disposition = _required_text(
            (await request.json()).get("disposition"), "disposition", 360
        )
    except (AttributeError, json.JSONDecodeError, ValueError) as exc:
        raise web.HTTPBadRequest(text=str(exc)) from exc
    with _STORE_LOCK:
        store = _read_store(ctx)
        checkpoint = store["checkpoints"].get(session_key)
        if checkpoint is None:
            raise web.HTTPNotFound(text="checkpoint not found")
        attention = _attention_state(checkpoint)
        if attention["status"] != "claimed":
            return _attention_conflict(checkpoint)
        if attention["claimed_by"] != claimant:
            raise web.HTTPForbidden(text="only the claimant may resolve attention")
        checkpoint["attention"] = _attention_transition(
            attention,
            status="resolved",
            claimed_by=claimant[:120],
            claimed_at=attention["claimed_at"],
            disposition=disposition,
            resolved_by=claimant[:120],
            resolved_at=datetime.now(UTC).isoformat(),
        )
        checkpoint["updated_at"] = datetime.now(UTC).isoformat()
        _storage(ctx).set(_STORE_KEY, store)
    return web.json_response({"checkpoint": checkpoint})


def _native_session(
    source: str,
    native_id: str,
    store: dict[str, Any],
    discovered: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    session_key = _native_key(source, native_id)
    for session in _available_native_sessions(store, discovered):
        if session.get("key") == session_key:
            return session
    raise web.HTTPNotFound(text="native session is not currently discoverable")


def _native_event_detail(value: Any) -> str:
    if value is None:
        return ""
    return _optional_text(value, "detail", 80)


def _native_event_trail(event: str, detail: str) -> str:
    action = {
        "session_started": "Session started.",
        "session_resumed": "Session resumed.",
        "subagent_started": "Subagent started.",
        "subagent_stopped": "Subagent finished.",
        "session_ended": "Session ended.",
    }[event]
    if event.startswith("subagent_") and detail:
        return f"Subagent {detail} {action.split()[-1]}"
    if event == "session_ended" and detail:
        return f"Session ended: {detail}."
    return action


def _timeline_entry(text: str, source: str) -> dict[str, str]:
    return {"text": text, "source": source, "timestamp": datetime.now(UTC).isoformat()}


def _checkpoint_timeline(checkpoint: dict[str, Any] | None) -> list[dict[str, str]]:
    if checkpoint is None:
        return []
    timeline = checkpoint.get("session_timeline")
    if timeline:
        return _session_timeline(timeline)
    return [_timeline_entry(text, "checkpoint") for text in checkpoint.get("trail", [])]


def _append_timeline(
    timeline: list[dict[str, str]], entry: dict[str, str]
) -> list[dict[str, str]]:
    if any(item["text"] == entry["text"] for item in timeline):
        return timeline[-_MAX_TRAIL_ITEMS:]
    return [*timeline, entry][-_MAX_TRAIL_ITEMS:]


def _append_trail(trail: list[str], text: str) -> list[str]:
    if text in trail:
        return trail[-_MAX_TRAIL_ITEMS:]
    return [*trail, text][-_MAX_TRAIL_ITEMS:]


def _append_checkpoint_trail(
    timeline: list[dict[str, str]], trail: list[str]
) -> list[dict[str, str]]:
    for text in trail:
        timeline = _append_timeline(timeline, _timeline_entry(text, "checkpoint"))
    return timeline


def _default_native_checkpoint(
    session: dict[str, Any], state: str, trail: str
) -> dict[str, Any]:
    checkpoint = _validate_checkpoint(
        session["key"],
        {
            "role": session["agent"],
            "identity": session["title"],
            "engine": session["engine"],
            "model": session["model"],
            "state": state,
            "summary": f"{session['agent']} session is active.",
            "main_items": [],
            "trail": [trail],
            "progress": {"kind": "none", "completed": 0, "total": 0, "label": ""},
            "attention": {"status": "none"},
        },
    )
    checkpoint["session_timeline"] = [_timeline_entry(trail, "native_lifecycle")]
    return checkpoint


async def _put_native_session(request: web.Request, ctx: AppContext) -> web.Response:
    """Register a bounded provider-owned session before it may publish updates."""
    _require_multiplex_producer(request)
    source = request.match_info["source"]
    native_id = request.match_info["native_id"]
    try:
        raw = await request.json()
        if not isinstance(raw, dict):
            raise ValueError("native session must be an object")
        record = _registered_native_record(source, native_id, raw)
    except (json.JSONDecodeError, ValueError) as exc:
        raise web.HTTPBadRequest(text=str(exc)) from exc
    with _STORE_LOCK:
        store = _read_store(ctx)
        entries = store.setdefault("registered_native_sessions", {})
        if not isinstance(entries, dict):
            raise web.HTTPServiceUnavailable(
                text="native registration storage is unsupported"
            )
        current = entries.get(record["key"])
        created = current is None
        if created and len(entries) >= _MAX_REGISTERED_NATIVE_SESSIONS:
            raise web.HTTPConflict(text="native registration capacity reached")
        previous_event = ""
        if isinstance(current, dict):
            stable = ("key", "project_root", "transcript_path")
            if any(str(current.get(field) or "") != record[field] for field in stable):
                raise web.HTTPConflict(text="native session identity cannot change")
            previous_event = str(current.get("last_event") or "")
            if previous_event in _NATIVE_EVENT_STATES:
                record["last_event"] = previous_event
        entries[record["key"]] = record
        _storage(ctx).set(_STORE_KEY, store)
    return web.json_response(
        {
            "session": _registered_native_sessions(store)[record["key"]],
            "created": created,
            "last_event": previous_event,
        }
    )


async def _put_native_checkpoint(request: web.Request, ctx: AppContext) -> web.Response:
    _require_multiplex_producer(request)
    try:
        raw = await request.json()
        if not isinstance(raw, dict):
            raise ValueError("checkpoint must be an object")
    except (json.JSONDecodeError, ValueError) as exc:
        raise web.HTTPBadRequest(text=str(exc)) from exc
    # Off the loop: this globs two session trees and reads transcript edges.
    discovered = await asyncio.to_thread(discover_native_sessions)
    with _STORE_LOCK:
        store = _read_store(ctx)
        session = _native_session(
            request.match_info["source"],
            request.match_info["native_id"],
            store,
            discovered,
        )
        checkpoint = _validate_checkpoint(
            session["key"],
            {
                **raw,
                "role": session["agent"],
                "identity": session["title"],
                "engine": session["engine"],
                "model": session["model"],
            },
        )
        checkpoints = store["checkpoints"]
        current = checkpoints.get(session["key"])
        _make_room_for_checkpoint(checkpoints, session["key"])
        checkpoint["session_timeline"] = _append_checkpoint_trail(
            _checkpoint_timeline(current),
            checkpoint["trail"],
        )
        checkpoints[session["key"]] = checkpoint
        _storage(ctx).set(_STORE_KEY, store)
    return web.json_response({"checkpoint": checkpoint})


async def _post_native_event(request: web.Request, ctx: AppContext) -> web.Response:
    _require_multiplex_producer(request)
    try:
        raw = await request.json()
        if not isinstance(raw, dict):
            raise ValueError("native event must be an object")
        event = _required_text(raw.get("event"), "event", 32)
        if event not in _NATIVE_EVENT_STATES:
            raise ValueError("event is not supported")
        detail = _native_event_detail(raw.get("detail"))
    except (json.JSONDecodeError, ValueError) as exc:
        raise web.HTTPBadRequest(text=str(exc)) from exc

    # Off the loop: this globs two session trees and reads transcript edges.
    discovered = await asyncio.to_thread(discover_native_sessions)
    with _STORE_LOCK:
        store = _read_store(ctx)
        session = _native_session(
            request.match_info["source"],
            request.match_info["native_id"],
            store,
            discovered,
        )
        checkpoints = store["checkpoints"]
        current = checkpoints.get(session["key"])
        trail = _native_event_trail(event, detail)
        if current is None:
            _make_room_for_checkpoint(checkpoints, session["key"])
            checkpoint = _default_native_checkpoint(
                session, _NATIVE_EVENT_STATES[event], trail
            )
        else:
            checkpoint = _validate_checkpoint(
                session["key"],
                {
                    **current,
                    "role": session["agent"],
                    "identity": session["title"],
                    "engine": session["engine"],
                    "model": session["model"],
                    "state": _NATIVE_EVENT_STATES[event],
                    "trail": _append_trail(current.get("trail", []), trail),
                },
            )
            checkpoint["session_timeline"] = _append_timeline(
                _checkpoint_timeline(current),
                _timeline_entry(trail, "native_lifecycle"),
            )
        checkpoints[session["key"]] = checkpoint
        registered = store.get("registered_native_sessions")
        if isinstance(registered, dict) and session["key"] in registered:
            record = registered[session["key"]]
            if isinstance(record, dict):
                record["last_event"] = event
        _storage(ctx).set(_STORE_KEY, store)
    return web.json_response({"checkpoint": checkpoint})


def _goal_loop_objective(message: object) -> str:
    lines = [line.strip() for line in str(message or "").splitlines() if line.strip()]
    if not lines:
        return ""
    first = lines[0]
    if first.startswith("Goal:"):
        first = first.removeprefix("Goal:").strip()
    return first[:240]


def _runtime_snapshot(request: web.Request) -> dict[str, Any]:
    state = request.app.get("state")
    if state is None:
        raise web.HTTPServiceUnavailable(text="KiroCrew session runtime is unavailable")
    slots = getattr(state, "_slots", None)
    if not isinstance(slots, dict):
        raise web.HTTPServiceUnavailable(
            text="KiroCrew session runtime has an unsupported format"
        )
    subagents = getattr(state, "subagents", None)
    goal_service = get_instance()
    router = getattr(request.app, "router", None)
    return_handoff = router is not None and any(
        route.method == "POST"
        and route.resource.get_info().get("formatter")
        == "/api/chat/slots/{slot}/return-handoff"
        for route in router.routes()
    )

    sessions: dict[str, Any] = {}
    for key, slot in slots.items():
        active_subagents = []
        if subagents is not None:
            active_subagents = subagents.running_agents_for(f"dashboard:{key}")
        total_stages = getattr(slot, "_plan_stage_count", 0)
        tracker = getattr(slot, "_orch_tracker", None)
        plan: dict[str, Any] | None = None
        if total_stages:
            current_index = (
                getattr(tracker, "current_stage", 0) if tracker is not None else 0
            )
            plan = {
                "active": bool(getattr(slot, "_in_stage_execution", False)),
                "current": min(max(int(current_index) + 1, 1), total_stages),
                "total": total_stages,
                "goal": str(getattr(slot, "_plan_goal", ""))[:160],
            }
        goal: dict[str, Any] | None = None
        if goal_service is not None:
            loop = goal_service.get_by_slot(key)
            if loop is not None:
                goal = {
                    "active": bool(loop.active),
                    "cycle": int(loop.cycle_count),
                    "max_cycles": int(loop.max_cycles),
                    "objective": _goal_loop_objective(loop.message),
                }
        sessions[key] = {
            "capabilities": {"return_handoff": return_handoff},
            "agents_active": int(bool(getattr(slot, "running", False))),
            "subagents_active": len(active_subagents),
            "plan": plan,
            "goal": goal,
        }
    return {"sessions": sessions}


async def _get_runtime(request: web.Request, _: AppContext) -> web.Response:
    _require_user(request)
    return web.json_response(_runtime_snapshot(request))


async def _list_external_sessions(request: web.Request, ctx: AppContext) -> web.Response:
    _require_user(request)
    # Off the loop: this globs two session trees and reads transcript edges.
    discovered = await asyncio.to_thread(discover_native_sessions)
    with _STORE_LOCK:
        store = _read_store(ctx)
        sessions = _native_sessions_with_tracking(
            _available_native_sessions(store, discovered), store
        )
    return web.json_response({"sessions": sessions})


async def _post_native_tracking(request: web.Request, ctx: AppContext) -> web.Response:
    """Explicitly retain or release a native provider card; this is not a close action."""
    _require_user(request)
    session_key = request.match_info["session_key"]
    if _NATIVE_SESSION_KEY.fullmatch(session_key) is None:
        raise web.HTTPNotFound(text="native session not found")
    try:
        payload = await request.json()
    except json.JSONDecodeError as exc:
        raise web.HTTPBadRequest(text="tracking payload must be JSON") from exc
    tracked = payload.get("tracked") if isinstance(payload, dict) else None
    if not isinstance(tracked, bool):
        raise web.HTTPBadRequest(text="tracking payload requires a boolean tracked field")
    # Off the loop: this globs two session trees and reads transcript edges.
    discovered = await asyncio.to_thread(discover_native_sessions)
    with _STORE_LOCK:
        store = _read_store(ctx)
        native_sessions = {
            str(session.get("key")): session
            for session in _available_native_sessions(store, discovered)
            if isinstance(session, dict) and isinstance(session.get("key"), str)
        }
        entries = store.setdefault("tracked_native_sessions", {})
        if not isinstance(entries, dict):
            raise web.HTTPServiceUnavailable(text="native tracking storage is unsupported")
        if tracked:
            session = native_sessions.get(session_key)
            if session is None:
                raise web.HTTPNotFound(text="native session is no longer available to track")
            if session_key not in entries and len(entries) >= _MAX_TRACKED_NATIVE_SESSIONS:
                raise web.HTTPConflict(text="native tracking capacity reached")
            entries[session_key] = _native_snapshot(
                session, viewer=str(request.get("user") or "")
            )
        else:
            entries.pop(session_key, None)
        _storage(ctx).set(_STORE_KEY, store)
    return web.json_response({"session_key": session_key, "tracked": tracked})


async def _get_session_presence(request: web.Request, ctx: AppContext) -> web.Response:
    """Expose one lifecycle vocabulary for dashboard, provider, and saved records."""
    _require_user(request)
    state = request.app.get("state")
    if state is None or not hasattr(state, "serialize_slots"):
        raise web.HTTPServiceUnavailable(text="KiroCrew session runtime is unavailable")
    slots = state.serialize_slots()
    # Off the loop: this globs two session trees and reads transcript edges.
    discovered = await asyncio.to_thread(discover_native_sessions)
    with _STORE_LOCK:
        store = _read_store(ctx)
        native_sessions = _native_sessions_with_tracking(
            _available_native_sessions(store, discovered), store
        )
        checkpoints = list(store["checkpoints"].values())
    live_keys = {
        str(slot.get("key")) for slot in slots if isinstance(slot, dict) and slot.get("key")
    } | {
        str(session.get("key"))
        for session in native_sessions
        if isinstance(session, dict) and session.get("key")
    }
    records = [
        *(session_presence.dashboard_presence(slot) for slot in slots if isinstance(slot, dict)),
        *(session_presence.native_presence(session) for session in native_sessions if isinstance(session, dict)),
        *(
            session_presence.checkpoint_presence(checkpoint)
            for checkpoint in checkpoints
            if isinstance(checkpoint, dict) and checkpoint.get("session_key") not in live_keys
        ),
    ]
    return web.json_response({"sessions": session_presence.index_presence(records)})


def _workflow_run_view(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    run_id = raw.get("run_id")
    status = raw.get("status")
    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", run_id):
        return None
    if status not in _WORKFLOW_STATUSES:
        return None
    try:
        name = _optional_text(raw.get("name"), "workflow.name", 240)
        phase = _optional_text(raw.get("phase"), "workflow.phase", 160)
    except ValueError:
        return None
    event_count = raw.get("event_count", 0)
    agent_error_count = raw.get("agent_error_count", 0)
    if (
        isinstance(event_count, bool)
        or not isinstance(event_count, int)
        or not 0 <= event_count <= 100_000
        or isinstance(agent_error_count, bool)
        or not isinstance(agent_error_count, int)
        or not 0 <= agent_error_count <= 100_000
    ):
        return None
    return {
        "run_id": run_id,
        "name": name,
        "status": status,
        "phase": phase,
        "event_count": event_count,
        "agent_error_count": agent_error_count,
    }


async def _list_workflows(request: web.Request, _: AppContext) -> web.Response:
    _require_user(request)
    service = getattr(request.app.get("state"), "workflow_service", None)
    list_runs = getattr(service, "list_runs", None)
    if not callable(list_runs):
        return web.json_response({"runs": []})
    try:
        raw_runs = list_runs()
    except Exception:
        logger.warning("Multiplex could not list workflow runs", exc_info=True)
        return web.json_response({"runs": []})
    if not isinstance(raw_runs, list):
        return web.json_response({"runs": []})
    runs = [
        view
        for raw in raw_runs[:_MAX_WORKFLOW_RUNS]
        if (view := _workflow_run_view(raw))
    ]
    return web.json_response({"runs": runs})


def register_routes(_: AppContext) -> list[AppRoute]:
    return [
        AppRoute("GET", "/checkpoints", _list_checkpoints),
        AppRoute("GET", "/checkpoints/{session_key}", _get_checkpoint),
        AppRoute("PUT", "/checkpoints/{session_key}", _put_checkpoint),
        AppRoute(
            "POST", "/checkpoints/{session_key}/attention/claim", _post_attention_claim
        ),
        AppRoute(
            "POST",
            "/checkpoints/{session_key}/attention/release",
            _post_attention_release,
        ),
        AppRoute(
            "POST",
            "/checkpoints/{session_key}/attention/resolve",
            _post_attention_resolve,
        ),
        AppRoute(
            "PUT", "/native-checkpoints/{source}/{native_id}", _put_native_checkpoint
        ),
        AppRoute("PUT", "/native-sessions/{source}/{native_id}", _put_native_session),
        AppRoute("POST", "/native-events/{source}/{native_id}", _post_native_event),
        AppRoute("GET", "/runtime", _get_runtime),
        AppRoute("GET", "/external-sessions", _list_external_sessions),
        AppRoute("POST", "/external-sessions/{session_key}/tracking", _post_native_tracking),
        AppRoute("GET", "/session-presence", _get_session_presence),
        AppRoute("GET", "/workflows", _list_workflows),
    ]
