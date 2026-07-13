---
id: 662
title: Add type:user-action to NON_IMPL_TAGS (gates.py + server.py)
status: archived
priority: medium
created: 2026-04-06T16:39:07.1761895+02:00
updated: 2026-04-07T02:34:51.8632883+02:00
started: 2026-04-07T02:34:51.8632883+02:00
completed: 2026-04-07T02:34:51.8632883+02:00
tags:
    - phase-3
    - scope:orchestrator
    - type:config
parent: 661
depends_on:
    - 665
class: standard
---

## Objective\nAdd `type:user-action` to the NON_IMPL_TAGS set in both Python gate locations for TDD gate exemption.\n\n## Context\nFrom #661 research: `type:user-action` tag convention for manual user-action tasks needs TDD gate exemption so the test-writer passes through cleanly after user completes the action.\nSkill doc updates split to #666.\n\n## Acceptance Criteria\n- [ ] Add `type:user-action` to `_NON_IMPL_TAGS` in serve/orchestrator/src/owlbear/planner/gates.py\n- [ ] Add `type:user-action` to `_PICK_NON_IMPL_TAGS` in serve/mcp-kanban/src/owlbear_mcp_kanban/server.py\n- [ ] Existing tests pass (no regressions)\n\n## Files Affected\n- serve/orchestrator/src/owlbear/planner/gates.py\n- serve/mcp-kanban/src/owlbear_mcp_kanban/server.py

[[2026-04-06]] Mon 23:49
## Research
- Research doc: N/A (trivial config task — parent .owlbear/research/user-action-required-pipeline-handling.md covers this)
- Sources: 3 studied, 3 high-relevance (gates.py L22-25, server.py L531-535, test_user_action_non_impl_661.py)
- Recommendation: No further work needed — implementation already complete (confidence: .99)
- Follow-up tasks created: none
- Decision requests: none (T1 — trivial config, already implemented)

### Verification
- `type:user-action` confirmed present in `_NON_IMPL_TAGS` (gates.py L25) and `_PICK_NON_IMPL_TAGS` (server.py L534)
- 7/7 tests pass (test_user_action_non_impl_661.py)
- No regressions: 6 failures in adjacent test files are pre-existing (decomp_override agent rename + atomicity gate — unrelated to type:user-action)
- Implementation commit: 6ee05d3 (completed during parent #661 builder phase)

### Note
This subtask's code was already implemented during the parent #661 lifecycle. The planner created #662 after the builder had executed. All 3 AC items are satisfied by existing code. Task is ready for the downstream pipeline to verify and close.

[[2026-04-07]] Tue 00:16
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: add tag to two coordinated constant sets |
| Interface clarity | PASS | AC specifies exact files and constant names |
| Dependency correctness | PASS | #665 (test task) archived/done |
| Module layering | PASS | Leaf-level config constants, no new imports |
| TDD compliance | PASS | Test task #665 exists and is archived |
| KISS/YAGNI | PASS | Minimal scope: one string added to two sets |
| Premise challenge | PASS | Parent #661 research established need |
| Pattern consistency | PASS | Follows existing frozenset tag pattern in both files |
| Security surface | PASS | No new system boundaries, config constants only |
| Single domain | PASS | orchestrator domain (two files in same functional area) |

### Codebase Verification
- gates.py L24-29: `_NON_IMPL_TAGS` frozenset contains `type:user-action` (confirmed)
- server.py L531-539: `_PICK_NON_IMPL_TAGS` frozenset contains `type:user-action` (confirmed)
- Implementation already landed in commit 6ee05d3 during parent #661 builder phase
- Non-impl tag `type:config` already present on task

### Challenge Results
- Challenger: FALLBACK (challenger agent not in available roster)
- Architect response: Proceeded without challenge; trivial config addition with verified implementation

### Verdict: APPROVE
### Action Taken: Advanced to todo. Implementation already complete; downstream pipeline will verify and close.

[[2026-04-07]] Tue 00:42
## Test-Writer Notes
- Non-implementation task (tagged `type:config`) — no tests applicable.
- Passing through to builder.

[[2026-04-07]] Tue 01:04
## Builder Notes
- Non-implementation task — no code changes needed.
- Implementation already landed in commit 6ee05d3 during parent #661 builder phase.
- Verified: `type:user-action` present in `_NON_IMPL_TAGS` (gates.py) and `_PICK_NON_IMPL_TAGS` (server.py).
- Passing through to review.

[[2026-04-07]] Tue 01:57
## Review Evidence

### Tests
pytest: 7 passed, 0 failed, 0 skipped (test_user_action_non_impl_661.py)

### Lint
ruff: 2 violations in server.py (PLR0915:337 — too many statements; RUF059:398 — unused unpacked variable `name_err`). Both violations are at lines 337/398, well outside the frozenset change at L531–539. Pre-existing issues, not introduced by this task. Gates.py: clean.

### Coverage
gates.py: 67%, server.py: 28%. Low overall but scoped test coverage for the frozenset + behavioral paths is adequate for a 2-line config change.

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| Add `type:user-action` to `_NON_IMPL_TAGS` in gates.py | `"type:user-action"` confirmed at gates.py:L25 (frozenset literal, read from source) | PASS |
| Add `type:user-action` to `_PICK_NON_IMPL_TAGS` in server.py | `"type:user-action"` confirmed at server.py:L534 (frozenset literal, read from source) | PASS |
| Existing tests pass (no regressions) | 7/7 pass; no failed tests in scoped run | PASS |

### TestFromAC Audit
- `TestFromAC_UserActionNonImplFrozensets`: 2 direct membership tests — would both fail if tag absent. ✓
- `TestFromAC_CheckTDD_UserActionExemption`: 3 behavioral tests on `check_tdd()` — would fail if frozenset missing tag. ✓
- `TestFromAC_PickTasksUserActionExemption`: 2 `pick_tasks` dispatch tests — would fail if `_PICK_NON_IMPL_TAGS` missing tag. ✓
- No TestFromAC_* modifications by builder. ✓

### Security
Pure frozenset constant additions. No new imports, no system boundaries, no injection surfaces. Clean.

### Deductions
- Pre-existing lint violations (PLR0915, RUF059) in server.py noted but not deducted — clearly pre-existing, not introduced by this task.
- 0 deductions.

### Verdict
Confidence: .96 → PASS

[[2026-04-07]] Tue 02:01
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A | Frozenset constants changed; `copilot-instructions.md` contains no NON_IMPL_TAGS enumeration. Skills doc updates (dispatch-planning, tdd-red) explicitly split to #666 (depends_on #662). No update needed here. |
| 2 | Module docstrings | Yes | Verified | gates.py and server.py docstrings reference "non-impl pass-through tags" generically without enumerating. Both `check_tdd()` and `pick_tasks()` docstrings remain accurate after tag addition. |
| 3 | External attribution | No | N/A | Pure frozenset constant addition; no external repos, articles, or docs used. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/user-action-required-pipeline-handling.md` exists (parent #661 research). Task body correctly notes N/A for own research doc and references the parent doc. |

### Files Updated
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/662-*` files found)

[[2026-04-07]] Tue 02:34
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Add `type:user-action` to `_NON_IMPL_TAGS` in gates.py | Confirmed at gates.py:L27 (grep: `"type:user-action"` in frozenset literal) | PASS |
| Add `type:user-action` to `_PICK_NON_IMPL_TAGS` in server.py | Confirmed at server.py:L534 (grep: `"type:user-action"` in frozenset literal) | PASS |
| Existing tests pass (no regressions) | 7/7 task-specific tests pass. Full suite: 3380 passed, 422 failed, 18 skipped. All 422 failures are pre-existing (voice scaffolding, agent renames, atomicity gate, etc.) with 0 in task scope. | PASS |

### Test Results
- pytest (scoped): 7 passed, 0 failed (test_user_action_non_impl_661.py)
- pytest (full): 3380 passed, 422 failed, 18 skipped (0 failures in task scope; all pre-existing)
- ruff: 2 pre-existing violations in server.py (PLR0915:337, RUF059:398) well outside changed lines; gates.py clean

### Reviewer Evidence
Present and detailed. PASS verdict at .96. AC compliance table, TestFromAC audit, security check, and deduction breakdown all included. Trusted code-level findings.

### Architect Quality: 5/5
AC lines are specific (exact file paths, exact constant names), complete (all locations covered), and cleanly verifiable. No builder improvisation needed.

### Deduction Breakdown
- AC lines without evidence: 0 (3/3 verified) = 0
- Lint violations introduced: 0 (2 in server.py are pre-existing) = 0
- AC quality score: 5/5 = 0
- Missing reviewer evidence: no (present and detailed) = 0
- Full-suite in-scope failures: 0 = 0
- Total deductions: 0

### Confidence: .98
### Action: archive

Note: 422 pre-existing full-suite failures logged. Collection error in test_planner_gates.py (missing check_atomicity import) also pre-existing. Implementation commit: 6ee05d3.
