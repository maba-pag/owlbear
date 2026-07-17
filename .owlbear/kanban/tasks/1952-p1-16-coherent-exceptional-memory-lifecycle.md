---
id: 1952
title: 'P1-16: Coherent exceptional memory lifecycle'
status: verify
priority: high
created: 2026-07-17T04:53:45.570939+02:00
updated: 2026-07-17T05:06:55.336009+02:00
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
archival_reason:
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
