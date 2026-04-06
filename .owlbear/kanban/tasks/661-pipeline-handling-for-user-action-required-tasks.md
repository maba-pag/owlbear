---
id: 661
title: Pipeline handling for user-action-required tasks
status: in-progress
priority: nice-to-have
created: 2026-04-06T08:25:07.1782653+02:00
updated: 2026-04-06T18:01:27.9882351+02:00
tags:
    - phase-3
    - scope:orchestrator
    - type:feature
class: standard
---

## Objective
Design a mechanism for tasks that require manual user action (GUI verification, external approvals, etc.) to avoid futile pipeline pass-through cycles.

## Context
Task #597 proved the gap empirically: 6 pipeline agents correctly processed it as a type:test pass-through, but the objective (manual Teams GUI verification) was never fulfilled. The auditor rejected at .88 confidence, and the architect confirmed re-entering the pipeline would repeat the cycle verbatim.

Current workaround: architect rejects to ideation with a note recommending direct user execution. This works but is wasteful (full pipeline cycle before detection).

## Acceptance Criteria
- [ ] Define a convention for user-action-required tasks (tag, status, or dedicated handoff mechanism)
- [ ] Architect can identify and route these tasks early (skip test-writer/builder/reviewer)
- [ ] Orchestrator recognizes the convention and does not dispatch to automated agents
- [ ] Document the convention in agent-common.instructions.md or r-pipeline-protocol
- [ ] Verify with a dry-run scenario that the convention prevents the #597-style loop

## Evidence
- #597 pipeline cycle: all 6 agents passed through, auditor rejected, architect confirmed structural gap
- Auditor note: "The pipeline lacks a mechanism for user-action-required tasks"
- Architect (cycle 2): "No pipeline pattern exists for user-action-required tasks"

## Needs decomposition: multiple pipeline components affected (orchestrator, architect, agents-common, kanban-md config)

[[2026-04-06]] Mon 16:39
## Research
- Research doc: .owlbear/research/user-action-required-pipeline-handling.md
- Sources: 8 studied, 6 high-relevance (internal codebase + 2 external already logged)
- Recommendation: `type:user-action` tag + AR blocking + architect post-completion fast-path (confidence: .78)
- Follow-up tasks created: #662 (NON_IMPL_TAGS update), #663 (convention documentation), #664 (architect gate rules) — all at research
- Decision requests: none (T2 — uses existing infrastructure, convention changes only)

## Challenge Results
- Challenger: block (confidence in original: .35)
- Key challenges: (1) NON_IMPL_TAGS only exempts TDD gate, not dispatch — ACCEPTED, corrected in revised rec; (2) architect gate is instructional, identical to Option C — REBUTTED: tag is checkable data, blocking is mechanical; (3) post-unblock re-entry path undefined — ACCEPTED, added architect fast-path; (4) dual-nature tasks — ACCEPTED, added split-task guidance
- Researcher response: revised — lowered confidence from .85 to .78, incorporated all valid challenges, added Part 3 (post-AR fast-path) and dual-nature task handling

## Key Insight
The #597 loop happened because no user action was inserted into the cycle. The fix is ensuring user action happens BEFORE pipeline processing (via AR blocking), not eliminating pipeline stages. Blocking IS the mechanical enforcement — pick_tasks already excludes blocked tasks.

[[2026-04-06]] Mon 16:48
## Planning\n\n### Decomposition: User-Action Pipeline Handling (#661)\n- Tasks: 5 total (2 new + 3 existing refined)\n- Dependency layers: 3\n- Phase: 3\n\n### Task Graph\n\n| Seq | ID | Title | Depends | Tags |\n|-----|----|-------|---------|------|\n| 01 | #665 (new) | Test: type:user-action in NON_IMPL_TAGS gate sets | -- | scope:orchestrator, type:test |\n| 02 | #662 (refined) | Add type:user-action to NON_IMPL_TAGS (gates.py + server.py) | #665 | scope:orchestrator, type:config |\n| 03 | #666 (new) | Update NON_IMPL_TAGS skill doc references for type:user-action | #662 | scope:agent-config, type:docs |\n| 04 | #663 (as-is) | Document type:user-action convention in r-pipeline-protocol and agent-common | -- | scope:agent-config, type:docs |\n| 05 | #664 (deps fixed) | Add architect user-action gate rule and post-AR fast-path to w-arch-review | #663 | scope:agent-config, type:docs |\n\n### Dependency Chains\nChain A: #665 (test) -> #662 (impl gates.py + server.py) -> #666 (skill docs)\nChain B: #663 (convention docs) -> #664 (architect gate rules)\nFull parallelism between chains.\n\n### Edits Applied to Existing Tasks\n- #662: Narrowed to 2 Python files only (skill doc AC moved to #666). Depends_on changed from [661] to [665]. Parent set to 661.\n- #663: Tag scope:orchestrator changed to scope:agent-config. Depends_on cleared (independent chain). Parent set to 661.\n- #664: Depends_on changed from [661] to [663] (rules reference convention). Tag scope:orchestrator changed to scope:agent-config. Parent set to 661.\n\n### Verification\n- [x] Every impl task (#662) has a preceding test task (#665)\n- [x] No task has multiple responsibilities (4-location task split into code + docs)\n- [x] No multi-domain tasks (Python and skill docs separated)\n- [x] No cycles in dependency graph\n- [x] All subtasks at research status for architect to process individually

[[2026-04-06]] Mon 18:01
## Test-Writer Notes

**Test file:** `tests/test_user_action_non_impl_661.py`

**Classes:**
- `TestFromAC_UserActionNonImplFrozensets` — direct frozenset membership
- `TestFromAC_CheckTDD_UserActionExemption` — check_tdd() gate exemption
- `TestFromAC_PickTasksUserActionExemption` — pick_tasks dispatch inclusion

**Tests per category:**
| Category | Count |
|----------|-------|
| Happy path (`check_tdd` + `pick_tasks` inclusion) | 4 |
| Edge (mixed tags, minimal body) | 2 |
| Direct membership assertion | 2 |
| **Total** | **7** |

**RED phase confirmed:** 7 failed, 0 passed. Ruff: clean.

**AC coverage:**
| AC line | Tests |
|---------|-------|
| Define convention (type:user-action tag) | frozenset membership tests (#1, #2) |
| Orchestrator recognises convention / does not block dispatch | check_tdd tests (#3–#5), pick_tasks tests (#6–#7) |
| Exempted from TDD gate (in-progress, no TW notes) | all 5 behavioural tests |

**3 candidate tests removed** (tested existing behaviour — todo status pass-through, with-TDD-notes pass-through, no-tag exclusion boundary — all passed before implementation).
