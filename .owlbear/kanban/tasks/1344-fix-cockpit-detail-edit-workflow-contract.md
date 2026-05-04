---
id: 1344
title: Fix Cockpit detail edit workflow contract
status: backlog
priority: critical
created: 2026-05-04T17:27:34.891597+00:00
updated: 2026-05-04T17:28:16+00:00
tags:
- sync-blocker
- cockpit
- cockpit-api
- cockpit-frontend
parent:
depends_on:
- 1348
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

Cockpit exposes task-detail controls and mutation routes that do not agree on what is editable. The backend route accepts fields that either crash (`parent: null`) or silently no-op (`body: ""`), while the frontend renders relationship/blocking/action controls that are not persisted.

Cockpit is expected to be a central task endpoint, so visible edit controls must either mutate correctly or be explicitly read-only. This task follows the audit-approved Option A: complete the Cockpit detail edit workflow rather than merely hardening the backend.

## Acceptance Criteria

1. `POST /api/tasks/{id}/edit` defines explicit set/clear semantics for `parent`, `body`, `tags`, `depends_on`, and `block_reason`; invalid values return 422, not uncaught exceptions.
2. `parent: null` clears an existing parent or is rejected with a deliberate 422 contract; it must never raise `TypeError` from `parent > 0`.
3. `body: ""` clears the body or is rejected with a deliberate 422 contract; it must never return success while leaving the body unchanged.
4. `DetailTab` controls for `title`, `priority`, `body`, `tags`, `depends_on`, `parent`, and `block_reason` are controlled inputs where editable, and save sends the intended payload.
5. `DetailTab` unblock, unclaim, and move-backward actions call the appropriate Cockpit mutation endpoints after confirmation, handle 409/422/404 responses, and refresh/update UI state.
6. Successful edits consume the returned task via `onTaskUpdated` or an equivalent selected-task refresh, and refresh the board list when summary fields change.
7. Durable backend tests cover parent clear/reject behavior, empty-body behavior, list replacement for tags/deps, block/unblock semantics, and stale-token behavior.
8. Durable frontend tests prove edited relationship/blocking fields and action confirmations produce the expected API calls and UI refresh callbacks.

## Key Files

- `serve/cockpit/src/owlbear_cockpit/routes/mutation.py`
- `serve/cockpit/src/owlbear_cockpit/view.py`
- `serve/cockpit/web/src/components/DetailTab.tsx`
- `serve/cockpit/web/src/Shell.tsx`
- `tests/test_cockpit_mutation_api.py`
- `serve/cockpit/web/src/__tests__/DetailTab.test.tsx`

## Audit Evidence

- `EditRequest.parent` accepts `None`; `_build_edit_kwargs()` forwards it; `CockpitView.edit_task()` compares `parent > 0`. A direct TestClient repro produced `TypeError: '>' not supported between instances of 'NoneType' and 'int'`.
- `body: ""` reaches `CockpitView.edit_task()` but is skipped by `if body:`, so a clear-body request can look successful without mutating storage.
- `DetailTab` renders `depends_on`, `parent`, and `block_reason` controls, but `handleSave()` only sends `updated`, `title`, `priority`, and `body`.
- `onTaskUpdated` is declared but unused, and confirm dialogs for unblock/unclaim/move-backward only close the dialog.

## Recommendation

Implement the full edit workflow now. Backend-only hardening would remove the crash but leave Cockpit with misleading controls and inert task actions.
