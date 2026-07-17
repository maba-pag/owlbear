---
id: 1938
title: 'P1-05: Memory storage health'
status: collect
priority: medium
created: 2026-07-17T02:31:34.851802+02:00
updated: 2026-07-17T05:08:24.807288+02:00
tags:
  - phase-1
  - scope:memory
  - integrity
parent: 1945
depends_on: []
ac:
  - Given malformed memory files and three readable files sharing one UUID, 
    memory health returns unreadable paths and the complete duplicate path set 
    while normal entry loading retains its current canonical-selection behavior.
  - Given readable pending, curated, approved, contested, disputed, stale, and 
    deleted entries with unique UUIDs, memory health reports healthy.
  - A memory health read leaves memory paths, bytes, and mtimes unchanged.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
Expose unreadable memory records and complete duplicate-UUID path sets without changing memory lifecycle semantics or canonical loading.

## Scope
In scope: the memory engine's read-only health result and public diagnostic method. Out of scope: memory purge, lifecycle mutation, Cockpit aggregation, and UI behavior.

## Planning Authority
OpenSpec change: `redesign-workspace-health`, including the workspace-health spec and accepted design. Canonical lifecycle literals come from `MemoryState` in the memory package.

## Proof Guidance
Use a focused real-filesystem memory check plus the existing lifecycle regression surface. Add durable coverage only for a meaningful unreadable-path, duplicate-set, or non-mutation regression not already protected.

[[2026-07-17T05:06:08+02:00]]
## Builder Notes

Change envelope: add the memory engine's read-only storage health result and public diagnostic method; preserve normal load canonical selection and lifecycle semantics. Expected files: `serve/memory/src/owlbear_memory/models.py` (`MemoryHealth`), `serve/memory/src/owlbear_memory/engine.py` (`MemoryEngine.health`), `serve/memory/src/owlbear_memory/__init__.py` (export), and focused regression coverage in `tests/test_memory_health.py`.

Files changed: added `MemoryHealth` with `unreadable_paths`, complete `duplicate_paths`, and `healthy`; added an independent sorted `*.md` scan in `MemoryEngine.health()` that does not mutate loader/cache state or files; exported the result type; added real-filesystem tests for malformed files, three-way duplicate UUID reporting, latest-`updated_at` canonical loading, all seven lifecycle states, and path/byte/mtime preservation.

Change Module Map deviations: none. Cockpit aggregation, repair, lifecycle mutation, and UI remain out of scope.

Proof selected: `uv run pytest tests/test_memory_health.py -q` passed (`2 passed in 0.39s`). Editor diagnostics reported no errors for all changed files. Builder-challenger returned `decision: pass`, finding no concrete blocker and confirming the acceptance criteria are satisfied. Additional `uv`/ruff invocations intermittently exited 130 with no output during environment startup; this is recorded as an environment limitation. Existing unrelated engine lint findings/state-transition edits were preserved and are outside this task's health scope.

Durable-test justification: the test earns the Rent Test because duplicate path completeness and non-mutation are data-integrity risks that are easy to regress and hard to detect manually.

Follow-up risk: broader repository regression and lint commands should be rerun by verify when the shell startup issue is stable.

[[2026-07-17T05:08:24+02:00]]
## Verify Notes

Evidence reviewed:
- Task AC and OpenSpec authority `openspec/changes/redesign-workspace-health/specs/workspace-health/spec.md`, especially Memory integrity. It requires unreadable records and duplicate UUID paths to be reported; valid lifecycle states must not become health failures; health reads must not mutate files.
- `MemoryState` is the canonical lifecycle authority in `serve/memory/src/owlbear_memory/models.py`.
- Change Module Map in Builder Notes: `models.py`, `engine.py`, package export, and `tests/test_memory_health.py`.

Authority and implementation check:
- `MemoryHealth` exposes `unreadable_paths`, complete `duplicate_paths`, and derived `healthy`.
- `MemoryEngine.health()` scans the actual sorted markdown tree through the established `storage.read_entry` boundary. It collects every readable path for each UUID before filtering duplicate sets, and it leaves `_entries`, `_id_to_path`, `parse_errors`, and cache state untouched.
- The health scanner accepts all seven canonical `MemoryState` literals as readable records and does not classify lifecycle state or counts as a finding.
- No Change Module Map deviations: only mapped memory model/engine/package export plus focused regression coverage changed. Cockpit, repair, mutation, and UI boundaries are untouched.

Normal-path boundary and replacements:
- Real temporary filesystem is exercised; no command, loader, or health workflow is mocked. `storage.write_entry` prepares valid persisted fixtures, while `MemoryEngine.health()` and subsequent `load()` run normally against disk.
- Before/after snapshots prove health leaves paths, bytes, and mtimes unchanged. The duplicate test also proves normal loading retains the latest-`updated_at` canonical selection after health runs.

Commands run:
- `uv run pytest tests/test_memory_health.py tests/test_assess_memories.py tests/test_memory* -q` — `331 passed in 1.82s`.
- `uv run --project . test-root tests/test_memory_health.py serve/memory/src/owlbear_memory/engine.py` — both resolve to root pytest boundary.
- `uv run ruff check serve/memory/src/owlbear_memory/models.py serve/memory/src/owlbear_memory/engine.py serve/memory/src/owlbear_memory/__init__.py tests/test_memory_health.py` — all checks passed. The first invocation ended with environment-startup exit 130 and no output; per operational guidance, the read-only command was repeated once and passed.

Findings and patches:
- No implementation defects, scope drift, or unresolved AC found.
- No verifier patch applied.

Verifier-challenger:
- `verifier-challenger` returned `decision: pass`, confirming the real-filesystem proof covers unreadable paths, complete duplicate UUID path sets, lifecycle-state health, retained canonical loading, and non-mutation.

Final route: PASS to collect.
