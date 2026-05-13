---
id: 1532
title: 'P1-01: Tests for body newline normalization at MCP kanban ingress'
status: in-progress
priority: critical
created: 2026-05-13T12:29:10.026075+00:00
updated: 2026-05-13T14:09:42.219660+00:00
tags:
  - phase-1
  - scope:mcp-kanban
  - type:test
parent: 1531
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Summary

RED phase: write tests for the `_normalize_escaped_newlines()` helper and its integration into all 5 MCP kanban tool parameters.

Brief: see parent #1531

## Scope

**In scope:**
- Unit tests for the helper function (three-step protect/normalize/restore)
- Integration tests for all 5 affected parameters (create_task body, edit_task body, edit_task append_body, end_work note, create_dr body)
- Guidance message assertion when normalization occurs
- Guidance positional ordering (existing reminders still fire alongside normalization guidance)
- Escape convention preservation (`\\\\n` → literal `\n` in stored content) for all 5 parameters
- Passthrough (no normalization, no normalization guidance) when input has no literal `\n`

**Out of scope:**
- Implementation of the helper or call-site wiring
- Tool description text (docs-only, verified in impl task)
- Archive remediation, `\r\n`, non-body parameters

## Test Location

`tests/test_mcp_kanban_newline_norm_1531.py`

Existing proof scope: `tests/test_mcp_kanban.py` (must still pass after implementation)

## Acceptance Criteria

- [ ] Unit tests for `_normalize_escaped_newlines()`: protect step (escaped `\\\\n` preserved via sentinel), normalize step (literal `\\n` → real newline), restore step (sentinel → literal `\\n`)
- [ ] Integration tests: each of the 5 parameters triggers normalization (create_task body, edit_task body, edit_task append_body, end_work note, create_dr body)
- [ ] Guidance assertion: normalization guidance message appended to response when normalization occurs
- [ ] Guidance ordering: normalization guidance appends AFTER existing guidance (coexists, does not replace)
- [ ] Escape convention: `\\\\\\\\n` in input → literal `\\n` in stored content for all 5 affected parameters (create_task body, edit_task body, edit_task append_body, end_work note, create_dr body)
- [ ] Passthrough: when input has no literal `\\n`, no normalization occurs and no normalization-specific guidance is emitted (other guidance sources may still fire independently)
- [ ] Test file located at `tests/test_mcp_kanban_newline_norm_1531.py`
- [ ] All normalization-path tests fail in RED phase (passthrough regression guards may pass since no implementation exists to break clean-input behavior)

Proof bundle: skip
Existing proof scope: `tests/test_mcp_kanban.py` (must still pass after GREEN implementation in #1533)
2026-05-13T14:00:22+00:00
## Architecture Review (re-entry after 2nd review FAIL)

### Reviewer Findings Resolution

| # | Finding | Resolution |
|---|---|---|
| 1 | AC 8 vs AC 6 conflict — passthrough tests pass in RED | AC 8 narrowed: "All normalization-path tests fail in RED phase (passthrough regression guards may pass)" — correct TDD practice; regression guards verify negative case |
| 2 | AC 6 "no guidance emitted" too broad — end_work has non-normalization guidance | AC 6 narrowed: "no normalization-specific guidance is emitted (other guidance sources may still fire independently)" — feature scope is normalization only |
| 3 | AC 5 missing append_body escape test | AC 5 now explicitly lists all 5 parameters — test-writer must add `test_escape_convention_append_body_preserved` |

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests for one helper + its 5 integration points |
| Interface clarity | PASS | AC now explicitly scopes guidance contract and escape coverage per parameter |
| Dependency correctness | PASS | No deps; #1533 correctly depends on this |
| Module layering | PASS | Tests import from `owlbear_mcp_kanban.server` — matches existing patterns |
| TDD compliance | PASS | This IS the RED phase; refined AC 8 correctly allows regression-guard greens |
| KISS/YAGNI | PASS | Minimal scope |
| Premise challenge | PASS | MCP JSON transport corruption of `\n` confirmed in research |
| Pattern consistency | PASS | Mock AppContext + async tool calls + response assertions |
| Security surface | PASS | Internal string normalization, no new boundaries |
| Single domain | PASS | mcp-kanban only |

### Design Diverge
- Trigger: skipped — single obvious approach

### Challenge Results
- Challenger: SKIPPED — proof bundle `skip`

### Proof-Bundle Validation
- Planner assignment: skip
- Final bundle: skip
- Existing proof scope: `tests/test_mcp_kanban.py`
- Test-writer: SKIP (pass-through via `type:test` tag)

### AC Refinement Summary
Rewrote full body with three targeted AC clarifications: (1) RED gate scoped to normalization-path only, (2) passthrough contract scoped to normalization guidance, (3) escape convention explicitly requires all 5 parameters. The test file needs one addition: `append_body` escape-convention test case.

### Verdict: APPROVE (REFINE path — AC tightened, then advanced)
### Action Taken: Refined AC to resolve review-cycle conflicts, advanced to todo
2026-05-13T14:09:42+00:00
## Test-Writer Notes
- Test file: tests/test_mcp_kanban_newline_norm_1531.py (named after parent #1531, header confirms Task: #1532)
- Proof bundle: skip — tests pre-written and committed in prior session (commit: "test: add failing tests for body newline normalization (#1531, test-writer)")
- type:test tag → pass-through per w-tdd-red Step 1a/1d
- Classes: TestFromAC_NormalizeHelper, TestFromAC_CreateTaskNormalization, TestFromAC_EditTaskNormalization, TestFromAC_EndWorkNormalization, TestFromAC_CreateDrNormalization, TestFromAC_GuidancePositioning, TestFromAC_PassthroughNoNormalization
- Tests per category: happy/unit ~13, integration happy 11, edge 5, boundary 5, passthrough regression guards 5
- Total: ~34 tests; RED confirmed — 0 passed, ImportError on _normalize_escaped_newlines (not yet implemented)
- ruff: clean