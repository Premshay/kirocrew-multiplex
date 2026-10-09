# Changelog

## Unreleased

- A stored `active` or `awaiting_attention` card now reads `ended`, with its last-seen time, unless something live backs it: an open or tracked session, active execution, a pending approval or a peer request. Stored records are not edited.

## 0.1.1 — 2026-09-20

- Explain the whole-team overview through five concrete operator situations.
- Add a walkthrough for session checkpoints and a recorded review handoff.
- App behavior and permissions are unchanged.

## 0.1.0 — 2026-09-14

- Initial standalone release of the Multiplex KiroCrew app.
- Checkpoint-led list, cards, and compact grid views for KiroCrew, native, and
  workflow records.
- Optional provider lifecycle and checkpoint bridge scripts.
