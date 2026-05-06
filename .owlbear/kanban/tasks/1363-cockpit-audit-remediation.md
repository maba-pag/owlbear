---
id: 1363
title: Cockpit audit remediation
status: in-progress
priority: critical
created: 2026-05-06T00:58:14.547083+00:00
updated: 2026-05-06T14:42:18.182083+00:00
tags:
- cockpit
- audit-remediation
- type:epic
- scope:cockpit
- parent
- no-dispatch
parent:
depends_on: []
blocked: true
block_reason: live parent container — not dispatchable until all children done
claimed_at:
archival_reason:
archival_refs: []
---

## Epic Purpose
Parent grouping for the approved Cockpit audit remediation follow-up across backend, frontend, design-system foundation, tests, docs, and delivery.

## Scope
- In scope: approved Cockpit audit follow-up tasks created from the read-only audit, starting with the foundation/backend bundle.
- Out of scope for this epic task body: implementation details, dashboard redesign, and duplicate cache/SSE invalidation work already completed by #1346.

## Planning Notes
- First bundle is decomposed into TDD-paired child tasks under this parent.
- Child tasks are placed in backlog so the normal pipeline can architecture-review and dispatch them.

## Phase 1 Foundation/Backend Bundle
Tasks created under this epic:
- #1364 P1-01: Test Cockpit PDS v4 build compatibility. No dependencies.
- #1365 P1-02: Fix Cockpit PDS v4 build compatibility. Depends on #1364.
- #1366 P1-03: Test Cockpit PDS runtime loading under CSP. Depends on #1365.
- #1367 P1-04: Fix Cockpit PDS runtime loading under CSP. Depends on #1366.
- #1368 P1-05: Test kanban corruption scanner encoding hardening. No dependencies.
- #1369 P1-06: Harden kanban corruption scanner encoding handling. Depends on #1368.
- #1370 P1-07: Test Cockpit backend error envelope and guidance contract. No dependencies.
- #1371 P1-08: Implement Cockpit backend error envelope and guidance contract. Depends on #1370.
- #1372 P1-09: Test Cockpit health false-OK prevention. Depends on #1367, #1369, and #1371.
- #1373 P1-10: Implement Cockpit health false-OK prevention. Depends on #1372.
- #1374 P1-11: Test Cockpit frontend error-contract adoption. Depends on #1367, #1371, and #1373.
- #1375 P1-12: Implement Cockpit frontend error-contract adoption. Depends on #1374.

Dependency layers:
- Layer 1: #1364, #1368, #1370.
- Layer 2: #1365, #1369, #1371.
- Layer 3: #1366.
- Layer 4: #1367.
- Layer 5: #1372.
- Layer 6: #1373.
- Layer 7: #1374.
- Layer 8: #1375.

Planning constraints:
- All child tasks are in backlog, critical priority, tagged cockpit and audit-remediation.
- Every implementation task depends on its corresponding test task.
- Cache/SSE invalidation work from #1346 is intentionally excluded.

[[2026-05-06]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Pure epic container — one responsibility: group child tasks |
| Interface clarity | N/A | No implementation interface |
| Dependency correctness | PASS | No deps on epic itself; child deps are well-structured in layers |
| Module layering | N/A | No code |
| TDD compliance | N/A | No testable code |
| KISS/YAGNI | PASS | Minimal epic body, clear scope boundaries |
| Premise challenge | PASS | Grouping audit remediation tasks under a parent is appropriate |
| Pattern consistency | PASS | Follows epic pattern for multi-task bundles |
| Security surface | N/A | No code |
| Single domain | PASS | Cockpit domain only |

### Challenge Results
- Challenger: SKIPPED — all td:0 (epic container, no AC lines)
- Architect response: N/A

### Test Depth
- Max depth: 0
- Test-writer: SKIP

### Verdict: APPROVE
### Action Taken: Added `docs` pass-through tag. Epic container approved to `todo` — child tasks #1364–#1375 will be reviewed individually.
[[2026-05-06]]
## Test-Writer Notes
- Non-implementation task (tagged docs, type:epic) — no tests applicable.
- Epic container grouping child tasks #1364–#1375; no testable Python interfaces.
- Passing through to builder.
[[2026-05-06]]
## Builder Notes
- Non-implementation task (epic/docs pass-through); no source or test file changes required.
- Verified test-writer marked this as non-impl pass-through for child-task grouping only.
- Tests: not run (no testable implementation scope in this task).
- Coverage: N/A.
- ruff: N/A.
- Approach: pass-through advancement from in-progress to review per w-tdd-green Step 0a.
[[2026-05-06]]
## Review Evidence
### Test Results
- Not applicable. Task #1363 is a td:0 epic/container with no task-owned source or test artifact.
- quality-runner was not used. For td:0 container tasks in this repo, scoped quality-runner has no meaningful scope because there are no test paths or coverage targets; evidence comes from direct task-file and board inspection.

### Lint Results
- Not applicable. No source or test files are owned by this task.

### Coverage
- Not applicable. No code paths or modules are in scope.

### AC Compliance
| AC / Contract Line | Evidence | Status |
|---|---|---|
| Parent groups child tasks #1364-#1375 under one epic container | Task #1363 body lists all 12 child tasks and dependency layers; child tasks #1364, #1368, and #1370 each show `parent: 1363` | PASS |
| Parent is a planning/container artifact, not an independently reviewable implementation deliverable | Task #1363 Architecture Review says "Pure epic container" and says child tasks will be reviewed individually; parent-container precedent in task #1316 keeps the parent in-progress as container until children finish | FAIL |
| Embedded planning state is still accurate enough for review -> docs advancement | Task #1363 says "All child tasks are in backlog," but child task files #1364, #1368, and #1370 are already `status: review` | FAIL |

### Findings
1. Routing defect: a decomposed parent container with no task-owned code or documentation change was advanced through builder into review. The repo already has a contrary parent-container pattern in #1316, where the parent remains in-progress as a container while subtasks advance independently.
2. Stale parent-state text: the parent still declares all children are in backlog, but at least three child tasks have already advanced to review. That makes the parent unsuitable for review -> docs advancement as a stable artifact.

### Deductions
- -0.15: parent-container routing does not match the established decomposed-parent pattern.
- -0.05: parent planning text is already stale relative to live board state.
- -0.02: td:0 artifact review relied on direct kanban inspection because quality-runner has no usable scope for a pure container task.

### Verdict
- FAIL. Confidence: 0.78.
- Action: reject to backlog for architecture-level rerouting and parent-task contract cleanup.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Reclassify task #1363 as a live parent container or rewrite its explicit completion contract so it does not traverse review/docs as a finished deliverable while child tasks remain active | .owlbear/kanban/tasks/1363-cockpit-audit-remediation.md | Task #1363 AR says "Pure epic container"; task #1316 precedent keeps the parent in-progress as container |
| 2 | architect | Update or remove stale stateful planning text that claims all child tasks are in backlog | .owlbear/kanban/tasks/1363-cockpit-audit-remediation.md | Parent text says all children backlog; child task files #1364, #1368, and #1370 are status review |

### Reflection
- td:0 parent-container reviews need artifact verification, not code-centric assumptions.
- Parent-container precedent in historical tasks is a useful routing guardrail when a new epic is pushed through the normal non-impl path.
- Embedded live-status claims in parent tasks go stale quickly once children start moving; they should be written as creation-time facts or avoided.
[[2026-05-06]]


## Completion Contract

This task is a **live parent container** following the #1316 precedent. It does NOT traverse the pipeline as a standalone deliverable.

- **Container routing:** This task stays `in-progress` while child tasks #1364–#1375 advance independently through the pipeline. Test-writer and builder: pass-through with NO advancement beyond `in-progress`.
- **Completion trigger:** This task advances to `review` only after ALL child tasks (#1364–#1375) have reached `done`.
- **Stale planning text note:** The "Planning constraints" section above is a creation-time snapshot. Child task statuses are live on the board and may differ from the snapshot text. Do not treat embedded status claims as current state.

## Acceptance Criteria

- [ ] All 12 child tasks (#1364–#1375) are parented to this task (td:0)
- [ ] Epic remains in-progress as live container until all children reach `done` (td:0)
- [ ] Epic advances to `review` only after last child reaches `done` (td:0)

[[2026-05-06]]
## Architecture Review (Pass 2 — Reviewer Remediation)

### Context
Reviewer rejected this task from `review` back to `backlog` with two findings:
1. Parent container was incorrectly routed through the full pipeline as a non-impl pass-through (builder advanced it to `review` while children were still active).
2. Stale embedded text claimed "all child tasks are in backlog" when children had already advanced.

Precedent: #1316 (Knowledge Engine Activation) — parent container stays `in-progress` while 19 children advance independently.

### Remediation Actions
1. **Removed `docs` tag** — this tag triggered non-impl pass-through routing, which caused builder to advance the task. Incorrect for a live container.
2. **Added `parent` tag** — matches #1316 pattern. Signals container semantics to downstream agents.
3. **Added Completion Contract section** — explicit routing instructions: stay in-progress, advance only when all children done.
4. **Added AC section** — 3 verifiable criteria (all td:0) establishing the container contract.
5. **Added stale-text note** — creation-time snapshot disclaimer so downstream agents don't treat embedded status claims as live state.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Pure parent container |
| Dependency correctness | PASS | No deps on epic itself; child deps unchanged |
| Pattern consistency | PASS | Now follows #1316 parent-container precedent |
| Reviewer finding 1 (routing) | FIXED | `docs` tag removed, `parent` tag added, completion contract written |
| Reviewer finding 2 (stale text) | FIXED | Snapshot disclaimer added; AC avoids live-status assertions |

### Challenge Results
- Challenger: SKIPPED — all td:0, parent container, no design decisions

### Test Depth
- Max depth: 0
- Test-writer: SKIP (pass-through, no status advancement)

### Verdict: APPROVE
### Action Taken: Remediated reviewer findings. Parent container approved to `todo` — stays in-progress as live container per completion contract. Child tasks #1364–#1375 reviewed individually.
[[2026-05-06]]
Remediated reviewer findings from Pass 1. Removed `docs` tag (caused incorrect non-impl pass-through routing), added `parent` tag, wrote explicit Completion Contract and AC following #1316 parent-container precedent. Parent stays in-progress as live container; advances to review only after all 12 children (#1364–#1375) reach done.
[[2026-05-06]]
## Test-Writer Notes
- **Pass-through — non-implementation container task.**
- Test file: none created.
- AC lines: all `td:0` (container routing, child completion trigger, parent status tracking) — no testable Python interfaces.
- Completion Contract explicitly states: "Test-writer and builder: pass-through with NO advancement beyond `in-progress`."
- This task stays `in-progress` as a live parent container while child tasks #1364–#1375 advance independently.
- No tests written. No quality-runner run needed.
[[2026-05-06]]
## Builder Notes
- Pass-through on non-implementation live parent container task; no source or test files changed.
## Hygiene Note
Duplicate builder pass-through notes (20+ identical entries) trimmed on 2026-05-06. Task stays in-progress as live parent container per Completion Contract.
