"""Project provider facts onto one truthful Multiplex session-presence shape."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

_CATALOG_STATES = frozenset({"open", "tracked", "observed", "archived", "unknown"})
_EXECUTION_STATES = frozenset({"active", "idle", "unknown"})


def _workspace_roots(home: Path) -> list[tuple[str, Path]]:
    """Read registered workspaces; an unregistered path stays explicitly unmapped."""
    try:
        config = json.loads(
            (home / ".kiro" / "crew" / "config.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return []
    workspaces = config.get("workspaces")
    if not isinstance(workspaces, dict):
        return []
    roots: list[tuple[str, Path]] = []
    for workspace_id, raw in workspaces.items():
        if not isinstance(workspace_id, str) or not isinstance(raw, dict):
            continue
        directory = raw.get("dir")
        if isinstance(directory, str) and directory.startswith("/"):
            roots.append((workspace_id, Path(directory)))
    return roots


def workspace_for_path(path: object, *, home: Path | None = None) -> tuple[str, str]:
    """Return the longest registered workspace match for a concrete project path."""
    if not isinstance(path, str) or not path.startswith("/"):
        return "", "Unmapped"
    candidate = Path(path)
    matches = [
        (workspace_id, root)
        for workspace_id, root in _workspace_roots(home or Path.home())
        if candidate == root or candidate.is_relative_to(root)
    ]
    if not matches:
        return "", "Unmapped"
    workspace_id, _ = max(matches, key=lambda item: len(item[1].parts))
    return workspace_id, workspace_id.replace("-", " ").title()


def _presence(
    *,
    session_key: object,
    source: str,
    catalog: str,
    execution: str,
    project_root: object,
    workspace_id: object = "",
    evidence: str,
    home: Path | None = None,
) -> dict[str, str]:
    if catalog not in _CATALOG_STATES or execution not in _EXECUTION_STATES:
        raise ValueError("unsupported session presence state")
    project = (
        project_root
        if isinstance(project_root, str) and project_root.startswith("/")
        else ""
    )
    configured_id, workspace_label = workspace_for_path(project, home=home)
    known_workspace = workspace_id.strip() if isinstance(workspace_id, str) else ""
    return {
        "session_key": str(session_key or ""),
        "source": source,
        "catalog": catalog,
        "execution": execution,
        "workspace_id": known_workspace or configured_id,
        "workspace_label": (
            known_workspace.replace("-", " ").title()
            if known_workspace
            else workspace_label
        ),
        "project_root": project,
        "evidence": evidence,
    }


def dashboard_presence(
    slot: dict[str, Any], *, home: Path | None = None
) -> dict[str, str]:
    """A dashboard slot is authoritatively open even when no turn is executing."""
    return _presence(
        session_key=slot.get("key"),
        source="kirocrew",
        catalog="open",
        execution="active" if slot.get("running") is True else "idle",
        project_root=slot.get("project"),
        workspace_id=slot.get("workspace"),
        evidence="dashboard_slot",
        home=home,
    )


def native_presence(
    session: dict[str, Any], *, home: Path | None = None
) -> dict[str, str]:
    """Project native runtime evidence without treating a transcript as lifecycle truth."""
    runtime_catalog = session.get("runtime_catalog")
    runtime_execution = session.get("runtime_execution")
    runtime_evidence = session.get("runtime_evidence")
    catalog = runtime_catalog if runtime_catalog in _CATALOG_STATES else "observed"
    execution = (
        runtime_execution if runtime_execution in _EXECUTION_STATES else "unknown"
    )
    evidence = runtime_evidence if isinstance(runtime_evidence, str) else ""
    if session.get("tracked") is True and catalog != "open":
        catalog = "tracked"
        evidence = (
            f"explicit_tracking+{evidence}" if evidence else "explicit_tracking"
        )
    if not evidence:
        evidence = "bounded_transcript"
    return _presence(
        session_key=session.get("key"),
        source=str(session.get("source_type") or "native"),
        catalog=catalog,
        execution=execution,
        project_root=session.get("project_root"),
        evidence=evidence,
        home=home,
    )


def workflow_presence(workflow: dict[str, Any]) -> dict[str, str]:
    """Workflows are visible work records, not resumable chat sessions."""
    status = workflow.get("status")
    return _presence(
        session_key=f"workflow:{workflow.get('run_id', '')}",
        source="workflow",
        catalog="open" if status == "running" else "archived",
        execution="active" if status == "running" else "idle",
        project_root="",
        evidence="workflow_run",
    )


def checkpoint_presence(checkpoint: dict[str, Any]) -> dict[str, str]:
    """An orphaned record has durable detail but no lifecycle authority."""
    return _presence(
        session_key=checkpoint.get("session_key"),
        source="checkpoint",
        catalog="unknown",
        execution="unknown",
        project_root="",
        evidence="checkpoint_only",
    )


def index_presence(records: Iterable[dict[str, str]]) -> dict[str, dict[str, str]]:
    """Return the browser contract keyed by the same session identity as cards."""
    return {
        record["session_key"]: record
        for record in records
        if isinstance(record.get("session_key"), str) and record["session_key"]
    }
