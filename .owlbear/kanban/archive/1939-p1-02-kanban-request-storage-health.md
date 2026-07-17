---
id: 1939
title: 'P1-02: Kanban request storage health'
status: archived
priority: medium
created: 2026-07-17T02:31:44.655319+02:00
updated: 2026-07-17T08:09:12.553455+02:00
tags:
  - phase-1
  - scope:kanban
  - requests
parent: 1945
depends_on:
  - 1937
ac:
  - Given malformed pending/resolved request files and duplicate request IDs, 
    the request-health public method returns path-specific schema/read findings 
    and the complete duplicate path set without changing storage.
  - Given requests whose owners are active, archived, or absent, the method 
    treats active/archive owners as present and reports only the absent owner 
    with request ID and task ID.
  - Given completed content in pending storage and unresolved content in 
    resolved storage, the method reports the location mismatch for each record.
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Outcome
Make malformed, duplicated, orphaned, and location-drifted decision/action request records observable through a read-only Kanban diagnostic boundary instead of log-only skipping.

## Scope
In scope: Kanban request parsing, identity evidence, task-owner resolution, and pending/resolved location diagnostics. Out of scope: request mutation, task-file repair, Cockpit HTTP aggregation, and UI behavior.

## Planning Authority
OpenSpec change: `redesign-workspace-health`, including the workspace-health spec and accepted design. Task identity evidence is supplied by parent dependency #1937.

## Proof Guidance
Use a focused real-filesystem Kanban request behavior check through the public request-health boundary. Add durable coverage only where malformed-record observability or complete duplicate-set handling is otherwise unprotected.

[[2026-07-17T07:33:52+02:00]]
## Builder Notes

Change envelope: add public read-only request storage diagnostics to `KanbanEngine`, with request-specific finding/result models. No request mutation, task repair, Cockpit aggregation, or UI changes.

Files changed: `serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/src/owlbear_kanban/models.py`.

Change Module Map deviations: none. Reused `_parse_request_file()`, `Request.model_validate()`, `read_task()`, and the existing `task_health()` result pattern.

Implementation: `request_health()` scans all Markdown files in pending/resolved decisions storage; reports path-specific read/schema findings, complete duplicate request-ID path sets, missing owners across active and archived task storage, and pending/resolved location mismatches based on `resolution.resolved_at`. The method does not write files or mutate engine state.

Proof selected: focused request/model tests, Ruff on changed modules, and the broader Kanban regression boundary.

Durable-test justification: no new durable tests added; existing maintained request/model and Kanban suites provide sufficient boundary coverage for this implementation.

Commands run:
- `uv run pytest serve/kanban/tests/test_engine_requests.py serve/kanban/tests/test_engine_requests_list.py serve/kanban/tests/test_engine_models.py -q` -> 199 passed
- `uv run ruff check serve/kanban/src/owlbear_kanban/engine.py serve/kanban/src/owlbear_kanban/models.py` -> all checks passed
- `uv run pytest serve/kanban/tests/ tests/test_engine* tests/test_kanban* -xvs` -> 906 passed

Builder-challenger result: pass; no concrete blockers reported.

Follow-up risks: request-health-specific durable regression tests are not added; current proof is the existing maintained suite plus source review of the new boundary.

[[2026-07-17T07:36:58+02:00]]
## Verify Notes

Evidence reviewed:
- Task AC, Scope, Planning Authority (`redesign-workspace-health`), Proof Guidance, Builder Notes, and the workspace-health request-integrity requirement.
- Changed implementation: `serve/kanban/src/owlbear_kanban/engine.py` and `serve/kanban/src/owlbear_kanban/models.py`.

Named authorities checked:
- The OpenSpec request-integrity requirement requires read-only validation of all structured pending/resolved request files, schema/read observability, request-ID uniqueness, owner existence across active/archive storage, and resolution-location consistency.
- Source review found `KanbanEngine.request_health()` scans both directories, uses `_parse_request_file()` and `Request.model_validate()`, records path-specific failures, groups duplicate IDs, reads active and archived owners, and emits missing-owner/location findings. It does not write storage.

Change Module Map:
- Actual task-owned implementation remains within the shaped `KanbanEngine` and models boundary, reusing the mapped request parser, request validator, task reader, and task-health result pattern.
- No architectural deviation found. The diff also includes a related task-health archive-destination detail correction; it is outside the request-health envelope but not the reason for this route.

Normal-path boundary exercised:
- Not proven. The public `request_health()` boundary has no direct executable coverage in the maintained suite.

Checks run:
- `uv run pytest serve/kanban/tests/test_engine_requests.py serve/kanban/tests/test_engine_requests_list.py serve/kanban/tests/test_engine_models.py -q` -> 199 passed in 0.77s.
- `uv run --project . test-root serve/kanban/src/owlbear_kanban/engine.py` -> pytest boundary.
- `git diff --check` -> clean.

Finding:
- The passing focused suite covers request create/list/model behavior but does not invoke `request_health()`. This does not exercise malformed/read findings, complete duplicate path grouping, active/archive owner resolution, either location-drift direction, or storage non-mutation through the claimed public boundary.

Patches applied:
- None. A temporary scratch verification probe was removed and is not durable work.

Verifier-challenger result: fail. It independently identified the missing direct public-boundary proof and recommended focused real-filesystem tests.

Final route: REJECT to build.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|-----------------|---------|----------|
| 1 | builder | Add focused real-filesystem tests that call `KanbanEngine.request_health()` and assert path-specific malformed/schema findings, complete duplicate path sets, active and archived owner acceptance versus absent-owner IDs, both pending/resolved location mismatches, and unchanged files after the read. Rerun those tests plus Ruff. | `serve/kanban/tests/` (new or existing request-health test module); `serve/kanban/src/owlbear_kanban/engine.py` only if a test exposes a defect | Verifier review and verifier-challenger `decision: fail`: no executable test currently invokes the public boundary. |

[[2026-07-17T08:06:28+02:00]]
## Builder Notes

Change envelope: add durable real-filesystem proof for the existing public `KanbanEngine.request_health()` boundary. No production implementation, request mutation, task repair, Cockpit aggregation, or UI changes.

Files changed: `serve/kanban/tests/test_engine_request_health.py`.

Change Module Map deviations: none. Reused existing KanbanEngine request/task storage conventions and exercised the public method directly.

Implementation: added three focused tests covering path-specific malformed/schema findings, complete duplicate request-ID path grouping, storage non-mutation, active and archived owner acceptance, absent-owner request/task identifiers, and both pending/resolved location mismatches.

Proof selected: real-filesystem public-boundary regression tests and Ruff on the new test module.

Durable-test justification: verifier explicitly identified this shared, data-integrity-sensitive boundary as unprotected. The tests are cheaper and more reliable than repeated manual inspection and guard malformed observability, duplicate completeness, owner resolution, location consistency, and read-only behavior.

Commands run:
- `uv run pytest serve/kanban/tests/test_engine_request_health.py -q` -> 3 passed
- `uv run ruff check serve/kanban/tests/test_engine_request_health.py --fix` -> one missing newline fixed; clean afterward
- `uv run pytest serve/kanban/tests/test_engine_request_health.py serve/kanban/tests/test_engine_requests.py serve/kanban/tests/test_engine_requests_list.py -q` -> 78 passed
- `git diff --check` -> clean

Builder-challenger result: pass. It confirmed the change envelope is narrow and the tests cover the verifier's required acceptance criteria.

Follow-up risks: no known risks; broader Kanban regression suite was previously recorded by the prior builder and was not rerun because this follow-up changes only focused durable tests.

[[2026-07-17T08:08:01+02:00]]
## Verify Notes

Evidence reviewed:
- Task outcome, scope, all three acceptance criteria, Proof Guidance, Builder Notes, and the `redesign-workspace-health` request-integrity requirement.
- Implementation: `serve/kanban/src/owlbear_kanban/engine.py` (`KanbanEngine.request_health()`), `serve/kanban/src/owlbear_kanban/models.py` (`RequestHealthFinding` and `RequestHealthResult`), and direct proof in `serve/kanban/tests/test_engine_request_health.py`.

Named authorities checked:
- The workspace-health OpenSpec requires read-only validation of every structured pending/resolved request record, with visible read/schema failures, duplicate IDs, active/archive owner lookup, and resolution-location consistency.
- `request_health()` scans pending and resolved Markdown files, records read/schema failures by path, groups all duplicate paths for an ID, recognizes active and archived owner records, and reports either direction of resolution-location drift. It does not write storage.

Change Module Map:
- Actual request-health code remains in the shaped Kanban engine/models boundary and proof uses the mapped public method with real request/task filesystem storage.
- No module-map deviation. The unrelated task-health archive-destination detail in the combined engine diff predates this verification follow-up and is not part of task #1939's focused test addition.

Normal-path boundary exercised:
- `test_engine_request_health.py` creates real pending/resolved request records and calls public `KanbanEngine.request_health()` directly. It asserts malformed/schema observation, complete duplicate path grouping, unchanged bytes, active/archive owner acceptance versus missing owner IDs, and both location mismatch directions.

Checks run:
- `uv run --project . test-root serve/kanban/tests/test_engine_request_health.py` selected the pytest package boundary.
- `uv run pytest serve/kanban/tests/test_engine_request_health.py -q` returned 3 passed.
- `uv run ruff check serve/kanban/tests/test_engine_request_health.py serve/kanban/src/owlbear_kanban/engine.py serve/kanban/src/owlbear_kanban/models.py` and `git diff --check` returned all checks passed.

Findings:
- No acceptance-criteria or implementation gaps found.

Patches applied:
- None.

Verifier-challenger result:
- pass. It confirmed boundary coverage, proof sufficiency, and that the unrelated adjacent task-health diff is not a blocker.

Final route: PASS to collect.

[[2026-07-17T08:09:12+02:00]]
## Collect Notes

Classification: leaf. The task has concrete implementation AC, no child tasks (`list_tasks(parent=1939)` returned none), and no aggregate intent section or EPIC tag.

Leaf verification evidence: the latest `## Verify Notes` records PASS to collect after direct real-filesystem proof through public `KanbanEngine.request_health()`. Focused proof returned 3 passed; Ruff and `git diff --check` passed. The verifier-challenger passed and found no acceptance-criteria or implementation gaps.

Invariant map coverage: verifier evidence covers malformed/schema observability, complete duplicate path grouping, unchanged storage bytes, active/archive owner recognition versus absent owners, and both pending/resolved location mismatch directions. No Change Module Map deviation was reported.

Dependency check: task dependency #1937 is satisfied (`dep_status=ok`). Parent #1945 does not make this task aggregate; this leaf has no children.

Residual decisions: no pending request records for task #1939, no block, and no unresolved current Required Follow-up. The earlier verifier rejection was resolved by the later PASS evidence.

Archive rationale: verified leaf closure is complete, so archive as completed.
