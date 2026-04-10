---
id: 550
title: Trim knowledge __init__.py to 15 or fewer exports
status: archived
priority: nice-to-have
created: 2026-03-04T07:38:53.2483718+01:00
updated: 2026-03-22T19:21:20.0902852+01:00
started: 2026-03-07T00:55:27.3565874+01:00
completed: 2026-03-22T19:21:20.0902852+01:00
tags:
    - audit
    - architecture
    - knowledge
blocked: true
block_reason: Original trim scope already landed; define a new unresolved knowledge-package concern and a linked preceding test task before returning this item to backlog.
class: standard
---

The original implementation described by this task already appears to be present in the repository. This backlog item must be re-scoped before anyone does further code work.

Historical context: docs/research/knowledge-init-trim.md (stale against current tree)

## Verified Current State
- src/owlbear/memory/knowledge/__init__.py already exposes 14 public exports and resolves them lazily via `_LAZY_IMPORTS` / `__getattr__`.
- src/owlbear/bootstrap/knowledge.py already imports `TextChunker` from `owlbear.memory.knowledge.chunker`.
- tests/test_knowledge_public_api.py asserts the exact 14-symbol public API.
- tests/test_knowledge_init_trim.py asserts removed symbols are no longer accessible from `owlbear.memory.knowledge`.

## Acceptance Criteria
1. Do not send this task to implementation in its current form. The original trim work must not be re-implemented.
2. Before this task can advance, rewrite it to a single unresolved concern with exact file targets, exact symbols or behavior to change, and exact proving tests.
3. If the intended work was only the 14-symbol public-API trim, treat this task as duplicate or delivered work linked to commits `f4afea6`, `9fed9e2`, and `77860d8` plus archived test task #839.
4. Any new implementation scope created from this task must have an explicit preceding test task linked as a dependency.

[[2026-03-21]] Sat 02:46
## Architecture Review
**Verdict:** REFINE

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| INT-11: knowledge/__init__.py exports 35 symbols | Outdated. Live `src/owlbear/memory/knowledge/__init__.py` already exposes 14 public names in `__all__`. | Rewrite |
| Research complete: see `docs/research/knowledge-init-trim.md` | Useful as history, but stale against the live tree and follow-up workflow. | Keep as context only |
| Recommended 14 exports | Matches the live package API and existing tests. | Keep as historical evidence |
| Remove 21 symbols | Outdated. Live trim tests enforce a larger removed-symbol set than this body lists. | Rewrite |
| Only 1 production import change: bootstrap `TextChunker` import | Already satisfied. `src/owlbear/bootstrap/knowledge.py` imports `TextChunker` from the chunker submodule at line 22. | Rewrite |
| AC: clean public API surface, <=15 re-exports in `__all__` | Vague and already satisfied. Not a builder-ready contract. | Rewrite |

### Architecture Notes
- Live package surface: `src/owlbear/memory/knowledge/__init__.py` defines a 14-name `__all__` at line 11, a lazy import map at line 30, and lazy resolution via `__getattr__` at line 49. Approving #550 as implementation work would risk duplicate code changes.
- Import-site evidence: `src/owlbear/bootstrap/knowledge.py` already imports `TextChunker` from `owlbear.memory.knowledge.chunker` at line 22. The specific production fix named in the task is no longer pending.
- Test evidence already exists for the intended scope:
  - `tests/test_knowledge_public_api.py` line 6 defines `TestFromAC_KnowledgePublicAPI`; line 58 asserts exact set equality for the 14 retained exports; line 64 asserts the export count.
  - `tests/test_knowledge_init_trim.py` defines `TestFromAC_RemovedSymbols`, `TestFromAC_TextChunkerImportFix`, and `TestFromAC_ConsolidationImportFix`, which enforce that removed symbols are no longer accessible from `owlbear.memory.knowledge`.
  - `tests/test_knowledge_exports.py` already documents the post-trim expectations and qdrant lazy-load behavior.
- TDD compliance for the original scope exists historically through archived task #839 plus #550-linked commits, but there is no remaining unresolved GREEN work to send to a builder.
- Git evidence that the original scope already landed: `f4afea6` (`test: add failing tests for knowledge __init__.py trim (#550, test-writer)`), `9fed9e2` (`refactor: trim knowledge __init__.py to 14 public exports (#550, builder)`), and `77860d8` (`refactor: ruff-format test_knowledge_public_api.py (#550, builder)`).
- Failure Mode Map: N/A. This review is rejecting the current contract, not proposing a new codepath.

### Changes Made
- Rewrote the task body so it no longer asks for duplicate implementation.
- Left the task in `backlog` pending re-scoping or board cleanup.
- Verified related archived test task #839 and current file/test state before rejecting approval.

### Dependencies
- Verified: archived task #839 provides the explicit 14-export RED contract.
- Verified: no unresolved production dependency blocks the original trim because the code is already present.
- Required for any future rewrite: create an explicit preceding test task and link it as a dependency.

[[2026-03-21]] Sat 03:16
## Architecture Review
**Verdict:** BLOCK

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. Do not send this task to implementation in its current form. The original trim work must not be re-implemented. | Correct. This confirms the task is not builder-ready and does not belong in backlog. | Keep; return task to ideation |
| 2. Before this task can advance, rewrite it to a single unresolved concern with exact file targets, exact symbols or behavior to change, and exact proving tests. | Correct and verifiable. This is ideation or research work, not backlog-ready implementation scope. | Keep; move to ideation until rewritten |
| 3. If the intended work was only the 14-symbol public-API trim, treat this task as duplicate or delivered work linked to commits 4afea6, 9fed9e2, and 77860d8 plus archived test task #839. | Verified against git history and archived task #839. The original scope is already delivered. | Keep |
| 4. Any new implementation scope created from this task must have an explicit preceding test task linked as a dependency. | Correct TDD guard for any future rewrite. | Keep |

### Architecture Notes
- Backlog tasks must be builder-actionable. #550 is now a board triage item, not an implementation contract.
- Live code evidence: src/owlbear/memory/knowledge/__init__.py already defines a 14-name __all__ and lazy import map; src/owlbear/bootstrap/knowledge.py already imports TextChunker from the chunker submodule.
- Test evidence: 	ests/test_knowledge_public_api.py locks the retained 14-symbol API, 	ests/test_knowledge_init_trim.py locks removal of trimmed symbols, and 	ests/test_knowledge_exports.py reflects the post-trim lazy-import surface.
- TDD evidence: archived task #839 provided the RED contract before the GREEN commits for #550.
- Research evidence: docs/research/knowledge-init-trim.md is useful historical context but stale as a source of unresolved work, because its recommended implementation has already landed.
- Failure Mode Map: N/A. This decision rejects stale backlog placement rather than approving a new codepath.

### Changes Made
- Rejected backlog placement and returned the task to ideation.
- Preserved the current AC as re-scoping guidance instead of forcing a pseudo-implementation contract.
- Verified the delivered scope against source files, tests, archived task #839, and git history for #550.

### Dependencies
- Verified: archived task #839 already satisfied the explicit RED dependency for the original scope.
- Verified: no unresolved production dependency remains for the original trim.
- Required before any future backlog return: a fresh unresolved concern plus a linked preceding test task.
