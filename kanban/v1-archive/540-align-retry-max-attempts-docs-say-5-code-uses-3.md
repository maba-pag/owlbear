---
id: 540
title: 'Align retry max attempts: docs say 5, code uses 3'
status: archived
priority: nice-to-have
created: 2026-03-04T07:38:44.9656782+01:00
updated: 2026-03-22T19:21:19.4525061+01:00
started: 2026-03-07T00:36:40.0707744+01:00
completed: 2026-03-22T19:21:19.4525061+01:00
tags:
    - audit
    - resilience
    - docs
blocked: true
block_reason: 'Research stale: cited .github docs no longer say 5, and the task conflates 3-attempt message/tool retries with 5-attempt task retries. Re-scope before implementation.'
class: standard
---

R-5: python.instructions.md says max 5 attempts but all retry code uses stop_after_attempt(3). Either update docs to 3 or code to 5. AC: docs and code agree. See docs/resilience-audit.md.

## Research (trivial alignment)

N/A - trivial alignment. Rationale: every retry site in the codebase uses 3 attempts.

**Evidence (code uses 3 unanimously):**
- providers/copilot.py L62: stop_after_attempt(3)
- core/retry.py L45: stop_after_attempt(3)
- tools/hooked.py L59: _MAX_ATTEMPTS = 3
- daemon.py L45: _TRANSIENT_MAX_RETRIES = 3

**Docs that say 5:**
- .github/instructions/python.instructions.md L34
- .github/copilot-instructions.md L46 (tech stack table)

**Recommendation (.95):** Update both doc files to say 'max 3 attempts'. Code is correct  3 was deliberately chosen (daemon-retry-reconciliation.md notes 3x3=9 multiplicative attempts already excessive).

**Implementation:** Change 'max 5 attempts' to 'max 3 attempts' in python.instructions.md L34 and copilot-instructions.md L46.

[[2026-03-21]] Sat 04:36
## Architecture Review
**Verdict:** Block

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| `python.instructions.md says max 5 attempts but all retry code uses stop_after_attempt(3)` | Stale/inaccurate. `.github/instructions/python.instructions.md` already documents `max 3 attempts`, while `src/owlbear/config.py` intentionally keeps `task_retry_max_attempts = 5` for autonomous task retries. | Re-scope around the current retry-layer documentation instead of a nonexistent docs/code mismatch. |
| `Either update docs to 3 or code to 5` | Conflates distinct retry layers. `src/owlbear/providers/copilot.py`, `src/owlbear/core/retry.py`, `src/owlbear/tools/hooked.py`, and `src/owlbear/daemon.py` use fixed 3-attempt transport/tool/message retries, while task-level orchestration retries are configured separately. | Return to ideation and define exactly which retry layer the task owns. |
| `AC: docs and code agree` | Not mechanically verifiable. It names no files, no retry scope, and no non-goals. | Replace with file-specific AC if the task is revived. |

### Architecture Notes
- Current codebase has multiple retry scopes: transport retry in `src/owlbear/providers/copilot.py`, shared/tool retry in `src/owlbear/core/retry.py` and `src/owlbear/tools/hooked.py`, daemon message-level retry in `src/owlbear/daemon.py`, and task-level retry budget in `src/owlbear/config.py` consumed by `src/owlbear/daemon.py`.
- Current user guidance already matches the 3-attempt convention for tenacity-backed retries: `.github/instructions/python.instructions.md` says `max 3 attempts`, and `.github/copilot-instructions.md` does not state a 5-attempt rule.
- The remaining `docs say 5` references are stale audit artifacts in `docs/resilience-audit.md` and `docs/executive-audit-report.md`. That is a docs-scoping question, not evidence that runtime code is wrong.
- If revived, keep the task docs-only and choose one scope: annotate stale historical audit findings, or add a current-layer clarification doc that explicitly distinguishes 3-attempt transport/tool/message retries from 5-attempt task retries. Do not mix docs cleanup with runtime retry-policy changes.
- TDD note: no preceding test task is needed only if the task is rewritten as docs-only. Any runtime retry-policy change would require a paired test task first.

### Changes Made
- Claimed #540 for architect review.
- Verified live instruction files, runtime retry implementations, and audit references.
- Appended this review and prepared the task for return to ideation.

### Dependencies
- Verified: no explicit `depends_on` entries.
- Related context only: `docs/research/daemon-retry-reconciliation.md`, `docs/research/task-level-retry.md`.
