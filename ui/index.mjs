const React = window.__kirocrew_modules.react
const { useAppApi, useAppEvents, useNavigate } = window.__kirocrew_modules['@kirocrew/app-sdk']
const { ArrowUpRight, CircleAlert, CircleCheck, CirclePause, RefreshCw } = window.__kirocrew_modules['lucide-react']
const { createElement: h, useCallback, useEffect, useState } = React

const APP_API = '/api/apps/multiplex'
const styles = {
  root: { boxSizing: 'border-box', minHeight: 0, width: '100%', padding: '24px clamp(20px, 3vw, 52px) 48px', overflowY: 'auto', color: 'var(--text)' },
  header: { display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '18px', marginBottom: '24px' },
  titleRow: { display: 'flex', alignItems: 'center', gap: '10px' },
  title: { margin: 0, fontSize: '24px', fontWeight: 650, letterSpacing: '-0.025em', lineHeight: 1.1 },
  subtitle: { margin: '7px 0 0', color: 'var(--muted)', fontSize: '13px', lineHeight: 1.45, maxWidth: '720px' },
  pill: { background: '#e8d5f5', color: '#6d28d9', padding: '3px 9px', borderRadius: '9999px', fontSize: '11px', fontWeight: 650 },
  headerControls: { display: 'flex', alignItems: 'center', flexWrap: 'wrap', justifyContent: 'flex-end', gap: '10px' },
  ghostButton: { display: 'inline-flex', alignItems: 'center', gap: '6px', background: 'transparent', color: '#6d28d9', border: '1px solid #d8c4ee', padding: '7px 13px', borderRadius: '6px', fontSize: '12px', fontWeight: 600, cursor: 'pointer', whiteSpace: 'nowrap' },
  viewToggle: { display: 'inline-flex', alignItems: 'center', gap: '2px', padding: '3px', background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: '6px' },
  viewButton: { border: 'none', borderRadius: '4px', padding: '5px 9px', background: 'transparent', color: 'var(--muted)', cursor: 'pointer', fontSize: '12px', fontWeight: 600 },
  viewButtonActive: { background: 'var(--card)', color: 'var(--text)', boxShadow: '0 1px 2px rgba(0,0,0,.12)' },
  overview: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(145px, 1fr))', borderTop: '1px solid var(--border)', borderBottom: '1px solid var(--border)', marginBottom: '28px' },
  overviewCell: { display: 'grid', gap: '4px', padding: '15px 18px', borderRight: '1px solid var(--border)' },
  overviewLabel: { color: 'var(--muted)', fontSize: '11px', fontWeight: 650, letterSpacing: '0.045em', textTransform: 'uppercase' },
  overviewValue: { fontSize: '25px', lineHeight: 1, fontWeight: 650, letterSpacing: '-0.03em' },
  overviewBar: { display: 'flex', height: '4px', overflow: 'hidden', background: 'var(--border)', borderRadius: '999px', marginTop: '4px' },
  overviewSegment: { minWidth: '2px', height: '100%' },
  cardWideGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(520px, 1fr))', gap: '16px' },
  cardCompactGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '14px' },
  cardList: { display: 'grid', gap: '12px' },
  card: { boxSizing: 'border-box', minWidth: 0, background: 'var(--card)', border: '1px solid var(--border)', borderRadius: '8px', padding: '18px' },
  cardTop: { display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '12px' },
  role: { color: '#6d28d9', fontSize: '11px', fontWeight: 700, letterSpacing: '0.065em', textTransform: 'uppercase' },
  cardTitle: { margin: '8px 0 0', fontSize: '16px', fontWeight: 650, lineHeight: 1.3, overflowWrap: 'anywhere' },
  detail: { margin: '5px 0 0', color: 'var(--muted)', fontSize: '12px', overflowWrap: 'anywhere' },
  primaryButton: { display: 'inline-flex', alignItems: 'center', gap: '6px', background: '#6d28d9', color: '#fff', border: 'none', padding: '7px 13px', borderRadius: '6px', fontSize: '12px', fontWeight: 650, cursor: 'pointer', whiteSpace: 'nowrap' },
  checkpoint: { borderTop: '1px solid var(--border)', marginTop: '16px', paddingTop: '15px' },
  checkpointLabel: { margin: 0, color: 'var(--muted)', fontSize: '11px', fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase' },
  summary: { maxWidth: '96ch', margin: '7px 0 0', fontSize: '13px', lineHeight: 1.55 },
  runtime: { display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '10px' },
  runtimePill: { maxWidth: '100%', overflowWrap: 'anywhere', background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: '9999px', color: 'var(--muted)', fontSize: '11px', padding: '3px 8px' },
  bulletList: { display: 'grid', maxWidth: '96ch', gap: '5px', listStyle: 'disc outside', margin: '10px 0 0', padding: '0 0 0 20px', fontSize: '13px', lineHeight: 1.5 },
  editor: { borderTop: '1px solid var(--border)', marginTop: '14px', paddingTop: '14px' },
  editorIntro: { margin: '0 0 12px', color: 'var(--muted)', fontSize: '13px', lineHeight: 1.5 },
  fieldGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '10px' },
  field: { display: 'grid', gap: '5px' },
  fieldLabel: { color: 'var(--muted)', fontSize: '11px', fontWeight: 650 },
  input: { boxSizing: 'border-box', width: '100%', background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: '5px', color: 'var(--text)', padding: '8px 9px', font: 'inherit', fontSize: '13px' },
  textarea: { boxSizing: 'border-box', width: '100%', minHeight: '72px', resize: 'vertical', background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: '5px', color: 'var(--text)', padding: '8px 9px', font: 'inherit', fontSize: '13px', lineHeight: 1.5 },
  editorActions: { display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '12px' },
  editorDisclosure: { marginTop: '12px', color: 'var(--muted)', fontSize: '12px', fontWeight: 650, cursor: 'pointer' },
  footer: { display: 'flex', flexWrap: 'wrap', alignItems: 'flex-start', gap: '7px 16px', marginTop: '15px', color: 'var(--muted)', fontSize: '12px', lineHeight: 1.4 },
  footerItem: { display: 'flex', flex: '0 1 auto', alignItems: 'flex-start', gap: '5px', maxWidth: 'min(100%, 360px)', minWidth: 0, overflowWrap: 'anywhere' },
  nativeTools: { position: 'relative' },
  nativeToolsSummary: { listStyle: 'none', cursor: 'pointer' },
  nativeToolsMenu: { position: 'absolute', zIndex: 2, right: 0, display: 'grid', gap: '6px', minWidth: '168px', marginTop: '6px', padding: '8px', background: 'var(--card)', border: '1px solid var(--border)', borderRadius: '6px', boxShadow: '0 8px 24px rgba(0,0,0,.2)' },
  sectionHeading: { margin: '30px 0 11px', color: 'var(--muted)', fontSize: '12px', fontWeight: 700, letterSpacing: '0.055em', textTransform: 'uppercase' },
  workspaceFilter: { display: 'flex', alignItems: 'center', gap: '7px', color: 'var(--muted)', fontSize: '12px', fontWeight: 600 },
  empty: { padding: '48px 16px', color: 'var(--muted)', fontSize: '13px', textAlign: 'center' },
  error: { display: 'flex', gap: '8px', alignItems: 'flex-start', marginBottom: '14px', padding: '12px 14px', border: '1px solid var(--danger, #b91c1c)', borderRadius: '8px', color: 'var(--danger, #b91c1c)', fontSize: '13px' },
}

function timestampMs(value) {
  if (typeof value !== 'string' || !value.trim()) return 0
  const parsed = Date.parse(value)
  return Number.isFinite(parsed) ? parsed : 0
}

function checkpointPredatesObservation(slot, checkpoint) {
  const recordedAt = checkpoint?.recorded_at || checkpoint?.updated_at
  if (!slot?.native || !recordedAt) return false
  return timestampMs(slot.last_activity_at) > timestampMs(recordedAt)
}

function checkpointOverdue(slot) {
  return slot?.checkpoint_freshness?.overdue === true
}

function peerChannelAttention(slot) {
  const raw = Array.isArray(slot?.peer_channel_attention) ? slot.peer_channel_attention : []
  return raw.filter(item => textValue(item?.channel_id) && textValue(item?.from_role))
}

function peerDeliveryText(slot) {
  const count = Number(slot?.peer_channel_inbox_count)
  if (!Number.isInteger(count) || count <= 0) return ''
  return `${count} peer ${count === 1 ? 'delivery' : 'deliveries'} received`
}

function footerTimestamp(slot, checkpoint) {
  const labels = []
  if (slot?.native && slot.last_activity_at) {
    labels.push(`Observed ${new Date(slot.last_activity_at).toLocaleString()}`)
  }
  if (checkpoint?.recorded_at) labels.push(`Recorded ${new Date(checkpoint.recorded_at).toLocaleString()}`)
  else if (checkpoint?.updated_at) labels.push(`Checkpoint ${new Date(checkpoint.updated_at).toLocaleString()}`)
  if (labels.length) return labels.join(' · ')
  if (slot?.workflow) return `Workflow ${slot.workflow_run_id}`
  return slot?.native ? '' : 'Live projection'
}

function displayState(checkpoint, slot, presence = null) {
  if (slot?.workflow) {
    if (slot.workflow_status === 'running') return 'active'
    if (slot.workflow_status === 'failed') return 'failed'
    if (slot.workflow_status === 'cancelled') return 'paused'
    return 'unattended'
  }
  if (slot?.pending_approval) return 'awaiting attention'
  if (presence?.execution === 'active') return 'active'
  if (peerChannelAttention(slot).length > 0) return 'awaiting attention'
  if (checkpoint?.attention?.status === 'unassigned') return 'awaiting attention'
  if (presence?.catalog === 'open' && presence.execution === 'idle') return 'idle'
  if (presence?.catalog === 'open') return 'open'
  if (presence?.catalog === 'tracked') return 'tracked'
  if (presence?.catalog === 'observed') return 'observed'
  if (slot?.native) {
    if (checkpoint?.state === 'failed') return 'failed'
    return 'unattended'
  }
  if (checkpoint?.state) return checkpoint.state.replaceAll('_', ' ')
  if (slot?.stopping) return 'paused'
  return slot?.running ? 'active' : 'unattended'
}

function attentionText(checkpoint, slot) {
  const peerRequests = peerChannelAttention(slot)
  if (peerRequests.length > 0) {
    const request = peerRequests[0]
    const delivery = request.delivery === 'interrupt' ? ' · interrupt' : ''
    const more = peerRequests.length > 1 ? ` +${peerRequests.length - 1}` : ''
    return `Peer request from ${request.from_role}${delivery}${more}`
  }
  const attention = checkpoint?.attention
  if (!attention || attention.status === 'none') {
    if (slot?.pending_approval) return 'Needs approval'
    return 'No attention request'
  }
  const decision = attention.kind === 'decision'
    ? `Decision${attention.decision_key ? ` · ${attention.decision_key}` : ''}: `
    : ''
  if (attention.status === 'claimed') return `${decision}claimed by ${attention.claimed_by || 'someone'}`
  if (attention.status === 'resolved') return `${decision}resolved${attention.disposition ? ` · ${attention.disposition}` : ''}`
  return `${decision}needs you · unassigned`
}

function timelineEntry(value) {
  const text = typeof value === 'string'
    ? value.trim()
    : typeof value?.text === 'string'
      ? value.text.trim()
      : ''
  if (!text) return null
  return {
    text,
    source: typeof value?.source === 'string' ? value.source : (typeof value === 'string' ? 'checkpoint' : ''),
    timestamp: typeof value?.timestamp === 'string' ? value.timestamp : '',
    kind: typeof value?.kind === 'string' ? value.kind : '',
    priority: Number.isInteger(value?.priority) ? value.priority : 0,
    consequence: typeof value?.consequence === 'string' ? value.consequence.trim() : '',
  }
}

function timelineEntries(slot, checkpoint) {
  const slotTimeline = Array.isArray(slot?.session_timeline) ? slot.session_timeline : []
  const checkpointTimeline = Array.isArray(checkpoint?.session_timeline) ? checkpoint.session_timeline : []
  const observedTimeline = slotTimeline.length > 0 ? slotTimeline : checkpointTimeline
  const legacyTrail = observedTimeline.length > 0 ? [] : (Array.isArray(checkpoint?.trail) ? checkpoint.trail : [])
  const seen = new Set()
  return [...observedTimeline, ...legacyTrail]
    .map(timelineEntry)
    .filter(entry => {
      // Earlier KiroCrew versions serialized these gateway delivery receipts
      // into the work timeline. They are transport evidence, not authored
      // progress; preserve actual channel-authored entries and only hide the
      // exact old generated form.
      if (entry?.source === 'channel' && /^Received \d+ peer channel message\(s\)\.$/.test(entry.text)) return false
      if (!entry || seen.has(entry.text)) return false
      seen.add(entry.text)
      return true
    })
    .slice(-7)
}

function eventPriority(entry) {
  if (entry.kind === 'subagent_activity') return 70
  if (entry.priority > 0) return entry.priority
  return {
    checkpoint: 100,
    plan: 80,
    todo: 80,
    work: 80,
    attention: 90,
    terminal: 90,
    handoff: 90,
    goal_loop: 90,
    subagents: 20,
    session: 10,
    native_lifecycle: 10,
  }[entry.kind || entry.source] || 0
}

function canReturnToLoop(slot, runtime) {
  return !slot?.native && runtime?.goal?.active === true && runtime?.capabilities?.return_handoff === true
}

function fallbackPresence(slot) {
  if (slot?.workflow) {
    return {
      catalog: slot.workflow_status === 'running' ? 'open' : 'archived',
      execution: slot.workflow_status === 'running' ? 'active' : 'idle',
      workspace_id: '', workspace_label: 'Unmapped', project_root: '', evidence: 'workflow_run',
    }
  }
  if (slot?.checkpointOnly) {
    return { catalog: 'unknown', execution: 'unknown', workspace_id: '', workspace_label: 'Unmapped', project_root: '', evidence: 'checkpoint_only' }
  }
  if (slot?.native) {
    return { catalog: 'observed', execution: 'unknown', workspace_id: '', workspace_label: 'Unmapped', project_root: slot.project_root || '', evidence: 'bounded_transcript' }
  }
  return {
    catalog: 'open', execution: slot?.running === true ? 'active' : 'idle',
    workspace_id: slot?.workspace || '', workspace_label: slot?.workspace || 'Unmapped', project_root: slot?.project || '', evidence: 'dashboard_slot',
  }
}

function sessionLocation(presence) {
  if (!presence) return ''
  return [presence.workspace_label || 'Unmapped', presence.project_root].filter(Boolean).join(' · ')
}

function liveChangedPathOverlaps(overlaps, rows) {
  const liveKeys = new Set(rows.map(({ slot }) => slot?.key).filter(Boolean))
  const pathsBySession = new Map()
  for (const overlap of Array.isArray(overlaps) ? overlaps : []) {
    const path = textValue(overlap?.path)
    const sessionKeys = [...new Set(
      (Array.isArray(overlap?.session_keys) ? overlap.session_keys : [])
        .filter(key => liveKeys.has(key)),
    )]
    if (!path || sessionKeys.length < 2) continue
    for (const sessionKey of sessionKeys) {
      const paths = pathsBySession.get(sessionKey) || []
      pathsBySession.set(sessionKey, [...paths, path])
    }
  }
  return pathsBySession
}

function operatorDigest(slot, checkpoint) {
  const generic = new Set([
    'Session started.',
    'Session resumed.',
    'Waiting for tool approval.',
    'Turn cancelled.',
    'Turn cancelled; no completion outcome was recorded.',
  ])
  const vagueApproval = /^Approval needed: (?:unknown|tool|command)\.?$/i
  const candidates = timelineEntries(slot, checkpoint)
    .map((entry, index) => ({ entry, index, priority: eventPriority(entry) }))
    .filter(({ entry, priority }) => !generic.has(entry.text) && priority >= 60)
  const retained = candidates.length <= 7
    ? candidates
    : candidates
      .sort((left, right) => right.priority - left.priority || right.index - left.index)
      .slice(0, 7)
      .sort((left, right) => left.index - right.index)
  return retained.map(({ entry }) => {
    const incompleteApproval = vagueApproval.test(entry.text)
    const text = incompleteApproval
      ? 'Approval required; operation not supplied by provider.'
      : entry.text
    const consequence = incompleteApproval
      ? 'Open the conversation to inspect and approve or reject it.'
      : entry.consequence
    return { ...entry, text: consequence ? `${text} — ${consequence}` : text }
  })
}

function liveFact(slot, checkpoint, presence = null) {
  if (slot?.workflow) {
    if (slot.workflow_status === 'running') return 'The workflow is active.'
    if (slot.workflow_status === 'failed') return 'The workflow has failed.'
    if (slot.workflow_status === 'cancelled') return 'The workflow was cancelled.'
    return 'The workflow has finished.'
  }
  if (slot?.pending_approval) return 'A tool approval is waiting in this conversation.'
  if (slot?.waiting_for_input) return 'The turn has ended; the session is idle.'
  if (checkpoint?.state === 'failed') return 'The session has reported a failure.'
  if (slot?.native) {
    if (presence?.execution === 'active') return 'A provider-owned runtime record reports active work.'
    if (presence?.catalog === 'open' && presence.execution === 'idle') return 'A provider-owned runtime record reports an open idle session.'
    if (presence?.catalog === 'open') return 'A provider-owned runtime record reports an open process; its execution state is unknown.'
    if (presence?.catalog === 'tracked') return 'Explicitly retained in Multiplex; provider liveness is unknown.'
    return 'Transcript evidence is historical; provider liveness is unknown.'
  }
  if (slot?.stopping) return 'The session is paused.'
  if (slot?.running) return 'The session is active.'
  return 'No live activity signal is available.'
}

function textValue(value) {
  return typeof value === 'string' ? value.trim() : ''
}

function declaredGoal(slot, checkpoint, runtime) {
  if (!slot?.native) {
    const dashboardGoal = textValue(slot?.declared_goal)
    if (dashboardGoal) return dashboardGoal
  }
  const explicitGoal = textValue(checkpoint?.goal)
  if (explicitGoal) return explicitGoal
  if (!slot?.native) {
    const planGoal = textValue(slot?.plan_goal)
    if (planGoal) return planGoal
  }
  return 'No session goal declared.'
}

function autoNudgeInstruction(slot, runtime) {
  if (textValue(slot?.declared_goal)) return ''
  return textValue(runtime?.goal?.objective)
}

function currentTodo(slot) {
  return textValue(slot?.todo?.current)
}

function displayedEngine(slot, checkpoint) {
  if (slot?.native) return textValue(checkpoint?.engine) || textValue(slot?.engine)
  return ''
}

function workUpdates(slot, checkpoint) {
  const updates = [...operatorDigest(slot, checkpoint)]
  const known = new Set(updates.map(item => item.text))
  for (const [label, detail] of [['Decision', checkpoint?.decision], ['Blocker', checkpoint?.blocker]]) {
    const text = textValue(detail)
    const item = text && `${label}: ${text}`
    if (item && !known.has(item)) {
      updates.push({ text: item, source: 'checkpoint', timestamp: '', kind: 'checkpoint', priority: 100, consequence: '' })
      known.add(item)
    }
  }
  return updates
}

function cardData(slot, checkpoint, runtime = null, presence = null) {
  const workflow = slot?.workflow === true
  const hasRecordedDetail = typeof checkpoint?.summary === 'string' && checkpoint.summary.trim().length > 0
  const checkpointIsHistorical = checkpointPredatesObservation(slot, checkpoint)
  const todo = currentTodo(slot)
  const engine = displayedEngine(slot, checkpoint)
  return {
    title: checkpoint?.identity || slot?.title || slot?.key || 'Untitled session',
    role: checkpoint?.role || slot?.agent || 'Session',
    state: displayState(checkpoint, slot, presence),
    line: workflow
      ? [slot.workflow_run_id, slot.workflow_status, slot.workflow_phase].filter(Boolean).join(' · ')
      : [engine, checkpoint?.model || slot?.model, slot?.reasoning_effort, checkpoint?.changed_since_checkpoint?.[0]].filter(Boolean).join(' · '),
    goal: declaredGoal(slot, checkpoint, runtime),
    autoNudgeInstruction: autoNudgeInstruction(slot, runtime),
    currentWorkLabel: checkpointIsHistorical || checkpointOverdue(slot) ? 'Last recorded work' : 'Current work',
    currentWork: workflow
      ? (slot.workflow_phase ? `Current phase: ${slot.workflow_phase}` : 'No active phase is recorded.')
      : (hasRecordedDetail ? checkpoint.summary.trim() : (todo ? `Current task: ${todo}` : 'Work state not yet declared.')),
    nextAction: workflow
      ? 'Open Workflows to inspect the run.'
      : (textValue(checkpoint?.next_action) || (todo ? `Structured next task: ${todo}` : 'No next action declared.')),
    mainItems: workflow
      ? [`${slot.workflow_event_count || 0} structured event${slot.workflow_event_count === 1 ? '' : 's'}`, ...(slot.workflow_agent_error_count ? [`${slot.workflow_agent_error_count} agent error${slot.workflow_agent_error_count === 1 ? '' : 's'}`] : [])]
      : (hasRecordedDetail && Array.isArray(checkpoint?.main_items) ? checkpoint.main_items : []),
    updates: workUpdates(slot, checkpoint),
    liveStatus: liveFact(slot, checkpoint, presence),
  }
}

function handoffText(checkpoint, slot) {
  const attention = attentionText(checkpoint, slot)
  const card = cardData(slot, checkpoint)
  return [
    'Multiplex entry handoff',
    `Work: ${checkpoint.identity}`,
    `Role: ${checkpoint.role}`,
    `State: ${checkpoint.state.replaceAll('_', ' ')}`,
    `Goal: ${card.goal}`,
    `Current work: ${card.currentWork}`,
    `Next: ${card.nextAction}`,
    checkpoint.main_items?.length && `Main items: ${checkpoint.main_items.join('; ')}`,
    card.updates.length && `Updates: ${card.updates.map(item => item.text).join('; ')}`,
    checkpoint.progress?.kind !== 'none' && `${checkpoint.progress.kind}: ${checkpoint.progress.completed}/${checkpoint.progress.total}${checkpoint.progress.label ? ` · ${checkpoint.progress.label}` : ''}`,
    checkpoint.decision && `Decision: ${checkpoint.decision}`,
    checkpoint.blocker && `Blocker: ${checkpoint.blocker}`,
    checkpoint.canonical_record && `Canonical record: ${checkpoint.canonical_record}`,
    checkpoint.changed_since_checkpoint?.length && `Changed: ${checkpoint.changed_since_checkpoint.join('; ')}`,
    `Attention: ${attention}`,
    'Use this as orientation for the next response. Update it if it is no longer accurate.',
  ].filter(Boolean).join('\n')
}

function lines(value) {
  return String(value || '').split('\n').map(item => item.trim()).filter(Boolean)
}

function basisLines(basis) {
  if (!Array.isArray(basis)) return []
  return basis
    .filter(item => item && typeof item.kind === 'string' && typeof item.ref === 'string')
    .map(item => `${item.kind}: ${item.ref}`)
}

function parseBasis(value) {
  return lines(value).slice(0, 8).map(item => {
    const separator = item.indexOf(':')
    return {
      kind: separator < 0 ? item : item.slice(0, separator).trim(),
      ref: separator < 0 ? '' : item.slice(separator + 1).trim(),
    }
  })
}

function provenanceText(checkpoint) {
  if (!checkpoint?.recorded_at) return ''
  const sourceKind = textValue(checkpoint.source_kind) || 'asserted'
  const basis = Array.isArray(checkpoint.basis) ? checkpoint.basis : []
  const basisText = basis.length === 1 ? '1 evidence record' : `${basis.length} evidence records`
  return sourceKind === 'relayed' && basis.length === 0
    ? 'Source: relayed · no evidence record — confirm before acting.'
    : `Source: ${sourceKind} · ${basisText}`
}

function runtimeLabels(runtime) {
  if (!runtime) return []
  const labels = []
  if (runtime.agents_active) labels.push(`${runtime.agents_active} session agent${runtime.agents_active === 1 ? '' : 's'} working`)
  if (runtime.subagents_active) labels.push(`${runtime.subagents_active} subagent${runtime.subagents_active === 1 ? '' : 's'} working`)
  if (runtime.plan) labels.push(`Plan ${runtime.plan.current}/${runtime.plan.total}${runtime.plan.goal ? ` · ${runtime.plan.goal}` : ''}`)
  if (runtime.goal) labels.push(`Goal loop ${runtime.goal.cycle}/${runtime.goal.max_cycles || '∞'}`)
  return labels
}

function stateStyle(state) {
  const tone = state === 'awaiting attention'
    ? { background: '#fef3c7', color: '#b45309' }
    : state === 'failed'
      ? { background: '#fee2e2', color: '#b91c1c' }
      : state === 'paused'
        ? { background: 'var(--bg)', color: 'var(--muted)' }
        : { background: '#d1fae5', color: '#047857' }
  return { ...tone, padding: '2px 7px', borderRadius: '9999px', fontSize: '10px', fontWeight: 600, textTransform: 'capitalize', whiteSpace: 'nowrap' }
}

function checkpointDraft(slot, checkpoint) {
  const attentionStatus = checkpoint?.attention?.status || (slot?.pending_approval ? 'unassigned' : 'none')
  return {
    role: checkpoint?.role || slot?.agent || 'Session',
    identity: checkpoint?.identity || slot?.title || slot?.key || '',
    engine: checkpoint?.engine || slot?.agent || '',
    model: checkpoint?.model || slot?.model || '',
    state: checkpoint?.state || displayState(null, slot).replaceAll(' ', '_'),
    goal: checkpoint?.goal || '',
    next_action: checkpoint?.next_action || '',
    summary: checkpoint?.summary || '',
    main_items: checkpoint?.main_items || [],
    trail: timelineEntries(slot, checkpoint).map(item => item.text),
    progress: checkpoint?.progress || { kind: 'none', completed: 0, total: 0, label: '' },
    decision: checkpoint?.decision || '',
    blocker: checkpoint?.blocker || '',
    canonical_record: checkpoint?.canonical_record || '',
    source_kind: checkpoint?.source_kind || 'asserted',
    basis: Array.isArray(checkpoint?.basis) ? checkpoint.basis : [],
    attention: {
      status: attentionStatus,
      kind: checkpoint?.attention?.kind || 'none',
      decision_key: checkpoint?.attention?.decision_key || '',
      claimed_by: checkpoint?.attention?.claimed_by || '',
      disposition: checkpoint?.attention?.disposition || '',
    },
  }
}

function generatedCheckpoint(slot) {
  const generated = slot?.session_checkpoint
  if (!generated || typeof generated.summary !== 'string' || !generated.summary.trim()) return null
  return {
    goal: textValue(generated.goal),
    next_action: textValue(generated.next_action),
    summary: generated.summary,
    main_items: Array.isArray(generated.main_items) ? generated.main_items : [],
    trail: Array.isArray(generated.trail) ? generated.trail : [],
    progress: generated.progress || { kind: 'none', completed: 0, total: 0, label: '' },
    attention: generated.attention || { status: 'none', kind: 'none', decision_key: '' },
    updated_at: generated.updated_at || '',
    automatic: true,
  }
}

function checkpointFor(slot, durable) {
  const generated = generatedCheckpoint(slot)
  const generatedIsNewer = generated && (!durable?.updated_at || generated.updated_at >= durable.updated_at)
  const story = generatedIsNewer ? generated : durable
  if (!story) return durable
  const slotTimeline = Array.isArray(slot?.session_timeline) ? slot.session_timeline : []
  const durableTimeline = Array.isArray(durable?.session_timeline) ? durable.session_timeline : []
  const sessionTimeline = slotTimeline.length > 0 ? slotTimeline : durableTimeline
  const goal = textValue(story?.goal) || textValue(durable?.goal)
  const durableAttention = durable?.attention
  const durableAttentionTerminal = durableAttention?.status === 'claimed' || durableAttention?.status === 'resolved'
  const attention = durableAttentionTerminal
    ? durableAttention
    : (generatedIsNewer ? generated?.attention : durableAttention) || generated?.attention || { status: 'none', kind: 'none', decision_key: '' }
  return {
    session_key: slot?.key || durable?.session_key,
    role: durable?.role || slot?.agent || 'Session',
    identity: durable?.identity || slot?.title || slot?.key || '',
    engine: durable?.engine || slot?.agent || '',
    model: durable?.model || slot?.model || '',
    state: durable?.state || displayState(null, slot).replaceAll(' ', '_'),
    decision: durable?.decision || '',
    blocker: durable?.blocker || '',
    canonical_record: durable?.canonical_record || '',
    changed_since_checkpoint: durable?.changed_since_checkpoint || [],
    source_links: durable?.source_links || [],
    recorded_at: durable?.recorded_at || '',
    source_kind: durable?.source_kind || '',
    basis: durable?.basis || [],
    ...story,
    goal,
    session_timeline: sessionTimeline,
    attention,
  }
}

function workflowSlot(run) {
  if (!run || typeof run !== 'object') return null
  const runId = textValue(run.run_id)
  const status = textValue(run.status)
  if (!runId || !status) return null
  const name = textValue(run.name) || runId
  const phase = textValue(run.phase)
  const eventCount = Number.isInteger(run.event_count) && run.event_count >= 0 ? run.event_count : 0
  const agentErrorCount = Number.isInteger(run.agent_error_count) && run.agent_error_count > 0 ? run.agent_error_count : 0
  return {
    key: `workflow:${runId}`,
    workflow: true,
    workflow_run_id: runId,
    workflow_status: status,
    workflow_phase: phase,
    workflow_event_count: eventCount,
    workflow_agent_error_count: agentErrorCount,
    agent: 'Workflow',
    title: name,
    running: status === 'running',
  }
}

function Multiplex() {
  const api = useAppApi()
  const navigate = useNavigate()
  const [slots, setSlots] = useState([])
  const [externalSessions, setExternalSessions] = useState([])
  const [workflowRuns, setWorkflowRuns] = useState([])
  const [checkpoints, setCheckpoints] = useState([])
  const [changedPathOverlaps, setChangedPathOverlaps] = useState([])
  const [runtimeBySession, setRuntimeBySession] = useState({})
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [openingKey, setOpeningKey] = useState('')
  const [editingKey, setEditingKey] = useState('')
  const [draft, setDraft] = useState(null)
  const [savingKey, setSavingKey] = useState('')
  const [attentionActionKey, setAttentionActionKey] = useState('')
  const [resolvingKey, setResolvingKey] = useState('')
  const [resolution, setResolution] = useState('')
  const [returningKey, setReturningKey] = useState('')
  const [handoffInstruction, setHandoffInstruction] = useState('')
  const [submittingHandoffKey, setSubmittingHandoffKey] = useState('')
  const [trackingKey, setTrackingKey] = useState('')
  const [injectedHandoffs, setInjectedHandoffs] = useState(() => new Set())
  const [presenceBySession, setPresenceBySession] = useState({})
  const [showHistory, setShowHistory] = useState(false)
  const [workspaceFilter, setWorkspaceFilter] = useState('')
  const [viewMode, setViewMode] = useState('list')

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const [slotData, externalData, checkpointData, runtimeData, workflowData, presenceData] = await Promise.all([
        api.get('/api/chat/slots'),
        api.get(`${APP_API}/external-sessions`),
        api.get(`${APP_API}/checkpoints`),
        api.get(`${APP_API}/runtime`),
        api.get(`${APP_API}/workflows`),
        api.get(`${APP_API}/session-presence`),
      ])
      setSlots(Array.isArray(slotData) ? slotData : [])
      setExternalSessions(Array.isArray(externalData?.sessions) ? externalData.sessions : [])
      setCheckpoints(Array.isArray(checkpointData?.checkpoints) ? checkpointData.checkpoints : [])
      setChangedPathOverlaps(Array.isArray(checkpointData?.changed_path_overlaps) ? checkpointData.changed_path_overlaps : [])
      setRuntimeBySession(runtimeData?.sessions && typeof runtimeData.sessions === 'object' ? runtimeData.sessions : {})
      setWorkflowRuns(Array.isArray(workflowData?.runs) ? workflowData.runs.map(workflowSlot).filter(Boolean) : [])
      setPresenceBySession(presenceData?.sessions && typeof presenceData.sessions === 'object' ? presenceData.sessions : {})
      setError('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load Multiplex state')
    } finally {
      setLoading(false)
    }
  }, [api])

  useEffect(() => { void refresh() }, [refresh])
  useEffect(() => {
    const timer = window.setInterval(() => { void refresh() }, 30_000)
    return () => window.clearInterval(timer)
  }, [refresh])
  useAppEvents('slots', refresh)

  const openConversation = useCallback(async (slot, checkpoint) => {
    const handoffKey = checkpoint ? `${slot.key}:${checkpoint.updated_at || checkpoint.summary}` : ''
    setOpeningKey(slot.key)
    try {
      if (checkpoint && !injectedHandoffs.has(handoffKey)) {
        await api.post(`/api/chat/slots/${encodeURIComponent(slot.key)}/context`, {
          content: handoffText(checkpoint, slot),
          source: 'multiplex-handoff',
          ephemeral: true,
          maxAge: 86400,
        })
        setInjectedHandoffs(previous => new Set([...previous, handoffKey]))
      }
    } catch (err) {
      setError(`Conversation opened, but its handoff was not injected: ${err instanceof Error ? err.message : 'unknown error'}`)
    } finally {
      navigate(`/chat?sid=${encodeURIComponent(slot.key)}`)
    }
  }, [api, injectedHandoffs, navigate])

  const beginCheckpoint = useCallback((slot, checkpoint) => {
    setEditingKey(slot.key)
    setDraft(checkpointDraft(slot, checkpoint))
    setError('')
  }, [])

  const saveCheckpoint = useCallback(async slot => {
    if (!draft) return
    setSavingKey(slot.key)
    try {
      const response = await api.put(`${APP_API}/checkpoints/${encodeURIComponent(slot.key)}`, draft)
      const checkpoint = response?.checkpoint
      if (!checkpoint) throw new Error('The checkpoint was saved without a response record')
      setCheckpoints(previous => [checkpoint, ...previous.filter(item => item.session_key !== slot.key)])
      setEditingKey('')
      setDraft(null)
      setError('')
    } catch (err) {
      setError(`Checkpoint was not saved: ${err instanceof Error ? err.message : 'unknown error'}`)
    } finally {
      setSavingKey('')
    }
  }, [api, draft])

  const updateAttentionClaim = useCallback(async (slot, action, payload = undefined) => {
    setAttentionActionKey(`${slot.key}:${action}`)
    try {
      await api.post(`${APP_API}/checkpoints/${encodeURIComponent(slot.key)}/attention/${action}`, payload)
      setResolvingKey('')
      setResolution('')
      await refresh()
    } catch (err) {
      setError(`Could not ${action} attention: ${err instanceof Error ? err.message : 'unknown error'}`)
    } finally {
      setAttentionActionKey('')
    }
  }, [api, refresh])

  const setNativeTracking = useCallback(async (slot, tracked) => {
    setTrackingKey(slot.key)
    try {
      await api.post(`${APP_API}/external-sessions/${encodeURIComponent(slot.key)}/tracking`, { tracked })
      await refresh()
    } catch (err) {
      setError(`Provider tracking was not updated: ${err instanceof Error ? err.message : 'unknown error'}`)
    } finally {
      setTrackingKey('')
    }
  }, [api, refresh])

  const beginReturnHandoff = useCallback(slot => {
    setReturningKey(slot.key)
    setHandoffInstruction('')
    setError('')
  }, [])

  const returnToLoop = useCallback(async slot => {
    const instruction = handoffInstruction.trim()
    if (!instruction) {
      setError('A short handoff instruction is required.')
      return
    }
    setSubmittingHandoffKey(slot.key)
    try {
      await api.post(`/api/chat/slots/${encodeURIComponent(slot.key)}/return-handoff`, { instruction })
      setReturningKey('')
      setHandoffInstruction('')
      await refresh()
    } catch (err) {
      setError(`Could not return this session to its loop: ${err instanceof Error ? err.message : 'unknown error'}`)
    } finally {
      setSubmittingHandoffKey('')
    }
  }, [api, handoffInstruction, refresh])

  const checkpointBySession = new Map(checkpoints.map(checkpoint => [checkpoint.session_key, checkpoint]))
  const visibleSlots = slots.filter(slot => slot?.key)
  const nativeSessions = externalSessions.filter(session => session?.key && !visibleSlots.some(slot => slot.key === session.key))
  const workflowSessions = workflowRuns.filter(workflow => !visibleSlots.some(slot => slot.key === workflow.key) && !nativeSessions.some(session => session.key === workflow.key))
  const checkpointOnly = checkpoints.filter(checkpoint => !visibleSlots.some(slot => slot.key === checkpoint.session_key) && !nativeSessions.some(session => session.key === checkpoint.session_key) && !workflowSessions.some(session => session.key === checkpoint.session_key))
  const rows = [
    ...visibleSlots.map(slot => ({ slot, checkpoint: checkpointFor(slot, checkpointBySession.get(slot.key)) })),
    ...nativeSessions.map(slot => ({ slot, checkpoint: checkpointFor(slot, checkpointBySession.get(slot.key)) })),
    ...workflowSessions.map(slot => ({ slot, checkpoint: null })),
    ...checkpointOnly.map(checkpoint => ({ slot: { key: checkpoint.session_key, title: checkpoint.identity, running: false, checkpointOnly: true }, checkpoint })),
  ]
  const presenceRows = rows.map(row => ({ ...row, presence: presenceBySession[row.slot.key] || fallbackPresence(row.slot) }))
  const workspaceOptions = [...new Map(presenceRows.map(({ presence }) => [presence.workspace_id || '__unmapped__', presence.workspace_label || 'Unmapped'])).entries()]
  const filteredRows = workspaceFilter ? presenceRows.filter(({ presence }) => (presence.workspace_id || '__unmapped__') === workspaceFilter) : presenceRows
  const workingRows = filteredRows.filter(({ presence }) => presence.execution === 'active')
  const openRows = filteredRows.filter(({ presence }) => presence.catalog === 'open' && presence.execution !== 'active')
  const trackedRows = filteredRows.filter(({ presence }) => presence.catalog === 'tracked' && presence.execution !== 'active')
  const historyRows = filteredRows.filter(({ presence }) => !['open', 'tracked'].includes(presence.catalog) && presence.execution !== 'active')
  const attentionRows = filteredRows.filter(({ slot, checkpoint }) => checkpoint?.attention?.status === 'unassigned' || slot.pending_approval || peerChannelAttention(slot).length > 0)
  const groups = [
    ['Working now', workingRows],
    ['Open sessions', openRows],
    ['Tracked provider sessions', trackedRows],
    ...(showHistory ? [['History', historyRows]] : []),
  ].filter(([, groupRows]) => groupRows.length > 0)
  const sharedPathsBySession = liveChangedPathOverlaps(changedPathOverlaps, workingRows)
  const overview = [
    { label: 'Sessions', value: filteredRows.length, color: '#6d28d9' },
    { label: 'Working now', value: workingRows.length, color: '#2563eb' },
    { label: 'Need attention', value: attentionRows.length, color: '#b45309' },
    { label: 'Tracked', value: trackedRows.length, color: '#64748b' },
  ]
  const overviewTotal = Math.max(filteredRows.length, 1)

  return h('main', { style: styles.root },
    h('header', { style: styles.header },
      h('div', null,
        h('div', { style: styles.titleRow }, h('h1', { style: styles.title }, 'Multiplex'), h('span', { style: styles.pill }, 'Session overview')),
        h('p', { style: styles.subtitle }, 'Working, open, and explicitly tracked sessions. Attention is a card attribute, not a lifecycle state.'),
      ),
      h('div', { style: styles.headerControls },
        h('label', { style: styles.workspaceFilter }, 'Workspace', h('select', { style: styles.input, value: workspaceFilter, onChange: event => setWorkspaceFilter(event.target.value) }, h('option', { value: '' }, 'All'), ...workspaceOptions.map(([workspaceId, label]) => h('option', { key: workspaceId || 'unmapped', value: workspaceId }, label)))),
        h('div', { style: styles.viewToggle, role: 'group', 'aria-label': 'Session view' },
          h('button', { type: 'button', style: { ...styles.viewButton, ...(viewMode === 'list' ? styles.viewButtonActive : {}) }, onClick: () => setViewMode('list'), 'aria-pressed': viewMode === 'list' }, 'List'),
          h('button', { type: 'button', style: { ...styles.viewButton, ...(viewMode === 'cards' ? styles.viewButtonActive : {}) }, onClick: () => setViewMode('cards'), 'aria-pressed': viewMode === 'cards' }, 'Cards'),
          h('button', { type: 'button', style: { ...styles.viewButton, ...(viewMode === 'grid' ? styles.viewButtonActive : {}) }, onClick: () => setViewMode('grid'), 'aria-pressed': viewMode === 'grid' }, 'Grid'),
        ),
        h('button', { style: { ...styles.ghostButton, cursor: loading ? 'default' : 'pointer', color: loading ? 'var(--muted)' : '#7c3aed' }, onClick: () => { void refresh() }, disabled: loading }, h(RefreshCw, { size: 13 }), loading ? 'Loading…' : 'Refresh'),
      ),
    ),
    error && h('div', { style: styles.error }, h(CircleAlert, { size: 15 }), error),
    !loading && rows.length === 0 && h('div', { style: styles.empty }, 'No in-scope sessions yet. Multiplex shows live work, open sessions, tracked providers, and retained work records.'),
    !loading && filteredRows.length === 0 && h('div', { style: styles.empty }, 'No sessions match this workspace.'),
    !loading && filteredRows.length > 0 && h('section', { style: styles.overview, 'aria-label': 'Session overview' }, ...overview.map(item =>
      h('div', { key: item.label, style: styles.overviewCell },
        h('span', { style: styles.overviewLabel }, item.label),
        h('span', { style: { ...styles.overviewValue, color: item.color } }, item.value),
        h('span', { style: styles.overviewBar }, h('span', { style: { ...styles.overviewSegment, background: item.color, width: `${(item.value / overviewTotal) * 100}%` } })),
      ),
    )),
    h('section', null, ...groups.map(([label, groupRows]) =>
      h('section', { key: `group:${label}` },
        h('h2', { style: styles.sectionHeading }, `${label} · ${groupRows.length}`),
        h('div', { style: viewMode === 'grid' ? styles.cardCompactGrid : viewMode === 'cards' ? styles.cardWideGrid : styles.cardList }, ...groupRows.map(({ slot, checkpoint, presence }) => {
      const runtime = runtimeBySession[slot.key]
      const card = cardData(slot, checkpoint, runtime, presence)
      const { state, title, role, line } = card
      const needsAttention = checkpoint?.attention?.status === 'unassigned' || slot.pending_approval || peerChannelAttention(slot).length > 0
      const attentionStyle = needsAttention ? { color: '#b45309', fontWeight: 600 } : {}
      const runtimeItems = [
        ...runtimeLabels(runtime),
        ...(checkpointOverdue(slot) ? ['Checkpoint needs update'] : []),
      ]
      const isEditing = editingKey === slot.key && draft
      const isReturning = returningKey === slot.key
      const isResolving = resolvingKey === slot.key
      const attention = checkpoint?.attention
      const mayReturnToLoop = canReturnToLoop(slot, runtime)
      const sharedChangedPaths = sharedPathsBySession.get(slot.key) || []
      const updateDraft = field => event => setDraft(previous => ({ ...previous, [field]: event.target.value }))
      const updateAttention = field => event => setDraft(previous => ({ ...previous, attention: { ...previous.attention, [field]: event.target.value } }))
      const provenance = provenanceText(checkpoint)
      return h('article', { key: slot.key, style: styles.card },
        h('div', { style: styles.cardTop },
          h('div', { style: { minWidth: 0 } }, h('span', { style: styles.role }, role), h('h2', { style: styles.cardTitle }, title), line && h('p', { style: styles.detail }, line)),
          h('div', { style: { display: 'flex', flexWrap: 'wrap', justifyContent: 'flex-end', alignItems: 'center', gap: '8px' } },
            h('span', { style: stateStyle(state) }, state),
            !slot.workflow && h('button', { style: { ...styles.ghostButton, color: editingKey && editingKey !== slot.key ? 'var(--muted)' : '#7c3aed', cursor: editingKey && editingKey !== slot.key ? 'default' : 'pointer' }, onClick: () => beginCheckpoint(slot, checkpoint), disabled: Boolean(editingKey) && editingKey !== slot.key }, checkpoint ? 'Edit state' : 'Add work state'),
            mayReturnToLoop && h('button', { style: { ...styles.ghostButton, color: returningKey && returningKey !== slot.key ? 'var(--muted)' : '#7c3aed', cursor: returningKey && returningKey !== slot.key ? 'default' : 'pointer' }, onClick: () => beginReturnHandoff(slot), disabled: Boolean(returningKey) && returningKey !== slot.key }, 'Return to loop'),
            slot.workflow
              ? h('button', { style: styles.ghostButton, onClick: () => navigate('/workflows') }, 'Open workflow')
              : slot.native
              ? h('details', { style: styles.nativeTools },
                h('summary', { style: { ...styles.ghostButton, ...styles.nativeToolsSummary } }, 'Resume & tracking'),
                h('div', { style: styles.nativeToolsMenu },
                  checkpoint && h('button', { style: styles.ghostButton, onClick: () => { void navigator.clipboard?.writeText(handoffText(checkpoint, slot)) } }, 'Copy handoff'),
                  slot.native_session_id && h('button', { style: styles.ghostButton, onClick: () => { void navigator.clipboard?.writeText(slot.native_session_id) } }, 'Copy resume ID'),
                  h('button', { style: styles.ghostButton, onClick: () => { void setNativeTracking(slot, presence.catalog !== 'tracked') }, disabled: trackingKey === slot.key }, trackingKey === slot.key ? 'Updating…' : presence.catalog === 'tracked' ? 'Move to history' : 'Keep visible'),
                ),
              )
              : h('button', { style: { ...styles.primaryButton, cursor: openingKey === slot.key ? 'default' : 'pointer' }, onClick: () => { void openConversation(slot, checkpoint) }, disabled: openingKey === slot.key }, openingKey === slot.key ? 'Opening…' : 'Open', h(ArrowUpRight, { size: 13 })),
          ),
        ),
        h('div', { style: styles.checkpoint },
          h('p', { style: styles.checkpointLabel }, 'Goal'),
          h('p', { style: styles.summary }, card.goal),
          card.autoNudgeInstruction && h('div', { style: { marginTop: '10px' } },
            h('p', { style: styles.checkpointLabel }, 'AutoNudge instruction'),
            h('p', { style: styles.summary }, card.autoNudgeInstruction),
          ),
          h('div', { style: { marginTop: '10px' } },
            h('p', { style: styles.checkpointLabel }, card.currentWorkLabel),
            h('p', { style: styles.summary }, card.currentWork),
          ),
          provenance && h('p', { style: styles.detail }, provenance),
          card.mainItems.length > 0 && h('div', { style: { marginTop: '10px' } },
            h('p', { style: styles.checkpointLabel }, 'Main items'),
            h('ul', { style: styles.bulletList }, ...card.mainItems.map((item, index) => h('li', { key: `${slot.key}-item-${index}` }, item))),
          ),
          h('div', { style: { marginTop: '10px' } },
            h('p', { style: styles.checkpointLabel }, 'Next'),
            h('p', { style: styles.summary }, card.nextAction),
          ),
          card.updates.length > 0 && h('div', { style: { marginTop: '10px' } },
            h('p', { style: styles.checkpointLabel }, 'Updates'),
            h('ul', { style: styles.bulletList }, ...card.updates.map((item, index) => h('li', { key: `${slot.key}-update-${index}` }, item.text))),
          ),
          sharedChangedPaths.length > 0 && h('div', { style: { marginTop: '10px' } },
            h('p', { style: styles.checkpointLabel }, 'Shared changed paths'),
            h('p', { style: styles.summary }, `Also listed by another live card: ${sharedChangedPaths.join(', ')}. Checkpoints have no per-path record time, so this signals shared scope only—not writer, order, ownership, or resolution.`),
          ),
          attention?.can_claim && h('button', { style: { ...styles.ghostButton, marginTop: '10px' }, onClick: () => { void updateAttentionClaim(slot, 'claim') }, disabled: attentionActionKey === `${slot.key}:claim` }, attentionActionKey === `${slot.key}:claim` ? 'Claiming…' : 'Claim attention'),
          attention?.can_release && h('div', { style: { display: 'flex', gap: '8px', marginTop: '10px' } },
            h('button', { style: styles.ghostButton, onClick: () => { void updateAttentionClaim(slot, 'release') }, disabled: attentionActionKey === `${slot.key}:release` }, attentionActionKey === `${slot.key}:release` ? 'Releasing…' : 'Release'),
            h('button', { style: styles.ghostButton, onClick: () => { setResolvingKey(slot.key); setResolution(''); setError('') } }, 'Resolve'),
          ),
          runtimeItems.length > 0 && h('div', { style: styles.runtime }, ...runtimeItems.map(item => h('span', { key: item, style: styles.runtimePill }, item))),
        ),
        isResolving && h('form', { style: styles.editor, onSubmit: event => { event.preventDefault(); void updateAttentionClaim(slot, 'resolve', { disposition: resolution }) } },
          h('p', { style: styles.checkpointLabel }, 'Resolve attention'),
          h('label', { style: styles.field }, h('span', { style: styles.fieldLabel }, 'Disposition'), h('textarea', { style: styles.textarea, value: resolution, onChange: event => setResolution(event.target.value), maxLength: 360, required: true })),
          h('div', { style: styles.editorActions },
            h('button', { type: 'button', style: styles.ghostButton, onClick: () => { setResolvingKey(''); setResolution('') }, disabled: attentionActionKey === `${slot.key}:resolve` }, 'Cancel'),
            h('button', { type: 'submit', style: styles.primaryButton, disabled: attentionActionKey === `${slot.key}:resolve` }, attentionActionKey === `${slot.key}:resolve` ? 'Resolving…' : 'Resolve attention'),
          ),
        ),
        isReturning && h('form', { style: styles.editor, onSubmit: event => { event.preventDefault(); void returnToLoop(slot) } },
          h('p', { style: styles.checkpointLabel }, 'Return to loop'),
          h('p', { style: styles.editorIntro }, 'Give the next turn one short instruction. A human message can take priority before the automatic cycle. Multiplex records the handoff; it does not claim the work is complete.'),
          h('label', { style: styles.field }, h('span', { style: styles.fieldLabel }, 'Handoff instruction'), h('textarea', { style: styles.textarea, value: handoffInstruction, onChange: event => setHandoffInstruction(event.target.value), maxLength: 240, required: true })),
          h('div', { style: styles.editorActions },
            h('button', { type: 'button', style: styles.ghostButton, onClick: () => { setReturningKey(''); setHandoffInstruction(''); setError('') }, disabled: submittingHandoffKey === slot.key }, 'Cancel'),
            h('button', { type: 'submit', style: { ...styles.primaryButton, cursor: submittingHandoffKey === slot.key ? 'default' : 'pointer' }, disabled: submittingHandoffKey === slot.key }, submittingHandoffKey === slot.key ? 'Returning…' : 'Return to loop'),
          ),
        ),
        isEditing && h('form', { style: styles.editor, onSubmit: event => { event.preventDefault(); void saveCheckpoint(slot) } },
          h('p', { style: styles.checkpointLabel }, checkpoint ? 'Edit work state' : 'Add work state'),
          h('p', { style: styles.editorIntro }, 'Record a concise change: current work, next action, notes, or a material blocker. Do not paste a transcript.'),
          h('details', { style: styles.editorDisclosure },
            h('summary', null, 'Goal, status, identity and attention'),
            h('div', { style: { marginTop: '10px' } }, h('div', { style: styles.fieldGrid },
            h('label', { style: styles.field }, h('span', { style: styles.fieldLabel }, 'Role'), h('input', { style: styles.input, value: draft.role, onChange: updateDraft('role'), maxLength: 120, required: true })),
            h('label', { style: styles.field }, h('span', { style: styles.fieldLabel }, 'Work identity'), h('input', { style: styles.input, value: draft.identity, onChange: updateDraft('identity'), maxLength: 240, required: true })),
            h('label', { style: styles.field }, h('span', { style: styles.fieldLabel }, 'Engine'), h('input', { style: styles.input, value: draft.engine, onChange: updateDraft('engine'), maxLength: 120 })),
            h('label', { style: styles.field }, h('span', { style: styles.fieldLabel }, 'Model'), h('input', { style: styles.input, value: draft.model, onChange: updateDraft('model'), maxLength: 120 })),
            h('label', { style: styles.field }, h('span', { style: styles.fieldLabel }, 'Goal'), h('input', { style: styles.input, value: draft.goal, onChange: updateDraft('goal'), maxLength: 240 })),
            h('label', { style: styles.field }, h('span', { style: styles.fieldLabel }, 'Next action'), h('input', { style: styles.input, value: draft.next_action, onChange: updateDraft('next_action'), maxLength: 160 })),
            h('label', { style: styles.field }, h('span', { style: styles.fieldLabel }, 'State'), h('select', { style: styles.input, value: draft.state, onChange: updateDraft('state') },
              h('option', { value: 'unattended' }, 'Unattended'), h('option', { value: 'active' }, 'Active'), h('option', { value: 'awaiting_attention' }, 'Awaiting attention'), h('option', { value: 'paused' }, 'Paused'), h('option', { value: 'failed' }, 'Failed'),
            )),
            h('label', { style: styles.field }, h('span', { style: styles.fieldLabel }, 'Attention'), h('select', { style: styles.input, value: draft.attention.status, onChange: updateAttention('status') },
              h('option', { value: 'none' }, 'No attention request'), h('option', { value: 'unassigned' }, 'Needs you · unassigned'),
            )),
            h('label', { style: styles.field }, h('span', { style: styles.fieldLabel }, 'Attention type'), h('select', { style: styles.input, value: draft.attention.kind, onChange: updateAttention('kind') },
              h('option', { value: 'none' }, 'General attention'), h('option', { value: 'decision' }, 'Material decision'),
            )),
            draft.attention.kind === 'decision' && h('label', { style: styles.field }, h('span', { style: styles.fieldLabel }, 'Decision key'), h('input', { style: styles.input, value: draft.attention.decision_key, onChange: updateAttention('decision_key'), maxLength: 120 })),
            )),
          ),
          h('label', { style: { ...styles.field, marginTop: '10px' } }, h('span', { style: styles.fieldLabel }, 'Current work'), h('textarea', { style: styles.textarea, value: draft.summary, onChange: updateDraft('summary'), maxLength: 900, required: true })),
          h('label', { style: { ...styles.field, marginTop: '10px' } }, h('span', { style: styles.fieldLabel }, 'Next action'), h('input', { style: styles.input, value: draft.next_action, onChange: updateDraft('next_action'), maxLength: 160 })),
          h('div', { style: styles.fieldGrid, marginTop: '10px' },
            h('label', { style: styles.field }, h('span', { style: styles.fieldLabel }, 'Main items · one per line'), h('textarea', { style: styles.textarea, value: draft.main_items.join('\n'), onChange: event => setDraft(previous => ({ ...previous, main_items: lines(event.target.value).slice(0, 4) })), maxLength: 643 })),
            h('label', { style: styles.field }, h('span', { style: styles.fieldLabel }, 'Notes / changes · one short line per event'), h('textarea', { style: styles.textarea, value: draft.trail.join('\n'), onChange: event => setDraft(previous => ({ ...previous, trail: lines(event.target.value).slice(0, 7) })), maxLength: 1546 })),
          ),
          h('details', { style: styles.editorDisclosure },
            h('summary', null, 'Progress, decision, blocker and evidence'),
            h('div', { style: { marginTop: '10px' } },
              h('div', { style: styles.fieldGrid },
                h('label', { style: styles.field }, h('span', { style: styles.fieldLabel }, 'Progress type'), h('select', { style: styles.input, value: draft.progress.kind, onChange: event => setDraft(previous => ({ ...previous, progress: event.target.value === 'none' ? { kind: 'none', completed: 0, total: 0, label: '' } : { ...previous.progress, kind: event.target.value } })) }, h('option', { value: 'none' }, 'No saved progress'), h('option', { value: 'plan' }, 'Plan'), h('option', { value: 'goal' }, 'Goal'))),
                draft.progress.kind !== 'none' && h('label', { style: styles.field }, h('span', { style: styles.fieldLabel }, 'Completed'), h('input', { style: styles.input, type: 'number', min: 0, value: draft.progress.completed, onChange: event => setDraft(previous => ({ ...previous, progress: { ...previous.progress, completed: Number(event.target.value) } })) })),
                draft.progress.kind !== 'none' && h('label', { style: styles.field }, h('span', { style: styles.fieldLabel }, 'Total'), h('input', { style: styles.input, type: 'number', min: 1, value: draft.progress.total, onChange: event => setDraft(previous => ({ ...previous, progress: { ...previous.progress, total: Number(event.target.value) } })) })),
                draft.progress.kind !== 'none' && h('label', { style: styles.field }, h('span', { style: styles.fieldLabel }, 'Progress label'), h('input', { style: styles.input, value: draft.progress.label, onChange: event => setDraft(previous => ({ ...previous, progress: { ...previous.progress, label: event.target.value } })), maxLength: 160 })),
              ),
              h('div', { style: styles.fieldGrid, marginTop: '10px' },
                h('label', { style: styles.field }, h('span', { style: styles.fieldLabel }, 'Decision'), h('textarea', { style: styles.textarea, value: draft.decision, onChange: updateDraft('decision'), maxLength: 360 })),
                h('label', { style: styles.field }, h('span', { style: styles.fieldLabel }, 'Blocker'), h('textarea', { style: styles.textarea, value: draft.blocker, onChange: updateDraft('blocker'), maxLength: 360 })),
                h('label', { style: styles.field }, h('span', { style: styles.fieldLabel }, 'Canonical record'), h('textarea', { style: styles.textarea, value: draft.canonical_record, onChange: updateDraft('canonical_record'), maxLength: 500 })),
              ),
              h('div', { style: styles.fieldGrid, marginTop: '10px' },
                h('label', { style: styles.field }, h('span', { style: styles.fieldLabel }, 'Claim source'), h('select', { style: styles.input, value: draft.source_kind, onChange: updateDraft('source_kind') },
                  h('option', { value: 'observed' }, 'Observed directly'), h('option', { value: 'asserted' }, 'Asserted by this session'), h('option', { value: 'relayed' }, 'Relayed by another session'),
                )),
                h('label', { style: styles.field }, h('span', { style: styles.fieldLabel }, 'Evidence · kind: reference, one per line'), h('textarea', { style: styles.textarea, value: basisLines(draft.basis).join('\n'), onChange: event => setDraft(previous => ({ ...previous, basis: parseBasis(event.target.value) })), maxLength: 1840 })),
              ),
            ),
          ),
          h('div', { style: styles.editorActions },
            h('button', { type: 'button', style: styles.ghostButton, onClick: () => { setEditingKey(''); setDraft(null); setError('') }, disabled: savingKey === slot.key }, 'Cancel'),
            h('button', { type: 'submit', style: { ...styles.primaryButton, cursor: savingKey === slot.key ? 'default' : 'pointer' }, disabled: savingKey === slot.key }, savingKey === slot.key ? 'Saving…' : 'Save work state'),
          ),
        ),
        h('footer', { style: styles.footer },
          h('span', { style: { ...styles.footerItem, ...attentionStyle } }, needsAttention ? h(CircleAlert, { size: 12 }) : h(CircleCheck, { size: 12 }), attentionText(checkpoint, slot)),
          peerDeliveryText(slot) && h('span', { style: styles.footerItem }, peerDeliveryText(slot)),
          !(runtime?.agents_active && card.liveStatus === 'The session is active.') && h('span', { style: styles.footerItem }, card.liveStatus),
          h('span', { style: styles.footerItem }, sessionLocation(presence)),
          h('span', { style: styles.footerItem }, footerTimestamp(slot, checkpoint)),
        ),
      )
    })),
      ),
    )),
    !loading && historyRows.length > 0 && h('div', { style: { display: 'flex', justifyContent: 'center', margin: '4px 0 16px' } },
      h('button', { style: styles.ghostButton, onClick: () => setShowHistory(previous => !previous) }, showHistory ? `Hide history (${historyRows.length})` : `Show history (${historyRows.length})`),
    ),
  )
}

export default Multiplex
