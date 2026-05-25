# Kanban + MCP-Kanban Deployment-Readiness Audit

**Date:** 2026-05-04  
**Scope:** `serve/kanban/` (owlbear_kanban) + `serve/mcp-kanban/` (owlbear_mcp_kanban)  
**Goal:** Determine sync-to-main readiness  
**Constraint:** Read-only audit — no servers started, live board untouched  
**Verdict:** NOT ready for sync to main  

---

## Evidence Base

| Metric | Value |
|--------|-------|
| pytest (non-api) | 1873 passed, 87 failed, 0 errors |
| Ruff | Clean (0 violations) |
| Vitest (frontend) | All pass |
| ESLint | 1 warning (unrelated to kanban) |

### Green signals

- Cockpit HTTP routes (test_cockpit_kanban_routes.py)
- Engine move/claim (test_engine_move_claim.py)
- ID-to-filename cache (test_idtofilename_cache_944.py)
- Storage core read/write (test_storage_io.py)

### Red clusters

| Cluster | Failing tests | Root cause |
|---------|--------------|------------|
| Engine init/config | 15 | Grouped schema writer + init sequence changes |
| pick_tasks dispatch | 20 | Wave assembly / bucket logic rework incomplete |
| Migration/storage | 13 | New schema format lacks proven migration path |
| MCP guidance/create_dr | 17 | task_id validation + guidance contract changes |
| Cockpit OCC | 4 | Engine methods not wired for OCC |
| Engine lifecycle | 8 | end_work next-status derivation broken |

---

## Finding 1 — CRITICAL: Engine `end_work` success path broken

### Problem

In `engine.py` (L1530–1572), the success path defaults `move_to="research"` instead of deriving the next status from `config.statuses[idx+1]` per Brief B design. A plain `end_work(outcome="success")` regresses the task to research instead of advancing it.

### Evidence

- Failures in `test_engine_coverage_1068`, `test_list_sessions_952`
- Brief B decision (draft-kanban-engine-b-2026-04-20/decisions.md L180): `end_work(outcome="success")` must advance to next configured status
- Research: `.owlbear/research/end-work-compound-tool.md` §3.2 "Next-status derivation"

### Decision

Wire the config-based next-status derivation: read current status → find index in config.statuses → move to statuses[idx+1]. This is the design intent from Brief B and the compound-tool research.

### Relevant files

- `serve/kanban/src/owlbear_kanban/engine.py` (end_work method)
- `serve/kanban/src/owlbear_kanban/config_loader.py` (statuses sequence)
- `.owlbear/research/end-work-compound-tool.md` (design reference)
- `.owlbear/briefs/draft-kanban-engine-b-2026-04-20/decisions.md` (contract decision)

---

## Finding 2 — CRITICAL: MCP `create_dr` has no `task_id` validation

### Problem

The MCP server (`server.py` L369–387) accepts `task_id` as raw string and forwards to `decisions.py` (L84–117) which expects int and uses it in filename construction. Non-numeric input is never rejected — both a correctness and path-safety issue (OWASP: path traversal at trust boundary).

### Evidence

- Red tests in `test_mcp_kanban_1196`, `test_mcp_create_dr_1182`
- Source inspection: no `int()` coercion or validation anywhere in the call chain

### Decision

Validate + coerce `task_id` to int at the MCP boundary. Add an integration test asserting the boundary rejects path-traversal payloads (e.g., `"../etc/passwd"`, `"1; rm -rf"`).

### Relevant files

- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` (create_dr tool handler)
- `serve/kanban/src/owlbear_kanban/decisions.py` (downstream consumer)
- Tests: `test_mcp_kanban_1196.py`, `test_mcp_create_dr_1182.py`

---

## Finding 3 — HIGH: Board/config migration safety unproven

### Problem

Storage now emits grouped schema format (`storage.py` L171–174), but migration and compatibility test suites are red. This directly threatens the "must not disrupt existing boards" constraint — syncing this schema without a proven migration path could break live boards.

### Evidence

- 13 red tests across: `test_migrate.py`, `test_storage_1050.py`, `test_storage.py`, `test_engine_atomicity_1104.py`
- Consumer branch (main) uses old flat schema format

### Decision

Finish the compatibility pass: migration + storage suites must go green against consumer-format boards before sync. Prove read-old/write-new round-trip works.

### Relevant files

- `serve/kanban/src/owlbear_kanban/storage.py` (schema writer)
- `serve/kanban/src/owlbear_kanban/migrate.py` (migration logic)
- Tests: `serve/kanban/tests/test_storage_1050.py`, `serve/kanban/tests/test_storage.py`, `serve/kanban/tests/test_migrate.py`

---

## Finding 4 — HIGH: Lifecycle contract misaligned across 5 layers

### Problem

Engine, AgentView, MCP, handbook, and tests disagree on: (a) which outcomes exist, (b) how many tools there are (8 vs 9), (c) whether `fail` is available at the MCP level.

### Evidence

| Layer | Outcomes available | Tool count | Notes |
|-------|-------------------|-----------|-------|
| Engine | success, fail, block, reject | N/A | `fail` records failure + releases claim |
| AgentView | success, fail, reject, block, release | N/A | Maps both `fail` and `release` |
| MCP Server | success, block, reject, release | 9 | REMOVED `fail`, replaced with `release` |
| Handbook (h-mcp-kanban) | success, reject, release, block | 8 | Missing `create_dr` from table |
| README (mcp-kanban) | success, reject, release, block | 9 | Matches MCP server |

#### `fail` vs `release` — different semantics (NOT a rename)

| Outcome | Engine method | Semantics | Used by |
|---------|--------------|-----------|---------|
| `fail` | `end_work(outcome="fail")` | Records failure outcome + releases claim. "I tried, blocked by prereqs." | researcher, builder, r-pipeline-protocol |
| `release` | `release_task()` | Releases claim silently. "I'm giving this back." | Rare edge case |

Pipeline protocol explicitly documents `fail` for prerequisite blockers. MCP only offers `release`. This means agents following r-pipeline-protocol instructions cannot express "attempted and failed" through MCP.

### Decision

1. **Expose both `fail` and `release` in MCP** — different semantic intent, different audit trail
2. **Tool count = 9** — add `create_dr` row to handbook summary table
3. **Single reconciliation:** align all 5 layers to full outcome set (success, reject, fail, block, release) with documented "use when" per outcome

### Relevant files

- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` (tool registrations, end_work handler)
- `serve/kanban/src/owlbear_kanban/engine.py` (end_work, release_task)
- `serve/kanban/src/owlbear_kanban/agent_view.py` (outcome routing)
- `share/skills/h-mcp-kanban/SKILL.md` (handbook — tool summary table)
- `serve/mcp-kanban/README.md` (consumer docs)

---

## Finding 5 — HIGH: MCP startup calls `sweep()` (RISK ACCEPTED)

### Problem

The lifespan hook in `server.py` (L119) calls `sweep()` automatically on boot. Starting the MCP releases expired claims on the live board.

### Decision

**Risk accepted.** No task created. User assessed this as acceptable operational behavior given the sweep only targets genuinely expired claims.

---

## Finding 6 — HIGH: Python ≥3.14.4 floor raised without evidence

### Problem

Both `serve/kanban/pyproject.toml` and `serve/mcp-kanban/pyproject.toml` require `>=3.14.4`. Consumer branch specifies `>=3.12`. No 3.14-only feature usage found during audit.

### Decision

Audit for actual 3.14-only syntax/features. If none found (expected), revert to `>=3.12` to match consumer branch. If found, document the rationale.

### Relevant files

- `serve/kanban/pyproject.toml` (requires-python field)
- `serve/mcp-kanban/pyproject.toml` (requires-python field)
- Consumer branch comparison: `owlbear` repo's `pyproject.toml`

---

## Finding 7 — MEDIUM: OCC not wired through engine (4 real regressions)

### Problem

OCC was designed in CockpitView layer and storage layer (`write_task_if_unchanged()` exists and works), but the engine methods (`edit_task`, `move_task`, `sweep`) were never wired to accept `expected_updated` and route to OCC storage.

### Evidence — Triage results

| Test | Classification | Issue |
|------|---------------|-------|
| `test_edit_task_success_path_routes_through_write_task_if_unchanged` | Real regression | Engine `edit_task` lacks `expected_updated` |
| `test_move_task_success_path_routes_through_write_task_if_unchanged` | Real regression | Engine `move_task` bypasses OCC |
| `test_sweep_cas_stale_task_skipped_no_error_raised` | Real regression | `sweep()` should use OCC + catch ERR_STALE |
| `test_sweep_cas_stale_task_skipped_and_later_eligible_task_still_released` | Real regression | Same sweep issue |
| `test_compact_activity_delegates_to_storage_compact_activity_log` | Stale spec | Mock targets wrong module |

### Decision

Add `expected_updated: str | None = None` to engine's `edit_task()`, `move_task()`, and `sweep()`. When non-None, route to `storage.write_task_if_unchanged()`. In `sweep()`, catch `ConcurrencyError("ERR_STALE")` and skip stale tasks. Fix the stale mock test.

### Relevant files

- `serve/kanban/src/owlbear_kanban/engine.py` (edit_task, move_task, sweep)
- `serve/kanban/src/owlbear_kanban/storage.py` (write_task_if_unchanged — already complete)
- `serve/cockpit/src/owlbear_cockpit/view.py` (CockpitView — already passes expected_updated)
- Tests: `tests/test_engine_cockpit_view.py`

---

## Finding 8 — HIGH: pick_tasks wave assembly broken (20 tests red)

### Problem

The greedy bin-packing wave assembler in `agent_view.py` (L300–540) has bugs in: dependency-disjointness checking, agent-bucket compatibility matching (D63 symmetric check), and wave-size cap enforcement. 20 tests red.

### Decision

Fix the greedy algorithm constraint logic. All 20 tests in test_engine_pick_tasks_1074.py must pass.

### Relevant files

- `serve/kanban/src/owlbear_kanban/agent_view.py` (L300–540)
- `serve/kanban/src/owlbear_kanban/dispatch.py`
- `serve/kanban/tests/test_engine_pick_tasks_1074.py`

---

## Finding 9 — HIGH: Engine config validation incomplete (15 tests red)

### Problem

Engine constructor and config model missing several designed validation checks: entry_status/terminal_status validation, agent_map completeness (D24), agent_compatibility symmetry (D63), archival_reasons frozenset (D37), claim_timeout extended format (D29).

### Decision

Implement all designed validation checks. All 15 tests in test_engine_init_1067.py must pass. #1339 (lifecycle reconciliation) depends on this completing first.

### Relevant files

- `serve/kanban/src/owlbear_kanban/engine.py` (constructor, validation)
- `serve/kanban/src/owlbear_kanban/config_loader.py` (model fields, validators)
- `serve/kanban/tests/test_engine_init_1067.py`

---

## Sync Blockers Summary

| # | Severity | Blocker? | Minimum fix | Task |
|---|----------|----------|-------------|------|
| 1 | Critical | Yes | Wire next-status derivation from config.statuses | #1336 |
| 2 | Critical | Yes | Validate + coerce task_id at MCP boundary | #1337 |
| 3 | High | Yes | Green migration/storage suites | #1338 |
| 4 | High | Yes (contract) | Reconcile lifecycle outcomes across 5 layers | #1339 |
| 5 | High | — | Risk accepted | — |
| 6 | High | Yes | Revert or justify Python floor | #1340 |
| 7 | Medium | Soft | Wire OCC through engine methods | #1341 |
| 8 | High | Yes | Fix pick_tasks wave assembly | #1342 |
| 9 | High | Yes | Complete engine config validation | #1343 |

## Recommended Fix Sequence

1. **#1340 — Python floor** — audit for 3.14 features, revert if none
2. **#1337 — task_id validation** — security-critical, small scope
3. **#1343 — config validation** — prerequisite for lifecycle reconciliation
4. **#1336 — end_work next-status** — requires Brief B re-read, config must be valid
5. **#1339 — lifecycle reconciliation** — depends on #1343 being done
6. **#1342 — pick_tasks wave assembly** — independent, self-contained algorithm fix
7. **#1338 — migration/storage** — may be multi-step depending on gap size
8. **#1341 — OCC wiring** — isolated plumbing, lowest priority

### Dependencies

None. All 8 tasks are independent — they touch different subsystems and can be parallelized or executed in any order.
