---
id: 1937
title: 'P1-01: Kanban task and graph health evidence'
status: build
priority: high
created: 2026-07-17T02:31:31.385612+02:00
updated: 2026-07-17T05:22:11.222898+02:00
tags:
  - phase-1
  - scope:kanban
  - integrity
parent: 1945
depends_on: []
ac:
  - Given active/archive fixtures containing one readable task with two 
    independently detectable persisted-field defects and one unreadable task, 
    the Kanban task-health public method returns both readable-file findings 
    plus the read failure and leaves file paths, bytes, and mtimes unchanged.
  - Given same-ID fixtures within tasks, within archive, across both 
    directories, and a heterogeneous three-record set, the public method returns
    the complete path set and a repairable or unresolved classification for each
    ID without pairwise mutation.
  - Given missing parent/dependency/archival targets, dependency self-reference,
    a multi-task dependency cycle, and a well-formed task whose persisted state 
    is archived but whose record exists only in active storage with no archive 
    destination conflict, the public method returns findings naming the owner 
    and field or cycle involved; the location finding names the task ID and 
    active/archive locations; storage remains unchanged.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
Provide read-only normalized task evidence for persisted-file defects, complete duplicate-ID sets, location drift, broken references, self-reference, and dependency cycles.

## Scope
In scope: Kanban task-health models, scanner behavior, and the public engine health method. Out of scope: request diagnostics, storage mutation, claim maintenance, and Cockpit HTTP/UI behavior.

## Planning Authority
OpenSpec change: `redesign-workspace-health`, including the workspace-health spec and accepted design.

## Proof Guidance
Use a focused real-filesystem Kanban behavior check plus a downstream-impact scan. Because this is shared integrity behavior, retain or add durable regression coverage only where it protects the multi-finding, complete-set, or graph-analysis boundary.

[[2026-07-17T05:20:36+02:00]]
## Builder Notes
- Change envelope: read-only Kanban task-health evidence in `KanbanEngine.task_health()`; duplicate-set classification and dependency-cycle diagnostics only. No storage mutation, request diagnostics, claim maintenance, Cockpit behavior, or repair implementation changed.
- Files changed: `serve/kanban/src/owlbear_kanban/engine.py`; `serve/kanban/tests/test_engine_task_health.py`.
- Change Module Map: stayed within the shaped owners (`engine.py` public health method and Kanban tests); no deviation.
- Implementation: duplicate findings retain the complete path set and classify repairability from canonical frontmatter plus normalized body, including identical archived cross-directory records; cycle findings identify owner path, `depends_on`, and the concrete cycle.
- Proof selected: `uv run pytest serve/kanban/tests/test_corruption.py serve/kanban/tests/test_engine_task_health.py -q` -> 77 passed. Editor diagnostics report no errors for touched files; `git diff --check` is clean. Regression coverage snapshots bytes and mtimes to verify health scanning is non-mutating.
- Durable-test justification: shared integrity behavior is easy to regress and difficult to notice manually; the test protects complete duplicate-set classification, cycle evidence, and filesystem immutability at the public engine boundary.
- Builder-challenger: pass; no concrete blockers. It reviewed same-directory, heterogeneous 3+ records, cross-directory archived duplicates, missing references, self-reference, cycles, unreadable findings, and mutation proof.
- Follow-up risk: no dedicated assertion for every archive-location drift variant beyond the existing archived-in-active-storage finding; outside this task's minimal scope.

[[2026-07-17T05:22:11+02:00]]
## Verify Notes
- Evidence reviewed: builder commit `dda9e7e92` changes only the shaped owners: `serve/kanban/src/owlbear_kanban/engine.py` and `serve/kanban/tests/test_engine_task_health.py`; no Change Module Map deviation or interface expansion was found.
- Named authority checked: OpenSpec `redesign-workspace-health` workspace-health spec requires complete, read-only persisted-file evidence, complete duplicate-ID sets, location drift, broken references, self-reference, and every cycle participant. The public `KanbanEngine.task_health()` boundary is exercised directly with temporary filesystem boards; lower layers only parse persisted files.
- Normal-path proof: `uv run pytest serve/kanban/tests/test_corruption.py serve/kanban/tests/test_engine_task_health.py -q` passed, 77 tests. The durable test covers complete duplicate-set classification, cycle owner context, archived cross-directory duplicates, and byte/mtime immutability.
- Additional checks: `git show --check dda9e7e92` and `git diff --check` are clean. Editor diagnostics have no errors for the touched files.
- Finding: `uv run ruff check serve/kanban/src/owlbear_kanban/engine.py serve/kanban/tests/test_engine_task_health.py` fails with 12 violations: C901, PLR0912, and PLR0915 on `task_health`; six E501 finding constructors; PERF401; RUF005; and W292 (missing final newline in the new test). The formatter did not run because the preceding lint step failed.
- Patches applied: none. This requires restructuring the builder-owned method and test formatting, beyond a verifier local patch-pass.
- Verifier-challenger: not invoked because this is a REJECT verdict; it is required only before PASS.
- Final route: REJECT to build.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Refactor `task_health()` into locally scoped helpers or otherwise satisfy the configured Ruff complexity, branch, statement, line-length, performance, and tuple-construction rules; add the test file's final newline; rerun focused pytest and Ruff check/format. | `serve/kanban/src/owlbear_kanban/engine.py`; `serve/kanban/tests/test_engine_task_health.py` | Ruff reported 12 violations during verification. |
