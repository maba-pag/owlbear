---
id: 1442
title: 'P4-05: Probe scan-based task ID allocation and activity events'
status: archived
priority: medium
created: 2026-05-08T19:31:56.603397+00:00
updated: 2026-05-09T01:46:55.362815+00:00
tags:
- phase-4
- scope:kanban
- type:test
- verification-probe
- id-allocation
- activity
- deployment-readiness
parent: 1437
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context
Brief: see parent #1437.

## Scope
In scope: scratch-board probes for create_task ID allocation and activity event emission.
Out of scope: source changes, MCP transport, Cockpit UI, and full-suite proof.

## Acceptance Criteria
1. Test-writer records a scratch-board ID probe with active task filename prefixes 1 and 3 plus archive filename prefixes 2 and 5, then states that the next create_task call must use ID 6 with no config.yml next_id read or write.
2. Test-writer records a concurrent-create probe that exercises the create lock and expects distinct task filename prefixes for competing create_task calls.
3. Test-writer records an activity probe where create_task emits one mutation event containing task_id, action, source, detail, and timestamp fields.
4. Test-writer adds no pytest, vitest, or full-suite execution as functional proof; verification evidence is limited to scratch-board probe notes and activity file inspection.
[[2026-05-08]]


## Architect Refinement

**AC3 expansion:** The event field list must include `task_status_at_start` alongside the five fields already listed, for a total of six fields matching the `ActivityEvent` model. Parent #1437 direction states "emit complete mutation events, including task creation" — the probe must specify the full field set. For a creation event, `task_status_at_start` is the entry status of the newly created task.

**Test depth:** All AC lines are td:0 (probe notes, no test code). Test-writer: SKIP (type:test pass-through). Probes serve as contract specification for #1443.

## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Both probes concern `create_task` behavior changes — scan-based allocation and activity emission are within the same feature area |
| Interface clarity | PASS (after refinement) | AC3 expanded to include `task_status_at_start` for full `ActivityEvent` coverage |
| Dependency correctness | PASS | No dependencies — correct as root probe |
| Module layering | N/A | No source changes |
| TDD compliance | PASS | type:test pass-through; probes serve as contract spec for #1443 RED/GREEN |
| KISS/YAGNI | PASS | Minimal scope — notes-only deliverable |
| Premise challenge | PASS | Probes define contract before #1443 implementation |
| Pattern consistency | PASS | Follows probe pattern established in #1438 |
| Security surface | N/A | No new system boundaries |
| Single domain | PASS | kanban domain only |
| Failure Mode Map | N/A | No codepaths modified |
| Decision-request verification | N/A | No research doc referenced |
| User-action detection | SKIP | Counter-signal C3: type:test tag present |

### Codebase Context
- `allocate_next_id`: `serve/kanban/src/owlbear_kanban/storage.py` L571–581 — currently config-driven via `config.yml` `next_id` under `.next_id.lock`
- `create_task`: `serve/kanban/src/owlbear_kanban/engine.py` L941–1043 — no activity emission currently
- `_emit_event`: `serve/kanban/src/owlbear_kanban/engine.py` L1821–1845 — existing event helper, not called by `create_task`
- `ActivityEvent`: `serve/kanban/src/owlbear_kanban/models.py` L525–535 — 6-field model (timestamp, task_id, action, source, detail, task_status_at_start)
- `_naming.py` L33–35: `make_task_filename({id}, title)` → `{id}-{slug}.md`
- File locking: `_locking.py` L12–32 — `_exclusive_file_lock` via `fcntl.flock`

### Refinement Applied
- AC3: Added `task_status_at_start` to the expected event field list (6 fields total) to match `ActivityEvent` model and parent brief "complete mutation events" directive.

### Challenge Results
- Skipped: all AC lines are td:0 (per Step 2.1 gating rule).

### Test Depth
- All AC lines: td:0 (probe notes, no test code written in this task)
- Max depth: td:0
- Test-writer: SKIP (type:test pass-through)

### Verdict: APPROVE
### Action Taken: Refined AC3 to include full ActivityEvent field set (6 fields). Kept type:test tag and notes-based probe format. Advanced to todo.
[[2026-05-08]]
Architecture review complete. Refined AC3 to include task_status_at_start (6-field ActivityEvent contract per parent brief "complete mutation events" directive). All AC lines td:0 — probe specifications only. Follows established probe pattern from #1438. Advanced to todo.
[[2026-05-08]]
## Test-Writer Notes
- Non-implementation task (tagged type:test) — no tests applicable.
- All AC lines are td:0 (probe specification notes only); architecture review confirmed pass-through.
- Probes serve as contract spec for #1443 RED/GREEN.
- Passing through to builder.
[[2026-05-08]]
## Builder Notes
- Non-implementation task — no code changes needed.
- Verified pass-through condition from `## Test-Writer Notes` (type:test probe-only scope, td:0).
- No source files modified, no tests executed (per AC4 and pass-through workflow).
- Passing through to review.
[[2026-05-08]]
## Review Evidence
### Execution Summary
- quality-runner: not applicable. This task is td:0 and notes-only; there are no code or test-file deliverables to run, and AC4 limits functional proof to probe notes / activity-file inspection.
- code-reader: skipped per td:0 workflow.
- Deliverable surface reviewed: `.owlbear/kanban/tasks/1442-p4-05-probe-scan-based-task-id-allocation-and-activity-events.md`
- Artifact search: no `.owlbear/scratch/1442-*` files found.
- Prior review failures: none (`## Review Evidence` section absent before this review).

### Comparison Pattern
Sibling probe task `1438` contains concrete probe deliverables: `**Type:** type:test pass-through` at line 91, `### AC1` at line 95, `### AC2` at line 123, `### AC3` at line 140, and `### AC Coverage` at line 161 in `.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md`. Task `1442` does not contain an equivalent probe section.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| AC1 | AC requires a scratch-board ID probe at line 33 in `.owlbear/kanban/tasks/1442-p4-05-probe-scan-based-task-id-allocation-and-activity-events.md`. After architecture review, the task body contains only generic `## Test-Writer Notes` / `## Builder Notes` at lines 89-99 and no recorded ID probe. No separate `.owlbear/scratch/1442-*` artifact exists. | FAIL |
| AC2 | AC requires a concurrent-create probe at line 34 in `.owlbear/kanban/tasks/1442-p4-05-probe-scan-based-task-id-allocation-and-activity-events.md`. The task body lines 89-99 contain pass-through prose only; no concurrent-create probe note or separate artifact was found. | FAIL |
| AC3 | AC requires an activity probe at line 35, and the architect refinement at line 42 requires the full 6-field event shape including `task_status_at_start`. The task body contains no recorded activity probe or activity-file inspection. The expected sixth field exists on `ActivityEvent` at lines 525-536 in `serve/kanban/src/owlbear_kanban/models.py`. | FAIL |
| AC4 | AC4 forbids pytest/vitest/full-suite execution and limits proof to probe notes / activity-file inspection. Builder notes line 98 satisfy the “no tests executed” portion, but the required alternative proof surface is missing, so AC4 is not satisfied as a whole. | FAIL |

### Findings
- This is a notes-only deliverable failure, not an implementation failure. The task was incorrectly treated as full pass-through even though AC1-AC3 each require recorded probe artifacts.
- The missing artifacts block the downstream implementation contract: task `1443` depends on `1442` at line 17 and explicitly requires the builder to use the probe artifacts from `1442` at line 39 in `.owlbear/kanban/tasks/1443-p4-06-replace-next-id-config-allocation-and-hard-code-activity-logging.md`.

### Deductions
- Missing AC1 probe artifact: -0.28
- Missing AC2 probe artifact: -0.28
- Missing AC3 probe artifact: -0.28
- AC4 only partially satisfied (absence of executable proof is correct, but required non-executable proof is missing): -0.08

### Verdict
- FAIL
- Confidence: 0.08
- Route: `todo`
- Reason: proof-only gap on a `type:test` probe task; no code defect was reviewed because the required probe notes were never produced.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add the AC1 scratch-board ID probe artifact, explicitly covering active IDs `1` and `3`, archived IDs `2` and `5`, expected next ID `6`, and the "no `config.yml` `next_id` read/write" statement | `.owlbear/kanban/tasks/1442-p4-05-probe-scan-based-task-id-allocation-and-activity-events.md` | AC1 line 33; task body lines 89-99 contain no probe content; no `.owlbear/scratch/1442-*` file exists |
| 2 | test-writer | Add the AC2 concurrent-create probe artifact describing the create-lock exercise and the expected distinct filename prefixes for competing `create_task` calls | `.owlbear/kanban/tasks/1442-p4-05-probe-scan-based-task-id-allocation-and-activity-events.md` | AC2 line 34; task body lines 89-99 contain no probe content |
| 3 | test-writer | Add the AC3 activity probe artifact and include all six `ActivityEvent` fields, including `task_status_at_start`, plus the activity-file inspection evidence | `.owlbear/kanban/tasks/1442-p4-05-probe-scan-based-task-id-allocation-and-activity-events.md`, `serve/kanban/src/owlbear_kanban/models.py` | AC3 line 35; architect refinement line 42; `ActivityEvent` lines 525-536 |
| 4 | test-writer | Add an AC coverage mapping or equivalent per-AC note so downstream task `1443` can consume the probe artifacts as contract evidence | `.owlbear/kanban/tasks/1442-p4-05-probe-scan-based-task-id-allocation-and-activity-events.md`, `.owlbear/kanban/tasks/1443-p4-06-replace-next-id-config-allocation-and-hard-code-activity-logging.md` | `1438` shows the expected probe-note pattern at lines 91-161; `1443` line 39 depends on probe artifacts from `1442` |
[[2026-05-08]]
## Test-Writer Notes

**Type:** type:test pass-through — no test code written. All AC lines are td:0 (probe notes only). Probes define the contract for #1443 implementation.

---

### AC1 — Scratch-Board ID Probe (scan-based allocation)

**Setup:** Create a temporary board directory with:
- Active task files: `1-task-alpha.md`, `3-task-gamma.md` in `tasks/`
- Archive files: `2-task-beta.md`, `5-task-epsilon.md` in `archive/`
- No `config.yml` `next_id` field consulted

**Current behaviour (pre-#1443):** `allocate_next_id(kanban_dir)` opens `.next_id.lock`, reads `config.next_id` from `config.yml`, increments it, and writes it back (`storage.py` L571–581). Task filename prefixes are never scanned.

**Expected post-#1443 behaviour:** `allocate_next_id(kanban_dir)` (or its replacement) scans `tasks/*.md` and `archive/*.md` filename prefixes to find the maximum existing numeric prefix (max of {1, 3} ∪ {2, 5} = 5), then returns 5 + 1 = **6**. No `config.yml` read or write occurs for `next_id`. The `.next_id.lock` file may still be used for mutual exclusion during the scan.

**Observable contract:** `create_task("Probe Task")` on the above board must produce a task file with prefix `6-`. No `config.yml` is read or written to determine the ID.

---

### AC2 — Concurrent-Create Probe (create lock, distinct filename prefixes)

**Setup:** Two `KanbanEngine` instances (or two threads) pointing at the same board directory, both calling `create_task` concurrently. Existing files: `1-*.md` active, `5-*.md` archived (max ID = 5).

**Lock mechanism:** The scan-based allocator must acquire an exclusive file lock (e.g. `.next_id.lock` via `fcntl.flock(LOCK_EX)` — same lock file as today, already wired in `_locking.py` L12–32) before scanning filenames and writing the new task file. The scan and the write must both occur inside the same lock scope.

**Expected post-#1443 race sequence:**
- Caller A acquires lock → scans max = 5 → allocates 6 → writes `6-*.md` → releases lock
- Caller B acquires lock → scans max = 6 (file now on disk) → allocates 7 → writes `7-*.md` → releases lock

**Result:** Two task files exist with distinct numeric prefixes 6 and 7; no ID is reused or skipped.

**Filename generation reference:** `_naming.py` `make_task_filename(id, title)` → `{id}-{slug}.md`.

---

### AC3 — Activity Probe (create_task event emission, 6-field ActivityEvent)

**Current behaviour (pre-#1443):** `create_task` in `engine.py` L941–1043 never calls `_emit_event`. No `ActivityEvent` is appended to `activity.jsonl` for task creation.

**Expected post-#1443 behaviour:** `create_task` calls `self._emit_event(...)` immediately after the task file is written successfully. One `ActivityEvent` is appended to `activity.jsonl` containing all 6 fields of the `ActivityEvent` model (`models.py` L525–535):

| Field | Expected value for a creation event |
|-------|--------------------------------------|
| `timestamp` | ISO-8601 UTC string of the creation instant |
| `task_id` | Integer ID of the newly created task |
| `action` | `"create"` |
| `source` | Caller-supplied label (default: `"engine"`) |
| `detail` | Descriptive string (e.g. task title or `"task created"`) |
| `task_status_at_start` | Entry status of the newly created task (e.g. `"research"`) |

**Activity-file inspection evidence:**
- `activity.jsonl` exists at `kanban_dir / "activity.jsonl"` when `activity_log=True` on the engine.
- After `create_task("Probe Task")`, the last line of `activity.jsonl` must be a valid JSON object with all 6 keys present and non-null (except `task_status_at_start` which is `str | None` in the model — for a creation event it equals the entry status string, not null).
- `task_status_at_start` must equal the task's effective entry status: the `status` argument when provided, otherwise `config.pipeline.entry_status` (default `"research"`).

---

### AC Coverage

| AC | Coverage |
|----|----------|
| AC1 — scratch-board ID probe (active prefixes 1 & 3, archive prefixes 2 & 5, next ID 6, no config.yml next_id R/W) | Setup, current vs. expected behaviour, and observable contract documented above |
| AC2 — concurrent-create probe (create lock, distinct filename prefixes for competing create_task calls) | Lock mechanism, race sequence, and expected distinct-prefix outcome documented above |
| AC3 — activity probe (6-field ActivityEvent including task_status_at_start) | All 6 fields enumerated with expected creation-event values; activity-file inspection criteria stated; current absence of emission confirmed at engine.py L941–1043 |
| AC4 — no pytest/vitest/full-suite execution | Confirmed — no test code written, no test file created |

**Total:** 0 test files, 0 test functions. Pass-through — probes serve as contract specification for #1443 (RED/GREEN phases).
[[2026-05-09]]
## Builder Notes
- Non-implementation task — no code changes needed.
- Verified task body contains probe deliverables for AC1-AC4 under `## Test-Writer Notes` (td:0, type:test pass-through contract for #1443).
- Tests/lint not executed by builder per AC4 and pass-through workflow.
- Passing through to review.
[[2026-05-09]]
## Review Evidence
### Test Results
- Not applicable. This is a td:0 notes-only probe task. No task-local test files were found for tests/**/*1442*. AC4 limits proof to the probe notes and activity-file inspection criteria recorded in the task body.
- quality-runner skipped. There are no source or test artifacts to execute for this task type.

### Lint: not applicable
- No source or test files were changed for this task. The live deliverable is the task markdown artifact itself.

### Coverage: not applicable
- td:0 probe notes only; no touched runtime module requires a coverage gate in this review.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
- Not applicable. No TestFromAC classes or task-local tests exist for this td:0 probe task; the required proof surface is the probe-note artifact itself.

#### Security Review
- No issues. No source, dependency, or runtime-surface changes are in scope.

#### Test Integrity
- Not applicable. No task-local test files exist.

#### Test Quality
- Not applicable. This task intentionally produces probe notes rather than executable tests.

#### Data Safety
- No issues. No persistence or concurrency code changed in this task.

#### Implementation-Aware Gaps
- No implementation gap in scope for this task. The review target is the probe artifact at .owlbear/kanban/tasks/1442-p4-05-probe-scan-based-task-id-allocation-and-activity-events.md, and it now records each required condition.
- The current-state anchors in the probe notes match the live repo: storage.allocate_next_id still reads and writes config.next_id at serve/kanban/src/owlbear_kanban/storage.py:571-580; KanbanEngine.create_task still allocates via storage.allocate_next_id and does not emit a create activity event within serve/kanban/src/owlbear_kanban/engine.py:942-1045; ActivityEvent includes task_status_at_start at serve/kanban/src/owlbear_kanban/models.py:525-536; _exclusive_file_lock uses LOCK_EX at serve/kanban/src/owlbear_kanban/_locking.py:13-33; make_task_filename returns {id}-{slug}.md at serve/kanban/src/owlbear_kanban/_naming.py:33-35.

#### Builder Process Quality
| Metric | Value |
|---|---|
| Builder Notes sections | 2 |
| Approach variation | N/A |
| Assessment | CLEAN |

Rationale: the earlier review fail was a missing-probe artifact issue. The retry added the required notes under Test-Writer Notes; there is no repeated builder-owned implementation loop.

### Pass 2 — INFORMATIONAL
- One earlier review section remains in the task history at .owlbear/kanban/tasks/1442-p4-05-probe-scan-based-task-id-allocation-and-activity-events.md:101, but the retry closes that gap with concrete probe sections at lines 150-212.
- Downstream task 1443 still depends on this artifact at .owlbear/kanban/tasks/1443-p4-06-replace-next-id-config-allocation-and-hard-code-activity-logging.md:17-18 and explicitly consumes the probe artifacts at line 39.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1 | AC text at .owlbear/kanban/tasks/1442-p4-05-probe-scan-based-task-id-allocation-and-activity-events.md:33. Probe section at lines 150-161 now covers active prefixes 1 and 3, archive prefixes 2 and 5, next ID 6, and no config.yml next_id read or write. The current-behavior reference matches live code at serve/kanban/src/owlbear_kanban/storage.py:571-580. | N/A (td:0 probe note) | PASS |
| AC2 | AC text at .owlbear/kanban/tasks/1442-p4-05-probe-scan-based-task-id-allocation-and-activity-events.md:34. Probe section at lines 165-177 defines the exclusive-lock mechanism, serialized race sequence, and distinct prefixes 6 and 7. The cited lock and filename behaviors match serve/kanban/src/owlbear_kanban/_locking.py:13-33 and serve/kanban/src/owlbear_kanban/_naming.py:33-35. | N/A (td:0 probe note) | PASS |
| AC3 | AC text at .owlbear/kanban/tasks/1442-p4-05-probe-scan-based-task-id-allocation-and-activity-events.md:35 plus architect refinement at line 42. Probe section at lines 181-199 defines one create event with all six ActivityEvent fields and requires task_status_at_start to equal the effective entry status. That matches the parent approved direction at .owlbear/kanban/archive/1437-simplify-kanban-topology-for-deployment-readiness.md:35, the live ActivityEvent model at serve/kanban/src/owlbear_kanban/models.py:525-536, and the current absence of create-event emission inside serve/kanban/src/owlbear_kanban/engine.py:942-1045. | N/A (td:0 probe note) | PASS |
| AC4 | AC text at .owlbear/kanban/tasks/1442-p4-05-probe-scan-based-task-id-allocation-and-activity-events.md:36. The AC coverage row at line 210, the total row at line 212, the builder note at line 217, and the absence of task-local tests together satisfy the no-pytest/no-vitest/no-full-suite contract. | N/A (td:0 probe note) | PASS |

### Confidence: 0.97
### Verdict: PASS
[[2026-05-09]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | No behavior, API, CLI, config, or package structure changes; probe-notes-only deliverable |
| 2 | Module docstrings | No | N/A | No Python modules created or modified |
| 3 | External attribution | No | N/A | No external patterns or sources used |
| 4 | Research doc | No | N/A | No research doc produced for this task |
| 5 | Diagram maintenance (describes match) | No | N/A | No source files changed; doc-index shows no diagram describes-match |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested |
| 7 | Deletion detection | No | N/A | No files deleted |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `.owlbear/kanban/tasks/1442-p4-05-probe-scan-based-task-id-allocation-and-activity-events.md` | OUT (kanban task artifact, not IN-scope doc) | N/A |
| `serve/kanban/src/owlbear_kanban/storage.py` | OUT (referenced only, not modified) | N/A |
| `serve/kanban/src/owlbear_kanban/engine.py` | OUT (referenced only, not modified) | N/A |
| `serve/kanban/src/owlbear_kanban/models.py` | OUT (referenced only, not modified) | N/A |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/1442-*` files existed)
[[2026-05-09]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 — scratch-board ID probe (active 1&3, archive 2&5, next=6, no config.yml) | Probe section in task body under `### AC1` covers setup, current vs expected behavior, and observable contract. Reviewer verified at lines 150-161. Spot-checked: matches AC requirements. | PASS |
| AC2 — concurrent-create probe (create lock, distinct prefixes) | Probe section under `### AC2` defines lock mechanism, race sequence, distinct prefixes 6 and 7. Reviewer verified at lines 165-177. | PASS |
| AC3 — activity probe (6-field ActivityEvent incl. task_status_at_start) | Probe section under `### AC3` tabulates all 6 fields with expected creation-event values. Spot-checked against live `ActivityEvent` model at `serve/kanban/src/owlbear_kanban/models.py:525-536` — all 6 fields present and match. Reviewer verified at lines 181-199. | PASS |
| AC4 — no pytest/vitest/full-suite execution | AC coverage row at line 210 and builder notes at line 217 confirm no test code or execution. No task-local test files found. | PASS |

### Test Results
- pytest: 541 passed, 75 failed (all pre-existing — task changed zero source/test files; no cross-task regression possible)
- ruff: 12 violations in serve/knowledge/ and serve/tools/ (not touched by this task)

### Architect Quality: 5/5
AC lines are specific, complete, and verifiable. Each probe requirement names exact file prefixes, expected IDs, field sets, and exclusion criteria. Architect refinement caught the missing 6th field (task_status_at_start) for AC3 — proactive quality improvement.

### Deduction Breakdown
- Start: 1.00
- AC lines with no evidence: none (all 4 PASS) → 0
- Lint violations: background debt, not task-scoped → 0
- AC quality ≤ 3: no (5/5) → 0
- Missing reviewer evidence: no (present, detailed, PASS at 0.97) → 0
- Full-suite failures in task scope: none (td:0, zero files changed) → 0

### Confidence: 0.98
### Action: archive