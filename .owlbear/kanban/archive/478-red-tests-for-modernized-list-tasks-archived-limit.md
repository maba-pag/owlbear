---
id: 478
title: 'RED: tests for modernized list_tasks (archived, limit, reverse, blocked tri-state,
  lean JSON)'
status: archived
priority: medium
created: 2026-03-31 06:13:41.401837+02:00
updated: 2026-04-02 05:57:23.362765+02:00
started: 2026-04-02 05:57:22.908674+02:00
completed: 2026-04-02 05:57:22.908674+02:00
tags:
- scope:mcp
- type:test
- phase-2
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria

- [ ] Test archived=True passes --archived; archived=False omits it
- [ ] Test limit>0 passes --limit N; limit=0 omits it
- [ ] Test reverse=True passes --reverse; reverse=False omits it
- [ ] Test blocked=True passes --blocked (not --not-blocked)
- [ ] Test blocked=False passes --not-blocked (not --blocked)
- [ ] Test blocked=None passes neither flag
- [ ] Test lean JSON output: mock JSON with body/file/created/updated fields, verify they are stripped from result
- [ ] All tests fail before implementation (RED phase)

## Design Notes

Follow existing _patch_run() mock pattern in test_server.py. For lean JSON test, mock _run_kanban to return a JSON string with all fields, verify list_tasks strips the noisy ones.

See docs/research/modernize-list-tasks.md for full analysis.

[[2026-03-31]] Tue 08:41
## Research Validation
- Checklist: all 8 items pass (see modernize-list-tasks.md for sources)
- Tier: T1 Autonomous (test-writing, no arch changes)
- No duplicate tests exist for archived/limit/reverse/blocked tri-state/lean JSON
- Pattern: extend TestFromAC_Tools._patch_run() in test_server.py
- No DR needed

[[2026-03-31]] Tue 11:07
## Architecture Review
See docs/scratch/478-architect.md for full review.

[[2026-03-31]] Tue 11:07
## Architecture Review
See docs/scratch/478-architect.md for full review.

[[2026-03-31]] Tue 14:08
## Test-Writer Notes
- Test file: tests/test_mcp_kanban_list_tasks_472.py (pre-existing from #472 RED phase)
- Classes: TestFromAC_ListTasksSignature, TestFromAC_ListTasksCliFlags, TestFromAC_ListTasksLeanJson, TestFromAC_ListTasksStructuredContent
- Tests per category: happy 7, edge 8, error 0, boundary 3
- Total: 21 tests, all FAIL (confirmed by pytest run)
- ruff: clean
- AC coverage:
  - archived=True passes --archived: test_archived_true_passes_archived_flag (happy)
  - archived=False omits it: test_archived_false_omits_archived_flag (edge)
  - limit>0 passes --limit N: test_limit_positive_passes_limit_flag_and_value, test_limit_one_passes_limit_1 (happy, boundary)
  - limit=0 omits it: test_limit_zero_omits_limit_flag (edge)
  - reverse=True passes --reverse: test_reverse_true_passes_reverse_flag (happy)
  - reverse=False omits it: test_reverse_false_omits_reverse_flag (edge)
  - blocked=True passes --blocked (not --not-blocked): test_blocked_true_passes_blocked_flag (happy)
  - blocked=False passes --not-blocked (not --blocked): test_blocked_false_passes_not_blocked_flag (happy)
  - blocked=None passes neither flag: test_blocked_none_passes_no_block_filter_flags (edge)
  - lean JSON strips body/file/created/updated: test_stripped_fields_absent_from_result, test_all_tasks_in_list_have_fields_stripped (happy, edge)
  - All tests fail before implementation: all 21 FAIL (TypeError + AssertionError)

[[2026-03-31]] Tue 14:51
## Builder Notes
- Files changed: packages/mcp-kanban/src/owlbear_mcp_kanban/server.py, packages/mcp-kanban/tests/test_server.py
- Tests: 21 passed (test_mcp_kanban_list_tasks_472.py), ruff clean
- Lint: ruff clean
- Evidence: 21 FAILED RED then 21 PASSED GREEN; 2 pre-existing move/pick failures unrelated
- Fixes: removed block_filter, added archived/limit/reverse/blocked tri-state, --json flag, lean JSON strip, output_schema via fn_metadata; updated 3 obsolete refs in test_server.py

[[2026-03-31]] Tue 15:28
## Review Evidence
See docs/scratch/478-reviewer.md for full evidence.

[[2026-03-31]] Tue 15:28
## Review Evidence
See docs/scratch/478-reviewer.md for full evidence.

[[2026-03-31]] Tue 15:28
## Review Evidence
See docs/scratch/478-reviewer.md for full evidence.

[[2026-03-31]] Tue 16:14
## Test-Writer Notes (retry)
- Retry reason: reviewer FAIL — lean JSON tests only checked ABSENCE of stripped fields; _LEAN_FIELDS constant defined but never asserted
- Added: 5 new tests in TestFromAC_ListTasksLeanJsonPresence (presence assertions)
  - test_lean_json_retains_all_expected_lean_fields (uses _LEAN_FIELDS, fails vs [{} mutation])
  - test_lean_json_retains_id
  - test_lean_json_retains_title
  - test_lean_json_strips_exactly_four_fields (key count guard)
  - test_lean_json_multi_task_all_retain_id_and_title
- Preserved: 21 existing tests (all PASS)
- Note: new tests PASS against correct implementation (retry cycle); fail against [{} for task in tasks] mutation
- Total: 26 tests, ruff clean

[[2026-03-31]] Tue 16:43
## Builder Notes (retry)
- No code changes needed - previous implementation already correct
- 5 new TestFromAC_ListTasksLeanJsonPresence tests (presence guards) all PASS vs current server.py
- lean strip keeps all 10 lean fields correctly
- Tests: 26 passed (test_mcp_kanban_list_tasks_472.py), 95 passed (full mcp-kanban suite)
- Lint: ruff clean

[[2026-03-31]] Tue 17:19
## Review Evidence (retry)
### Test Results
- pytest tests/test_mcp_kanban_list_tasks_472.py: **26 passed, 0 failed**
- ruff check packages/mcp-kanban/src/ tests/test_mcp_kanban_list_tasks_472.py: All checks passed

### Retry Delta
- Prior FAIL reason: LAX lean JSON tests (absence-only assertions, _LEAN_FIELDS unused)
- Fix: TestFromAC_ListTasksLeanJsonPresence added (5 tests, pure additions)
- Git diff d1d557b: only 93-line addition -- original 21 tests byte-for-byte unchanged

### TestFromAC Coverage Table
| AC Line | Mapped Test | Would Fail If Violated? | Verdict |
|---------|-------------|------------------------|---------|
| archived=True passes --archived | test_archived_true_passes_archived_flag | Yes | COVERED |
| archived=False omits --archived | test_archived_false_omits_archived_flag | Yes | COVERED |
| limit>0 passes --limit N | test_limit_positive_passes_limit_flag_and_value, test_limit_one_passes_limit_1 | Yes | COVERED |
| limit=0 omits --limit | test_limit_zero_omits_limit_flag | Yes | COVERED |
| reverse=True passes --reverse | test_reverse_true_passes_reverse_flag | Yes | COVERED |
| reverse=False omits --reverse | test_reverse_false_omits_reverse_flag | Yes | COVERED |
| blocked=True passes --blocked | test_blocked_true_passes_blocked_flag | Yes | COVERED |
| blocked=False passes --not-blocked | test_blocked_false_passes_not_blocked_flag | Yes | COVERED |
| blocked=None passes neither flag | test_blocked_none_passes_no_block_filter_flags | Yes | COVERED |
| lean JSON strips body/file/created/updated | test_stripped_fields_absent_from_result + 5 presence tests | Yes | COVERED |
| All tests fail RED | Confirmed by test-writer notes (21 FAIL original) | Yes | COVERED |

### TestFromAC Comparison Table
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| All 21 original tests | No change (git diff confirms) | PRESERVED |
| TestFromAC_ListTasksLeanJsonPresence | 5 new tests added | ADDED (strengthening) |

### Test Quality
- Assertion specificity: STRONG -- _LEAN_FIELDS now used in assertions; field values checked (task[id] == _SAMPLE_FULL_TASK[id]); exact key count guard
- Mutation resistance: [{} for task in tasks] mutation now breaks test_lean_json_retains_all_expected_lean_fields
- test_lean_json_strips_exactly_four_fields: guards both over-strip and under-strip (key count = original - 4)
- Negative paths: all omit-flag cases covered
- Dimensions: Specificity STRONG, Mutation-resistance STRONG, Coverage STRONG

### Security Review
- No new code introduced (test-only additions) -- PASS

### Verdict: PASS
Confidence: .95

[[2026-03-31]] Tue 17:53
## Docs Gate
- 1. .github/copilot-instructions.md: No/N/A - high-level only
- 2. Docstrings: Yes/Pass - list_tasks has accurate docstring
- 3. sources/overview.md: No/N/A - sources in #472 section; no new sources
- 4. README.md: No/N/A - MCP tool not CLI
- 5. Research doc: Yes/Pass - modernize-list-tasks.md exists and linked
- 6. skills/mcp-kanban/SKILL.md: Yes/Updated - removed block_filter, added archived/limit/reverse/blocked

 Files Updated: skills/mcp-kanban/SKILL.md
 Scratch: None

[[2026-04-02]] Thu 05:57
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| archived=True passes --archived; False omits | test_archived_true_passes_archived_flag, test_archived_false_omits_archived_flag (L155-168) | PASS |
| limit>0 passes --limit N; 0 omits | test_limit_positive_passes_limit_flag_and_value, test_limit_one_passes_limit_1, test_limit_zero_omits_limit_flag | PASS |
| reverse=True passes --reverse; False omits | test_reverse_true_passes_reverse_flag, test_reverse_false_omits_reverse_flag | PASS |
| blocked=True passes --blocked (not --not-blocked) | test_blocked_true_passes_blocked_flag; server.py L183-186 tri-state | PASS |
| blocked=False passes --not-blocked (not --blocked) | test_blocked_false_passes_not_blocked_flag; server.py L183-186 | PASS |
| blocked=None passes neither flag | test_blocked_none_passes_no_block_filter_flags | PASS |
| lean JSON strips body/file/created/updated | test_stripped_fields_absent + 5 presence guards in LeanJsonPresence; server.py L188-192 | PASS |
| All tests fail before implementation (RED) | Test-writer notes: 21 FAIL confirmed | PASS |

### Test Results
- pytest (task scope): 26 passed, 0 failed
- pytest (full suite): 2784 passed, 239 failed (all pre-existing, none in mcp-kanban scope)
- ruff: All checks passed

### AC Quality: 4/5
AC was specific, testable, and led to clean implementation. Minor gap: lean JSON AC only specified absence; presence guards came from reviewer retry. Test-writer gap, not AC gap.

### Deduction breakdown
- Per AC line with no evidence: 0 x -.02 = 0
- Lint issues: 0 x -.05 = 0
- AC quality at 3 or below: N/A (score 4)
- Missing reviewer evidence: N/A (present, detailed)
- Full-suite failures in task scope: 0 x -.05 = 0
### Confidence: 1.0
### Action: archive
