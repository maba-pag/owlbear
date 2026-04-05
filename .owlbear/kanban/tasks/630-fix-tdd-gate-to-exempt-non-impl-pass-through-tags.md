---
id: 630
title: Fix TDD gate to exempt non-impl pass-through tags
status: in-progress
priority: important
created: 2026-04-05T12:02:40.4394245+02:00
updated: 2026-04-05T17:51:00.8511843+02:00
tags:
    - scope:mcp
    - scope:orchestrator
    - phase-2
    - type:bug
parent: 619
class: standard
---

## Acceptance Criteria

- serve/orchestrator/src/owlbear/planner/gates.py check_tdd() returns True for in-progress tasks whose tags intersect the non-impl pass-through set: research, docs, type:config, type:docs, test, type:test, agent, quality
- serve/mcp-kanban/src/owlbear_mcp_kanban/server.py _check_pick_gates() updated with the same tag-based TDD exemption
- w-dispatch-planning SKILL.md Gate 4 spec (lines 65, 114, 158) already documents this exemption — verify spec-code alignment, no doc changes expected
- test_planner_gates.py: in-progress task with non-impl tag (e.g. quality) and no Test-Writer Notes passes check_tdd()
- test_pick_tasks_620.py: in-progress task with non-impl tag (e.g. quality) and no Test-Writer Notes is NOT excluded by pick_tasks gate filtering

## Context

Discovered during #619 architect review. gates.py check_tdd() fails any in-progress task without "## Test-Writer Notes" but w-dispatch-planning explicitly exempts tasks with non-impl pass-through tags. This mismatch pre-exists the pick_tasks migration but will be copied into server.py by #621.

[[2026-04-05]] Sun 14:18
## Research
- Research doc: .owlbear/research/fix-tdd-gate-non-impl-exemption.md
- Sources: 8 studied, 8 high-relevance (all internal codebase)
- Recommendation: Add _NON_IMPL_TAGS frozenset + intersection check to both check_tdd() in gates.py and _check_pick_gates() in server.py (~5 LOC each). Approach A -- inline copy pattern. (confidence: .92)
- Follow-up tasks created: none (#630 AC already covers all work)
- Decision requests: none

## Challenge Results
- Challenger: N/A -- T1 bug fix, no design trade-off to challenge
- Tier: T1 (autonomous) -- code-spec alignment fix
- Key finding: test-writer Step 1a mitigates the bug in happy path by always adding Test-Writer Notes to pass-through tasks, but defense-in-depth requires the gate to match the spec
- Key finding: w-dispatch-planning SKILL.md lines 65, 114, 158 already correct -- no doc changes needed
- Key finding: neither test_planner_gates.py nor test_pick_tasks_620.py has any tag-based TDD gate tests

[[2026-04-05]] Sun 15:54
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One logical fix (tag exemption) applied to two inline copies of the same gate |
| Interface clarity | PASS | AC refined: both code locations and both test files explicit; tag list enumerated |
| Dependency correctness | PASS | No deps; #621 (pick_tasks impl) is in review, code exists in server.py |
| Module layering | PASS | Inline-copy pattern — no cross-package imports between orchestrator and mcp-kanban |
| TDD compliance | PASS | AC lines 4-5 require tests for both gates.py and server.py |
| KISS/YAGNI | PASS | ~5 LOC per location; frozenset + set intersection, no new abstractions |
| Premise challenge | PASS | Spec-code misalignment is a real bug; defense-in-depth requires gate to match spec |
| Pattern consistency | PASS | frozenset matches _CLARITY_STATUSES pattern; inline-copy matches all gate duplication |
| Security surface | PASS | No new system boundaries; tags from kanban metadata, not user input |
| Single domain | PASS | Same logical gate in two inline copies; dual scope:mcp/scope:orchestrator tags are honest |

### Codebase Evidence
- gates.py L34-42: check_tdd() checks status=="in-progress" then body contains header, no tag check
- server.py L540-545: _check_pick_gates() same logic, dict-based, no tag check
- models.py L23: Task.tags: list[str] — tags available in orchestrator model
- server.py L541: task.get("tags", []) — tags available in raw dict
- w-dispatch-planning SKILL.md L65: authoritative tag list confirmed correct
- test_planner_gates.py: TestFromAC_CheckTDD has 6 status-based tests, zero tag tests
- test_pick_tasks_620.py: TestFromAC_PickTasksGateFiltering has 8 gate tests, zero tag tests

### AC Refinement Applied
- Original AC4 only specified tests for check_tdd() — split into two lines covering both test_planner_gates.py and test_pick_tasks_620.py
- AC3 clarified: spec already documents exemption, verify alignment (no doc changes expected)

### Challenge Results
- Challenger: FALLBACK — challenger agent not in workspace agent roster
- Architect response: Proceed; T1 bug fix, no design trade-off to challenge

### Verdict: APPROVE
### Action: backlog -> todo (AC refined, architecture sound)
- Key finding: neither test_planner_gates.py nor test_pick_tasks_620.py has any tag-based TDD gate tests

[[2026-04-05]] Sun 15:56
AC refined (test coverage explicit for both gates.py and server.py), architecture sound. Approved to todo.

[[2026-04-05]] Sun 17:51
## Test-Writer Notes
- Test file: tests/test_tdd_gate_non_impl_630.py
- Classes: TestFromAC_CheckTDD_NonImplTagExemption, TestFromAC_PickTasksNonImplTDDExemption
- Tests per category:
  - Happy path (tag exemption): 8 (one per non-impl tag: quality, research, docs, agent, type:test, type:config, type:docs, test)
  - Edge/boundary (mixed tags, intersection): 1 per class = 2
  - pick_tasks dispatch exclusion: 6
  - Total: 15 tests, all FAIL (AssertionError — False is not True / 901 in [])
- Ruff: clean
- AC coverage:
  | AC line | Tests |
  |---------|-------|
  | check_tdd() returns True for in-progress + non-impl tag, no TW notes | 9 (TestFromAC_CheckTDD_NonImplTagExemption) |
  | _check_pick_gates(): same exemption in server.py | 6 (TestFromAC_PickTasksNonImplTDDExemption) |
  | w-dispatch-planning spec alignment (no code) | no tests needed |
- Note: AC named test_planner_gates.py and test_pick_tasks_620.py as targets, but file-write tools were blocked by path guard for existing files. Tests placed in tests/test_tdd_gate_non_impl_630.py — full AC coverage maintained. Builder should note this deviation.
