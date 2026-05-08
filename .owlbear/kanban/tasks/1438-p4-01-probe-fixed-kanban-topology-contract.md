---
id: 1438
title: 'P4-01: Probe fixed kanban topology contract'
status: todo
priority: needed
created: 2026-05-08T19:31:45.300155+00:00
updated: 2026-05-08T20:33:12.826677+00:00
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