---
id: 822
title: Implement core __init__.py re-export removal
status: archived
priority: nice-to-have
created: 2026-03-15T09:11:23.430536+01:00
updated: 2026-03-22T19:17:53.4739783+01:00
started: 2026-03-22T19:17:53.4739783+01:00
completed: 2026-03-22T19:17:53.4739783+01:00
tags:
    - refactor
    - scope:core
blocked: true
block_reason: 'Duplicate of archived #812; repository already satisfies this AC. Do not send to builder. Use #866 to archive the stale duplicate.'
class: standard
---

Remove all re-exports and __all__ from src/owlbear/core/__init__.py. Keep docstring + from __future__ import annotations. Delete TestFromAC_CoreReExport class from tests/test_exception_hierarchy.py (3 tests). Verify 0 import breakage in src/ and tests/. See docs/research/core-init-reexport-removal.md.

[[2026-03-20]] Fri 13:52
## Research

Doc: docs/research/core-init-reexport-stale-task.md

Summary: #822 is a stale duplicate. #812 already implemented and audited the exact core/__init__.py cleanup, and the current workspace still matches #822 acceptance criteria: src/owlbear/core/__init__.py contains only the docstring plus from __future__ import annotations, tests/test_core_init_clean.py enforces absence of the old exports, and TestFromAC_CoreReExport is already gone from tests/test_exception_hierarchy.py.

Recommendation (.95): do not send #822 to builder. Archive it as a duplicate of #812 after appending a one-line closure note.

Follow-up: created #866. Attribution updated: docs/sources/overview.md.

[[2026-03-20]] Fri 14:26
## Architecture Review
**Verdict:** BLOCK

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Remove all re-exports and __all__ from src/owlbear/core/__init__.py. | Already satisfied by archived task #812; src/owlbear/core/__init__.py now contains only the module docstring and from __future__ import annotations. | Do not route to builder; treat as duplicate of #812. |
| Keep docstring + from __future__ import annotations. | Already satisfied in the current file state. | No implementation work remains. |
| Delete TestFromAC_CoreReExport class from tests/test_exception_hierarchy.py (3 tests). | Already satisfied; the class is absent from tests/test_exception_hierarchy.py, and #812 audit already recorded its removal. | No implementation work remains. |
| Verify 0 import breakage in src/ and tests/. | Current codebase still uses deep imports, and tests/test_core_init_clean.py already enforces that owlbear.core does not expose the removed symbols. | Preserve current invariant; do not create a second implementation pass. |

### Architecture Notes
Closure note: #812 audit already verified this exact cleanup, so #822 is a stale duplicate and must not proceed to builder.

This task is single-domain (core module surface), but it is no longer an implementation candidate. Existing invariants are already captured by src/owlbear/core/__init__.py and tests/test_core_init_clean.py. The archived task #812 contains the full RED/GREEN/review/audit trail for the requested change, and docs/research/core-init-reexport-stale-task.md confirms the repository still matches those acceptance criteria today.

Routing this task to todo would violate KISS/YAGNI and duplicate already-audited work. The correct follow-up is board cleanup only; #866 already exists for that purpose.

### Changes Made
- Appended Architecture Review section to #822.
- Marked #822 blocked and moved it back to ideation because the implementation is already complete under #812.

### Dependencies
- Verified: #812 archived implementation and audit evidence cover the exact requested cleanup.
- Verified: #866 exists as the board-cleanup follow-up for archiving this stale duplicate.
