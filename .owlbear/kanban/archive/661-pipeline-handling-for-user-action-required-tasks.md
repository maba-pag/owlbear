---
id: 661
title: Pipeline handling for user-action-required tasks
status: archived
priority: medium
created: 2026-04-06T08:25:07.1782653+02:00
updated: 2026-04-06T23:01:24.1300673+02:00
started: 2026-04-06T23:01:24.1300673+02:00
completed: 2026-04-06T23:01:24.1300673+02:00
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

[[2026-04-06]] Mon 21:31
## Builder Notes

**Files changed (2):**
- `serve/orchestrator/src/owlbear/planner/gates.py` — added `"type:user-action"` to `_NON_IMPL_TAGS` frozenset
- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` — added `"type:user-action"` to `_PICK_NON_IMPL_TAGS` frozenset

**Test results:** 7 passed, 0 failed (`tests/test_user_action_non_impl_661.py`)
- `TestFromAC_UserActionNonImplFrozensets`: 2/2 ✓
- `TestFromAC_CheckTDD_UserActionExemption`: 3/3 ✓
- `TestFromAC_PickTasksUserActionExemption`: 2/2 ✓

**Lint:** 2 pre-existing violations in server.py (PLR0915 line 337, RUF059 line 398) — not introduced by this change. Zero new lint violations.

**Commit:** `6ee05d3` feat(orchestrator): add type:user-action to NON_IMPL_TAGS gate sets #661

[[2026-04-06]] Mon 21:58
## Review Evidence

### Test Results
- pytest (scoped): **7 passed, 0 failed** — independent execution confirmed
- ruff: **2 violations** — both pre-existing (PLR0915 L337, RUF059 L398 in server.py), neither in `_PICK_NON_IMPL_TAGS` area (~L531), zero new violations from builder changes

### Coverage
- `owlbear.planner.gates`: 67% (full module); specific changed line (`"type:user-action"` in `_NON_IMPL_TAGS`) 100% exercised by both membership test + 3 behavioral tests
- `owlbear_mcp_kanban.server`: 28% (full module, large file); specific changed line (`"type:user-action"` in `_PICK_NON_IMPL_TAGS`) 100% exercised by membership test + 2 `pick_tasks` behavioral tests
- Below 90% module threshold — deduction applied. Low numbers are an artifact of scoped tests not exercising the full module; pre-existing code covered by `test_planner_gates_selector.py`, `test_pick_tasks_620.py`, etc.

### Changed Files (independently verified)
- `serve/orchestrator/src/owlbear/planner/gates.py` L24-31: `_NON_IMPL_TAGS` frozenset confirmed to contain `"type:user-action"` ✅
- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` L531-543: `_PICK_NON_IMPL_TAGS` frozenset confirmed to contain `"type:user-action"` ✅
- `tests/test_user_action_non_impl_661.py` (196 lines, new file, committed at 6ee05d3)

### Step 5 — Pass 1: Critical Checks

#### 5.0 AC-to-Test Coverage

| AC Line | Mapped Tests | Would Fail if AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: Define convention (type:user-action tag) | `test_type_user_action_in_non_impl_tags_gates`, `test_type_user_action_in_pick_non_impl_tags_server` | Yes — direct membership assertion | COVERED |
| AC2: Architect early routing (skip TW/builder/reviewer) | None | N/A — documentation change, in subtask #664 | DEFERRED (#664 research) |
| AC3: Orchestrator recognizes convention (no dispatch block) | `test_user_action_tag_in_progress_no_tdd_notes_passes` + 2 more, `test_user_action_in_progress_no_tdd_notes_included_in_dispatch` + 1 more | Yes — check_tdd() returns False without the tag; pick_tasks excludes without tag | COVERED |
| AC4: Document convention in agent-common/r-pipeline-protocol | None | N/A — documentation change, in subtask #663 | DEFERRED (#663 in review) |
| AC5: Dry-run scenario showing #597-style loop prevented | None | N/A — documentation/verification, in subtask #663 | DEFERRED (#663 in review) |

AC2, AC4, AC5 are legitimately deferred to subtasks per the decomposition plan (Chain B: #663 → #664). #663 builder notes confirm documentation was completed and it is currently in review. AC2 route: #664 is in research, depending on #663. Not a test-writer failure — these require doc-file content checks outside this code scope.

#### 5.1 Security Review
- No hardcoded secrets, API keys, or tokens
- Frozenset string addition — zero injection surface
- No path operations, no deserialization, no user-controlled inputs
- No new dependencies
**PASS**

#### 5.2 TestFromAC Integrity
Builder commit `6ee05d3` modifies only `gates.py` and `server.py`. Test file unchanged from test-writer commit. Test count: 7 → 7. No TestFromAC modifications detected.
**PASS**

#### 5.3 Test Quality
- **Assertion specificity**: STRONG — `assert "type:user-action" in _NON_IMPL_TAGS` and `assert check_tdd(task) is True` are mutation-meaningful assertions. Flipping either frozenset entry or the intersection logic would cause immediate failures.
- **Negative/error-path**: ADEQUATE — behavioral tests specify exact `is True` return, no `assert result` laziness. Missing: no test that a task WITHOUT the tag still fails TDD gate (pre-existing behavior; test-writer noted 3 tests removed as they tested existing behavior that was already passing).
- **Test independence**: PASS — each test constructs fresh Task/dict objects, no shared mutable state.
- **Descriptive names**: PASS — all names match their exact assertion.
**No WEAK dimension. Test quality: ADEQUATE.**

#### 5.4 Data Safety
No runtime data — frozenset constants. No data safety concerns.
**PASS**

#### 5.5 Implementation-Aware Gap Analysis
Two one-line changes to module-private frozensets. The implementation surface is exactly 2 strings added to 2 frozensets. Both are exercised. No untested paths.
**PASS**

#### 5.7 Builder Process
Single set of Builder Notes, single commit. CLEAN.

### AC Compliance Table

| AC | Evidence | Status |
|----|----------|--------|
| AC1 (define convention) | `_NON_IMPL_TAGS` L27 contains `"type:user-action"` (gates.py read); `_PICK_NON_IMPL_TAGS` L539 contains `"type:user-action"` (server.py read) | PASS |
| AC2 (architect routing) | Not in scope for this PR — subtask #664 (research, explicit Chain B dependency on #663) | DEFERRED |
| AC3 (orchestrator recognition) | `pick_tasks` passes in-progress type:user-action through gate (test 910 and 911 in dispatch list); `check_tdd` returns True for in-progress + type:user-action + no TW Notes | PASS |
| AC4 (documentation) | Not in scope for this PR — subtask #663 (currently in review, builder completed all 4 doc AC items: r-pipeline-protocol §5 subsection, agent-common table, r-project-standards update, dry-run scenario) | DEFERRED |
| AC5 (dry-run) | Part of #663 documentation — 8-step dry-run scenario in r-pipeline-protocol §5 per #663 builder notes | DEFERRED |

### Deductions
| Finding | Deduction |
|---------|-----------|
| Module-level coverage below 90% (gates.py 67%, server.py 28%) — new lines 100% exercised, low module % due to other functions covered by separate test suites | -0.04 |
| AC2 (architect gate rule, subtask #664) not yet complete | -0.04 |
| Total deductions | -0.08 |

### Verdict
- Tests: 7/7 pass
- Lint: 2 pre-existing violations, 0 new
- AC code items: 2/2 PASS
- AC deferred items: 3 (actively in flight — #663 in review, #664 in research)
- Security: PASS
- Test integrity: PASS
- Test quality: ADEQUATE

**Confidence: .92 → PASS**

[[2026-04-06]] Mon 22:02
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `.github/copilot-instructions.md` is 9 lines (project identity + branch table only) — no tag tables, no gate behavior documentation. No entry to update. |
| 2 | Module docstrings | Yes | Verified | `gates.py` module docstring describes gate mechanism generically ("non-impl pass-through tasks are exempt") — accurate with `type:user-action` added. `check_tdd` docstring accurate. `_check_pick_gates` and `pick_tasks` docstrings in `server.py` accurate. No changes needed. |
| 3 | External attribution | No | N/A | Task body states "2 external already logged" — no new sources. `.owlbear/sources/overview.md` already current. |
| 4 | CLI changes | No | N/A | Only frozenset constant additions to private module-level sets. No exported API or CLI surface changed. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/user-action-required-pipeline-handling.md` exists. Linked in task body under Research section. Follow-up tasks #662, #663, #664, #665, #666 confirmed created in Planning section. |

### Files Updated
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/661-*` files found)

[[2026-04-06]] Mon 23:01
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: Define convention (type:user-action tag) | `_NON_IMPL_TAGS` gates.py:L27, `_PICK_NON_IMPL_TAGS` server.py:L539 | PASS |
| AC2: Architect early routing | Deferred to subtask #664 (research, Chain B dependency) | DEFERRED |
| AC3: Orchestrator recognizes convention | 7 tests pass: check_tdd + pick_tasks behavioral tests | PASS |
| AC4: Document convention | Deferred to subtask #663 (in review) | DEFERRED |
| AC5: Dry-run scenario | Deferred to subtask #663 (in review) | DEFERRED |

### Test Results
- pytest (scoped): 7 passed, 0 failed
- pytest (full suite): pre-existing failures only, zero failures in task scope
- ruff: 2 pre-existing violations (PLR0915 L337, RUF059 L398 in server.py), zero new

### Architect Quality: 4/5
Clear AC covering multiple domains. Decomposition into 5 subtasks (2 chains) handled cleanly. Minor gap: umbrella AC spans code + docs, but planner separated responsibilities well.

### Deduction Breakdown
- No deductions. Code AC items (AC1, AC3) fully evidenced. Deferred items (AC2, AC4, AC5) are legitimate decomposition with active subtasks. Pre-existing lint not introduced by this change. Reviewer evidence detailed and present.

### Confidence: .98
### Action: archive
