---
id: 846
title: Tests for UsageTracker secondary wiring (RED)
status: archived
priority: nice-to-have
created: 2026-03-17T21:52:20.6123179+01:00
updated: 2026-03-23T02:18:00.8634545+01:00
started: 2026-03-23T02:17:14.9403314+01:00
completed: 2026-03-23T02:17:14.9403314+01:00
tags:
    - scope:core
    - phase-3
    - type:test
class: standard
---

**Source:** #844 (TDD RED phase)

**AC:**

1. `test_usage_record_operation_field`: `UsageRecord` accepts `operation: str` field; default is `'turn'`; existing records without operation remain valid (backward compat).
2. `test_record_agent_usage_creates_record`: `record_agent_usage()` from `memory.usage` creates a `UsageRecord` with correct operation, model, provider, session_id and appends to tracker.
3. `test_record_agent_usage_noop_when_no_tracker`: `record_agent_usage()` is a silent no-op when `tracker is None`.
4. `test_record_agent_usage_enriches_cost`: `record_agent_usage()` populates `estimated_cost_usd` and `premium_requests` fields (mocked).
5. `test_condenser_records_usage`: `SummarizingCondenser` records a `UsageRecord` with `operation='condenser'` after condensation run (mock Agent.run).
6. `test_entity_extractor_records_usage`: `EntityExtractor` records a `UsageRecord` with `operation='entity_extraction'` after extraction (mock Agent.run).
7. All tests FAIL (RED) before implementation.

**File:** `tests/test_usage_wiring.py`

[[2026-03-17]] Tue 22:14

## Test-Writer Notes

- Test file: tests/test_usage_wiring.py
- Classes: TestFromAC_UsageRecordOperationField, TestFromAC_RecordAgentUsage, TestFromAC_CondenserUsageWiring, TestFromAC_EntityExtractorUsageWiring
- Tests per category: happy 8, edge 4, error 4, boundary 3
- Total: 19 tests, all FAIL v
- ruff: clean
- AC coverage:
  - AC1 (operation field): test_operation_field_default_is_turn, test_operation_field_accepts_custom_value, test_backward_compat_jsonl_without_operation, test_operation_field_serializes
  - AC2 (record_agent_usage creates record): test_import_from_memory_usage, test_creates_record_appended_to_tracker, test_operation_stored_in_record
  - AC3 (noop when None): test_noop_when_tracker_is_none
  - AC4 (enriches cost): test_enriches_estimated_cost_usd, test_enriches_premium_requests, test_enrichment_failure_does_not_raise
  - AC5 (condenser wiring): test_condenser_constructor_accepts_tracker_and_provider, test_condenser_records_operation_condenser, test_condenser_no_record_when_no_tracker, test_condenser_no_record_when_below_threshold
  - AC6 (extractor wiring): test_extractor_constructor_accepts_tracker_and_provider, test_extractor_records_operation_entity_extraction, test_extractor_no_record_when_no_tracker, test_extractor_no_record_on_empty_text

[[2026-03-17]] Tue 23:44

## Builder Notes

- Files changed: src/owlbear/memory/usage.py, src/owlbear/core/condenser.py, src/owlbear/memory/knowledge/extractor.py
- Tests: 19 passed (exit code 0, terminal run #5357347a)
- Lint: ruff All checks passed!
- Coverage: WMI hang prevented numeric capture; tests verified via exit code
- Fixes applied: Added # noqa: PLR0913 to record_agent_usage and SummarizingCondenser.**init**
- Changes: UsageRecord.operation field (default=turn), record_agent_usage() function, SummarizingCondenser tracker/provider params, EntityExtractor tracker/provider params

[[2026-03-18]] Wed 00:39

## Review Evidence>> ## Review: #846  Tests for UsageTracker secondary wiring (RED)>> ### Test Results>> - pytest (independent reviewer run) timed out after 240s: subprocess.TimeoutExpired for tests/test_usage_wiring.py>> - No reliable pass/fail count available due timeout blocker>> ### Lint Results>> - uv run ruff check src/owlbear/memory/usage.py src/owlbear/core/condenser.py src/owlbear/memory/knowledge/extractor.py tests/test_usage_wiring.py>> - Result: All checks passed>> ### Coverage>> - Scoped coverage run timed out after 240s (subprocess.TimeoutExpired with --cov)>> ### Critical Findings>> - Test artifact integrity failure: tests/test_usage_wiring.py is untracked in git (git status shows ?? ; git ls-files returns empty)>> - AC implementation lines exist: usage.py operation default + record_agent_usage; condenser.py operation=condenser wiring; extractor.py operation=entity_extraction wiring>> - TestFromAC method-name set matches Test-Writer Notes, but reviewer cannot validate execution outcome due pytest timeout>> ### AC Compliance>> - AC1-AC6: implementation evidence present in source and mapped tests exist, but execution UNVERIFIED due pytest timeout>> - AC7 (RED historical state): cannot independently re-verify in current review run>> ### Verdict>> FAIL>> ### Required Fixes>> - Make tests/test_usage_wiring.py tracked/committed in repository>> - Resolve scoped pytest/coverage timeout for this task so reviewer can run tests independently and collect pass counts>> ### Action>> review -> todo (blocked)

[[2026-03-18]] Wed 13:24

## Review Evidence

## Review: #846 - Tests for UsageTracker secondary wiring (RED)

### Test Results

- Command: uv run pytest tests/test_usage_wiring.py -q --tb=short
- Result: 19 passed, 5 warnings, 0 failed (0.59s)
- Evidence: scoped run completed successfully in reviewer environment.

### Lint Results

- Command: uv run ruff check src/ tests/
- Result: 7 errors in unrelated pre-existing files outside task scope.
- Scoped command: uv run ruff check src/owlbear/memory/usage.py src/owlbear/core/condenser.py src/owlbear/memory/knowledge/extractor.py tests/test_usage_wiring.py
- Scoped result: All checks passed.

### Coverage

- Expanded module-relevant suite executed with pytest --cov (terminal summary stream suppressed in this environment).
- Verified with command: uv run coverage report -m src/owlbear/memory/usage.py src/owlbear/core/condenser.py src/owlbear/memory/knowledge/extractor.py
- src/owlbear/core/condenser.py: 100%
- src/owlbear/memory/knowledge/extractor.py: 100%
- src/owlbear/memory/usage.py: 94%

### Pass 1 - CRITICAL

#### Security Review

- No hardcoded secrets, injection sinks, unsafe deserialization, shell execution, or path-traversal vectors found in touched files.
- No new dependencies introduced by this task.

#### Test Integrity (TestFromAC)

| Original Test | Change Made | Assessment |
|---|---|---|
| TestFromAC_UsageRecordOperationField::test_operation_field_default_is_turn | Name present in current file | PRESERVED |
| TestFromAC_UsageRecordOperationField::test_operation_field_accepts_custom_value | Name present in current file | PRESERVED |
| TestFromAC_UsageRecordOperationField::test_backward_compat_jsonl_without_operation | Name present in current file | PRESERVED |
| TestFromAC_UsageRecordOperationField::test_operation_field_serializes | Name present in current file | PRESERVED |
| TestFromAC_RecordAgentUsage::test_import_from_memory_usage | Name present in current file | PRESERVED |
| TestFromAC_RecordAgentUsage::test_creates_record_appended_to_tracker | Name present in current file | PRESERVED |
| TestFromAC_RecordAgentUsage::test_noop_when_tracker_is_none | Name present in current file | PRESERVED |
| TestFromAC_RecordAgentUsage::test_enriches_estimated_cost_usd | Name present in current file | PRESERVED |
| TestFromAC_RecordAgentUsage::test_enriches_premium_requests | Name present in current file | PRESERVED |
| TestFromAC_RecordAgentUsage::test_operation_stored_in_record | Name present in current file | PRESERVED |
| TestFromAC_RecordAgentUsage::test_enrichment_failure_does_not_raise | Name present in current file | PRESERVED |
| TestFromAC_CondenserUsageWiring::test_condenser_constructor_accepts_tracker_and_provider | Name present in current file | PRESERVED |
| TestFromAC_CondenserUsageWiring::test_condenser_records_operation_condenser | Name present in current file | PRESERVED |
| TestFromAC_CondenserUsageWiring::test_condenser_no_record_when_no_tracker | Name present in current file | PRESERVED |
| TestFromAC_CondenserUsageWiring::test_condenser_no_record_when_below_threshold | Name present in current file | PRESERVED |
| TestFromAC_EntityExtractorUsageWiring::test_extractor_constructor_accepts_tracker_and_provider | Name present in current file | PRESERVED |
| TestFromAC_EntityExtractorUsageWiring::test_extractor_records_operation_entity_extraction | Name present in current file | PRESERVED |
| TestFromAC_EntityExtractorUsageWiring::test_extractor_no_record_when_no_tracker | Name present in current file | PRESERVED |
| TestFromAC_EntityExtractorUsageWiring::test_extractor_no_record_on_empty_text | Name present in current file | PRESERVED |

Critical integrity finding:

- git status --short -- tests/test_usage_wiring.py reports: ?? tests/test_usage_wiring.py
- git ls-files -- tests/test_usage_wiring.py returns no entry
- git log --oneline -- tests/test_usage_wiring.py returns no history
- Result: the TestFromAC artifact is not tracked/committed, so the repository does not carry the reviewed safety net.

#### Test Quality

| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | ADEQUATE | AC-critical tests assert specific fields/values; minor constructor existence checks are lightweight but non-critical. |
| Negative/error paths | STRONG | Covers tracker=None, enrichment failure swallow, below-threshold condenser, and empty extractor input. |
| Mutation reasoning | ADEQUATE | Operation wiring assertions would catch wrong operation literal; some call-shape checks use flexible kwargs/args OR pattern. |
| Test independence | STRONG | tmp_path-based trackers and local mocks keep tests isolated. |
| Descriptive names | STRONG | Test names clearly encode scenario + expected behavior. |

#### Data Safety

- No new race condition or atomicity regression introduced in reviewed wiring changes.
- Helper remains no-op when tracker is None and catches enrichment exceptions without crashing callers.

### Pass 2 - INFORMATIONAL

- Global ruff baseline is currently red in unrelated files; scoped lint for task files is clean.
- Existing warning logs in usage recording remain broad (BLE001); this mirrors existing behavior and did not introduce new security risk.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| 1. UsageRecord operation default/backward-compat | src/owlbear/memory/usage.py line 41 and line 122 | test_operation_field_default_is_turn; test_backward_compat_jsonl_without_operation | PASS |
| 2. record_agent_usage creates/append record fields | src/owlbear/memory/usage.py line 115 and line 168 | test_creates_record_appended_to_tracker; test_operation_stored_in_record | PASS |
| 3. no-op when tracker is None | src/owlbear/memory/usage.py line 129 | test_noop_when_tracker_is_none | PASS |
| 4. enriches estimated_cost_usd and premium_requests | src/owlbear/memory/usage.py lines 140-151 | test_enriches_estimated_cost_usd; test_enriches_premium_requests | PASS |
| 5. condenser records operation='condenser' | src/owlbear/core/condenser.py lines 91-97 | test_condenser_records_operation_condenser | PASS |
| 6. extractor records operation='entity_extraction' | src/owlbear/memory/knowledge/extractor.py lines 106-112 | test_extractor_records_operation_entity_extraction | PASS |
| 7. RED phase all failing before implementation | kanban task notes show Total: 19 tests, all FAIL v | Test-Writer Notes evidence in task history | PASS |

### Verdict: FAIL

- Reason: Critical test-artifact integrity failure (tests/test_usage_wiring.py is untracked and therefore not preserved in repository history).

### Action Taken

- move: review -> todo
- block reason: Task test artifact tests/test_usage_wiring.py must be tracked/committed before re-review.

[[2026-03-22]] Sun 23:33

## Test-Writer Notes (retry)

- Retry reason: reviewer FAIL was about untracked test artifact, not missing tests.
- Fixed: removed stale #noqa: N801 directives (RUF100) and replaced pytest.approx with direct equality for mocked float values (numpy compat issue).
- Committed: git commit 117c0be (tests/test_usage_wiring.py, 457 lines).
- Preserved: 19 existing tests (all PASS after fixes). ruff: clean.

[[2026-03-23]] Mon 00:01

## Builder Notes (retry 2026-03-22)

- Retry reason: test artifact now committed at 117c0be (test-writer re-committed tests/test_usage_wiring.py)
- Files changed: src/owlbear/memory/usage.py, src/owlbear/core/condenser.py, src/owlbear/memory/knowledge/extractor.py (committed ed9bea3); tests/test_usage_wiring.py (committed 117c0be)
- Tests: 19 passed (uv run pytest tests/test_usage_wiring.py -q --tb=short)
- Lint: ruff clean on all 4 task-specific files
- Coverage: 65/88/76pct scoped to test_usage_wiring.py only (missed lines are pre-existing helpers unrelated to AC); full-suite coverage confirmed 94-100pct by prior reviewer run
- Fixes applied: None. Implementation unchanged; test artifact commit was the only gap

[[2026-03-23]] Mon 00:40

## Review Evidence

[[2026-03-23]] Mon 00:40

## Review: #846 - Tests for UsageTracker secondary wiring (RED)

[[2026-03-23]] Mon 00:40

### Test Results

[[2026-03-23]] Mon 00:40

- uv run pytest tests/test_usage_wiring.py -q --tb=short => 19 passed, 0 failed, 2 warnings (optional qdrant_client skips).

[[2026-03-23]] Mon 00:40

### Lint Results

[[2026-03-23]] Mon 00:41

- Scoped ruff check on src/owlbear/memory/usage.py, src/owlbear/core/condenser.py, src/owlbear/memory/knowledge/extractor.py, tests/test_usage_wiring.py => All checks passed.

[[2026-03-23]] Mon 00:41

- Full ruff check src/ tests/ reports unrelated baseline RUF100 violations outside this task scope.

[[2026-03-23]] Mon 00:41

### Coverage

[[2026-03-23]] Mon 00:41

- coverage report on touched modules: src/owlbear/memory/usage.py 94%, src/owlbear/core/condenser.py 100%, src/owlbear/memory/knowledge/extractor.py 100%.

[[2026-03-23]] Mon 00:41

### Pass 1 - CRITICAL

[[2026-03-23]] Mon 00:41

- Test-Writer AC Coverage: AC1 through AC6 each map to explicit TestFromAC methods in tests/test_usage_wiring.py and would fail on corresponding wiring/default regressions; no MISSING and no LAX mappings.

[[2026-03-23]] Mon 00:41

- Security Review: no hardcoded secrets, injection sinks, path traversal handling, unsafe deserialization, or dependency changes in task files.

[[2026-03-23]] Mon 00:41

- Test Integrity: git diff -- tests/test_usage_wiring.py is empty; git diff 117c0be..HEAD -- tests/test_usage_wiring.py is empty; builder commit ed9bea3 does not touch tests. TestFromAC methods preserved.

[[2026-03-23]] Mon 00:41

- Test Quality: assertion specificity ADEQUATE; negative/error paths STRONG; mutation reasoning STRONG; independence STRONG; descriptive names STRONG.

[[2026-03-23]] Mon 00:41

- Data Safety: no race, atomicity, or unbounded-input regressions introduced in reviewed task scope.

[[2026-03-23]] Mon 00:41

- Implementation-aware gaps: no significant untested paths found in newly introduced record_agent_usage or condenser/extractor usage-wiring branches.

[[2026-03-23]] Mon 00:41

### Pass 2 - INFORMATIONAL

[[2026-03-23]] Mon 00:41

- Broader optional run surfaced unrelated failures in tests/test_condenser.py bootstrap wiring due build_toolsets arity mismatch at src/owlbear/bootstrap/**init**.py:157; outside #846 commit scope.

[[2026-03-23]] Mon 00:41

### AC Compliance

[[2026-03-23]] Mon 00:42

- AC1 PASS: UsageRecord operation default and backward compatibility are present in src/owlbear/memory/usage.py and validated by TestFromAC_UsageRecordOperationField tests.

[[2026-03-23]] Mon 00:42

- AC2 PASS: record_agent_usage creates and appends UsageRecord with operation/model/provider/session_id wiring; validated by test_creates_record_appended_to_tracker and test_operation_stored_in_record.

[[2026-03-23]] Mon 00:42

- AC3 PASS: tracker None no-op at record_agent_usage early return; validated by test_noop_when_tracker_is_none.

[[2026-03-23]] Mon 00:42

- AC4 PASS: estimated_cost_usd and premium_requests enrichment wiring validated by test_enriches_estimated_cost_usd and test_enriches_premium_requests; enrichment failure path validated by test_enrichment_failure_does_not_raise.

[[2026-03-23]] Mon 00:42

- AC5 PASS: SummarizingCondenser records usage with operation condenser via record_agent_usage call in src/owlbear/core/condenser.py; validated by test_condenser_records_operation_condenser.

[[2026-03-23]] Mon 00:42

- AC6 PASS: EntityExtractor records usage with operation entity_extraction via record_agent_usage call in src/owlbear/memory/knowledge/extractor.py; validated by test_extractor_records_operation_entity_extraction.

[[2026-03-23]] Mon 00:42

- AC7 PASS: historical RED state documented in Test-Writer Notes and TestFromAC artifact is now tracked and preserved.

[[2026-03-23]] Mon 00:42

### Verdict: PASS

[[2026-03-23]] Mon 00:42

### Confidence: .92

[[2026-03-23]] Mon 00:42

### Action Taken

[[2026-03-23]] Mon 00:42

- Move review to docs gate.

[[2026-03-23]] Mon 01:40

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Internal wiring; SummarizingCondenser already referenced; tracker params are opt-in internals |
| 2 | Docstrings complete | Yes | Updated | Added tracker/provider to SummarizingCondenser Args; added full Args section to EntityExtractor; usage.py docstrings already accurate |
| 3 | docs/sources/overview.md | No | N/A | TDD task, no external patterns |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | No research phase |
| 6 | No impact | No | N/A | Item 2 had docs impact |

### Files Updated

- src/owlbear/core/condenser.py (docstring: added tracker/provider to Args)
- src/owlbear/memory/knowledge/extractor.py (docstring: added Args section with model/tracker/provider)

### Scratch Files Cleaned

- docs/scratch/846-cov.txt, 846-test-err.txt, 846-test-out.txt, 846-verify-err.txt, 846-verify-out.txt

[[2026-03-23]] Mon 02:18

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 3e98831 | chore | kanban/tasks/846-*, activity.jsonl | #846 |
