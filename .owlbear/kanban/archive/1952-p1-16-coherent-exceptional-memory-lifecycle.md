---
id: 1952
title: 'P1-16: Coherent exceptional memory lifecycle'
status: archived
priority: high
created: 2026-07-17T04:53:45.570939+02:00
updated: 2026-07-17T05:21:28.208031+02:00
tags:
  - phase-1
  - scope:memory
  - lifecycle
  - integrity
parent: 1958
depends_on: []
ac:
  - 'AC-1: Given a contested, disputed, or stale entry, mutable title, content, categories,
    confidence, or scope values, and its current update token, MemoryEngine.edit persists
    the supplied values, refreshes updated_at, retains the source state and lifecycle
    metadata, and recomputes score from confidence plus existing outstanding and unremarkable
    counts when confidence changes.'
  - 'AC-2: Given an approved or curated entry first reported factually wrong, record_factually_wrong
    persists contested state and the reporting task; the same task reporting again
    leaves the persisted entry unchanged, while a different task report persists disputed
    state with contested_by_task null.'
  - 'AC-3: Given a contested, disputed, or stale entry and its current update token,
    MemoryEngine.resolve persists approved state, current approved_at and updated_at,
    and null contested_by_task; stale also persists didnt_use_count 0 while confidence,
    outstanding_count, unremarkable_count, and score remain unchanged, and contested
    or disputed assessment counters remain unchanged.'
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Outcome
The canonical memory engine supports human correction without lifecycle-state escape, keeps score synchronized with confidence, and preserves coherent challenge and stale-recovery history.

## Planning Source
- OpenSpec: `openspec/changes/expose-memory-lifecycle-in-cockpit`
- Capability requirements: Detail-aligned editing, Score-led memory overview, Accurate contested provenance, Fresh stale recovery window

## Scope
- In scope: memory-domain edit, factual-challenge, resolve, score, and persisted lifecycle semantics.
- Out of scope: MCP policy, Cockpit HTTP routes, frontend behavior, and documentation.

## Change Contract
Preserve deleted-entry rejection, approved edits downgrading to curated, same-task factual-report no-op behavior, confidence bounds, and optimistic concurrency.

Proof guidance: run focused memory engine checks plus a downstream-impact scan of maintained state-machine and voting/scoring behavior; durable guards are warranted for shared persisted lifecycle semantics.

[[2026-07-17T05:06:55+02:00]]
## Builder Notes
- Change envelope: `MemoryEngine.edit`, `record_factually_wrong`, and `resolve`; one focused regression test update in `tests/test_memory_state_machine.py`.
- Files changed: `serve/memory/src/owlbear_memory/engine.py`, `tests/test_memory_state_machine.py`.
- Change Module Map deviations: none; implementation stayed within the memory engine and its existing state-machine test boundary.
- Proof selected: focused maintained memory lifecycle/assessment suite plus Ruff and diff hygiene.
- Durable-test justification: updated three obsolete assertions that contradicted the new exceptional-edit contract and added one regression guard for stale resolve clearing provenance/resetting non-use count; these protect shared persisted lifecycle semantics.
- Commands run: `uv run --project . pytest tests/test_assess_memories.py tests/test_confirmation_cycle.py tests/test_memory* -q` -> `357 passed`; `uv run --project . ruff check serve/memory/src/owlbear_memory/engine.py tests/test_memory_state_machine.py` -> all checks passed; `git diff --check` -> clean.
- Builder-challenger result: pass; independently reran the cited focused pytest and Ruff checks.
- Follow-up risks: verifier should inspect downstream lifecycle assumptions and confirm AC-1/AC-2 persisted field behavior at the public MemoryEngine boundary.

[[2026-07-17T05:09:17+02:00]]
## Verify Notes
- Evidence reviewed: builder commit `005f8167d` changes only `serve/memory/src/owlbear_memory/engine.py` and `tests/test_memory_state_machine.py`; builder reported 357 focused memory tests and Ruff clean.
- Named authorities checked: `openspec/changes/expose-memory-lifecycle-in-cockpit/specs/cockpit-memory-lifecycle/spec.md` requirements Detail-aligned editing, Accurate contested provenance, and Fresh stale recovery window; `tasks.md` items 1.1 and 1.2.
- Change Module Map: no deviation. The implementation remains in the mapped `MemoryEngine` owner with state-machine and confirmation/assessment tests; no MCP, Cockpit, frontend, or documentation files changed.
- Normal-path boundary: exercised the public `MemoryEngine` through actual filesystem storage and fresh-engine reads. No command, workflow, or persistence boundary was mocked.
- AC-1: `edit` copies the full entry, persists all five mutable fields, updates timestamps, retains lifecycle/source metadata, and recomputes score from confidence with existing score counts.
- AC-2: confirmation-cycle coverage verifies first-task contested provenance, same-task no-op, and different-task disputed transition clearing provenance.
- AC-3: resolution coverage verifies exceptional-to-approved transition, timestamps, provenance clearing, stale-only non-use reset, and preserved score-relevant history.
- Checks run:
  - `uv run --project . pytest tests/test_memory_state_machine.py -v` -> 34 passed.
  - `uv run --project . pytest tests/test_assess_memories.py tests/test_confirmation_cycle.py -q` -> 72 passed.
  - `uv run --project . pytest tests/test_memory_state_machine.py tests/test_assess_memories.py tests/test_confirmation_cycle.py -q` -> 106 passed.
  - `uv run --project . ruff check serve/memory/src/owlbear_memory/engine.py tests/test_memory_state_machine.py` -> all checks passed.
  - `git diff --check` -> clean.
- Patches applied: none.
- Verifier-challenger result: pass; confirmed adequate public-boundary persistence evidence, no unresolved AC, and no scope or module-map drift.
- Final route: PASS -> collect.

[[2026-07-17T05:21:28+02:00]]
## Collect Notes
- Classification: leaf. Task has no child tasks, no aggregate/EPIC title or tags, and no aggregate intent section; parent assignment to #1958 does not make this task an aggregate.
- Leaf verification evidence: `## Verify Notes` records PASS, builder commit `005f8167d`, focused public-boundary persistence checks (34 state-machine tests, 72 assessment/confirmation tests, and 106 combined tests), Ruff clean, diff hygiene clean, and verifier-challenger pass.
- Invariant map coverage: AC-1 edit persistence and score synchronization, AC-2 contested/disputed provenance transitions, and AC-3 resolution/stale recovery semantics are all explicitly mapped in Verify Notes. Change Module Map reports no deviation.
- Child coverage: `list_tasks(parent=1952)` returned no children; aggregate dependency-gate checks are not applicable. Task dependencies are empty.
- Residual decisions: no pending request records, no block, and no unresolved Required Follow-up. Builder follow-up risk was explicitly discharged by verifier public-boundary checks.
- Rationale: verified leaf closure is complete; archive mechanically as completed without re-reviewing implementation details.
- Verdict: ARCHIVED.
