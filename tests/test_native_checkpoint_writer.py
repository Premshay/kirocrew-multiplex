from __future__ import annotations

import importlib.util
from pathlib import Path


def _writer_module():
    path = Path(__file__).parents[1] / "scripts" / "multiplex_checkpoint.py"
    spec = importlib.util.spec_from_file_location("multiplex_checkpoint", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_native_checkpoint_writer_authors_goal_and_next_action() -> None:
    module = _writer_module()
    args = module.parse_args(
        [
            "--source",
            "codex",
            "--session-id",
            "codex-123",
            "--goal",
            "Make Multiplex checkpoints useful.",
            "--summary",
            "Adding native checkpoint fields.",
            "--item",
            "Expose native arguments",
            "--milestone",
            "Mapped the writer contract.",
            "--next-action",
            "Run the focused writer tests.",
        ]
    )

    payload = module.checkpoint_payload(args)

    assert payload["goal"] == "Make Multiplex checkpoints useful."
    assert payload["next_action"] == "Run the focused writer tests."
    assert payload["main_items"] == ["Expose native arguments"]
