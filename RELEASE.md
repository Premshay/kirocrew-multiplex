# Release readiness

Version 0.1.1 updates manifest copy and usage documentation only; runtime code,
permissions, and artwork are unchanged from the verified 0.1.0 release below.
App Store inclusion requires
maintainer approval of the listing request.

Verified on 2026-09-20:

- 92 app tests passed with imports from stock KiroCrew 0.8.0 source at upstream
  commit `234121ed0`, using the installed Python dependency environment.
- JavaScript syntax and patch whitespace checks passed.
- Clean-clone local installation succeeded in an isolated app home.
- The shipped UI rendered in Chromium with fictional session data.
- The store screenshot contains no real sessions, workspace paths, or identities.
- The screenshot covers active work, helper and plan signals, pending tool
  approval, an unclaimed decision, an idle stale checkpoint, tracked native
  sessions, and resolved attention.
- Source audit removed personal-name fixture values. Public repository attribution
  remains in the installation URL and Git author metadata.
- Stock upstream lacks the agent `session_checkpoint` tool and return-handoff
  endpoint. The README states those limits; the return control now requires an
  actually registered POST endpoint as well as an active loop.
- Removed personal-harness scope overrides, companion-written approval status,
  and companion runtime-policy lookups. Regression tests verify discovery from
  stock workspace configuration and runtime snapshots without companion files
  or policy calls.

Live acceptance completed on 2026-09-20 in a fresh Python 3.12 environment with
stock KiroCrew 0.8.0 at `234121ed0` and its declared dependencies:

- All 92 tests passed again in the clean environment.
- Local installation and enablement succeeded with operator-authorized trust
  scoped to Multiplex in a separate test home.
- Authenticated runtime and checkpoint routes returned HTTP 200.
- The stock dashboard was built from that same checkout. Multiplex opened from
  its sidebar, and List, Cards, and Grid selected successfully.
- The card editor saved current work, next action, and an update; the saved
  current-work text remained visible after a full page reload.
- The rendered light-theme page was visually inspected. Acceptance captures
  remain private; the published gallery contains fictional data only.

The host's unrelated `/api/instances` request returned HTTP 403. Agent inference
was not exercised; a host sandbox restriction prevented background agent
startup. Neither blocked the app routes or dashboard actions tested above.

The release must run on stock KiroCrew without a companion plugin or personal
agent harness. Optional host extensions are not installation requirements.
Local platform-startup failures are not evidence of a Multiplex dependency;
live acceptance must use a correctly configured stock host.

Earlier KiroCrew versions have not been validated. Verify anonymous repository
access when publishing and submit the official listing issue at the release pin.

Packaging follows the external-app skill: Git ignores app credentials, install
metadata, generated build directories, and runtime data. The current publishing
guide supersedes the skill's older registry-PR recipe: request an official
catalog listing through an issue after verification, without a code PR.

The screenshot is a browser capture of `ui/index.mjs` using fictional API
responses and SDK stubs. It is labelled as demonstration data. Hero and icon
images are illustrations, not product captures.

Do not include real session screenshots, gateway storage, credentials, hooks
containing local paths, or private project names in a release archive.
