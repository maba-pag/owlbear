# Stale Core Re-export Implementation Task

> **Owning tasks:** #822 - Implement core `__init__.py` re-export removal; #866 - Archive stale duplicate core re-export implementation task (#822)
> **Date:** 2026-03-20  **Status:** Complete

## 1. Context and Question

Task #822 asks for code changes that remove all re-exports and `__all__` from
`src/owlbear/core/__init__.py`, delete `TestFromAC_CoreReExport`, and verify that
no imports break.

This research checks whether that implementation work is still needed, or whether
the task is stale because the exact change already landed under an earlier task.
Follow-up task #866 exists to perform the board cleanup once that conclusion is
verified.

## 2. Sources Studied

| Source | URL | Relevance | What we used |
|--------|-----|-----------|--------------|
| `kanban/tasks/812-remove-unused-re-exports-from-core-init-py.md` | Local task file | 1.0 | Builder, review, and audit evidence that the requested change already shipped under #812 |
| `src/owlbear/core/__init__.py` | Local source file | 1.0 | Confirms the file already contains only the docstring and `from __future__ import annotations` |
| `tests/test_core_init_clean.py` | Local test file | 1.0 | Confirms dedicated tests already enforce absence of re-exports and `__all__` |
| `tests/test_exception_hierarchy.py` | Local test file | 1.0 | Confirms `TestFromAC_CoreReExport` is already absent |
| GitHub Docs - Closing an issue | <https://docs.github.com/en/issues/tracking-your-work-with-issues/administering-issues/closing-an-issue> | .75 | Supports closing work when bugs are fixed or the work is not planned |
| GitLab Docs - Manage issues | <https://docs.gitlab.com/user/project/issues/managing_issues/#close-an-issue> | .80 | Supports closing issues when work is resolved or no longer needed instead of leaving duplicate action items open |

## 3. Analysis

### 3.1 Current repository state vs. #822 acceptance criteria

| #822 requirement | Current evidence | Status |
|------------------|------------------|--------|
| Remove re-exports and `__all__` from `core/__init__.py` | `src/owlbear/core/__init__.py` already contains only the docstring and `from __future__ import annotations` | Already satisfied |
| Delete `TestFromAC_CoreReExport` | `tests/test_exception_hierarchy.py` no longer contains that class | Already satisfied |
| Verify no import breakage | `tests/test_core_init_clean.py` already asserts the old exports are absent; a fresh targeted pytest run on 2026-03-20 passed 34 tests across `test_core_init_clean.py` and `test_exception_hierarchy.py` | Already satisfied |

### 3.2 Provenance on the board

| Item | Evidence | Implication |
|------|----------|-------------|
| #812 | Archived task body shows the builder implemented the exact removal | The code work already happened |
| #812 audit | Explicit note: "#822 is redundant since #812 already implemented the removal" | The board already contains duplicate-task evidence |
| #822 | Still sits at `ideation` with implementation-oriented AC | Current status no longer matches repo reality |
| #866 | Created as the board-cleanup follow-up for this research conclusion | No new implementation task is needed |

### 3.3 Options

| Option | Outcome | Trade-off | Confidence |
|--------|---------|-----------|------------|
| Send #822 through implementation pipeline | Re-does already completed work | Wastes board capacity and invites redundant churn | .05 |
| Archive #822 as a stale duplicate of #812 | Aligns the board with the shipped code and existing audit trail | Needs a short closure note only | .95 |
| Re-open code changes for re-validation | Produces no new information | Adds noise; tests and audit evidence already exist | .00 |

## 4. Recommendation (.95 confidence)

Do not send #822 to builder.

Treat it as a stale duplicate of #812, append a one-line closure note that cites
the #812 audit evidence, and archive it instead of moving it deeper into the
implementation pipeline.

This is the simplest action that matches the current repository state, preserves
the existing source of truth, and avoids re-executing already completed work.

## 5. Follow-up Tasks

1. #866 — Archive stale duplicate core re-export implementation task (#822).
   Board cleanup only: append the closure note to #822 citing #812 audit
   evidence, then archive #822 instead of sending it through implementation.
2. No additional follow-up tasks are required.
