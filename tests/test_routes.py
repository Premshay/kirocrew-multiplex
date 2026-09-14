from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest
from aiohttp import web
from kiro_crew.apps.app_storage import AppStorage
from kiro_crew.apps.context import AppContext
from kiro_crew.apps.route_registry import AppRoute


@pytest.fixture()
def routes_module():
    path = Path(__file__).parents[1] / "backend" / "routes.py"
    package = types.ModuleType("multiplex_backend")
    package.__path__ = [str(path.parent)]
    sys.modules[package.__name__] = package
    spec = importlib.util.spec_from_file_location("multiplex_backend.routes", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def context(tmp_path):
    return AppContext(
        name="multiplex", data_dir=tmp_path, storage=AppStorage("multiplex", tmp_path)
    )


class FakeRequest(dict):
    def __init__(
        self,
        payload=None,
        *,
        session_key="atlas-review",
        source="codex",
        native_id="codex-123",
        user=True,
        user_id="operator",
        producer=None,
        app=None,
    ):
        super().__init__()
        if user:
            self["user"] = user_id
        if producer:
            self["app"] = producer
        self.match_info = {
            "session_key": session_key,
            "source": source,
            "native_id": native_id,
        }
        self._payload = payload
        self.app = app or {}

    async def json(self):
        return self._payload


def _payload(state="awaiting_attention"):
    return {
        "role": "Review",
        "identity": "atlas / PR #1677",
        "engine": "Claude Code",
        "model": "Opus",
        "state": state,
        "goal": "Review the Multiplex work-state implementation.",
        "next_action": "Publish the reviewed implementation.",
        "summary": "The docs change is ready for review.",
        "main_items": ["Review the state rule", "Prepare the handoff"],
        "trail": ["Started with the state rule.", "Found a rendered formatting issue."],
        "progress": {
            "kind": "plan",
            "completed": 1,
            "total": 2,
            "label": "Documentation pass",
        },
        "attention": {"status": "unassigned"},
    }


def _native_payload():
    return {
        "state": "active",
        "goal": "Verify the native checkpoint writer.",
        "summary": "The adapter write is being verified.",
        "main_items": ["Exercise identity binding"],
        "trail": ["Started native writer verification."],
        "progress": {"kind": "none", "completed": 0, "total": 0, "label": ""},
        "attention": {"status": "none"},
    }


def _native_event(event="subagent_started", detail="Explore"):
    return {"event": event, "detail": detail}


@pytest.mark.asyncio
async def test_checkpoint_round_trip_requires_dashboard_authentication(
    routes_module, context
):
    with pytest.raises(web.HTTPUnauthorized):
        await routes_module._put_checkpoint(
            FakeRequest(_payload(), user=False), context
        )
    with pytest.raises(web.HTTPUnauthorized):
        await routes_module._get_runtime(FakeRequest(user=False), context)

    response = await routes_module._put_checkpoint(FakeRequest(_payload()), context)
    stored = json.loads(response.body)
    assert stored["checkpoint"]["session_key"] == "atlas-review"
    assert stored["checkpoint"]["updated_at"]
    assert stored["checkpoint"]["recorded_at"]
    assert stored["checkpoint"]["source_kind"] == "asserted"
    assert stored["checkpoint"]["basis"] == []
    assert (
        stored["checkpoint"]["goal"]
        == "Review the Multiplex work-state implementation."
    )
    assert stored["checkpoint"]["next_action"] == "Publish the reviewed implementation."
    assert stored["checkpoint"]["trail"] == [
        "Started with the state rule.",
        "Found a rendered formatting issue.",
    ]

    listed = await routes_module._list_checkpoints(FakeRequest(), context)
    assert json.loads(listed.body)["checkpoints"][0]["identity"] == "atlas / PR #1677"
    assert (context.data_dir / "kv" / "checkpoints.json").is_file()


@pytest.mark.asyncio
async def test_checkpoint_list_indexes_exact_changed_path_overlaps(
    routes_module, context
):
    first = {**_payload("active"), "changed_since_checkpoint": ["backend/routes.py"]}
    second = {
        **_payload("active"),
        "changed_since_checkpoint": ["backend/routes.py", "ui/index.mjs"],
    }
    historical = {
        **_payload("unattended"),
        "changed_since_checkpoint": ["backend/routes.py"],
    }
    await routes_module._put_checkpoint(
        FakeRequest(first, session_key="first"), context
    )
    await routes_module._put_checkpoint(
        FakeRequest(second, session_key="second"), context
    )
    await routes_module._put_checkpoint(
        FakeRequest(historical, session_key="historical"), context
    )

    response = await routes_module._list_checkpoints(FakeRequest(), context)
    overlaps = json.loads(response.body)["changed_path_overlaps"]

    assert overlaps == [
        {
            "path": "backend/routes.py",
            "session_keys": ["first", "historical", "second"],
        }
    ]


def test_changed_path_overlap_index_ignores_malformed_legacy_entries(routes_module):
    overlaps = routes_module._changed_path_overlaps(
        [
            {
                "session_key": "first",
                "changed_since_checkpoint": ["backend/routes.py", {"not": "a path"}],
            },
            {
                "session_key": "second",
                "changed_since_checkpoint": ["backend/routes.py", "backend/routes.py"],
            },
        ]
    )

    assert overlaps == [
        {"path": "backend/routes.py", "session_keys": ["first", "second"]}
    ]


@pytest.mark.asyncio
async def test_checkpoint_rejects_unknown_state(routes_module, context):
    with pytest.raises(web.HTTPBadRequest) as raised:
        await routes_module._put_checkpoint(FakeRequest(_payload("unknown")), context)
    assert raised.value.text == "state is not supported"


def test_attention_defaults_to_no_kind(routes_module):
    """A payload that says nothing about kind is not a decision."""
    stored = routes_module._validate_checkpoint("s", _payload())
    assert stored["attention"]["kind"] == "none"
    assert stored["attention"]["decision_key"] == ""


def test_decision_kind_carries_its_key(routes_module):
    payload = _payload()
    payload["attention"] = {
        "status": "unassigned",
        "kind": "decision",
        "decision_key": "knowledge-pool-binding",
    }
    stored = routes_module._validate_checkpoint("s", payload)
    assert stored["attention"]["kind"] == "decision"
    assert stored["attention"]["decision_key"] == "knowledge-pool-binding"


def test_decision_key_without_decision_kind_is_rejected(routes_module):
    # Silently dropping it would leave the writer believing a key was recorded.
    payload = _payload()
    payload["attention"] = {"status": "unassigned", "decision_key": "orphan-key"}
    with pytest.raises(ValueError, match="decision_key requires"):
        routes_module._validate_checkpoint("s", payload)


def test_unknown_attention_kind_is_rejected(routes_module):
    payload = _payload()
    payload["attention"] = {"status": "unassigned", "kind": "verdict"}
    with pytest.raises(ValueError, match="attention.kind is not supported"):
        routes_module._validate_checkpoint("s", payload)


def test_checkpoint_stamps_arrival_and_ignores_client_timestamp(routes_module):
    payload = _payload()
    payload.update(
        {
            "recorded_at": "1999-01-01T00:00:00+00:00",
            "source_kind": "observed",
            "basis": [{"kind": "commit", "ref": "6e0f1637"}],
        }
    )

    stored = routes_module._validate_checkpoint("s", payload)

    assert stored["recorded_at"] != payload["recorded_at"]
    assert stored["source_kind"] == "observed"
    assert stored["basis"] == [{"kind": "commit", "ref": "6e0f1637"}]


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("source_kind", "heard", "source_kind is not supported"),
        ("basis", [{"kind": "ticket", "ref": "x"}], "basis.kind is not supported"),
        ("basis", [{"kind": "commit", "ref": ""}], "basis.ref is required"),
    ],
)
def test_checkpoint_rejects_unverifiable_provenance(routes_module, field, value, error):
    payload = _payload()
    payload[field] = value

    with pytest.raises(ValueError, match=error):
        routes_module._validate_checkpoint("s", payload)


def test_stored_checkpoint_without_kind_still_renders(routes_module):
    """Back-compat: records written before attention carried a kind read as an
    ordinary entry, never backfilled into a decision they never declared."""
    legacy = {"attention": {"status": "unassigned", "claimed_by": "", "disposition": ""}}
    state = routes_module._attention_state(legacy)
    assert state["status"] == "unassigned"
    assert state["kind"] == "none"
    assert state["decision_key"] == ""


def test_decision_reuses_the_claim_lifecycle_without_a_second_one(routes_module):
    """Decisions are raised/owned/resolved through attention's own statuses, so a
    checkpoint write still cannot mint a claim — the dedicated endpoint owns it."""
    payload = _payload()
    payload["attention"] = {
        "status": "claimed",
        "kind": "decision",
        "decision_key": "knowledge-pool-binding",
    }
    with pytest.raises(ValueError, match="dedicated action endpoint"):
        routes_module._validate_checkpoint("s", payload)


@pytest.mark.parametrize(
    "transition",
    [
        {"status": "claimed", "claimed_by": "operator"},
        {"status": "unassigned", "claimed_by": ""},
        {"status": "resolved", "claimed_by": "operator", "disposition": "done"},
    ],
)
def test_every_transition_keeps_the_decision_identity(routes_module, transition):
    """Ownership changes; what the entry is ABOUT does not.

    Each transition rewrites the attention dict wholesale, so a decision that
    loses its key on claim stops being the decision anyone was tracking — which
    is the whole reason decisions ride this lifecycle.
    """
    previous = {
        "status": "unassigned",
        "kind": "decision",
        "decision_key": "knowledge-pool-binding",
        "claimed_by": "",
        "claimed_at": "",
        "disposition": "",
        "resolved_by": "",
        "resolved_at": "",
    }
    nxt = routes_module._attention_transition(previous, **transition)
    assert nxt["kind"] == "decision"
    assert nxt["decision_key"] == "knowledge-pool-binding"
    assert nxt["status"] == transition["status"]


def test_transition_leaves_an_ordinary_entry_ordinary(routes_module):
    previous = routes_module._attention_state({"attention": {"status": "unassigned"}})
    nxt = routes_module._attention_transition(previous, status="claimed")
    assert nxt["kind"] == "none"
    assert nxt["decision_key"] == ""


@pytest.mark.asyncio
async def test_claim_release_resolve_preserve_a_decision_key(routes_module, context):
    """The wiring, not just the helper: drive all three handlers in sequence.

    This is the case the shipped slice got wrong — the helper is only a fix if
    every transition actually routes through it.
    """
    payload = _payload()
    payload["attention"] = {
        "status": "unassigned",
        "kind": "decision",
        "decision_key": "knowledge-pool-binding",
    }
    await routes_module._put_checkpoint(FakeRequest(payload), context)

    for handler, request in (
        (routes_module._post_attention_claim, FakeRequest(user_id="alice")),
        (routes_module._post_attention_release, FakeRequest(user_id="alice")),
        (routes_module._post_attention_claim, FakeRequest(user_id="alice")),
        (
            routes_module._post_attention_resolve,
            FakeRequest({"disposition": "settled"}, user_id="alice"),
        ),
    ):
        attention = json.loads((await handler(request, context)).body)["checkpoint"][
            "attention"
        ]
        assert attention["kind"] == "decision"
        assert attention["decision_key"] == "knowledge-pool-binding"


def test_route_registration_uses_relative_app_routes(routes_module, context):
    routes = routes_module.register_routes(context)
    assert [(route.method, route.path) for route in routes] == [
        ("GET", "/checkpoints"),
        ("GET", "/checkpoints/{session_key}"),
        ("PUT", "/checkpoints/{session_key}"),
        ("POST", "/checkpoints/{session_key}/attention/claim"),
        ("POST", "/checkpoints/{session_key}/attention/release"),
        ("POST", "/checkpoints/{session_key}/attention/resolve"),
        ("PUT", "/native-checkpoints/{source}/{native_id}"),
        ("PUT", "/native-sessions/{source}/{native_id}"),
        ("POST", "/native-events/{source}/{native_id}"),
        ("GET", "/runtime"),
        ("GET", "/external-sessions"),
        ("POST", "/external-sessions/{session_key}/tracking"),
        ("GET", "/session-presence"),
        ("GET", "/workflows"),
    ]
    assert all(isinstance(route, AppRoute) for route in routes)


@pytest.mark.asyncio
async def test_attention_claim_transition_derives_claimant_and_requires_release(
    routes_module, context
):
    await routes_module._put_checkpoint(FakeRequest(_payload()), context)

    claimed = await routes_module._post_attention_claim(
        FakeRequest(user_id="alice"), context
    )
    claimed_checkpoint = json.loads(claimed.body)["checkpoint"]
    assert claimed_checkpoint["attention"]["status"] == "claimed"
    assert claimed_checkpoint["attention"]["claimed_by"] == "alice"
    assert claimed_checkpoint["attention"]["claimed_at"]

    conflict = await routes_module._post_attention_claim(
        FakeRequest(user_id="bob"), context
    )
    assert conflict.status == 409
    assert json.loads(conflict.body)["checkpoint"]["attention"]["claimed_by"] == "alice"
    with pytest.raises(web.HTTPForbidden):
        await routes_module._post_attention_release(FakeRequest(user_id="bob"), context)

    alice_view = json.loads(
        (
            await routes_module._list_checkpoints(FakeRequest(user_id="alice"), context)
        ).body
    )
    bob_view = json.loads(
        (
            await routes_module._list_checkpoints(FakeRequest(user_id="bob"), context)
        ).body
    )
    alice_attention = alice_view["checkpoints"][0]["attention"]
    bob_attention = bob_view["checkpoints"][0]["attention"]
    assert {
        key: alice_attention[key]
        for key in ("status", "claimed_by", "can_claim", "can_release", "can_resolve")
    } == {
        "status": "claimed",
        "claimed_by": "alice",
        "can_claim": False,
        "can_release": True,
        "can_resolve": True,
    }
    assert {
        key: bob_attention[key]
        for key in ("status", "claimed_by", "can_claim", "can_release", "can_resolve")
    } == {
        "status": "claimed",
        "claimed_by": "alice",
        "can_claim": False,
        "can_release": False,
        "can_resolve": False,
    }

    released = await routes_module._post_attention_release(
        FakeRequest(user_id="alice"), context
    )
    assert json.loads(released.body)["checkpoint"]["attention"] == {
        "status": "unassigned",
        "kind": "none",
        "decision_key": "",
        "claimed_by": "",
        "claimed_at": "",
        "disposition": "",
        "resolved_by": "",
        "resolved_at": "",
    }


@pytest.mark.asyncio
async def test_attention_resolution_preserves_claimant_and_rejects_editor_forgery(
    routes_module, context
):
    await routes_module._put_checkpoint(FakeRequest(_payload()), context)
    await routes_module._post_attention_claim(FakeRequest(user_id="alice"), context)

    with pytest.raises(web.HTTPBadRequest):
        await routes_module._put_checkpoint(
            FakeRequest(
                {
                    **_payload(),
                    "attention": {"status": "claimed", "claimed_by": "mallory"},
                }
            ),
            context,
        )

    resolved = await routes_module._post_attention_resolve(
        FakeRequest(
            {"disposition": "Escalated to the release owner."}, user_id="alice"
        ),
        context,
    )
    attention = json.loads(resolved.body)["checkpoint"]["attention"]
    assert attention["status"] == "resolved"
    assert attention["claimed_by"] == "alice"
    assert attention["resolved_by"] == "alice"
    assert attention["disposition"] == "Escalated to the release owner."


@pytest.mark.asyncio
async def test_decision_identity_survives_attention_transitions(routes_module, context):
    payload = _payload()
    payload["attention"] = {
        "status": "unassigned",
        "kind": "decision",
        "decision_key": "embedder-thread-policy",
    }
    await routes_module._put_checkpoint(FakeRequest(payload), context)

    claimed = await routes_module._post_attention_claim(
        FakeRequest(user_id="alice"), context
    )
    assert json.loads(claimed.body)["checkpoint"]["attention"]["kind"] == "decision"

    resolved = await routes_module._post_attention_resolve(
        FakeRequest({"disposition": "Recorded."}, user_id="alice"), context
    )
    attention = json.loads(resolved.body)["checkpoint"]["attention"]
    assert attention["kind"] == "decision"
    assert attention["decision_key"] == "embedder-thread-policy"


def test_routes_load_without_a_package_context():
    path = Path(__file__).parents[1] / "backend" / "routes.py"
    spec = importlib.util.spec_from_file_location("_kirocrew_app_multiplex", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    assert callable(module.discover_native_sessions)


@pytest.mark.asyncio
async def test_external_sessions_require_dashboard_authentication(
    routes_module, context, monkeypatch
):
    monkeypatch.setattr(
        routes_module, "discover_native_sessions", lambda: [{"key": "native:codex:one"}]
    )
    with pytest.raises(web.HTTPUnauthorized):
        await routes_module._list_external_sessions(FakeRequest(user=False), None)
    response = await routes_module._list_external_sessions(FakeRequest(), context)
    assert json.loads(response.body) == {
        "sessions": [{"key": "native:codex:one", "tracked": False}]
    }


@pytest.mark.asyncio
async def test_native_tracking_is_explicit_and_retains_a_missing_transcript(
    routes_module, context, monkeypatch
):
    native = {
        "key": "native:codex:codex-123",
        "title": "project: Codex session codex-12",
        "agent": "Native Codex",
        "engine": "Codex",
        "model": "gpt-5.6",
        "source_type": "codex",
        "native_session_id": "codex-123",
        "project_root": "/work/project",
        "last_activity_at": "2026-08-12T10:00:00Z",
        "native": True,
        "running": False,
    }
    monkeypatch.setattr(routes_module, "discover_native_sessions", lambda: [native])

    tracked = await routes_module._post_native_tracking(
        FakeRequest({"tracked": True}, session_key=native["key"]), context
    )
    assert json.loads(tracked.body) == {"session_key": native["key"], "tracked": True}

    monkeypatch.setattr(routes_module, "discover_native_sessions", lambda: [])
    response = await routes_module._list_external_sessions(FakeRequest(), context)
    session = json.loads(response.body)["sessions"]
    assert len(session) == 1
    assert {field: session[0][field] for field in native} == native
    assert session[0]["tracked"] is True
    assert session[0]["tracked_by"] == "operator"
    assert session[0]["tracked_at"]

    released = await routes_module._post_native_tracking(
        FakeRequest({"tracked": False}, session_key=native["key"]), context
    )
    assert json.loads(released.body) == {"session_key": native["key"], "tracked": False}
    assert json.loads((await routes_module._list_external_sessions(FakeRequest(), context)).body) == {"sessions": []}


@pytest.mark.asyncio
async def test_session_presence_keeps_idle_dashboard_slots_open_and_native_observed(
    routes_module, context, monkeypatch
):
    class State:
        def serialize_slots(self):
            return [
                {
                    "key": "chat-5",
                    "running": False,
                    "workspace": "project",
                    "project": "/work/project",
                }
            ]

    monkeypatch.setattr(
        routes_module,
        "discover_native_sessions",
        lambda: [
            {
                "key": "native:codex:one",
                "source_type": "codex",
                "project_root": "/work/project/native",
            }
        ],
    )
    request = FakeRequest(app={"state": State()})
    with pytest.raises(web.HTTPUnauthorized):
        await routes_module._get_session_presence(FakeRequest(user=False), context)

    response = await routes_module._get_session_presence(request, context)
    sessions = json.loads(response.body)["sessions"]
    assert sessions["chat-5"]["catalog"] == "open"
    assert sessions["chat-5"]["execution"] == "idle"
    assert sessions["native:codex:one"]["catalog"] == "observed"
    assert sessions["native:codex:one"]["execution"] == "unknown"


@pytest.mark.asyncio
async def test_workflow_projection_requires_authentication_and_whitelists_compact_metadata(
    routes_module,
):
    class WorkflowService:
        def list_runs(self):
            return [
                {
                    "run_id": "wf_000003",
                    "name": "multiplex-first-run-v3",
                    "status": "finished",
                    "phase": "Verify",
                    "event_count": 9,
                    "agent_error_count": 0,
                    "result": {"secret": "must not project"},
                    "last_log": "must not project",
                },
                {"run_id": "bad id", "status": "finished"},
                {"run_id": "wf_000004", "status": "unknown"},
            ]

    request = FakeRequest(
        app={"state": types.SimpleNamespace(workflow_service=WorkflowService())}
    )
    with pytest.raises(web.HTTPUnauthorized):
        await routes_module._list_workflows(FakeRequest(user=False), None)
    response = await routes_module._list_workflows(request, None)
    assert json.loads(response.body) == {
        "runs": [
            {
                "run_id": "wf_000003",
                "name": "multiplex-first-run-v3",
                "status": "finished",
                "phase": "Verify",
                "event_count": 9,
                "agent_error_count": 0,
            }
        ],
    }


@pytest.mark.asyncio
async def test_native_checkpoint_requires_multiplex_app_credential_and_binds_identity(
    routes_module, context, monkeypatch
):
    native = {
        "key": "native:codex:codex-123",
        "agent": "Native Codex",
        "title": "project: Codex session codex-123",
        "engine": "Codex",
        "model": "gpt-5.6",
    }
    monkeypatch.setattr(routes_module, "discover_native_sessions", lambda: [native])
    with pytest.raises(web.HTTPForbidden):
        await routes_module._put_native_checkpoint(
            FakeRequest(_native_payload()), context
        )
    response = await routes_module._put_native_checkpoint(
        FakeRequest(_native_payload(), producer="multiplex"), context
    )
    checkpoint = json.loads(response.body)["checkpoint"]
    assert checkpoint["session_key"] == "native:codex:codex-123"
    assert checkpoint["identity"] == native["title"]
    assert checkpoint["engine"] == "Codex"
    assert checkpoint["goal"] == "Verify the native checkpoint writer."


@pytest.mark.asyncio
async def test_antigravity_registration_is_scoped_idempotent_and_uses_native_paths(
    routes_module, context, monkeypatch, tmp_path
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setattr(routes_module, "load_scope_roots", lambda _: [tmp_path])
    monkeypatch.setattr(routes_module, "discover_native_sessions", lambda: [])
    payload = {
        "workspace_path": str(workspace),
        "title": "Provider review",
        "model": "gemini-3-pro",
        "transcript_path": str(workspace / "session.jsonl"),
    }
    request = FakeRequest(
        payload, source="antigravity", native_id="conversation-123", producer="multiplex"
    )

    response = await routes_module._put_native_session(request, context)
    session = json.loads(response.body)["session"]
    assert session["key"] == "native:antigravity:conversation-123"
    assert session["project_root"] == str(workspace)
    assert session["runtime_evidence"] == "antigravity_hook"

    await routes_module._put_native_session(request, context)
    external = json.loads(
        (await routes_module._list_external_sessions(FakeRequest(), context)).body
    )["sessions"]
    assert [item["key"] for item in external] == [session["key"]]

    class State:
        def serialize_slots(self):
            return []

    presence = json.loads(
        (
            await routes_module._get_session_presence(
                FakeRequest(app={"state": State()}), context
            )
        ).body
    )["sessions"][session["key"]]
    assert (presence["catalog"], presence["execution"]) == ("observed", "unknown")

    checkpoint = json.loads(
        (
            await routes_module._put_native_checkpoint(
                FakeRequest(
                    _native_payload(),
                    source="antigravity",
                    native_id="conversation-123",
                    producer="multiplex",
                ),
                context,
            )
        ).body
    )["checkpoint"]
    assert checkpoint["engine"] == "Antigravity (Gemini)"
    assert checkpoint["identity"] == "Provider review"

    changed_scope = {**payload, "workspace_path": str(tmp_path)}
    with pytest.raises(web.HTTPConflict):
        await routes_module._put_native_session(
            FakeRequest(
                changed_scope,
                source="antigravity",
                native_id="conversation-123",
                producer="multiplex",
            ),
            context,
        )


@pytest.mark.asyncio
async def test_antigravity_registration_rejects_unscoped_workspace(
    routes_module, context, monkeypatch, tmp_path
):
    monkeypatch.setattr(routes_module, "load_scope_roots", lambda _: [tmp_path / "allowed"])
    with pytest.raises(web.HTTPBadRequest):
        await routes_module._put_native_session(
            FakeRequest(
                {"workspace_path": str(tmp_path / "outside")},
                source="antigravity",
                native_id="conversation-123",
                producer="multiplex",
            ),
            context,
        )


@pytest.mark.asyncio
async def test_antigravity_registration_is_bounded(
    routes_module, context, monkeypatch, tmp_path
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setattr(routes_module, "load_scope_roots", lambda _: [tmp_path])
    monkeypatch.setattr(routes_module, "_MAX_REGISTERED_NATIVE_SESSIONS", 1)
    payload = {"workspace_path": str(workspace)}
    await routes_module._put_native_session(
        FakeRequest(
            payload,
            source="antigravity",
            native_id="conversation-1",
            producer="multiplex",
        ),
        context,
    )

    with pytest.raises(web.HTTPConflict):
        await routes_module._put_native_session(
            FakeRequest(
                payload,
                source="antigravity",
                native_id="conversation-2",
                producer="multiplex",
            ),
            context,
        )


def test_checkpoint_accepts_legacy_records_without_goal_or_next_action(routes_module):
    payload = _payload()
    payload.pop("goal")
    payload.pop("next_action")

    checkpoint = routes_module._validate_checkpoint("atlas-review", payload)

    assert checkpoint["goal"] == ""
    assert checkpoint["next_action"] == ""


@pytest.mark.asyncio
async def test_native_checkpoint_rejects_undiscovered_identity(
    routes_module, context, monkeypatch
):
    monkeypatch.setattr(routes_module, "discover_native_sessions", lambda: [])
    with pytest.raises(web.HTTPNotFound):
        await routes_module._put_native_checkpoint(
            FakeRequest(_native_payload(), producer="multiplex"), context
        )


@pytest.mark.asyncio
async def test_native_event_preserves_story_and_appends_bounded_milestone(
    routes_module, context, monkeypatch
):
    native = {
        "key": "native:codex:codex-123",
        "agent": "Native Codex",
        "title": "project: Codex session codex-123",
        "engine": "Codex",
        "model": "gpt-5.6",
    }
    monkeypatch.setattr(routes_module, "discover_native_sessions", lambda: [native])
    await routes_module._put_native_checkpoint(
        FakeRequest(_native_payload(), producer="multiplex"), context
    )
    response = await routes_module._post_native_event(
        FakeRequest(_native_event(), producer="multiplex"), context
    )
    checkpoint = json.loads(response.body)["checkpoint"]
    assert checkpoint["summary"] == "The adapter write is being verified."
    assert checkpoint["goal"] == "Verify the native checkpoint writer."
    assert checkpoint["trail"] == [
        "Started native writer verification.",
        "Subagent Explore started.",
    ]
    assert [entry["text"] for entry in checkpoint["session_timeline"]] == [
        "Started native writer verification.",
        "Subagent Explore started.",
    ]
    assert [entry["source"] for entry in checkpoint["session_timeline"]] == [
        "checkpoint",
        "native_lifecycle",
    ]
    assert all(entry["timestamp"] for entry in checkpoint["session_timeline"])


@pytest.mark.asyncio
async def test_native_events_keep_an_ordered_bounded_structured_timeline(
    routes_module, context, monkeypatch
):
    native = {
        "key": "native:codex:codex-123",
        "agent": "Native Codex",
        "title": "project: Codex session codex-123",
        "engine": "Codex",
        "model": "gpt-5.6",
    }
    monkeypatch.setattr(routes_module, "discover_native_sessions", lambda: [native])
    events = [
        ("session_started", ""),
        ("session_resumed", ""),
        *[("subagent_started", f"worker-{index}") for index in range(7)],
    ]
    for event, detail in events:
        response = await routes_module._post_native_event(
            FakeRequest(_native_event(event, detail), producer="multiplex"),
            context,
        )

    checkpoint = json.loads(response.body)["checkpoint"]
    assert checkpoint["identity"] == native["title"]
    assert checkpoint["engine"] == "Codex"
    assert [entry["text"] for entry in checkpoint["session_timeline"]] == [
        f"Subagent worker-{index} started." for index in range(7)
    ]
    assert [entry["source"] for entry in checkpoint["session_timeline"]] == [
        "native_lifecycle"
    ] * 7


@pytest.mark.asyncio
async def test_native_checkpoint_preserves_prior_lifecycle_timeline_and_dedupes_events(
    routes_module, context, monkeypatch
):
    native = {
        "key": "native:codex:codex-123",
        "agent": "Native Codex",
        "title": "project: Codex session codex-123",
        "engine": "Codex",
        "model": "gpt-5.6",
    }
    monkeypatch.setattr(routes_module, "discover_native_sessions", lambda: [native])

    for _ in range(2):
        await routes_module._post_native_event(
            FakeRequest(_native_event("session_started", ""), producer="multiplex"),
            context,
        )
    response = await routes_module._put_native_checkpoint(
        FakeRequest(_native_payload(), producer="multiplex"),
        context,
    )

    checkpoint = json.loads(response.body)["checkpoint"]
    assert checkpoint["trail"] == ["Started native writer verification."]
    assert [entry["text"] for entry in checkpoint["session_timeline"]] == [
        "Session started.",
        "Started native writer verification.",
    ]
    assert [entry["source"] for entry in checkpoint["session_timeline"]] == [
        "native_lifecycle",
        "checkpoint",
    ]


@pytest.mark.asyncio
async def test_native_event_requires_producer_and_accepts_only_known_events(
    routes_module, context, monkeypatch
):
    native = {
        "key": "native:codex:codex-123",
        "agent": "Native Codex",
        "title": "project: Codex session codex-123",
        "engine": "Codex",
        "model": "gpt-5.6",
    }
    monkeypatch.setattr(routes_module, "discover_native_sessions", lambda: [native])
    with pytest.raises(web.HTTPForbidden):
        await routes_module._post_native_event(FakeRequest(_native_event()), context)
    with pytest.raises(web.HTTPBadRequest):
        await routes_module._post_native_event(
            FakeRequest(_native_event("untrusted"), producer="multiplex"), context
        )


def test_runtime_snapshot_reports_counts_and_plan_progress(routes_module):
    class RunningSubagents:
        def running_agents_for(self, parent_key):
            assert parent_key == "dashboard:atlas-review"
            return [{"id": "one"}, {"id": "two"}]

    class Tracker:
        current_stage = 1

    class Slot:
        running = True
        _plan_stage_count = 3
        _orch_tracker = Tracker()
        _in_stage_execution = True
        _plan_goal = "Finish the documentation"

    class State:
        _slots = {"atlas-review": Slot()}
        subagents = RunningSubagents()

    request = FakeRequest(app={"state": State()})
    snapshot = routes_module._runtime_snapshot(request)
    assert snapshot["sessions"]["atlas-review"] == {
        "capabilities": {"return_handoff": False},
        "agents_active": 1,
        "subagents_active": 2,
        "plan": {
            "active": True,
            "current": 2,
            "total": 3,
            "goal": "Finish the documentation",
        },
        "goal": None,
    }


@pytest.mark.parametrize("method", ["POST", "GET", None])
def test_runtime_handoff_requires_registered_post_route(routes_module, method):
    app = web.Application()
    app["state"] = types.SimpleNamespace(_slots={"demo": types.SimpleNamespace()})
    if method:
        async def handler(request):
            return web.Response()

        app.router.add_route(method, "/api/chat/slots/{slot}/return-handoff", handler)
    snapshot = routes_module._runtime_snapshot(FakeRequest(app=app))
    assert snapshot["sessions"]["demo"]["capabilities"]["return_handoff"] is (method == "POST")


def test_runtime_snapshot_does_not_consult_companion_policy(routes_module):
    class Slot:
        agent = "crew-codex"
        running = False
        _plan_stage_count = 0

    class State:
        _slots = {"identity": Slot()}
        subagents = None

    def policy_for(agent):
        pytest.fail("runtime snapshots must not consult a companion policy")
    request = FakeRequest(
        app={
            "state": State(),
            "platform_context": types.SimpleNamespace(
                providers=types.SimpleNamespace(
                    agent_runtime_policy=policy_for
                )
            ),
        }
    )

    snapshot = routes_module._runtime_snapshot(request)

    assert "identity" not in snapshot["sessions"]["identity"]


def test_runtime_snapshot_requires_no_companion_files(
    routes_module, monkeypatch
):
    class Slot:
        agent = "crew-codex"
        running = False
        _plan_stage_count = 0

    class State:
        _slots = {"codex-card": Slot()}
        subagents = None

    def forbid_read(*args, **kwargs):
        pytest.fail("runtime snapshots must not read companion state files")

    monkeypatch.setattr(Path, "read_text", forbid_read)

    snapshot = routes_module._runtime_snapshot(FakeRequest(app={"state": State()}))

    assert "approval_posture" not in snapshot["sessions"]["codex-card"]


def test_goal_loop_objective_excludes_autonudge_control_instruction(routes_module):
    assert routes_module._goal_loop_objective(
        "Goal: Keep the Multiplex work-state card truthful.\n"
        "Each idle cycle, make one atomic step."
    ) == ("Keep the Multiplex work-state card truthful.")
    instruction = "Continue working on Multiplex design\n" "without a control prefix"
    assert routes_module._goal_loop_objective(instruction) == (
        "Continue working on Multiplex design"
    )


@pytest.mark.asyncio
async def test_full_store_evicts_the_oldest_checkpoint_instead_of_refusing(
    routes_module, context
):
    store = routes_module._read_store(context)
    for index in range(routes_module._MAX_CHECKPOINTS):
        store["checkpoints"][f"filler-{index:04d}"] = {
            "session_key": f"filler-{index:04d}",
            "updated_at": f"2026-08-{index % 28 + 1:02d}T00:{index % 60:02d}:00+00:00",
        }
    context.storage.set(routes_module._STORE_KEY, store)

    response = await routes_module._put_checkpoint(
        FakeRequest(_payload(), session_key="arriving-session"), context
    )

    assert json.loads(response.body)["checkpoint"]["session_key"] == "arriving-session"
    checkpoints = routes_module._read_store(context)["checkpoints"]
    assert len(checkpoints) == routes_module._MAX_CHECKPOINTS
    assert "arriving-session" in checkpoints
    assert "filler-0000" not in checkpoints


@pytest.mark.asyncio
async def test_full_store_still_updates_a_checkpoint_it_already_holds(
    routes_module, context
):
    store = routes_module._read_store(context)
    for index in range(routes_module._MAX_CHECKPOINTS - 1):
        store["checkpoints"][f"filler-{index:04d}"] = {
            "session_key": f"filler-{index:04d}",
            "updated_at": f"2026-08-{index % 28 + 1:02d}T00:00:00+00:00",
        }
    store["checkpoints"]["atlas-review"] = {
        "session_key": "atlas-review",
        "updated_at": "2026-07-01T00:00:00+00:00",
    }
    context.storage.set(routes_module._STORE_KEY, store)

    await routes_module._put_checkpoint(FakeRequest(_payload()), context)

    checkpoints = routes_module._read_store(context)["checkpoints"]
    # An update is not an arrival: the oldest entry is this session's own prior
    # record, and evicting to make room for its replacement would delete it.
    assert len(checkpoints) == routes_module._MAX_CHECKPOINTS
    assert "filler-0000" in checkpoints
