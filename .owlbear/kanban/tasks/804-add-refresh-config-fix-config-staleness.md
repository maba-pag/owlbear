---
id: 804
title: Add refresh_config + fix config staleness
status: todo
priority: needed
created: '2026-04-10T21:21:04.269881+00:00'
updated: '2026-04-13T02:07:49.975817+00:00'
tags:
- phase-1
- scope:mcp-kanban
- config
- rigor:thorough
parent: 798
depends_on:
- 803
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `refresh_config()` method on `KanbanEngine`: reloads config from disk, updates `self._config` + all derived state (tasks_dir, archive_dir, rank maps)
- `create_task` calls `refresh_config()` internally (or equivalent) to ensure fresh config for `next_id`
- After `refresh_config()`, `_status_rank()` and `_priority_rank()` use new config values
- #803 tests pass GREEN
- Existing MCP tests pass (O4)

## Context

Phase 1, independent pair. Depends on #803 (RED tests).
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`
[[2026-04-13]]
## Research
- Research doc: .owlbear/research/refresh-config-impl-804.md (existing, validated)
- Sources: 7 studied, 4 high-relevance (engine.py impl, config_loader, test files, #803 research)
- Recommendation: No new code needed — all 5 AC points already implemented. Builder phase is verification-only: run #803 tests + MCP tests, confirm code matches AC. (confidence: 0.95)
- Follow-up tasks created: none (implementation complete, tests passing)
- Decision requests: none
- Tier: T1 — Autonomous (verification pass, no arch/security implications)

## Validation Pass (2026-04-13)
Existing research doc from 2026-04-11 confirmed against current codebase:
- `refresh_config()` at engine.py L151-160: reloads `_config`, `_tasks_dir`, `_archive_dir`
- `create_task()` at engine.py L309-353: local `load_config()` + post-save `self._config = config` (failure-safe pattern)
- `_status_rank()` / `_priority_rank()` at L141-144: on-demand from `self._config`, no caching
- test_refresh_config_803.py: 6/6 PASSED
- test_config_staleness_fix_828.py: 6/6 PASSED
- Line numbers shifted (L106→L151 for refresh_config) due to upstream changes — analysis still valid

## Challenge Results
- Challenger: FALLBACK — T1 trivial finding (implementation already exists, all tests GREEN)
- Confidence in original: 0.95
- Key challenges: none (validation pass only)
- Researcher response: confirmed — no changes to recommendation
[[2026-04-13]]
## Architecture Review

### AC Assessment

| AC line | Assessment | Action |
|---------|-----------|--------|
| AC1: `refresh_config()` reloads config, updates `_config` + derived state | PASS — verified at engine.py L151-161: reloads via `load_config()`, updates `_tasks_dir`, `_archive_dir`. Rank maps (`_priority_rank`, `_status_rank` at L133-137) read `self._config` on every call (no caching), so they automatically reflect refreshed config. | None |
| AC2: `create_task` calls `refresh_config()` or equivalent | PASS — verified at engine.py L315: calls `load_config()` inside exclusive file lock, then at L346 assigns `self._config = config`, L348-349 updates `_tasks_dir`/`_archive_dir`. This is the "(or equivalent)" fresh-config pattern — stronger than `refresh_config()` because it operates under lock. | None |
| AC3: After `refresh_config()`, rank methods use new config | PASS — both methods are on-demand property lookups from `self._config` (L133-137), no caching. Verified by design. | None |
| AC4: #803 tests pass GREEN | VERIFIABLE — `test_refresh_config_803.py` exists with 6 tests. Research validation reports 6/6 PASSED. Dependency #803 in `review` (BLOCKED by Quality-Runner infra issue, not code quality). Builder can verify by running tests directly. | None |
| AC5: Existing MCP tests pass (O4) | VERIFIABLE — standard builder gate. | None |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | `refresh_config()` IS the config staleness fix — one logical concern despite "+" in title |
| Interface clarity | PASS | Method name, inputs (none), outputs (void), side effects (updates `_config`, `_tasks_dir`, `_archive_dir`) all specified |
| Dependency correctness | PASS | Depends on #803 (RED tests). #803 in review/blocked — correct dep, dispatch system will sequence |
| Module layering | PASS | All changes within `owlbear_kanban` engine, no cross-package concerns |
| TDD compliance | PASS | #803 is the preceding test task |
| KISS/YAGNI | PASS | Implementation already exists — verification-only build phase, no speculative additions |
| Premise challenge | PASS | All 5 AC points already implemented (confirmed at engine.py L133-161, L310-354). Task was planned before impl; now serves as formal pipeline verification. Valid progression. |
| Pattern consistency | PASS | Follows engine's existing config management patterns (load_config, save_config, BoardConfig model) |
| Security surface | PASS | No new system boundaries — config is loaded from trusted local YAML |
| Single domain | PASS | scope:mcp-kanban only |

### Failure Mode Map
N/A — no new codepaths introduced. Implementation pre-exists and is verified by #803 tests + #828 tests.

### Challenge Results
- Challenger: FALLBACK — no challenger agent available in current agent roster
- Confidence in APPROVE: 0.95 — all AC lines verifiable, implementation confirmed in codebase, tests reportedly passing, single-domain verification-only task

### Research Alignment
Research recommendation (confidence 0.95): "No new code needed — all 5 AC points already implemented. Builder phase is verification-only." Codebase inspection confirms this assessment at engine.py L133-161 and L310-354.

### Builder Guidance
This is a **verification-only** task. The builder should:
1. Run `test_refresh_config_803.py` — confirm 6/6 pass
2. Run `test_config_staleness_fix_828.py` — confirm 6/6 pass
3. Run MCP kanban test suite — confirm no regressions
4. Confirm code at engine.py matches AC (already verified in this review)

### Verdict: APPROVE
### Action Taken: Advanced to todo. Verification-only build phase — all AC already implemented. Dependency #803 must clear review before dispatch.