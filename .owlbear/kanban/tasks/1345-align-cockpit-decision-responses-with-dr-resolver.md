---
id: 1345
title: Align Cockpit decision responses with DR resolver
status: backlog
priority: critical
created: 2026-05-04T17:27:34.911141+00:00
updated: 2026-05-04T17:28:16+00:00
tags:
- sync-blocker
- cockpit
- decisions
- kanban
parent:
depends_on:
- 1339
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

Cockpit's decision-resolution API accepts `response="completed"`, but the kanban DR resolver only processes `approved`, `rejected`, and `needs-info`. A `completed` response can therefore make a pending DR disappear from Cockpit's pending list while never being moved to `resolved/` or summarized back onto the task.

Audit decision: remove `completed` from Cockpit DR resolution for now. If action requests need `completed`, model them separately instead of overloading decision requests.

## Acceptance Criteria

1. `POST /api/decisions/{id}/resolve` accepts only `approved`, `rejected`, and `needs-info` for decision requests.
2. Requests with `response="completed"` return 422 and do not mutate the decision file.
3. Cockpit frontend `ResolveModal` and tests remain aligned with the three-response DR contract.
4. Existing tests that expected `completed` for DRs are rewritten or removed as stale contract tests.
5. Resolver integration tests prove each accepted response is later processed by `resolve_pending_drs()`:
	- `approved` and `rejected` append a summary, unblock the task, and move the DR to `resolved/`.
	- `needs-info` appends a summary and moves the DR to `resolved/` without unblocking the task unless current intended behavior says otherwise.
6. No pending DR with a non-pending response can remain invisible in `pending/` after resolver processing.

## Key Files

- `serve/cockpit/src/owlbear_cockpit/routes/decisions.py`
- `serve/kanban/src/owlbear_kanban/decisions.py`
- `serve/cockpit/web/src/components/ResolveModal.tsx`
- `tests/test_cockpit_decisions_api.py`
- `tests/test_cockpit_decisions_api_1189.py`
- `tests/test_cockpit_decisions_api_1190.py`

## Audit Evidence

- Cockpit route schema currently includes `completed`.
- Engine resolver logs unknown responses and skips them.
- Cockpit pending-list endpoint hides any file whose frontmatter response is no longer `pending`, so `completed` can create an invisible unresolved file.

## Recommendation

Keep decision requests strict: `approved`, `rejected`, `needs-info`. Split action-request lifecycle later only if a real consumer requires `completed`.
