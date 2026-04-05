---
id: 530
title: Parameterize observability metadata dict type
status: archived
priority: nice-to-have
created: 2026-03-04T07:38:36.1891917+01:00
updated: 2026-03-22T19:20:05.9212141+01:00
started: 2026-03-07T00:26:11.1497454+01:00
completed: 2026-03-22T19:20:05.9212141+01:00
tags:
    - audit
    - code-quality
    - scope:core
blocked: true
block_reason: Current source already satisfies the AC; src/owlbear/core/observability.py already uses dict[str, Any]. Refresh or archive this stale audit task before reopening.
class: standard
---

F-13: observability.py metadata: dict = {} uses bare dict instead of dict[str, Any]. Prevents Pylance from catching type misuse. AC: metadata typed as dict[str, Any]. See docs/code-quality-audit.md.

Research: N/A - trivial type annotation, one-line change.
- L55 in src/owlbear/core/observability.py: change `metadata: dict = {}` to `metadata: dict[str, Any] = {}`
- Add `Any` to the `from typing import TYPE_CHECKING` import (becomes `from typing import Any, TYPE_CHECKING`)

[[2026-03-21]] Sat 04:59
## Architecture Review
**Verdict:** BLOCK

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| `metadata` typed as `dict[str, Any]` | Already satisfied in current source: `src/owlbear/core/observability.py` imports `Any` and declares `metadata: dict[str, Any] = {}`. | Do not dispatch implementation from #530; stale audit task. |
| Add `Any` to the typing import | Already satisfied in current source. | Covered by the current file state. |
| Implied one-line implementation handoff | Not a live backlog item anymore. Moving this to `todo` would duplicate already-landed work, and there is no remaining implementation delta to hand off to a builder. | Return to `ideation` and block until the audit/board state is refreshed. |

### Architecture Notes
- Verified current source in `src/owlbear/core/observability.py`: line 18 imports `Any`, line 54 already declares `metadata: dict[str, Any] = {}`.
- Verified the same file already includes `class ToolStats(TypedDict)` at line 57, which shows this observability audit slice has already moved past the original March 3 findings.
- Verified archived sibling task `#531` completed the adjacent `ToolStats` audit fix, and the live workspace now reflects both the `ToolStats` improvement and the `metadata` type annotation.
- Verified existing observability coverage exists in `tests/test_observability_hook.py`; there is no remaining implementation delta to justify a new builder handoff.
- Because the AC are already satisfied in the workspace, approving `#530` to `todo` would create a duplicate implementation task and ambiguous ownership. This task should leave the active backlog until someone refreshes the audit finding or converts it into explicit board-cleanup work.
- Failure mode map: not applicable. This is a stale backlog item with no new runtime codepath to review.

### Changes Made
- Claimed `#530` as `architect-gpt54-530`.
- Appended this architecture review after verifying the live source and related observability task history.
- Preparing to move `#530` out of the active backlog with a stale-task block.

### Dependencies
- Added/Removed/Verified: verified `src/owlbear/core/observability.py`, `tests/test_observability_hook.py`, and archived sibling task `#531`; no RED predecessor is applicable because no implementation work remains.
