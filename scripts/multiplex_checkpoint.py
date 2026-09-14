#!/usr/bin/env python3
"""Record a bounded milestone checkpoint for one registered native session."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Sequence


APP_NAME = "multiplex"
GATEWAY = os.environ.get("MULTIPLEX_GATEWAY", "http://127.0.0.1:5476")
_BASIS_KINDS = frozenset({"commit", "channel_message", "canonical_record"})
SECRET_PATH = Path(os.environ.get(
    "MULTIPLEX_APP_SECRET_FILE", f"~/.kiro/crew/apps/{APP_NAME}/.app_secret"
)).expanduser()


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def _put_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="PUT",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def _app_credential() -> str:
    secret = SECRET_PATH.read_text(encoding="utf-8").strip()
    if not secret:
        raise RuntimeError("Multiplex app credential is unavailable")
    result = _post_json(f"{GATEWAY}/api/apps/{APP_NAME}/token", {}, {"X-App-Secret": secret})
    credential = str(result.get("token") or "")
    if not credential:
        raise RuntimeError("Multiplex app credential exchange failed")
    return credential


def record_native_event(source: str, session_id: str, event: str, detail: str = "") -> dict[str, Any]:
    credential = _app_credential()
    native_id = urllib.parse.quote(session_id, safe="")
    return _post_json(
        f"{GATEWAY}/api/apps/{APP_NAME}/native-events/{source}/{native_id}?token={urllib.parse.quote(credential, safe='')}",
        {"event": event, "detail": detail},
        {},
    )


def register_native_session(
    source: str,
    session_id: str,
    *,
    workspace_path: str,
    title: str = "",
    model: str = "",
    transcript_path: str = "",
) -> dict[str, Any]:
    credential = _app_credential()
    native_id = urllib.parse.quote(session_id, safe="")
    return _put_json(
        f"{GATEWAY}/api/apps/{APP_NAME}/native-sessions/{source}/{native_id}?token={urllib.parse.quote(credential, safe='')}",
        {
            "workspace_path": workspace_path,
            "title": title,
            "model": model,
            "transcript_path": transcript_path,
        },
    )


def parse_basis(values: list[str]) -> list[dict[str, str]]:
    """Turn explicit kind: reference arguments into bounded evidence records."""
    if len(values) > 8:
        raise RuntimeError("at most eight --basis values are allowed")
    records: list[dict[str, str]] = []
    for value in values:
        kind, separator, reference = value.partition(":")
        if not separator or not kind.strip() or not reference.strip():
            raise RuntimeError("--basis must use 'kind: reference'")
        normalized_kind = kind.strip()
        if normalized_kind not in _BASIS_KINDS:
            raise RuntimeError("--basis kind is not supported")
        records.append({"kind": normalized_kind, "ref": reference.strip()})
    return records


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source", choices=("antigravity", "claude", "codex"), required=True
    )
    parser.add_argument("--session-id", required=True, help="Stable provider-native session ID")
    parser.add_argument("--goal", default="", help="Current objective (max 240 chars)")
    parser.add_argument("--summary", required=True, help="Current work in one short sentence")
    parser.add_argument("--item", action="append", default=[], help="Current main item; repeat at most four times")
    parser.add_argument("--milestone", required=True, help="Short completed, changed, or blocked event")
    parser.add_argument(
        "--next-action",
        default="",
        help="Concrete next step when work remains (max 160 chars)",
    )
    parser.add_argument("--state", choices=("unattended", "active", "awaiting_attention", "paused", "failed"), default="active")
    parser.add_argument("--decision", default="")
    parser.add_argument(
        "--workspace", default="",
        help="Project root to register under when the session is not yet known "
             "(defaults to the working directory)",
    )
    parser.add_argument("--title", default="", help="Display title for a first registration")
    parser.add_argument("--blocker", default="")
    parser.add_argument(
        "--source-kind",
        choices=("observed", "asserted", "relayed"),
        default="asserted",
        help="Whether this writer observed, asserted, or relayed the claim",
    )
    parser.add_argument(
        "--basis",
        action="append",
        default=[],
        metavar="KIND: REFERENCE",
        help="Evidence record; repeat at most eight times",
    )
    return parser.parse_args(argv)


def checkpoint_payload(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "state": args.state,
        "goal": args.goal,
        "summary": args.summary,
        "main_items": args.item,
        "trail": [args.milestone],
        "next_action": args.next_action,
        "decision": args.decision,
        "blocker": args.blocker,
        "source_kind": args.source_kind,
        "basis": parse_basis(args.basis),
        "progress": {"kind": "none", "completed": 0, "total": 0, "label": ""},
        "attention": {"status": "none", "claimed_by": "", "disposition": ""},
    }


def main() -> int:
    args = parse_args()
    if len(args.item) > 4:
        raise RuntimeError("at most four --item values are allowed")
    credential = _app_credential()
    native_id = urllib.parse.quote(args.session_id, safe="")
    payload = checkpoint_payload(args)
    url = (
        f"{GATEWAY}/api/apps/{APP_NAME}/native-checkpoints/{args.source}/{native_id}"
        f"?token={urllib.parse.quote(credential, safe='')}"
    )

    def _put() -> dict[str, Any]:
        return _put_json(url, payload)

    try:
        try:
            result = _put()
        except urllib.error.HTTPError as exc:
            # 404 means Multiplex does not know this session, not that the
            # checkpoint is bad. Registration was already implemented here and
            # simply unreachable from the command line, so a session whose id
            # changed -- a gateway restart rekeys one -- could never recover:
            # every later checkpoint 404'd and the caller was told only that it
            # "isn't registered", with nothing it could do about it.
            if exc.code != 404:
                raise
            try:
                register_native_session(
                    args.source,
                    args.session_id,
                    workspace_path=args.workspace or os.getcwd(),
                    title=args.title,
                )
            except urllib.error.HTTPError as reg_exc:
                # Registration is refused for some sources ("native source does
                # not support registration" for claude, which is registered by
                # its SessionStart hook instead). A bare 404 told the caller only
                # that it "isn't registered" -- true, unactionable, and silent
                # about the fact that nothing it can run will change that. Say
                # what the server said.
                detail = reg_exc.read().decode("utf-8", "replace").strip()
                raise RuntimeError(
                    f"native checkpoint was not recorded: session {args.session_id} is "
                    f"not discoverable as a NATIVE session ({detail or reg_exc.reason}).\n"
                    f"If this is a KiroCrew dashboard session, that is correct and this "
                    f"script is the wrong tool: Multiplex deliberately omits sessions it "
                    f"already manages, because their card comes from the dashboard slot "
                    f"and a native record beside it would be 'a shadow that can never "
                    f"hold a checkpoint'. Use the session_checkpoint MCP tool.\n"
                    f"If that tool is missing from the toolset, Crew does not own this "
                    f"project's .claude/settings.local.json -- one live claim per project "
                    f"DIRECTORY, so a sibling session in the same repo holds it. Giving "
                    f"each long-lived session its own worktree gives each its own claim."
                ) from reg_exc
            result = _put()
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"native checkpoint was not recorded: {exc}") from exc
    checkpoint = result.get("checkpoint") or {}
    print(f"recorded {checkpoint.get('session_key', 'native checkpoint')}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
