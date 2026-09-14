from __future__ import annotations

import json
import subprocess
from pathlib import Path


UI_PATH = Path(__file__).parents[1] / "ui" / "index.mjs"


def _live_changed_path_overlaps() -> dict[str, list[str]]:
    source = UI_PATH.read_text()
    helpers = source.split("function Multiplex()", maxsplit=1)[0]
    sdk_import = (
        "const { useAppApi, useAppEvents, useNavigate } = "
        "window.__kirocrew_modules['@kirocrew/app-sdk']"
    )
    lucide_import = (
        "const { ArrowUpRight, CircleAlert, CircleCheck, CirclePause, RefreshCw } = "
        "window.__kirocrew_modules['lucide-react']"
    )
    lucide_stubs = (
        "const ArrowUpRight = null; const CircleAlert = null; "
        "const CircleCheck = null; const CirclePause = null; const RefreshCw = null"
    )
    sdk_stubs = (
        "const useAppApi = null; const useAppEvents = null; "
        "const useNavigate = null"
    )
    react_stubs = (
        "const h = null; const useCallback = null; const useEffect = null; "
        "const useState = null"
    )
    helpers = helpers.replace(
        "const React = window.__kirocrew_modules.react",
        "const React = {}",
    ).replace(sdk_import, sdk_stubs)
    helpers = helpers.replace(lucide_import, lucide_stubs).replace(
        "const { createElement: h, useCallback, useEffect, useState } = React",
        react_stubs,
    )
    script = helpers + """
const overlaps = liveChangedPathOverlaps(
  [
    {
      path: 'backend/routes.py',
      session_keys: ['active-one', 'active-two', 'historical'],
    },
    { path: 'ui/index.mjs', session_keys: ['active-one', 'historical'] },
  ],
  [
    { slot: { key: 'active-one' } },
    { slot: { key: 'active-two' } },
  ],
)
process.stdout.write(JSON.stringify(Object.fromEntries(overlaps)))
"""
    completed = subprocess.run(
        ["node", "--input-type=module", "--eval", script],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def _card_data_cases() -> list[dict[str, object]]:
    source = UI_PATH.read_text()
    helpers = source.split("function Multiplex()", maxsplit=1)[0]
    helpers = helpers.replace(
        "const React = window.__kirocrew_modules.react",
        "const React = {}",
    ).replace(
        "const { useAppApi, useAppEvents, useNavigate } = window.__kirocrew_modules['@kirocrew/app-sdk']",
        "const useAppApi = null; const useAppEvents = null; const useNavigate = null",
    ).replace(
        "const { ArrowUpRight, CircleAlert, CircleCheck, CirclePause, RefreshCw } = window.__kirocrew_modules['lucide-react']",
        "const ArrowUpRight = null; const CircleAlert = null; const CircleCheck = null; const CirclePause = null; const RefreshCw = null",
    ).replace(
        "const { createElement: h, useCallback, useEffect, useState } = React",
        "const h = null; const useCallback = null; const useEffect = null; const useState = null",
    )
    script = helpers + """
const cards = [
  cardData({ key: 'timeline', running: true, plan_goal: 'Make session state comprehensible.', last_message: 'Do not render this prompt fragment.', session_timeline: [{ text: 'Plan adopted.', source: 'plan' }] }, null),
  cardData({ key: 'identity', agent: 'crew-codex', model: 'gpt-5.6' }, null, { identity: { engine: 'Codex ACP', engine_source: 'configured' } }),
  cardData({ key: 'identity-unknown', agent: 'crew-codex', model: 'gpt-5.6' }, null),
  cardData({ key: 'checkpoint', declared_goal: 'Make the dashboard intent explicit.', todo: { current: 'Render the goal first.' }, session_timeline: [{ text: 'Subagent started.', source: 'subagent' }] }, { goal: 'Explain the active work.', next_action: 'Verify the card contract.', summary: 'Implementing the timeline.', main_items: ['Render goal-led card'], decision: 'Use checkpoint as the single writer.', trail: ['Legacy duplicate.'] }),
  cardData({ key: 'native', native: true, plan_goal: 'Must not be used for native cards.' }, { goal: 'Verify native producer state.', trail: ['Native hook connected.'] }),
  cardData({ key: 'native-no-goal', native: true, plan_goal: 'Must not be used for native cards.' }, null),
  cardData({ key: 'loop-instruction', running: true }, null, {
    goal: {
      objective: 'Continue working on Multiplex design.',
    },
  }),
  cardData({ key: 'declared-goal-loop', declared_goal: 'Keep Multiplex truthful.' }, null, {
    goal: { objective: 'Goal: Keep Multiplex truthful.' },
  }),
  [
    canReturnToLoop({ key: 'eligible' }, { goal: { active: true }, capabilities: { return_handoff: true } }),
    canReturnToLoop({ key: 'paused' }, { goal: { active: false } }),
    canReturnToLoop({ key: 'native', native: true }, { goal: { active: true }, capabilities: { return_handoff: true } }),
    canReturnToLoop({ key: 'unsupported' }, { goal: { active: true } }),
  ],
  [
    fallbackPresence({ key: 'running', running: true }),
    fallbackPresence({ key: 'idle', running: false, waiting_for_input: true }),
    fallbackPresence({ key: 'native', native: true, project_root: '/work/project' }),
    fallbackPresence({ key: 'saved', checkpointOnly: true }),
    sessionLocation({ workspace_label: 'Project', project_root: '/work/project' }),
    displayState(null, { key: 'tracked', native: true }, { catalog: 'tracked', execution: 'unknown' }),
    liveFact({ key: 'native-active', native: true }, null, { catalog: 'observed', execution: 'active' }),
  ],
  cardData(
    { key: 'native-stale-checkpoint', native: true, last_activity_at: '2026-08-11T12:05:00Z' },
    { summary: 'Earlier recorded work.', updated_at: '2026-08-11T12:00:00Z' },
  ),
  [
    footerTimestamp({ key: 'native', native: true }, { updated_at: '2026-08-11T12:00:00Z' }),
    footerTimestamp({ key: 'native', native: true, last_activity_at: '2026-08-11T12:05:00Z' }, { updated_at: '2026-08-11T12:00:00Z' }),
  ],
  cardData({ key: 'raw-message', last_message: 'Do not render this prompt fragment.' }, null),
  runtimeLabels({ approval_posture: { state: 'applied', mode: 'agent-full-access' } }),
  runtimeLabels({ approval_posture: { state: 'unavailable', mode: 'agent-full-access' } }),
  operatorDigest({ key: 'digest', session_timeline: [
    { text: 'Session resumed.', source: 'session' },
    { text: 'Waiting for tool approval.', source: 'attention' },
    { text: 'Turn cancelled.', source: 'terminal' },
    { text: 'Approval needed: unknown.', source: 'attention', kind: 'attention', priority: 95 },
    { text: 'Approval needed: git.', source: 'attention', kind: 'attention', priority: 95, consequence: 'Awaiting your approval.' },
    { text: 'Goal loop stopped: blocked.', source: 'goal_loop', consequence: 'No further automatic cycles will fire.' },
    { text: 'Subagents: 1 active of 1.', source: 'subagents', kind: 'subagent_activity', priority: 20 },
    { text: 'Completed: install hooks.', source: 'todo', kind: 'work', priority: 80, consequence: 'All current TODO items are complete.' },
  ] }, null),
  [
    timelineEntries({ session_timeline: [
      { text: 'Received 3 peer channel message(s).', source: 'channel', kind: 'channel' },
      { text: 'Peer completed the focused test run.', source: 'channel', kind: 'work' },
    ] }, null).map(entry => entry.text),
    [
      peerDeliveryText({ peer_channel_inbox_count: 1 }),
      peerDeliveryText({ peer_channel_inbox_count: 3 }),
      peerDeliveryText({ peer_channel_inbox_count: 0 }),
    ],
    attentionText(null, { peer_channel_attention: [{ channel_id: 'deadbeef', from_role: 'Verifier', delivery: 'interrupt' }] }),
    displayState(null, { peer_channel_attention: [{ channel_id: 'deadbeef', from_role: 'Verifier', delivery: 'interrupt' }] }),
    displayState(null, { peer_channel_attention: [{ channel_id: 'deadbeef', from_role: 'Verifier', delivery: 'interrupt' }] }, { catalog: 'open', execution: 'active' }),
    cardData({ checkpoint_freshness: { overdue: true } }, { summary: 'Old checkpoint.', next_action: 'Refresh it.' }).currentWorkLabel,
  ],
  checkpointFor(
    { key: 'stored', session_timeline: [], session_checkpoint: { next_action: 'Publish the next-action contract.', summary: 'Newer KiroCrew state.', attention: { status: 'unassigned', kind: 'decision', decision_key: 'adapter-identity' }, updated_at: '2026-08-10T12:00:00+00:00' } },
    { goal: 'Persisted durable goal.', summary: 'Stored checkpoint.', updated_at: '2026-08-09T12:00:00+00:00', session_timeline: [{ text: 'Older milestone.', source: 'checkpoint' }] },
  ),
  checkpointFor(
    { key: 'claimed', session_checkpoint: { summary: 'A newer agent checkpoint.', attention: { status: 'unassigned', kind: 'decision', decision_key: 'reopen' }, updated_at: '2026-08-10T12:00:00+00:00' } },
    { summary: 'A claimed durable checkpoint.', attention: { status: 'claimed', kind: 'decision', decision_key: 'reopen', claimed_by: 'operator' }, updated_at: '2026-08-09T12:00:00+00:00' },
  ),
  [
    workflowSlot({ run_id: 'wf_000003', name: 'multiplex-first-run-v3', status: 'finished', phase: 'Verify', event_count: 9, agent_error_count: 0, result: { secret: 'must not project' }, last_log: 'must not project' }),
    cardData(workflowSlot({ run_id: 'wf_000004', name: 'multiplex-postfix-check', status: 'failed', phase: 'Verify', event_count: 8, agent_error_count: 1 }), null),
  ],
  [
    footerTimestamp({}, { recorded_at: '2026-08-11T12:03:00Z', updated_at: '2026-08-11T12:00:00Z' }),
    provenanceText({ recorded_at: '2026-08-11T12:03:00Z', source_kind: 'relayed', basis: [] }),
    attentionText({ attention: { status: 'unassigned', kind: 'decision', decision_key: 'pool-size' } }, {}),
  ],
  cardData(
    { key: 'idle-chat', running: false, waiting_for_input: true },
    { attention: { status: 'none' } },
  ),
]
process.stdout.write(JSON.stringify(cards))
"""
    completed = subprocess.run(["node", "--input-type=module", "--eval", script], check=True, capture_output=True, text=True)
    return json.loads(completed.stdout)


def test_card_data_uses_structured_timeline_and_never_last_message() -> None:
    (
        timeline_only, configured_identity, unknown_identity,
        checkpoint_and_timeline,
        native_trail, native_without_goal, loop_instruction, loop_goal,
        return_eligibility, session_visibility, historical_native_checkpoint, footer_timestamps, raw_message_only, confirmed_posture, unavailable_posture,
        digest, channel_projection, preserved_checkpoint, claimed_attention, workflow, provenance, idle_chat,
    ) = _card_data_cases()

    assert timeline_only["goal"] == "Make session state comprehensible."
    assert timeline_only["currentWork"] == "Work state not yet declared."
    assert timeline_only["nextAction"] == "No next action declared."
    assert timeline_only["liveStatus"] == "The session is active."
    assert timeline_only["updates"] == [{
        "text": "Plan adopted.",
        "source": "plan",
        "timestamp": "",
        "kind": "",
        "priority": 0,
        "consequence": "",
    }]

    assert configured_identity["line"] == "gpt-5.6"
    assert unknown_identity["line"] == "gpt-5.6"
    assert "crew-codex" not in unknown_identity["line"]

    assert checkpoint_and_timeline["goal"] == "Make the dashboard intent explicit."
    assert checkpoint_and_timeline["currentWork"] == "Implementing the timeline."
    assert checkpoint_and_timeline["nextAction"] == "Verify the card contract."
    assert checkpoint_and_timeline["mainItems"] == ["Render goal-led card"]
    assert [item["text"] for item in checkpoint_and_timeline["updates"]] == [
        "Decision: Use checkpoint as the single writer.",
    ]
    source = UI_PATH.read_text()
    assert "listStyle: 'disc outside'" in source
    assert "'Main items'" in source

    assert native_trail["goal"] == "Verify native producer state."
    assert [item["text"] for item in native_trail["updates"]] == ["Native hook connected."]
    assert native_without_goal["goal"] == "No session goal declared."

    assert loop_instruction["goal"] == "No session goal declared."
    assert loop_instruction["autoNudgeInstruction"] == "Continue working on Multiplex design."
    assert loop_goal["goal"] == "Keep Multiplex truthful."
    assert loop_goal["autoNudgeInstruction"] == ""
    assert loop_goal["currentWork"] == "Work state not yet declared."
    assert return_eligibility == [True, False, False, False]
    assert session_visibility == [
        {"catalog": "open", "execution": "active", "workspace_id": "", "workspace_label": "Unmapped", "project_root": "", "evidence": "dashboard_slot"},
        {"catalog": "open", "execution": "idle", "workspace_id": "", "workspace_label": "Unmapped", "project_root": "", "evidence": "dashboard_slot"},
        {"catalog": "observed", "execution": "unknown", "workspace_id": "", "workspace_label": "Unmapped", "project_root": "/work/project", "evidence": "bounded_transcript"},
        {"catalog": "unknown", "execution": "unknown", "workspace_id": "", "workspace_label": "Unmapped", "project_root": "", "evidence": "checkpoint_only"},
        "Project · /work/project",
        "tracked",
        "A provider-owned runtime record reports active work.",
    ]
    assert historical_native_checkpoint["currentWorkLabel"] == "Last recorded work"
    assert historical_native_checkpoint["currentWork"] == "Earlier recorded work."
    assert footer_timestamps[0].startswith("Checkpoint ")
    assert footer_timestamps[1].startswith("Observed ")
    assert " · Checkpoint " in footer_timestamps[1]

    assert raw_message_only["goal"] == "No session goal declared."
    assert raw_message_only["currentWork"] == "Work state not yet declared."

    assert channel_projection == [
        ["Peer completed the focused test run."],
        ["1 peer delivery received", "3 peer deliveries received", ""],
        "Peer request from Verifier · interrupt",
        "awaiting attention",
        "active",
        "Last recorded work",
    ]
    assert raw_message_only["updates"] == []
    assert "Do not render this prompt fragment." not in json.dumps(raw_message_only)

    assert idle_chat["state"] == "unattended"
    assert idle_chat["liveStatus"] == "The turn has ended; the session is idle."

    assert confirmed_posture == []
    assert unavailable_posture == []

    assert preserved_checkpoint["goal"] == "Persisted durable goal."
    assert preserved_checkpoint["next_action"] == "Publish the next-action contract."
    assert preserved_checkpoint["summary"] == "Newer KiroCrew state."
    assert preserved_checkpoint["attention"] == {
        "status": "unassigned",
        "kind": "decision",
        "decision_key": "adapter-identity",
    }
    assert [item["text"] for item in preserved_checkpoint["session_timeline"]] == ["Older milestone."]
    assert claimed_attention["attention"]["status"] == "claimed"
    assert claimed_attention["attention"]["claimed_by"] == "operator"
    assert [item["text"] for item in digest] == [
        "Approval required; operation not supplied by provider. — Open the conversation to inspect and approve or reject it.",
        "Approval needed: git. — Awaiting your approval.",
        "Goal loop stopped: blocked. — No further automatic cycles will fire.",
        "Subagents: 1 active of 1.",
        "Completed: install hooks. — All current TODO items are complete.",
    ]

    workflow_slot, workflow_card = workflow
    assert workflow_slot == {
        "key": "workflow:wf_000003",
        "workflow": True,
        "workflow_run_id": "wf_000003",
        "workflow_status": "finished",
        "workflow_phase": "Verify",
        "workflow_event_count": 9,
        "workflow_agent_error_count": 0,
        "agent": "Workflow",
        "title": "multiplex-first-run-v3",
        "running": False,
    }
    assert "secret" not in json.dumps(workflow_slot)
    assert "last_log" not in json.dumps(workflow_slot)
    assert workflow_card["state"] == "failed"
    assert workflow_card["goal"] == "No session goal declared."
    assert workflow_card["currentWork"] == "Current phase: Verify"
    assert workflow_card["mainItems"] == ["8 structured events", "1 agent error"]

    assert provenance[0].startswith("Recorded ")
    assert provenance[1] == "Source: relayed · no evidence record — confirm before acting."
    assert provenance[2] == "Decision · pool-size: needs you · unassigned"


def test_workspace_view_has_full_width_list_card_and_grid_modes() -> None:
    source = UI_PATH.read_text()

    assert "maxWidth: '1200px'" not in source
    assert "const [viewMode, setViewMode] = useState('list')" in source
    assert "'aria-label': 'Session view'" in source
    assert "setViewMode('cards')" in source
    assert "setViewMode('grid')" in source
    assert "viewMode === 'grid' ? styles.cardCompactGrid : viewMode === 'cards' ? styles.cardWideGrid : styles.cardList" in source
    assert "styles.footerItem" in source
    assert "overflowWrap: 'anywhere'" in source
    assert "maxWidth: '96ch'" in source
    assert "Resume & tracking" in source
    assert "Move to history" in source
    assert "'aria-label': 'Session overview'" in source


def test_changed_path_overlap_requires_two_live_cards() -> None:
    assert _live_changed_path_overlaps() == {
        "active-one": ["backend/routes.py"],
        "active-two": ["backend/routes.py"],
    }


def test_ui_separates_goal_work_updates_and_live_status() -> None:
    source = UI_PATH.read_text()
    assert "'Goal'" in source
    assert "'Current work'" in source
    assert "'Next'" in source
    assert "'Updates'" in source
    assert "Current checkpoint" not in source
    assert "Recorded detail" not in source
    assert "last_message" not in source
    assert "return-handoff" in source
    assert "canReturnToLoop(slot, runtime)" in source
    assert "maxLength: 240" in source
    assert "Claim attention" in source
    assert "'Release'" in source
    assert "'Resolve'" in source
    assert "updateAttentionClaim(slot, 'claim')" in source
    assert 'api.get(`${APP_API}/workflows`)' in source
    assert "function workflowSlot(run)" in source
    assert "Open workflow" in source
    assert "function fallbackPresence(slot)" in source
    assert "api.get(`${APP_API}/session-presence`)" in source
    assert "'Working now'" in source
    assert "'Open sessions'" in source
    assert "'Tracked provider sessions'" in source
    assert "'History'" in source
    assert "Workspace" in source
    assert "function footerTimestamp" in source
    assert "setNativeTracking" in source
    assert "Explicitly retained in Multiplex; provider liveness is unknown." in source
    assert "Last recorded work" in source
    assert "Transcript evidence is historical" in source
    assert "Show history" in source
    assert "Shared changed paths" in source
    assert "Checkpoints have no per-path record time" in source
    assert "function liveChangedPathOverlaps" in source
    assert "function provenanceText" in source
    assert "recorded_at || checkpoint?.updated_at" in source
    assert "Attention type" in source


def test_session_card_titles_wrap_instead_of_truncating() -> None:
    title_style = (
        UI_PATH.read_text()
        .split("cardTitle:", maxsplit=1)[1]
        .split("\n", maxsplit=1)[0]
    )
    assert "overflowWrap: 'anywhere'" in title_style
    assert "textOverflow" not in title_style
    assert "whiteSpace" not in title_style
