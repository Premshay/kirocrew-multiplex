from __future__ import annotations

import importlib.util
from pathlib import Path

PRESENCE_PATH = Path(__file__).parents[1] / "backend" / "session_presence.py"


def _module():
    spec = importlib.util.spec_from_file_location(
        "multiplex_session_presence_test", PRESENCE_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _home_with_workspaces(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    config = home / ".kiro" / "crew" / "config.json"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(
        """{"workspaces": {"project": {"dir": "/work/project"}, "child": {"dir": "/work/project/child"}}}""",
        encoding="utf-8",
    )
    return home


def test_dashboard_slot_is_open_while_idle_and_keeps_declared_workspace(
    tmp_path: Path,
) -> None:
    presence = _module().dashboard_presence(
        {
            "key": "chat-5",
            "running": False,
            "workspace": "project",
            "project": "/work/project",
        },
        home=_home_with_workspaces(tmp_path),
    )

    assert presence == {
        "session_key": "chat-5",
        "source": "kirocrew",
        "catalog": "open",
        "execution": "idle",
        "workspace_id": "project",
        "workspace_label": "Project",
        "project_root": "/work/project",
        "evidence": "dashboard_slot",
    }


def test_native_session_is_observed_not_claimed_open_and_uses_longest_workspace(
    tmp_path: Path,
) -> None:
    presence = _module().native_presence(
        {
            "key": "native:codex:one",
            "source_type": "codex",
            "project_root": "/work/project/child/repo",
        },
        home=_home_with_workspaces(tmp_path),
    )

    assert presence["catalog"] == "observed"
    assert presence["execution"] == "unknown"
    assert presence["workspace_id"] == "child"
    assert presence["workspace_label"] == "Child"


def test_native_runtime_and_explicit_tracking_have_distinct_lifecycle_meanings(
    tmp_path: Path,
) -> None:
    module = _module()
    runtime = module.native_presence(
        {
            "key": "native:claude:live",
            "source_type": "claude",
            "project_root": "/work/project",
            "runtime_catalog": "open",
            "runtime_execution": "unknown",
            "runtime_evidence": "claude_session_registry",
        },
        home=_home_with_workspaces(tmp_path),
    )
    tracked = module.native_presence(
        {
            "key": "native:codex:retained",
            "source_type": "codex",
            "project_root": "/work/project",
            "tracked": True,
        },
        home=_home_with_workspaces(tmp_path),
    )

    assert (runtime["catalog"], runtime["execution"], runtime["evidence"]) == (
        "open",
        "unknown",
        "claude_session_registry",
    )
    assert (tracked["catalog"], tracked["execution"], tracked["evidence"]) == (
        "tracked",
        "unknown",
        "explicit_tracking",
    )


def test_unmapped_path_is_explicit_and_checkpoint_only_has_no_lifecycle_authority(
    tmp_path: Path,
) -> None:
    module = _module()
    native = module.native_presence(
        {
            "key": "native:claude:one",
            "source_type": "claude",
            "project_root": "/outside",
        },
        home=_home_with_workspaces(tmp_path),
    )
    checkpoint = module.checkpoint_presence({"session_key": "saved-only"})

    assert native["workspace_id"] == ""
    assert native["workspace_label"] == "Unmapped"
    assert checkpoint["catalog"] == "unknown"
    assert checkpoint["execution"] == "unknown"
