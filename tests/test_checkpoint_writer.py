from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _writer_module():
    path = Path(__file__).parents[1] / "scripts" / "multiplex_checkpoint.py"
    spec = importlib.util.spec_from_file_location("multiplex_checkpoint", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_writer_parses_typed_evidence_records() -> None:
    writer = _writer_module()

    assert writer.parse_basis(["commit: bf845bb6", "channel_message: cd0d6bf9"]) == [
        {"kind": "commit", "ref": "bf845bb6"},
        {"kind": "channel_message", "ref": "cd0d6bf9"},
    ]


@pytest.mark.parametrize("value", ["commit", ": missing kind", "commit:   "])
def test_writer_rejects_ambiguous_evidence_records(value: str) -> None:
    writer = _writer_module()

    with pytest.raises(RuntimeError, match="kind: reference"):
        writer.parse_basis([value])


def test_writer_rejects_unknown_evidence_kind() -> None:
    writer = _writer_module()

    with pytest.raises(RuntimeError, match="kind is not supported"):
        writer.parse_basis(["ticket: OPS-10"])
