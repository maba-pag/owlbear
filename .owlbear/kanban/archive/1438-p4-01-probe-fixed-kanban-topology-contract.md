---
id: 1438
title: 'P4-01: Probe fixed kanban topology contract'
status: archived
priority: medium
created: 2026-05-08T19:31:45.300155+00:00
updated: 2026-05-09T01:52:47.640292+00:00
tags:
- phase-4
- scope:kanban
- type:test
- verification-probe
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
In scope: define scratch-board and contract-inspection probes for fixed kanban product topology.
Out of scope: source changes and full pytest or vitest execution.

## Acceptance Criteria
1. Test-writer records a scratch-board topology probe in Test-Writer Notes that creates a board with only tasks, archive, and decisions directories and no config.yml, then states the expected observable constants for statuses, priorities, archive reasons, claim timeout, dispatch policy, activity behavior, and storage paths.
2. Test-writer records a contract-inspection probe for BoardConfig, load_config, and KanbanEngine.board_config that verifies topology values are product constants rather than user-editable config fields by artifact inspection of function signatures or returned model fields.
3. Test-writer records a negative probe where a config.yml containing changed status, priority, path, archive reason, activity_log, claim_timeout, or agent routing values cannot alter the engine-facing topology.
4. Test-writer adds no pytest, vitest, or full-suite execution as functional proof; verification evidence is limited to scratch-board probe notes and contract inspection artifacts.
[[2026-05-08]]


## Architect Refinement

**AC1 expansion:** The expected observable constants must include the full topology surface from #1439 AC1. Add to the enumeration: status-to-agent routing, default priority, entry status, terminal status, dispatch wave size, and non-implementation tags. The complete probe constant categories are: statuses, priorities, archival reasons, entry status, terminal status, default priority, claim timeout, dispatch wave size, status-to-agent routing, non-implementation tags, activity logging (always on per #1437 approved direction), and storage paths (tasks, archive, decisions).

**AC3 expansion:** The negative probe override list must also cover default_priority, wave_size, non_impl_tags, entry_status, and terminal_status — not just the subset in the original AC3.

**Test depth:** All AC lines are td:0 (probe notes, no test code). Test-writer: SKIP (type:test pass-through). Probes serve as contract specification for #1439.
[[2026-05-08]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: define probe specification for fixed kanban topology contract |
| Interface clarity | PASS (after refinement) | AC1/AC3 expanded to cover full topology surface matching #1439 AC1 |
| Dependency correctness | PASS | No dependencies — correct as root probe |
| Module layering | N/A | No source changes |
| TDD compliance | PASS | type:test pass-through; probes serve as contract spec for #1439 RED/GREEN |
| KISS/YAGNI | PASS | Minimal scope — notes-only deliverable |
| Premise challenge | PASS | Probes are needed to define the contract before #1439 implementation |
| Pattern consistency | PASS | Follows probe-before-implementation pattern from parent #1437 decomposition |
| Security surface | N/A | No new system boundaries |
| Single domain | PASS | kanban domain only |
| Failure Mode Map | N/A | No codepaths modified |
| Decision-request verification | N/A | No research doc referenced |
| User-action detection | SKIP | Counter-signal C3: type:test tag present |

### Refinement Applied
- AC1: Expanded constant categories to match #1439's full topology surface — added status-to-agent routing, default priority, entry/terminal status, dispatch wave size, non-implementation tags. 13 categories total.
- AC3: Expanded negative-probe override list to include default_priority, wave_size, non_impl_tags, entry_status, terminal_status.
- Confirmed activity_log expected constant = true (per #1437 approved direction "hard-code activity logging on"), not false (current live config value).

### Codebase Context
- BoardConfig: `serve/kanban/src/owlbear_kanban/models.py` L166–197 — all topology fields currently configurable
- load_config: `serve/kanban/src/owlbear_kanban/config_loader.py` L34–60 — requires config.yml, raises FileNotFoundError when absent
- KanbanEngine: `serve/kanban/src/owlbear_kanban/engine.py` L331–430 — loads config on init
- decisions path: `serve/kanban/src/owlbear_kanban/decisions.py` L86 — hardcoded as `kanban_dir / "decisions"`
- Sub-models: PathsConfig (L107), PipelineConfig (L122), AgentsConfig (L133), PolicyConfig (L141)

### Challenge Results
- Challenger: block (confidence 0.24 for original pytest-conversion proposal)
- Architect response: ACCEPTED — reverted pytest conversion, kept notes-based probe format per task scope and parent #1437 constraints. Adopted challenger's feedback on incomplete topology surface and activity_log discrepancy. Refinement now covers all 13 constant categories aligned with #1439 AC1.

### Test Depth
- All AC lines: td:0 (probe notes, no test code written in this task)
- Max depth: td:0
- Test-writer: SKIP (type:test pass-through)

### Verdict: APPROVE
### Action Taken: Refined AC1/AC3 to cover full topology surface (13 constant categories). Kept type:test tag and notes-based probe format. Advanced to todo.
[[2026-05-08]]
## Test-Writer Notes

**Type:** type:test pass-through — no test code written. All AC lines are td:0 (probe notes only). Probes define the contract for #1439 implementation.

---

### AC1 — Scratch-Board Topology Probe (no config.yml)

**Setup:** Create a temporary directory with only `tasks/`, `archive/`, and `decisions/` subdirectories. No `config.yml` present.

**Current behaviour (pre-#1439):** `load_config(kanban_dir)` raises `FileNotFoundError` because `config_path.exists()` returns False. `KanbanEngine(kanban_dir)` propagates the error — engine cannot initialize without config.yml.

**Expected post-#1439 behaviour:** Engine initializes from product constants without reading any config file. Observable constant values:

| Category | Expected constant |
|----------|------------------|
| statuses | `["research", "backlog", "todo", "in-progress", "review", "docs", "done"]` |
| priorities | `["someday", "nice-to-have", "important", "needed", "critical"]` |
| archival_reasons | `frozenset({"completed", "deprecated", "dropped", "duplicate", "wontfix"})` |
| entry_status | `"research"` |
| terminal_status | `"done"` |
| default_priority | `"important"` |
| claim_timeout | `timedelta(hours=1)` / `"1h"` |
| wave_size | `4` |
| status_to_agent_routing | `{"research": "researcher", "backlog": "architect", "todo": "test-writer", "in-progress": "builder", "review": "reviewer", "docs": "doc-writer", "done": "auditor"}` |
| non_impl_tags | `frozenset({"research", "docs", "type:config", "type:docs", "test", "type:test", "agent", "quality", "type:user-action"})` — already hardcoded in `dispatch._NON_IMPL_TAGS` |
| activity_log | `True` (always on; ignores any config value) |
| tasks_path | `kanban_dir / "tasks"` |
| decisions_path | `kanban_dir / "decisions"` (already hardcoded in `decisions._resolve_decisions_dir`) |

Note: `archive_path = kanban_dir / "archive"` is also a fixed storage constant.

---

### AC2 — Contract-Inspection Probe

**Target symbols:** `BoardConfig` (`models.py`), `load_config` (`config_loader.py`), `KanbanEngine.board_config` (`engine.py`).

**Current state (pre-#1439):**
- `BoardConfig` has `statuses: list[str]`, `priorities: list[str]`, `pipeline: PipelineConfig` (with `entry_status`, `terminal_status`, `wave_size`, `claim_timeout`, `default_priority`), `agents: AgentsConfig` (with `agent_map`), `policy: PolicyConfig` (with `non_impl_tags`, `archival_reasons`), `activity_log: bool` — all user-editable Pydantic fields.
- `load_config(kanban_dir: Path) -> BoardConfig` — requires `config.yml`; returns a model whose topology fields are fully driven by the YAML file.
- `KanbanEngine.board_config()` — no such property exists today; topology is accessed via `self._config` internally.

**Expected post-#1439 contract:**
- Topology constants are not present as mutable Pydantic fields on `BoardConfig` (or `BoardConfig` is replaced/deprecated with a frozen constants object).
- `load_config` signature remains `(kanban_dir: Path)` but does NOT raise `FileNotFoundError` when config.yml is absent — it returns a constants-only object (or the function is replaced by a constants accessor).
- `KanbanEngine.board_config` exposes a read-only view where all 13 constant categories match the product-defined values above, regardless of any config file content.
- Artifact inspection evidence: `inspect.signature(load_config)` accepts `kanban_dir: Path`; returned object's topology attributes match the constant table; `BoardConfig.model_fields` (or equivalent) does not include mutable topology keys (statuses, priorities, archival_reasons, agent_map, non_impl_tags, wave_size, claim_timeout, entry_status, terminal_status, default_priority, activity_log).

---

### AC3 — Negative Probe (config.yml cannot override topology)

**Override list — all of the following placed in a config.yml and loaded:**
- `statuses: [alpha, beta, gamma]`
- `priorities: [low, high]`
- `paths.tasks_dir: "custom-tasks"`
- `paths.archive_dir: "custom-archive"`
- `policy.archival_reasons: [done, cancelled]`
- `activity_log: false`
- `pipeline.claim_timeout: "99h"`
- `agents.agent_map: {alpha: some-agent}`
- `pipeline.default_priority: "low"`
- `pipeline.wave_size: 100`
- `policy.non_impl_tags: [custom-tag]`
- `pipeline.entry_status: "alpha"`
- `pipeline.terminal_status: "gamma"`

**Expected post-#1439 behaviour:** `KanbanEngine(kanban_dir).board_config` returns product constants for all 13 categories — none of the overrides above take effect on the engine-facing topology. The config.yml (if still read at all) may retain `next_id` and other non-topology fields without altering constants.

---

### AC Coverage

| AC | Coverage |
|----|---------|
| AC1 — scratch-board probe (13 categories) | Probe notes above list all 13 categories with expected values |
| AC2 — contract inspection (BoardConfig, load_config, board_config) | Pre/post state documented; artifact inspection criteria specified |
| AC3 — negative probe (expanded override list) | All 13 config keys enumerated; expected no-effect outcome stated |
| AC4 — no pytest/vitest execution | Confirmed — no test code written, no test file created |

**Total:** 0 test files, 0 test functions. Pass-through — probes serve as contract specification for #1439 (RED/GREEN phases).
[[2026-05-08]]
## Builder Notes
- Non-implementation task — no code changes needed.
- Verified AC scope is probe-only contract notes (td:0) with explicit out-of-scope for source changes and test execution.
- Tests: not run by design for this task type.
- Lint: not run by design for this task type.
- Passing through to review.
[[2026-05-08]]
## Review Evidence
### Test Results
- Not applicable. This is a td:0 notes-only probe task with no test code or executable proof surface per [.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md](.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md#L44), [.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md](.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md#L91), and [.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md](.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md#L168-L170). Workspace search found no task-local test files matching `tests/**/*1438*`.

### Lint Results
- Not applicable. No source or test files were changed for this task; builder explicitly recorded no lint run by design in [.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md](.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md#L175-L177).

### Coverage
- Not applicable for td:0 probe notes.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| AC1 | Scratch-board probe records constant-based startup with no `config.yml` and enumerates statuses, routing, activity behavior, and storage paths in [.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md](.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md#L101-L119). | PASS |
| AC2 | The probe correctly targets `BoardConfig`, `load_config`, and `KanbanEngine.board_config` in [.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md](.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md#L125), but its current-state note says `KanbanEngine.board_config()` does not exist in [.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md](.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md#L130) while the live engine already defines `def board_config(self) -> BoardConfig` in [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L457-L463). The same AC2 artifact-inspection checklist omits storage-path mutability from the required `BoardConfig.model_fields` proof in [.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md](.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md#L136), even though storage paths are part of the topology contract in [.owlbear/kanban/tasks/1439-p4-02-collapse-kanban-engine-topology-into-product-constants.md](.owlbear/kanban/tasks/1439-p4-02-collapse-kanban-engine-topology-into-product-constants.md#L32) and the current schema exposes mutable path fields through `PathsConfig` and `BoardConfig.paths` in [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L107-L113) and [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L190). | FAIL |
| AC3 | Negative probe enumerates status, priority, path, activity, timeout, routing, and other override attempts, then states they must not affect engine-facing topology in [.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md](.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md#L145-L157). | PASS |
| AC4 | The task explicitly remains notes-only with no pytest/vitest execution in [.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md](.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md#L168-L170). | PASS |

### Findings
1. AC2 misstates the live API surface. The probe says `KanbanEngine.board_config()` does not exist, but the current engine already exposes that method. For a contract-inspection probe, that is not a harmless wording issue; it weakens the downstream inspection target and can let #1439 “prove” the wrong interface shape.
2. AC2 does not fully inspect storage-path mutability. The task treats storage paths as topology in AC1/AC3, and #1439 makes storage paths part of the product-topology contract, but the AC2 checklist omits `paths.tasks_dir` and `paths.archive_dir` from the required mutability-removal proof.

### Deductions
-0.10 incorrect current-state API description for `KanbanEngine.board_config`.
-0.08 incomplete artifact-inspection checklist for storage-path topology fields.
-0.02 no direct commit/diff evidence for immutability checks on this notes-only pass-through task.

### Verdict
FAIL -> todo
Confidence: 0.75
Reason: first-cycle probe-quality gap. Implementation changes are not needed; the test-writer must tighten the probe notes so #1439 inherits an accurate, complete contract.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Correct the AC2 current-state probe so it reflects the live `KanbanEngine.board_config()` method and explains the real pre-#1439 exposure of config-backed topology. | .owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md, serve/kanban/src/owlbear_kanban/engine.py | [.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md](.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md#L130), [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L457-L463) |
| 2 | test-writer | Extend the AC2 artifact-inspection checklist to require proof that mutable storage-path fields are removed or made non-authoritative alongside the other topology fields. | .owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md, serve/kanban/src/owlbear_kanban/models.py | [.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md](.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md#L136), [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L107-L113), [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L190) |
[[2026-05-08]]
## Test-Writer Notes (Revision — Review FAIL corrections)

**Type:** type:test pass-through — no test code written. All AC lines are td:0 (probe notes only).

**Review FAIL items addressed:**
1. AC2 current-state for `KanbanEngine.board_config()` was wrong — method already exists. Corrected below.
2. AC2 artifact-inspection checklist was missing storage-path fields. Extended below.

---

### AC2 — Contract-Inspection Probe (CORRECTED)

**Target symbols:** `BoardConfig` (`models.py`), `load_config` (`config_loader.py`), `KanbanEngine.board_config` (`engine.py`).

**Current state (pre-#1439):**
- `BoardConfig` has `statuses: list[str]`, `priorities: list[str]`, `paths: PathsConfig` (with `tasks_dir: str`, `archive_dir: str`), `pipeline: PipelineConfig` (with `entry_status`, `terminal_status`, `wave_size`, `claim_timeout`, `default_priority`), `agents: AgentsConfig` (with `agent_map`), `policy: PolicyConfig` (with `non_impl_tags`, `archival_reasons`), `activity_log: bool` — all user-editable Pydantic fields (`models.py` L107–197).
- `load_config(kanban_dir: Path) -> BoardConfig` — requires `config.yml`; raises `FileNotFoundError` when absent; returns a model whose topology fields are fully driven by the YAML file.
- `KanbanEngine.board_config()` — **already exists** (`engine.py` L457–L463); returns `self._config.model_copy(deep=True)`. Today that deep copy still exposes all topology fields as user-editable Pydantic values (statuses, priorities, paths, pipeline, agents, policy, activity_log) because `self._config` is fully driven by the YAML file. The method exists; the problem is that the config backing it is mutable and file-driven.

**Expected post-#1439 contract:**
- Topology constants are not present as mutable Pydantic fields on `BoardConfig` (or `BoardConfig` is replaced/deprecated with a frozen constants object).
- `load_config` signature remains `(kanban_dir: Path)` but does NOT raise `FileNotFoundError` when config.yml is absent — it returns a constants-only object (or the function is replaced by a constants accessor).
- `KanbanEngine.board_config` exposes a read-only view where all 13 constant categories match the product-defined values above, regardless of any config file content.
- Artifact inspection evidence: `inspect.signature(load_config)` accepts `kanban_dir: Path`; returned object's topology attributes match the constant table; `BoardConfig.model_fields` (or equivalent) does not include mutable topology keys (statuses, priorities, archival_reasons, agent_map, non_impl_tags, wave_size, claim_timeout, entry_status, terminal_status, default_priority, activity_log, **paths.tasks_dir, paths.archive_dir**). The `PathsConfig` sub-model fields `tasks_dir` and `archive_dir` are also mutable topology fields — post-#1439 these must not be user-overridable (current `BoardConfig.paths: PathsConfig` exposes them as editable strings in `models.py` L107–L113 and L190).

---

### AC Coverage (unchanged from prior cycle — all probes still valid)

| AC | Coverage |
|----|---------|
| AC1 — scratch-board probe (13 categories) | Probe notes in prior cycle list all 13 categories with expected values |
| AC2 — contract inspection (BoardConfig, load_config, board_config) | Corrected: pre-state now accurately describes live `board_config()` method; artifact-inspection checklist extended with storage-path fields |
| AC3 — negative probe (expanded override list) | All 13 config keys enumerated; expected no-effect outcome stated |
| AC4 — no pytest/vitest execution | Confirmed — no test code written, no test file created |

**Total:** 0 test files, 0 test functions. Pass-through — corrected probes serve as contract specification for #1439.
[[2026-05-09]]
## Builder Notes
- Non-implementation task pass-through confirmed from Test-Writer Notes (td:0 probe-only scope).
- Code changes: none.
- Tests: not run by design for this task type.
- Lint: not run by design for this task type.
- Coverage: not applicable.
- Evidence summary: AC scope is notes-only contract probes; source changes and executable proof are explicitly out of scope for this task.
- Fixes applied: none required.
[[2026-05-09]]
## Review Evidence
### Test Results
- Not applicable. This is a td:0 notes-only probe task, and AC4 explicitly limits proof to probe notes and contract-inspection artifacts in [.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md](.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md#L34) and [.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md](.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md#L253). Workspace file search found no task-local test files matching `tests/**/*1438*`.
- Quality-runner was not dispatched because there is no executable td:0 test/lint surface for this task review.

### Lint Results
- Not applicable. The review scope is the kanban task artifact itself; no task-local source or test files exist to lint.

### Coverage
- Not applicable for td:0 probe notes.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| AC1 | The scratch-board probe still defines a board with only `tasks/`, `archive/`, and `decisions/`, no `config.yml`, and enumerates the expected topology constants in [.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md](.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md#L95) and [.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md](.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md#L101). | PASS |
| AC2 | The corrected AC2 section now matches the live API surface by stating that `KanbanEngine.board_config()` already exists and returns a deep copy, consistent with [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L457) and [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L463). It also extends the artifact-inspection checklist to cover mutable storage-path topology fields, which the live schema currently exposes via [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L107), [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L112), [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L113), [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L166), and [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L190). The corrected probe is recorded in [.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md](.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md#L227) and [.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md](.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md#L236). | PASS |
| AC3 | The negative probe still enumerates config overrides for status, priority, path, archive reason, activity logging, timeout, routing, and other topology fields, then requires the engine-facing contract to ignore them in [.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md](.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md#L140) and [.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md](.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md#L157). This remains aligned with the downstream contract in [.owlbear/kanban/tasks/1439-p4-02-collapse-kanban-engine-topology-into-product-constants.md](.owlbear/kanban/tasks/1439-p4-02-collapse-kanban-engine-topology-into-product-constants.md#L32). | PASS |
| AC4 | The task remains notes-only with no pytest/vitest execution as functional proof in [.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md](.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md#L34) and [.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md](.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md#L253). | PASS |

### Findings
- No blocking findings. The prior AC2 issue is corrected in the revision section, and the probe contract is now accurate and complete enough for task #1439.

### Deductions
-0.03 earlier superseded AC2 wording remains in task history above the corrected section; downstream readers must use the later revision at [.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md](.owlbear/kanban/tasks/1438-p4-01-probe-fixed-kanban-topology-contract.md#L227).
-0.02 no direct commit/diff evidence for immutability checks on this notes-only pass-through task.

### Verdict
PASS -> docs
Confidence: 0.95
Reason: The corrected AC2 probe now reflects the live `board_config()` API and explicitly includes storage-path topology in the inspection contract, closing the only prior blocker while preserving the td:0 notes-only scope.

### Action
- Advanced to docs.
[[2026-05-09]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | No behavior, API, CLI, config, or package structure changes — notes-only probe task |
| 2 | Module docstrings | No | N/A | No Python modules created or modified (Builder Notes: "Code changes: none") |
| 3 | External attribution | No | N/A | No external patterns used |
| 4 | Research doc | No | N/A | No research doc produced |
| 5 | Diagram maintenance (describes match) | No | N/A | `kanban.excalidraw` describes `.owlbear/kanban/**` but no architectural change occurred — only task body notes written; diagram accuracy unaffected |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested |
| 7 | Deletion detection | No | N/A | No files deleted |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `.owlbear/kanban/tasks/1438-*.md` | OUT (task artifact, not IN-scope doc) | N/A |
| `serve/kanban/src/owlbear_kanban/engine.py` | OUT (source, referenced only, not changed) | N/A |
| `serve/kanban/src/owlbear_kanban/models.py` | OUT (source, referenced only, not changed) | N/A |
| `serve/kanban/src/owlbear_kanban/config_loader.py` | OUT (source, referenced only, not changed) | N/A |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no scratch files matching `1438-*` existed)
[[2026-05-09]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 — scratch-board probe (13 categories) | Task body enumerates all 13 topology constant categories (statuses, priorities, archival_reasons, entry/terminal status, default priority, claim timeout, wave size, routing, non_impl_tags, activity_log, storage paths) with expected values | PASS |
| AC2 — contract inspection (BoardConfig, load_config, board_config) | Corrected section accurately states `KanbanEngine.board_config()` exists at engine.py L457–463; artifact-inspection checklist extended to include storage-path mutability via PathsConfig (models.py L107–113, L190). Spot-checked against live code — accurate. | PASS |
| AC3 — negative probe (expanded override list) | All 13 config override keys enumerated with expected no-effect outcome stated | PASS |
| AC4 — no pytest/vitest execution | No test files matching `*1438*` found; 0 test files, 0 test functions — confirmed notes-only | PASS |

### Test Results
- pytest: 4915 passed, 247 failed, 4 skipped — all failures pre-existing (accessor migration, mcp-memory schema, PDS v4 migration); none in task scope (no code changed)
- vitest: 1163 passed, 17 failed — all failures pre-existing (PDS migration, Shell, ErrorContract); none in task scope
- ruff: 1 fixable F401 in unrelated file (serve/tools/tests/test_test_root.py)
- eslint: 1 error + 3 warnings in unrelated files

### Architect Quality: 4/5
AC well-structured for probe scope. Refinement expanded 13 categories to match #1439 surface after challenger feedback. Minor gap: codebase context listed engine.py L331–430 but `board_config()` is at L457, outside that range — contributed to test-writer's initial AC2 misstatement. Filled by reviewer in cycle 1.

### Deduction Breakdown
- AC lines: 4/4 with evidence → no deduction
- Lint: no task-scope violations → no deduction
- AC quality: 4/5 (>3) → no deduction
- Reviewer evidence: present, detailed, two cycles with PASS at 0.95 → no deduction
- Full-suite failures: 264 total, 0 in task scope → no deduction
- Superseded AC2 wording remains in task history above corrected section; downstream #1439 readers must use the later revision → -0.02

### Confidence: 0.98
### Action: archive