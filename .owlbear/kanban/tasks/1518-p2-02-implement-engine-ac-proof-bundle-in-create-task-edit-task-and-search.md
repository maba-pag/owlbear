---
id: 1518
title: 'P2-02: Implement engine ac/proof_bundle in create_task, edit_task, and search'
status: review
priority: critical
created: 2026-05-13T02:29:31.968335+00:00
updated: 2026-05-13T06:09:54.229366+00:00
tags:
  - phase-2
  - scope:kanban
  - tdd
  - feature
parent: 1514
depends_on:
  - 1517
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1514

## Scope
In scope: Add ac/proof_bundle params to create_task and edit_task; implement proof_bundle frozenset validation, dual AC mutation (full replacement OR atomic add/remove with mutual exclusion), AC guardrails, search extension
Out of scope: MCP tools, migration, skill files

## Acceptance Criteria
- AC1: `KanbanEngine.create_task()` and `edit_task()` accept `proof_bundle` param; reject values not in `VALID_PROOF_BUNDLES` with `ValidationError(code="ERR_PROOF_BUNDLE_INVALID")` whose `user_message` contains every member of `VALID_PROOF_BUNDLES`
- AC2: `KanbanEngine.edit_task()` supports `ac` (full replacement), `add_ac` (append), and `remove_ac` (exact-match removal); raises `ValidationError` when `ac` and `add_ac`/`remove_ac` are both provided
- AC3: `KanbanEngine.edit_task()` rejects duplicate `add_ac` items with `ValidationError` listing existing duplicates
- AC4: `KanbanEngine.create_task()` and `edit_task()` enforce AC guardrails: max 20 items raises `ValidationError`; item exceeding 500 chars raises `ValidationError`
- AC5: `KanbanEngine.list_tasks(search="keyword")` returns tasks where `keyword` is a case-insensitive substring match in any frontmatter `ac` item

Proof bundle: smoke
Existing proof scope: tests/test_engine_ac_1517.py
Smoke scope: Add `user_message` assertions to `test_create_task_invalid_proof_bundle_raises_validation_error` and `test_edit_task_invalid_proof_bundle_raises_validation_error` verifying the message contains all VALID_PROOF_BUNDLES members.
2026-05-13T06:07:14+00:00
## Architecture Review (Re-scope)

### Context
Reviewer rejected previous cycle: AC1 proof gap — existing tests assert only error code, not the `user_message` listing valid options. AC2–AC5 confirmed fully covered.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Engine-level ac/proof_bundle CRUD |
| Interface clarity | PASS | AC1 refined: explicit edit_task coverage + oracle removed |
| Dependency correctness | PASS | #1517 archived (confidence 1.00) |
| Module layering | PASS | Engine validates → model normalizes |
| TDD compliance | PASS | Smoke escalation covers the gap |
| KISS/YAGNI | PASS | Minimal change: 2 assertions added |
| Premise challenge | PASS | Implementation verified in engine.py:198-207 |
| Pattern consistency | PASS | Follows existing ValidationError patterns |
| Security surface | PASS | No new external boundaries |
| Single domain | PASS | scope:kanban only |

### AC Refinement
- AC1: Expanded to explicitly name both `create_task()` and `edit_task()` (was create_task only). Replaced vague "listing valid options" with precise "`user_message` contains every member of `VALID_PROOF_BUNDLES`".

### Proof-Bundle Validation
- Planner assignment: behavioral (original); existing (first arch-review de-escalation)
- Final bundle: smoke
- Existing proof scope: tests/test_engine_ac_1517.py (42 tests, AC2-AC5 fully proven)
- Smoke scope: 2 `user_message` assertions in existing test methods
- Escalation rationale: Reviewer proved `existing` bundle was insufficient for AC1's "listing valid options" contract. Escalating to `smoke` requires the test-writer to add targeted assertions without full TDD overhead.

### Design Diverge
- Trigger: skipped — single clear approach

### Challenge Results
- Challenger: reconsider (0.64)
- Findings accepted: (1) AC1 scope gap — edit_task not named; (2) "valid options" oracle undefined
- Findings rejected: AC5 ambiguity — challenger misread test_list_tasks_search_ac_does_not_match_title_or_body; test correctly verifies both ac-based and title-based search coexist
- Architect response: Refined AC1 to address both accepted findings; escalated proof bundle

### Verdict: APPROVE
### Action Taken: Refined AC1 (scope + oracle), escalated proof bundle existing→smoke with explicit smoke scope, advanced to todo.
2026-05-13T06:09:54+00:00
## Test-Writer Notes
- Proof bundle: smoke — 2 targeted smoke tests for AC1 `user_message` coverage gap
- Test file: `tests/test_engine_ac_1518.py`
- Class: `TestFromAC_ProofBundleUserMessage`
- Tests written: 2 (smoke category)

| Test | AC | Category |
|---|---|---|
| `test_create_task_invalid_proof_bundle_user_message_contains_all_valid_bundles` | AC1 | smoke |
| `test_edit_task_invalid_proof_bundle_user_message_contains_all_valid_bundles` | AC1 | smoke |

- AC coverage: AC1 fully covered (both `create_task` and `edit_task` `user_message` assertions)
- Quality-runner result: 2 passed, 0 failed, lint clean
- Builder skip: all smoke tests GREEN — implementation already satisfies the `user_message` contract (engine.py:207). Advancing directly to review.