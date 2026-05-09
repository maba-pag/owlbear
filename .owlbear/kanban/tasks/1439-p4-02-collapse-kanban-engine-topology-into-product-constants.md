---
id: 1439
title: 'P4-02: Collapse kanban engine topology into product constants'
status: review
priority: critical
created: 2026-05-08T19:31:49.034076+00:00
updated: 2026-05-09T03:38:42.259151+00:00
tags:
- phase-4
- scope:kanban
- type:refactor
- topology
- deployment-readiness
parent: 1437
depends_on:
- 1438
blocked: false
block_reason:
claimed_at: 2026-05-09T03:38:42.259151+00:00
archival_reason:
archival_refs: []
---

## Context
Brief: see parent #1437.

## Scope
In scope: kanban engine topology authority and read APIs.
Out of scope: MCP transport, Cockpit UI, docs, and setup seed changes.

## Acceptance Criteria
1. Builder introduces one importable product-topology constant in `serve/kanban/src/owlbear_kanban/` defining canonical values for all topology categories: statuses (7), priorities (5), entry_status, terminal_status, default_priority, claim_timeout, wave_size, status-to-agent routing (agent_map), non_impl_tags, archival_reasons, activity_log (True), storage paths (tasks_dir, archive_dir, decisions_dir), status_predicates (empty dict), agent_types (empty dict), agent_compatibility (empty dict). Core values match the #1438 probe constant table. (td:1)
2. `KanbanEngine(kanban_dir)` initialises from a board directory containing only `tasks/`, `archive/`, and `decisions/` subdirectories with no config.yml. `board_config` returns an object whose topology attributes match the product constant. `next_id` defaults to 1 when config.yml is absent (scan-based allocation is #1443 scope). (td:2)
3. Given a scratch board whose config.yml overrides any topology field (all categories from AC1), `KanbanEngine.board_config` and `AgentView` methods expose product-constant values, not file overrides. (td:2)
4. `load_config` no longer raises `FileNotFoundError` when config.yml is absent; it returns a topology-constant object, reading only `next_id` from the file when present. `save_config` persists only `next_id` (not topology fields) so that `allocate_next_id` continues to function. `board_config` return shape preserves attribute paths (`statuses`, `priorities`, `pipeline.entry_status`, `pipeline.terminal_status`, `pipeline.wave_size`, `pipeline.claim_timeout`, `pipeline.default_priority`, `agents.agent_map`, `policy.non_impl_tags`, `policy.archival_reasons`, `paths.tasks_dir`, `paths.archive_dir`) so that out-of-scope consumers (MCP server, Cockpit view) compile. `dispatch._NON_IMPL_TAGS` is replaced by a reference to the product-topology constant. Task frontmatter parsing for per-task data fields (status, priority, tags, blocked) validates against product-topology statuses and priorities. (td:2)
[[2026-05-09]]


## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: collapse configurable topology into product constants |
| Interface clarity | PASS (after refinement) | AC expanded to all 16 topology categories including agent_types, agent_compatibility, status_predicates. Attribute path backward-compat specified. |
| Dependency correctness | PASS | Depends on #1438 (archived/done). No missing dependencies. |
| Module layering | PASS | Changes within serve/kanban/src/owlbear_kanban/ (single package). Out-of-scope MCP/Cockpit not modified. |
| TDD compliance | PASS (after refinement) | Original AC5 prohibited pytest — REMOVED. Task now goes through normal TDD pipeline. |
| KISS/YAGNI | PASS | Removing config flexibility is simplification, not over-engineering. |
| Premise challenge | PASS | Parent #1437 approved direction explicitly mandates this change. |
| Pattern consistency | PASS | Aligns with existing dispatch._NON_IMPL_TAGS pattern (already hardcoded constants). Consolidates into unified constant. |
| Security surface | N/A | No new system boundaries. |
| Single domain | PASS | kanban domain only. |
| Failure Mode Map | See below | load_config and save_config behavior changes identified. |
| Decision-request verification | N/A | No research doc referenced. |
| User-action detection | SKIP | Counter-signal C1: AC defines importable module and function signatures. |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| load_config (no config.yml) | File absent | Was FileNotFoundError, now returns defaults | Yes — AC2/AC4 | Engine starts cleanly without config |
| allocate_next_id → save_config | Persists topology alongside next_id | Was full config write | Narrowed in AC4 | save_config writes only next_id |
| BoardConfig attribute access by MCP/Cockpit | AttributeError if fields removed | N/A | Mitigated in AC4 | Attribute paths preserved for backward compat |
| config.yml malformed YAML | Parse error | ConfigError (unchanged) | Yes | Same as before |

### Codebase Context
- BoardConfig: `models.py` L166–195 — all topology fields mutable Pydantic fields (statuses, priorities, pipeline, agents, policy, paths, activity_log)
- PathsConfig: `models.py` L119–130, PipelineConfig: L133–142, AgentsConfig: L145–151, PolicyConfig: L154–167
- load_config: `config_loader.py` L34–60 — requires config.yml, raises FileNotFoundError
- KanbanEngine.__init__: `engine.py` L345–430 — calls load_config, derives paths from config
- KanbanEngine.board_config: `engine.py` L457–465 — deep copy of self._config
- AgentView: `agent_view.py` L51–54 — reads config via engine.board_config throughout (L148, L359, L594, L937, L1241). Also reads agent_types (L444), agent_compatibility (L445)
- Engine status_predicates: `engine.py` L920 — reads config.policy.status_predicates
- dispatch._NON_IMPL_TAGS: `dispatch.py` L56–68 — hardcoded frozenset, separate from BoardConfig
- decisions_path: `decisions.py` L86 — already hardcoded as kanban_dir / "decisions"
- allocate_next_id: `storage.py` L571–580 — calls load_config then save_config to persist next_id
- save_config: `storage.py` L224–271 — writes full grouped schema including topology
- config.yml: `.owlbear/kanban/config.yml` — activity_log: false (becomes True per parent direction)

### Refinements Applied
1. **AC1 expanded** from ~10 to 16 topology categories: added entry_status, terminal_status, decisions_dir, status_predicates (empty), agent_types (empty), agent_compatibility (empty).
2. **AC3 expanded** negative-probe override list to cover all 16 categories.
3. **AC4 rewritten** to specify: (a) load_config returns defaults when config.yml absent, (b) save_config persists only next_id for allocate_next_id continuity, (c) board_config return shape preserves attribute paths for backward compat with out-of-scope MCP/Cockpit consumers, (d) dispatch._NON_IMPL_TAGS consolidated.
4. **AC5 removed** — prohibited pytest, conflicting with TDD pipeline. Task goes through normal test-writer → builder flow. #1438 probe informs test specification but does not replace testing.
5. **Backward compatibility note** added to AC4: attribute paths (pipeline.entry_status, agents.agent_map, policy.non_impl_tags, etc.) preserved so out-of-scope consumers (MCP server, Cockpit view) compile.

### Challenge Results
- Challenger: block (confidence 0.52) — raised: (1) allocate_next_id → save_config path persists topology, (2) agent_types/agent_compatibility/status_predicates missing from constant set, (3) board_config return shape undefined, (4) #1438 probe AC2 known errors.
- Architect response: ACCEPTED issues 1–3 — refined AC4 (save_config narrowed to next_id only), expanded AC1 to 16 categories, added backward-compat attribute path preservation to AC4. REBUTTED issue 4 — probe constant VALUES are correct even though probe's structural analysis had errors; AC references specific values, not probe structure. Overall: challenger feedback incorporated into stronger AC.

### Test Depth
- AC1: td:1 (smoke test — verify constant exists with expected values)
- AC2: td:2 (multiple paths — no-config init, board_config return, next_id default)
- AC3: td:2 (multiple override scenarios across 16 categories)
- AC4: td:2 (load_config, save_config, board_config shape, dispatch, frontmatter parsing)
- Max depth: td:2
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined AC (expanded to 16 topology categories, removed anti-testing AC5, added backward-compat constraint and save_config narrowing). Advanced to todo.
[[2026-05-09]]
[[2026-05-09]]
Architecture review complete. Refined AC from 5 lines to 4: (1) expanded topology constant from ~10 to 16 categories (added entry_status, terminal_status, decisions_dir, status_predicates, agent_types, agent_compatibility), (2) removed AC5 anti-testing constraint that conflicted with TDD pipeline, (3) specified save_config narrowing to next_id only for allocate_next_id continuity, (4) added backward-compat attribute path preservation for out-of-scope MCP/Cockpit consumers. Challenger raised 4 issues (block, 0.52 confidence); accepted 3 into AC refinement, rebutted 1 (probe structural errors don't affect constant values). All 13 Step 2 criteria evaluated — all PASS.
[[2026-05-09]]
## Test-Writer Notes

**Test file:** `tests/test_kanban_topology_1439.py`

**Classes:**
- `TestFromAC_TopologyConstant` — AC1 coverage
- `TestFromAC_EngineNoConfig` — AC2 coverage
- `TestFromAC_OverridesIgnored` — AC3 coverage
- `TestFromAC_LoadSaveAndDispatch` — AC4 coverage

**Tests per category:**
| Category | Count | Failure mode |
|----------|-------|-------------|
| Happy (topology constant values) | 22 | ModuleNotFoundError (`owlbear_kanban.topology` absent) |
| Happy (engine no-config init) | 7 | FileNotFoundError (load_config requires config.yml) |
| Error/Override (overrides ignored) | 17 | AssertionError (config values returned instead of product topology) |
| Error/Boundary (load/save/dispatch/frontmatter) | 17 | FileNotFoundError + AssertionError |

**Total: 63 tests, all FAIL confirmed** (uv run pytest, 0.51s, exit 1)

**AC coverage table:**
| AC | Covered | Failure mode |
|----|---------|-------------|
| AC1: topology constant with 17 categories | ✓ 22 tests | ModuleNotFoundError |
| AC2: engine no-config-yml init | ✓ 7 tests | FileNotFoundError |
| AC3: config overrides ignored (all 17 categories + AgentView) | ✓ 17 tests | AssertionError |
| AC4: load_config absent; save_config next_id only; attribute paths; dispatch ref; frontmatter | ✓ 17 tests | FileNotFoundError + AssertionError |

**Ruff:** clean (exit 0)
**Commit:** 7f90fb8d "test: add topology constant and engine refactor tests (#1439, test-writer)"

**Key design decisions:**
- Topology constant tested via `importlib.import_module("owlbear_kanban.topology")` inside each method (avoids collection-time import failure)
- Expected values derived from `.owlbear/kanban/config.yml` + `dispatch._NON_IMPL_TAGS` inline frozenset
- For AC4 dispatch ref test: `dispatch._NON_IMPL_TAGS is PRODUCT_TOPOLOGY.non_impl_tags` (identity, not just equality) per AC "reference" wording
- Override tests use STATUS_RANK-valid statuses to pass engine init (`_validate_dispatch_rank_coverage`) while still being different from product topology
- Frontmatter validation: "released" is in STATUS_RANK but NOT in product topology — tests that config allowing it is irrelevant after refactor; priority test verifies product topology takes precedence over config-override restriction
[[2026-05-09]]
## Builder Notes
- Implementation:
  - serve/kanban/src/owlbear_kanban/topology.py
  - serve/kanban/src/owlbear_kanban/config_loader.py
  - serve/kanban/src/owlbear_kanban/storage.py
  - serve/kanban/src/owlbear_kanban/dispatch.py
  - serve/kanban/src/owlbear_kanban/corruption.py
- Fixes applied:
  - Added canonical `PRODUCT_TOPOLOGY` constant with all AC topology categories (statuses, priorities, pipeline defaults, agent map, non-impl tags, archival reasons, paths, decisions_dir, empty status/agent compatibility maps, activity_log=true).
  - Updated `load_config` to never fail on missing `config.yml`; now returns topology-constant `BoardConfig` and reads only `next_id` when file exists.
  - Updated `save_config` to persist only `next_id`.
  - Replaced `dispatch._NON_IMPL_TAGS` inline set with direct reference to `PRODUCT_TOPOLOGY.non_impl_tags` (identity reference).
  - Frontmatter validation now resolves against product topology behavior through engine-config loading path; override config values are ignored.
- Tests:
  - quality-runner scoped task suite: 63 passed, 0 failed (`tests/test_kanban_topology_1439.py`)
- Coverage:
  - quality-runner scoped report overall 26% for selected touched modules
  - module breakdown: config_loader 100%, topology 100%, storage 37%, corruption 34%, dispatch 28%
- Lint:
  - ruff clean on touched source files + task test file
- Evidence summary:
  - RED verified before implementation (63 failing tests)
  - GREEN verified after implementation via quality-runner (63 passing)
  - commit: `cca1a625`