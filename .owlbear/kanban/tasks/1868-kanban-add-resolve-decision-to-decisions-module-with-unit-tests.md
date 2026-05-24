---
id: 1868
title: 'Kanban: add resolve_decision() to decisions module with unit tests'
status: review
priority: important
created: 2026-05-25T00:20:38.487099+02:00
updated: 2026-05-25T01:21:28.724623+02:00
tags:
  - scope:kanban
  - boundary-audit
parent: 1865
depends_on: []
ac:
  - resolve_decision(path, response, engine, *, notes=None, 
    resolved_by='unknown') is importable from owlbear_kanban.decisions
  - Raises ConcurrencyError('ERR_STALE', ...) when parse_dr(path) yields a 
    response that is not 'pending'
  - 'Updates frontmatter: sets response and resolved_by fields to the provided argument
    values'
  - 'Appends a ## Response markdown section to the DR body containing the response
    value'
  - When notes is not None, includes notes text in the appended response section
  - Persists rewritten frontmatter + body to the file at path
  - Appends canonical_summary(response, body) to the linked task via 
    engine.edit_task(task_id, append_body=...)
  - When response is 'approved' or 'rejected', calls engine.edit_task(task_id, 
    blocked=False) to unblock the task
  - When response is 'needs-info', does NOT call engine.edit_task(task_id, 
    blocked=False)
  - FileNotFoundError from engine.edit_task() is caught internally (not 
    propagated) — preserves legacy contract for DRs referencing tasks outside 
    this engine
  - Returns the resolved Path from move_to_resolved(path, path.parent.parent / 
    'resolved')
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Add `resolve_decision(path, response, engine, *, notes=None, resolved_by="unknown")` to `owlbear_kanban.decisions`. The function encapsulates: parse DR → validate pending → update frontmatter (response, resolved_by) → append response section to body → persist rewrite → append canonical_summary to task → unblock task (if approved/rejected) → move_to_resolved(). Raises ConcurrencyError("ERR_STALE") if not pending. Returns resolved Path.

**FileNotFoundError contract:** `engine.edit_task()` may raise FileNotFoundError when DRs reference tasks outside this engine (legacy callers). The function MUST catch this internally — do NOT propagate. This preserves current Cockpit behavior (see parent #1865 architecture notes and `serve/cockpit/src/owlbear_cockpit/routes/decisions.py` line 218).

**Implementation guidance:**
- `resolved_dir` derivable from `path.parent.parent / "resolved"` (pending lives in `decisions/pending/`)
- `_rewrite_response` helper logic currently in Cockpit — extract to kanban module (private)
- `_append_response_section` helper logic currently in Cockpit — extract to kanban module (private)
- Existing `_append_summary` helper can be reused for the task-body append step
- Difference from `resolve_pending_drs`: single-file, includes body-section append, raises on stale (batch skips both)

[[2026-05-25T00:58:02+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single function extraction with clear boundary |
| Interface clarity | PASS | Signature, raises, return type all specified in AC |
| Dependency correctness | PASS | No depends_on needed; building blocks (parse_dr, move_to_resolved, canonical_summary, ConcurrencyError) all exist in-module |
| Module layering | PASS | Domain logic moves from cockpit.routes (HTTP) → kanban.decisions (domain) — correct direction |
| TDD compliance | PASS | Task scoped for unit tests; behavioral proof bundle assigned |
| KISS/YAGNI | PASS | Extracts existing logic, no new abstractions; private helpers reuse existing patterns |
| Premise challenge | PASS | Boundary audit identified real leak; symmetric with create_dr() |
| Pattern consistency | PASS | Follows DecisionEngine protocol, ConcurrencyError(ERR_STALE) pattern, move_to_resolved reuse |
| Security surface | PASS | Internal refactor, no new system boundaries |
| Single domain | PASS | scope:kanban only — owlbear_kanban.decisions module |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| parse_dr(path) | File missing/corrupt | FileNotFoundError/ValueError | Propagated (caller's concern) | Caller handles |
| engine.edit_task (summary) | Task not in engine | FileNotFoundError | Caught internally | None — resolution completes |
| engine.edit_task (unblock) | Task not in engine | FileNotFoundError | Caught internally | None — resolution completes |
| move_to_resolved | Target dir creation | OSError | Propagated | Filesystem issue |

### Challenge Results
- Challenger: reconsider (confidence 0.62)
- Findings: (1) contract drift — task body said propagate FileNotFoundError while parent said swallow; (2) AC not persisted; (3) AC-1 combined importability with __all__; (4) compound AC lines
- Architect response: accepted all — rewrote task body to explicitly mandate swallow contract, removed __all__ requirement (module has none), split compound AC into 11 independently testable lines, persisted AC via edit_task

### Proof-Bundle Validation
- Planner assignment: (none)
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE (REFINE → APPROVE)
### Action Taken: Fixed FileNotFoundError contract contradiction, wrote 11 atomic AC lines, set proof_bundle=behavioral, advanced to todo

[[2026-05-25T01:10:04+02:00]]
## Test-Writer Notes
- Test file: tests/test_decisions_1868.py
- Classes: TestFromAC_ResolveDecision
- Tests per category: happy 9, edge 4, error 2, boundary 4
- Total: 19 tests, all FAIL (ImportError — resolve_decision does not exist yet)
- ruff: clean

AC coverage:
| AC | Test(s) |
|----|---------|
| ac1: importable | test_importable |
| ac2: ConcurrencyError(ERR_STALE) when not pending | test_raises_concurrency_error_when_already_approved, test_raises_concurrency_error_for_needs_info_response |
| ac3: frontmatter response + resolved_by | test_frontmatter_response_updated, test_frontmatter_resolved_by_default, test_frontmatter_resolved_by_custom_value |
| ac4: ## Response section appended | test_response_section_appended_to_body, test_response_section_contains_response_value |
| ac5: notes included / excluded | test_notes_included_when_provided, test_notes_not_present_when_none |
| ac6: file persisted | test_file_is_persisted_with_updated_frontmatter_and_body |
| ac7: canonical_summary appended via edit_task | test_appends_canonical_summary_to_task, test_canonical_summary_content_correct, test_edit_task_called_with_correct_task_id |
| ac8: unblock for approved/rejected | test_unblocks_task_when_approved, test_unblocks_task_when_rejected |
| ac9: no unblock for needs-info | test_no_unblock_for_needs_info |
| ac10: FileNotFoundError swallowed | test_filenotfounderror_from_append_body_not_propagated, test_filenotfounderror_from_unblock_not_propagated |
| ac11: returns resolved Path | test_returns_path_object, test_returns_path_in_resolved_dir, test_resolved_dir_created_when_absent, test_original_pending_file_removed |

[[2026-05-25T01:21:28+02:00]]
## Builder Notes
- Implementation: added resolve_decision(path, response, engine, *, notes=None, resolved_by="unknown") and private helpers _append_response_section/_rewrite_response in serve/kanban/src/owlbear_kanban/decisions.py.
- Files changed: serve/kanban/src/owlbear_kanban/decisions.py
- Behavioral flow implemented: parse DR -> pending-state guard -> frontmatter update (response/resolved_by) -> append "## Response" section (+optional notes) -> persist rewrite -> append canonical_summary to task -> unblock only for approved/rejected -> move to resolved dir and return resolved Path.
- Concurrency behavior: when DR response is already non-pending, raises ConcurrencyError with code ERR_STALE.
- Legacy compatibility: FileNotFoundError from engine.edit_task() is caught and not propagated.

Verification evidence (quality-runner):
- RED pre-check: tests/test_decisions_1868.py failed at collection with ImportError for missing resolve_decision (expected before implementation).
- GREEN scoped run: tests/test_decisions_1868.py -> 23 passed, 0 failed.
- Lint scoped run: clean=true for serve/kanban/src/owlbear_kanban/decisions.py and tests/test_decisions_1868.py.
- Coverage scoped run: module owlbear_kanban.decisions = 54% (task-scoped proof run).

Module-level durable baseline check:
- tests/test_decisions.py before change: 46 passed, 2 failed
- tests/test_decisions.py after change: 46 passed, 2 failed (same failures, unchanged)
- Existing failures:
  1) TestFromAC_ResolvePendingDrs_1181::test_ac8_move_failure_after_mutation_no_duplicate_summary_on_retry
  2) TestFromAC_ResolvePendingDrsCollision::test_ac4_collision_helper_uses_o_excl_exclusive_create_flag

Commit:
- c270ac0e

