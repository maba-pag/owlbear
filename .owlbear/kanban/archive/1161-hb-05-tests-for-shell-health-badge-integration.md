---
id: 1161
title: 'HB-05: Tests for Shell health badge integration'
status: archived
priority: important
created: 2026-04-28T17:35:08.979042+00:00
updated: 2026-04-28T22:41:39.622172+00:00
tags:
- phase:cockpit
- scope:cockpit-frontend
- type:test
parent:
depends_on:
- 1158
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

Seed from ideation task #1042 — cockpit health badge feature.
Shell status bar: `data-region="status-bar"` in `serve/cockpit/web/src/Shell.tsx`.
Hook: `useScanPolling` (#1159). Component: `HealthBadge` (#1160).

## Acceptance Criteria

- [ ] Test: Shell renders HealthBadge in the status bar region
- [ ] Test: HealthBadge receives scan results from useScanPolling
- [ ] Test: badge updates when scan poll returns new results
- [ ] Test: badge is absent or inert before first poll completes

## Scope

- **In scope:** Shell integration tests; hook and component may be mocked
- **Out of scope:** Hook internals, component styling, backend endpoint

[[2026-04-28]]
## Architecture Review

### Verdict: MERGE — absorbed into #1162

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Shell integration tests only |
| Interface clarity | FAIL | AC4 "absent or inert" allows contradictory implementations; AC2 ignores ScanItem type mismatch between hook (nullable) and component (non-null) |
| Dependency correctness | PASS | #1158 archived/done, component + hook exist |
| Module layering | PASS | Test code only |
| TDD compliance | N/A | Task IS the test deliverable |
| KISS/YAGNI | PASS | Minimal 4 test cases |
| Premise challenge | FAIL | `type:test` tag causes double pass-through (test-writer + builder both skip). Nobody writes the tests. Separate test task is structurally incompatible with TDD pipeline. |
| Pattern consistency | PASS | Follows Shell.test.tsx patterns |
| Security surface | N/A | Test code |
| Single domain | PASS | Cockpit frontend |

### Challenge Results
- Challenger: **block** (confidence 0.18 in original APPROVE)
- Architect response: **accepted** — challenger correctly identified (a) double pass-through structural flaw for `type:test`, (b) AC4 ambiguity allowing contradictory implementations, (c) unacknowledged ScanItem nullable→non-null type mismatch between useScanPolling and HealthBadge

### Root Cause
The test/build decomposition pattern (separate #1161 for tests, #1162 for implementation) is structurally unsound in the TDD pipeline: `type:test` tag makes test-writer pass through, which cascades to builder pass-through, so the test file is never written.

### Action Taken
**MERGED into #1162** with refined AC:
1. AC4 ambiguity resolved → "HealthBadge not rendered while isLoading is true" (absent, not inert)
2. ScanItem normalisation requirement made explicit (hook nullable fields → component non-null)
3. All 4 test AC lines incorporated into #1162 alongside implementation AC
4. Removed #1162's dependency on #1161
5. #1162 scope expanded: "Shell integration tests (merged from #1161)" added to in-scope
[[2026-04-28]]
## Audit

### AC Verification (merge execution)

| AC Line | Evidence | Status |
|---------|----------|--------|
| Test: Shell renders HealthBadge in status bar | #1162 AC1: "HealthBadge rendered inside [data-region='status-bar']" | PASS |
| Test: HealthBadge receives scan results from useScanPolling | #1162 AC2: includes ScanItem normalisation requirement | PASS |
| Test: badge updates when scan poll returns new results | #1162 AC3: "Badge reflects updated scan results when poll returns new data" | PASS |
| Test: badge is absent or inert before first poll completes | #1162 AC4: refined to "not rendered while isLoading is true" (ambiguity resolved) | PASS |

Merge verified: #1162 context references merge from #1161, scope includes "Shell integration tests (merged from #1161)", dependency on #1161 removed.

### Test Results
- pytest: 2813 passed, 114 failed (all pre-existing in kanban/storage/config domains, none in task scope), 4 skipped
- ruff: 4 violations (copilot_auth, mcp-knowledge server, mcp-memory approve, orchestrator example), none in task scope

### Architect Quality: 5/5
Identified structural double pass-through flaw for type:test tasks in TDD pipeline. Accepted challenger block (confidence 0.18). Took clear corrective action: merge with AC refinement, AC4 ambiguity resolved, ScanItem normalisation made explicit.

### Deduction Breakdown
- AC evidence gaps: 0 (all 4 lines absorbed into #1162 with refinements)
- Lint in scope: 0
- AC quality: 5/5 (no deduction)
- Reviewer evidence: architecture review section thorough (merge task, not code task)
- Full-suite failures in scope: 0

### Confidence: 1.00
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 79967865 | chore | kanban task 1161 | #1161 |