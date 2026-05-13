---
id: 1530
title: 'P3-01: consolidation test — dep-lookup exception tuple parity (AC5)'
status: archived
priority: needed
created: 2026-05-13T12:18:18.887371+00:00
updated: 2026-05-13T16:53:14.725598+00:00
tags:
  - phase-3
  - scope:kanban
  - consolidation-test
parent: 1525
depends_on:
  - 1527
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Summary

Write a consolidation test asserting that the exception tuple used for dep lookups in `start_work()` matches the one in `show_task()`.

Brief: see parent #1525

## Acceptance Criteria

- AC5: A test asserts that both `start_work()` and `show_task()` catch the same set of exception types `{FileNotFoundError, CorruptionError, ValueError, KeyError}` in their dep iteration loops — verified via AST inspection of ExceptHandler nodes, discriminating dep-iteration handlers from other try/except blocks by requiring CorruptionError presence in the handler tuple

## Scope

- In scope: consolidation test in `serve/kanban/tests/` following the `test_consolidate_helpers.py` AST pattern
- Out of scope: implementation changes, MCP tests, source-regex approaches

## Context

- `show_task()` dep iteration at `agent_view.py` L250 uses `except (FileNotFoundError, CorruptionError, ValueError, KeyError)`
- `start_work()` dep iteration at `agent_view.py` L996 uses the identical handler
- `show_task()` has a separate `FileNotFoundError`-only handler at L238 — CorruptionError presence discriminates the dep-iteration handler
- This test prevents future drift between the two dep-lookup sites

Proof bundle: behavioral
2026-05-13T16:20:31+00:00
## Research
- Research doc: .owlbear/research/dep-lookup-exception-parity.md
- Sources: 4 studied, 2 high-relevance (both agent_view.py sites)
- Recommendation: AST-inspection approach following test_consolidate_helpers.py pattern (confidence: 0.92)
- Follow-up tasks created: none (task #1530 is itself the follow-up)
- Decision requests: none

## Challenge Results
- Challenger: SKIPPED — trivial research, single viable approach
- Key findings: Both show_task() and start_work() dep-iteration handlers use identical 4-exception tuple; CorruptionError serves as discriminator to isolate dep-iteration handlers from other try/except in same methods; ~30 LOC test following established AST pattern
2026-05-13T16:29:21+00:00
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One test asserting exception-tuple parity between two sites |
| Interface clarity | PASS | AC specifies exact types, AST method, and CorruptionError discriminator |
| Dependency correctness | PASS | #1527 archived-completed; implementation satisfies invariant |
| Module layering | PASS | Test reads source via AST — no runtime imports |
| TDD compliance | PASS | Consolidation test is the deliverable; test-writer writes it |
| KISS/YAGNI | PASS | ~30 LOC structural assertion, no abstractions |
| Premise challenge | PASS | Drift guard for two dep-iteration sites — no IDE/stdlib equivalent |
| Pattern consistency | PASS | Follows test_consolidate_helpers.py AST inspection pattern |
| Security surface | PASS | No system boundaries |
| Single domain | PASS | Kanban domain only |

### Challenge Results
- Challenger: reconsider (0.71)
- Key findings: (1) "or source inspection" under-specified — source-regex brittle; (2) "tuple" implies order matters, set equality is correct semantic; (3) handler disambiguation needed (show_task has multiple handlers); (4) process note about research-phase SKIPPED was misread
- Architect response: ACCEPTED (1)(2)(3) — refined AC5 to AST-only, set semantics, CorruptionError discriminator. REBUTTED (4) — "SKIPPED" was research-phase challenger; architecture challenger ran now as required.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE (REFINE path — AC5 tightened per challenger findings)
### Action Taken: Refined AC5 wording (set semantics, AST-only, discriminator clause), updated Context section with line numbers and disambiguation note, advanced to todo
2026-05-13T16:37:18+00:00
## Test-Writer Notes
- Test file: serve/kanban/tests/test_agent_view_dep_exception_parity.py (durable consolidation-test)
- Classes: TestDepLookupExceptionParity
- Tests per category: happy 5, edge 0, error 0, boundary 2 (bare-except guards)
- Total: 7 tests
- ruff: clean

### AC Coverage
| AC | Tests |
|----|-------|
| AC5: both methods catch {FileNotFoundError, CorruptionError, ValueError, KeyError} via AST inspection with CorruptionError discriminator | test_show_task_has_exactly_one_dep_iteration_handler, test_start_work_has_exactly_one_dep_iteration_handler, test_show_task_dep_handler_catches_exact_exception_set, test_start_work_dep_handler_catches_exact_exception_set, test_dep_handlers_are_identical_across_methods, test_show_task_dep_handler_is_not_bare_except, test_start_work_dep_handler_is_not_bare_except |

### Builder Skip: Implementation Already Satisfies Invariant
All 7 tests PASS against current code — task #1527 already aligned both dep-iteration handlers. This drift guard is GREEN on current code. Advancing directly to review; no builder work required.
2026-05-13T16:44:49+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1530 -> docs | AC mapped to code and evidence sufficient.
- Upstream evidence reviewed first: test-writer notes report 7 targeted tests PASS, ruff clean, and no source changes were required because the invariant already holds.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC5 | `serve/kanban/src/owlbear_kanban/agent_view.py:250` and `serve/kanban/src/owlbear_kanban/agent_view.py:996` both catch `(FileNotFoundError, CorruptionError, ValueError, KeyError)` in the dep-iteration loops. | `serve/kanban/tests/test_agent_view_dep_exception_parity.py:48` selects candidate handlers by `CorruptionError` membership; `:83` and `:95` assert exactly one candidate per method; `:109` and `:123` assert the exact 4-type set; `:139` asserts cross-method parity. | PASS |

- Proof sufficiency: The test inspects the named consumer methods directly, uses AST `ExceptHandler` parsing instead of regex, and makes falsifiable exact-set assertions per method plus a parity assertion across methods. That is sufficient for the structural AC as written.
- Safety & security: No new runtime surface, dependency, or input-handling behavior changed; review is limited to structural source inspection and test quality.

## Observations
- The bare-except checks at `serve/kanban/tests/test_agent_view_dep_exception_parity.py:158` and `serve/kanban/tests/test_agent_view_dep_exception_parity.py:168` are slightly broader than AC5 because they fail on any bare `except:` anywhere in each method, not only the dep-iteration handler. This increases future sensitivity but does not create a current false green.
- Challenger cross-check: proceed (confidence 0.84). No blocking issues found in AC-to-code mapping, test-to-AC alignment, or proof sufficiency.
2026-05-13T16:46:06+00:00
## Docs Gate

**Verdict: PASS — no docs impact**

### Convention Mapping
- Changed file: `serve/kanban/tests/test_agent_view_dep_exception_parity.py` (new test only, zero source changes)
- Mapped target: `serve/kanban/README.md`

### Checklist

| Item | Result | Evidence |
|------|--------|----------|
| README Verification | N/A — no update needed | No behavior changed. README already accurately states "Dep-lookup exceptions are swallowed silently; failed lookups are excluded from the active-ID set." Task confirms the invariant already holds; no drift introduced. |
| External Attribution | N/A | Sources cited in research section are internal code files (agent_view.py sites), not external third-party references. |
| Research Doc | VERIFIED | `.owlbear/research/dep-lookup-exception-parity.md` exists; linked in task body at the Research section. |
| Deletion Detection | N/A | No files deleted. No orphaned references possible. |

### Scratch Cleanup
No `1530-*` scratch files found.
2026-05-13T16:53:14+00:00
## Audit
### Regression Detection
- quality-runner mode full: 209 failed (pre-existing), 4599 passed, 14 skipped, 5 errors. Task deliverable (7 tests) all PASS. Baseline before task: 252 failed / 4550 passed (from #1526 run). Failure count decreased — zero source changes in this task make regressions impossible.
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS (single file added: `serve/kanban/tests/test_agent_view_dep_exception_parity.py` — kanban domain, test-only)
- purpose match: PASS (consolidation test asserting dep-lookup exception tuple parity between show_task() and start_work() via AST inspection — matches AC5)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 5/5
AC5 names exact exception types, specifies AST inspection method, and CorruptionError discriminator. Challenger-driven refinements (set semantics, AST-only, discriminator clause) produced a tight, falsifiable AC. Tests are well-structured with 7 assertions covering exact sets, cross-method parity, and bare-except guards.

### Commit Integrity
- upstream commit presence: PASS (`e2abaf16 test: add dep-lookup exception parity drift guard (#1530, test-writer)` — single file changed)
- kanban commit packaging: pending (this archive cycle)

### Deduction Breakdown
No deductions applied.

### Confidence: 1.00
### Action: archive