---
id: 549
title: Add re-exports to empty __init__.py files
status: archived
priority: nice-to-have
created: 2026-03-04T07:38:52.389879+01:00
updated: 2026-03-22T19:17:42.1013288+01:00
started: 2026-03-07T00:49:54.9360728+01:00
completed: 2026-03-22T19:17:42.1013288+01:00
tags:
    - audit
    - architecture
    - scope:core
blocked: true
block_reason: 'Stale umbrella: #814 implemented tools; #813/#815 resolved won''t-do by decision A; #572 covers planning follow-up. Do not dispatch.'
class: standard
---

INT-10: auth, planning, projects, providers, safety, tools, tools/browser have empty __init__.py. No public API surface defined. Add re-exports for key public types. See docs/integration-audit.md.

## AC

- [ ] Each listed __init__.py re-exports key public types
- [ ] Public API discoverable via package imports
- [ ] Ruff clean, all tests pass

[[2026-03-21]] Sat 03:18
## Architecture Review
**Verdict:** BLOCK

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Each listed __init__.py re-exports key public types | Vague, stale, and already split across #813, #814, #815, and #572. | Reject current AC |
| Public API discoverable via package imports | Non-verifiable and contradicted by `docs/decisions/resolved/813-re-export-feature-gate.md` (Option A: do not add re-exports). | Reject current AC |
| Ruff clean, all tests pass | Standard gate only; no TDD predecessor and no single coherent implementation remains. | Not sufficient |

### Architecture Notes
- Current state no longer matches INT-10: `src/owlbear/tools/__init__.py` already exports 10 symbols; `src/owlbear/tools/browser/__init__.py` is docstring-only; `src/owlbear/planning/__init__.py` is the only empty `__init__.py`.
- Board state is already resolved: #814 archived implemented, #813 archived won't-do, #815 archived won't-do, and #572 exists for the planning-only follow-up.
- This umbrella task is multi-domain and stale. Do not dispatch it to a builder.

### Changes Made
- Reviewed current codebase, related tasks, and the resolved decision record
- Blocked the task in ideation to prevent stale implementation dispatch

### Dependencies
- Verified: #814 archived
- Verified: #813 archived
- Verified: #815 archived
- Verified: #572 backlog
- Verified: `docs/decisions/resolved/813-re-export-feature-gate.md`
