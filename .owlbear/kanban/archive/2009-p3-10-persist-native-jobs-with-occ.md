---
id: 2009
title: 'P3-10: Persist native jobs with OCC'
status: archived
priority: high
created: 2026-07-23T02:23:45.208534+02:00
updated: 2026-07-23T02:46:21.647980+02:00
tags:
  - phase-3
  - scope:core
  - runtime
  - jobs
  - storage
  - occ
  - security
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-003
  - packet:DN-003-PK-010
parent: 2001
depends_on:
  - 2000
ac:
  - 'AC-1: Given an empty explicit work root and accepted `JobGeneration`, public
    materialization writes one active shape job per target using supplied IDs and
    digest/receipt references, then lists records and OCC tokens by job ID. Replay
    returns the same records, tokens, and bytes; a differing occupied ID raises `JobConflictError`
    with `code == "ERR_JOB_CONFLICT"`, and traversal or symlink substitution preserves
    committed bytes.'
  - 'AC-2: Given a current OCC token, one public operational update or active-to-archive
    move commits one complete `JobRecord` with a new token. Given a stale token or
    two processes using the same token, one call succeeds and each loser raises `JobConcurrencyError`
    with `code == "ERR_JOB_OCC_STALE"`; one readable record remains in active or archive
    storage with no temporary or partial file.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Bootstrap Projection Identity
- `change_id`: `replace-delivery-pipeline`
- `delivery_digest`: `9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8`
- `delivery_node_id`: `DN-003`
- `packet_id`: `DN-003-PK-010`

## Outcome
Contained active/archive job storage materializes accepted `JobGeneration` and updates one operational job record under optimistic concurrency control without copying normative authority.

## Scope
In scope: explicit work-root job topology; active/archive create, read, and list operations; generation materialization with supplied positive monotonic IDs; immutable OCC tokens; operational updates; active-to-archive moves; deterministic ordering; path and symlink containment; and no-overwrite behavior.

Out of scope: attempts, findings, and receipts; cross-record transactions and recovery manifests; lifecycle predicates; requests; invalidation; dispatch; proof checkout; and live workspace data creation.

## Current Foundation And Ownership
Deepen the native `jobs.py` contracts delivered by packet `DN-003-PK-001` behind one cohesive job-store owner. Reuse descriptor-relative, no-follow, no-overwrite, fsync, and stable-diagnostic patterns from `receipt.py` and `storage_io.py` when current source supports them. Replace neither legacy task storage nor its callers.

Public writes return a frozen `JobRecord` plus its current OCC token. A differing record at an occupied job ID raises exported `JobConflictError` with `code == "ERR_JOB_CONFLICT"`; a stale token raises exported `JobConcurrencyError` with `code == "ERR_JOB_OCC_STALE"`. Byte-equivalent replay returns the same record, token, and bytes.

## Authority
Resolve behavior from `REQ-016`, `IF-003`, `KEEP-007`, `RISK-002`, design sections 2, 7.1, and 13, and packet `DN-003-PK-001`.

Proof guidance: exercise public job-store APIs over a temporary explicit work root for idempotent materialization, stale-token and real two-process OCC races, containment, no-overwrite, deterministic listing, and durable readback. Store-level proof supplements later public transaction proof and does not claim the complete `PROOF-003` boundary.

[[2026-07-23T02:43:21+02:00]]
## Builder Notes
- Change envelope: native `JobStore` only, rooted at an explicit work directory; materialization, active/archive reads and lists, OCC-protected operational updates/archive moves, containment, deterministic persistence, and public exports. No legacy task-store callers, lifecycle predicates, attempts/findings/receipts, transactions, dispatch, or live data creation changed.
- Files changed: `serve/kanban/src/owlbear_kanban/jobs.py`, `serve/kanban/src/owlbear_kanban/__init__.py`, and `serve/kanban/tests/test_jobs.py`.
- Change Module Map deviations: none. The shaped owner was `jobs.py`; package export and nearest durable behavioral tests were updated as required by the public contract.
- Proof selected: durable public-API tests, justified because no-overwrite persistence, OCC stale-token rejection, cross-process races, archive movement, and symlink containment are shared correctness/security risks.
- Commands run: `uv run pytest serve/kanban/tests/test_jobs.py` (22 passed); `uv run ruff check serve/kanban/src/owlbear_kanban/jobs.py serve/kanban/src/owlbear_kanban/__init__.py serve/kanban/tests/test_jobs.py` (passed); `uv run ruff format --check` over the same files (passed).
- Builder-challenger result: pass. It identified an initial partial-materialization conflict risk; repaired by preflighting every generation record under the lock before any write, with a regression test proving a later conflict leaves no earlier record created.
- Follow-up risks: lifecycle/transaction coordination is intentionally outside this packet; the store provides the contained primitive for later owners.

[[2026-07-23T02:45:35+02:00]]
## Verify Notes
- Evidence reviewed: Builder commit `f6550b0ed` changes only the shaped `JobStore` owner, its public package exports, direct durable tests, and the task record. No local verifier patch was needed.
- Named authorities checked: the historical admission graph authoritative for this bootstrap task ties DN-003 / IF-003 to REQ-016 atomic/concurrency-safe work transactions, KEEP-007 containment/atomic-write preservation, and RISK-002 concurrent-writer corruption. The task correctly limits this packet to a contained job-store primitive rather than claiming full PROOF-003.
- Change Module Map: no deviation. `jobs.py` owns behavior; `__init__.py` exports the public types; `test_jobs.py` exercises its public filesystem boundary.
- Normal-path boundary: real temporary explicit work roots exercise materialization/replay/conflict preflight, deterministic active/archive persistence and readback, OCC update/archive moves, stale-token rejection, two forked processes sharing one token, and symlink substitution. Replacements occur only beneath the public store boundary.
- Checks run: `uv run pytest serve/kanban/tests/test_jobs.py` (22 passed); `uv run ruff check serve/kanban/src/owlbear_kanban/jobs.py serve/kanban/src/owlbear_kanban/__init__.py serve/kanban/tests/test_jobs.py` (passed); `uv run ruff format --check serve/kanban/src/owlbear_kanban/jobs.py serve/kanban/src/owlbear_kanban/__init__.py serve/kanban/tests/test_jobs.py` (passed); `git show --check HEAD` (clean).
- Findings: none. Public `JobStore` implements descriptor-relative no-follow paths, no-overwrite materialization with complete preflight, immutable content-derived OCC tokens, serialized atomic updates/archive moves, and fsync-backed durable records.
- Patches applied: none.
- Verifier-challenger: pass; it confirmed AC coverage, proof sufficiency, and no scope drift.
- Final route: PASS to collect.

[[2026-07-23T02:46:21+02:00]]
## Collect Notes
- Classification: leaf. No child tasks returned by `list_tasks(parent=2009)`; its parent relationship does not make this task an aggregate.
- Leaf verification evidence: `## Verify Notes` records PASS after `uv run pytest serve/kanban/tests/test_jobs.py` (22 passed), focused Ruff checks, formatting check, and a clean `git show --check HEAD`; verifier-challenger passed.
- Intent source and invariant coverage: task Outcome/Scope and AC-1/AC-2 are covered upstream by public `JobStore` materialization/replay/conflict preflight, deterministic active/archive readback, containment, OCC updates/archive moves, stale-token rejection, and two-process race proof. Collector did not re-review code-level AC.
- Child coverage and parent dependency gate: not applicable to this leaf; no child tasks exist.
- Tested commit and tied normal-path proof: `f6550b0ed`; Verify Notes tie the named pytest command and public filesystem-boundary coverage to that implementation commit.
- Residual decisions: `list_requests(task_id=2009, status=pending)` and `list_requests(task_id=2009, status=resolved)` both returned no records. No unresolved required follow-up appears in task history.
- Archive rationale: verifier evidence and request state are complete; archive as completed.
