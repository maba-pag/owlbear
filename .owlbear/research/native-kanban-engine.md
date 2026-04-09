# Native Kanban Engine — Research

> **Owning task:** #712 — Native kanban engine: replace kanban-md Go binary with Python engine
> **Date:** 2026-04-09 **Status:** Complete

## 1. Context and Question

Task #712 proposes replacing the kanban-md Go binary (v0.33.0) with a native Python
`KanbanEngine` inside `serve/mcp-kanban/`. Three drivers: distribution friction
(platform-specific binary), ownership (workarounds around Go bugs), and simplification
(subprocess→library call). Full brief: `.owlbear/briefs/draft-kanban-native/brief.md`.

Prior research (#144, March 2026) recommended keeping kanban-md at .90 confidence,
but was calibrated for single-operator scope — not distribution.

## 2. Sources Studied

| # | Source | Relevance | What |
|---|--------|:---------:|------|
| 1 | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` | .95 | Current MCP server — 15 `_run_kanban()` subprocess calls |
| 2 | `.owlbear/briefs/draft-kanban-native/brief.md` | .95 | Full Brief with API surface, file formats, decisions D1-D7 |
| 3 | `.owlbear/research/kanban-replacement-options.md` | .90 | Prior #144 research — 4 alternatives, recommended augmentation |
| 4 | `.owlbear/kanban/config.yml` | .95 | Live board config — 7 statuses, next_id=733 |
| 5 | `.owlbear/kanban/activity.jsonl` | .85 | Activity log — action vocab: edit, release, move, claim, create |
| 6 | `pypi.org/project/ruamel.yaml` | .80 | v0.19.1, round-trip YAML, 0.5M daily downloads |
| 7 | Task file `712-*.md` | .90 | Live YAML frontmatter — Go nanosecond timestamps confirmed |
| 8 | Codebase-wide seam search (40+ locations) | .95 | Complete binary reference inventory |

## 3. Analysis

### 3a. YAML Library Comparison

| Criterion | ruamel.yaml | PyYAML | strictyaml |
|-----------|:-----------:|:------:|:----------:|
| Round-trip preservation | **Yes** (typ='rt') | No | Partial |
| Comment preservation | **Yes** | No | N/A |
| Field order preserved | **Yes** | No | Yes |
| Timestamp: raw string pass-through | **Yes** (resolver disabled) | No | N/A |
| Pure Python (no C build) | Yes (default mode) | Needs C ext | Yes |
| Daily downloads | 500K | 25M | 10K |
| Adds dependency | 1 (~160KB) | 1 | 2 (wraps ruamel) |

**Verdict:** ruamel.yaml is the only viable option for lossless YAML round-trip. D1 confirmed.

**Critical detail:** Go emits nanosecond timestamps (e.g., `2026-04-09T03:16:18.2333914+02:00`).
Python datetime only supports microseconds. ruamel.yaml's default YAML 1.1 resolver
would parse these into datetime objects, losing precision. Fix: disable the timestamp
resolver so timestamps stay as raw strings. The engine stores timestamps as strings
and formats new ones in ISO 8601 with timezone.

### 3b. Seam Inventory (binary references to migrate/remove)

| Category | Count | Key Locations |
|----------|:-----:|---------------|
| MCP server subprocess calls | 15 | `server.py` — all 8 tools via `_run_kanban()` |
| Orchestrator board reader | 3 | `board.py`, `cli.py`, `loop.py` |
| Setup scripts | 2 | `.owlbear/kanban/setup.ps1`, `seed/.owlbear/kanban/setup.ps1` |
| Documentation | 4 | `README.md`, `setup-guide.md`, `sharing-guide.md`, `kanban/README.md` |
| Skill files | 2 | `h-kanban-md/SKILL.md`, `h-mcp-kanban/SKILL.md` |
| E2E scripts | 1 | `.owlbear/scripts/e2e_smoke.py` |
| Test fixtures | 1 | `tests/fixtures/mock_acp_agent.py` |
| Test files (mocking `_run_kanban`) | 15+ | `test_server.py`, `test_start_work_470.py`, `test_pick_tasks_*`, etc. |
| `.gitignore` | 1 | `*.exe` exclusion |
| `pyproject.toml` | 1 | `integration` marker description |

### 3c. Migration Phase Risk Assessment

| Phase | Risk | Mitigation |
|-------|------|-----------|
| 1. Engine modules | **High** — correctness foundation | Golden snapshot: capture kanban-md JSON for sample tasks, compare engine output. Round-trip test on all 700+ files. |
| 2. MCP server migration | **High** — behavioral contract, self-referential (kanban managing its own replacement) | Atomic switchover: old code works until the switch. All existing tests must pass. Feature freeze during migration. |
| 3. Cleanup sweep | **Low** — mechanical but broad | Seam inventory above is the checklist. Orchestrator is out of scope (D7: unused, should use MCP). |

### 3d. Decomposition Assessment

Task #712 is too large for a single task — it spans engine design, YAML I/O,
8 operations, MCP migration, and cleanup. **Needs decomposition** by the planner.
The brief's 3-phase structure is the right breakdown axis, with Phase 1 further
split into: config loading, task YAML I/O, individual operations, compound ops.

## 4. Recommendation (confidence: .85)

**Proceed with native Python engine replacement as specified in the Brief.**

The Brief (D1-D7) is well-reasoned. Key validations:
- ruamel.yaml is the correct YAML library choice (only option for lossless round-trip)
- Timestamp handling needs explicit resolver disabling (confirmed by live task files)
- 3-phase migration plan with atomic Phase 2 switchover correctly addresses the self-referential risk
- Seam inventory is comprehensive (40+ locations catalogued)
- Orchestrator exclusion (D7) is correct — unused code should use MCP if ever needed

**Risk:** The largest risk is behavioral drift in compound operations (`start_work`/`end_work`).
Mitigation: golden snapshot parity tests capturing kanban-md's actual output for reference.

Challenge: FALLBACK — skipped (research validates existing Brief decisions, no novel recommendation to challenge)

## 5. Follow-up Tasks

- Decomposition task for planner (Phase 1-3 breakdown into atomic subtasks)
- See task IDs created below
