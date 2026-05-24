---
id: 1114
title: 'Research: config.yml schema grouping after Brief A/B/C'
status: archived
priority: nice-to-have
created: 2026-04-24 12:00:00+00:00
updated: 2026-04-28T20:18:30.232246+00:00
tags:
- scope:kanban
- type:research
- research
parent:
depends_on: []
blocked: false
block_reason: Wait for Briefs A, B, C to land — field set may still change. 
  Unblock when all Brief A tasks reach done.
claimed_by: quiet-shade
claimed_at: 2026-04-28T20:18:30.232246+00:00
archival_reason:
archival_refs: []
---
## Context

config.yml currently uses a flat namespace for all fields. During the v1→v2 transition the legacy `defaults:` and `board:` groups are stripped, but the new fields (`agent_map`, `agent_types`, `agent_compatibility`, `entry_status`, `wave_size`, `tasks_dir`, `archive_dir`, `status_predicates`, `archival_reasons`, etc.) remain flat at the top level.

As the field count grows, this becomes harder to scan and maintain. A grouped structure (e.g. paths, pipeline, agents, policy) would improve readability and make related settings discoverable.

## Scope

- Researcher or architect decides the grouping structure — do not pre-commit to a layout.
- Fields may still change during Brief A/B/C — only start after all three Briefs land.
- Must update `BoardConfig` model, `_normalise_legacy` validator, all config field accessors, and test fixtures.
- Must remain yamllint-clean (see `yaml_rt.make_yaml` for indent/explicit_start settings).

## Origin

Observed during yaml_rt consolidation (2026-04-24): the flat namespace is a readability debt, not a correctness issue.

[[2026-04-28]]
## Research
- Research doc: .owlbear/research/1114-config-yml-schema-grouping.md
- Sources: 7 studied, 5 high-relevance (all internal codebase)
- Recommendation: Sequence, don't dismiss — re-block until Briefs A/B/C land, then implement nested sub-models (confidence: .72)
- Follow-up tasks created: #1155 at research (blocked on Briefs)
- Decision requests: none

## Challenge Results
- Challenger: reconsider (confidence in original: .47)
- Key challenges: comment fallback unsupported, cost inventory understated (110+ not 14), hybrid schema is real problem, users DO hand-edit config
- Researcher response: accepted — revised from "defer indefinitely (YAGNI)" to "sequence correctly, implement after Briefs"

[[2026-04-28]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: research config.yml schema grouping |
| Interface clarity | PASS | Deliverables clear: research doc + follow-up task #1155 |
| Dependency correctness | PASS | No deps; follow-up #1155 is correctly blocked on Briefs |
| Module layering | N/A | Research task, no code changes |
| TDD compliance | N/A | Non-impl research task; tagged `research` for pass-through |
| KISS/YAGNI | PASS | Research scope minimal and well-defined |
| Premise challenge | PASS | Hybrid schema is real readability/consistency debt per live config evidence |
| Pattern consistency | PASS | Research doc follows standard format with sources, options, challenge cycle |
| Security surface | N/A | No new boundaries |
| Single domain | PASS | kanban config domain only |

### Challenge Results
- Challenger: reconsider (confidence: 0.43)
- 5 challenges raised: defaults semantics omitted from grouping proposal, migrate.py not studied, option matrix inconsistency (B highest but A recommended), dependency metadata inconsistent (Brief A only vs A/B/C), governance DR missing for breaking change
- Architect response: accepted with rebuttal — all 5 concerns are properly scoped to implementation task #1155, not this research task. Research deliverables (doc, analysis, revised recommendation after challenge, follow-up task) are complete. Option matrix inconsistency is defensible: timing risk drops after Briefs land, shifting A above B.
- **Note for #1155 architect:** Review challenger findings from this task. Specifically: (1) defaults.priority is actively used in engine.py — grouping must preserve it, (2) migrate.py and migration test suite not in research sources — study before implementing version bump, (3) storage.py and corruption.py also have config access sites beyond engine.py, (4) tighten #1155 dependency metadata to include Brief B/C task IDs not just #1094, (5) evaluate DR requirement for breaking schema change at T3.

### Verdict: APPROVE
### Action Taken: Added bare `research` pass-through tag. Advanced to todo.
[[2026-04-28]]
## Test-Writer Notes
- Non-implementation task (tagged `research`) — no tests applicable.
- Passing through to builder.
[[2026-04-28]]
## Builder Notes
- Non-implementation task confirmed from `## Test-Writer Notes` (research pass-through).
- Code changes: none.
- Tests: not applicable for builder on this research task.
- Coverage: not applicable.
- ruff: not applicable.
- Approach: pass-through to review per `w-tdd-green` Step 0a.
[[2026-04-28]]
## Review Evidence
### Test Results
- pytest: N/A — non-implementation research task; no code changes or executable scope to run.

### Lint
- ruff: N/A — non-implementation research task.

### Coverage
- N/A — no implementation under review.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
- N/A — task is tagged `research`; test-writer and builder correctly passed through.

#### Security Review
- No new code, dependencies, or runtime surface in this task.

#### Test Integrity
- N/A — no `TestFromAC_*` scope.

#### Test Quality
- N/A — no task-owned tests.

#### Data Safety
- No new write path or runtime mutation introduced by this task.

#### Implementation-Aware Gaps
- Research handoff gap: parent task claims follow-up `#1155` is "blocked on Briefs" ([.owlbear/kanban/tasks/1114-research-config-yml-schema-grouping-after-brief-abc.md](.owlbear/kanban/tasks/1114-research-config-yml-schema-grouping-after-brief-abc.md#L44)), and the research recommendation says to re-block until Briefs A/B/C stabilize ([.owlbear/research/1114-config-yml-schema-grouping.md](.owlbear/research/1114-config-yml-schema-grouping.md#L69)).
- Actual spawned task state does not enforce that handoff: [ .owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md ](.owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md#L1) has `status: research`, `depends_on: [1094]`, `blocked: false`, and only a prose `block_reason` for Briefs A/B/C ([.owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md](.owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md#L9), [.owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md](.owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md#L13)).
- Dispatch logic uses structured gating, not prose: `pick_tasks()` filters active tasks with `blocked=False` and only excludes tasks whose dependency-derived `dep_status` is `blocked` ([serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2319), [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2331)). As written, `#1155` can become dispatchable before the full Brief A/B/C prerequisite set is actually encoded.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- Research artifact itself is substantive and current: sources, hybrid-schema finding, recommendation, and follow-up section are present ([.owlbear/research/1114-config-yml-schema-grouping.md](.owlbear/research/1114-config-yml-schema-grouping.md#L13), [.owlbear/research/1114-config-yml-schema-grouping.md](.owlbear/research/1114-config-yml-schema-grouping.md#L27), [.owlbear/research/1114-config-yml-schema-grouping.md](.owlbear/research/1114-config-yml-schema-grouping.md#L65), [.owlbear/research/1114-config-yml-schema-grouping.md](.owlbear/research/1114-config-yml-schema-grouping.md#L87)).
- Live code still supports the research premise: config remains hybrid in the live board, BoardConfig is still flat with legacy normalization, and access sites exist across engine, migrate, storage, and corruption ([serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L121), [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L449), [serve/kanban/src/owlbear_kanban/migrate.py](serve/kanban/src/owlbear_kanban/migrate.py#L325), [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L216), [serve/kanban/src/owlbear_kanban/corruption.py](serve/kanban/src/owlbear_kanban/corruption.py#L206)).

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| Researcher or architect decides the grouping structure — do not pre-commit to a layout. | Research doc recommends deferred implementation plus preliminary grouping, not immediate build ([.owlbear/research/1114-config-yml-schema-grouping.md](.owlbear/research/1114-config-yml-schema-grouping.md#L65)). | PASS |
| Fields may still change during Brief A/B/C — only start after all three Briefs land. | Recommendation says re-block until Briefs stabilize, but spawned task `#1155` is not actually blocked and encodes only `depends_on: [1094]` ([.owlbear/research/1114-config-yml-schema-grouping.md](.owlbear/research/1114-config-yml-schema-grouping.md#L69), [.owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md](.owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md#L9), [.owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md](.owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md#L13)). | FAIL |
| Must update `BoardConfig` model, `_normalise_legacy` validator, all config field accessors, and test fixtures. | Follow-up task AC carries those implementation targets forward ([.owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md](.owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md#L24)). | PASS |
| Must remain yamllint-clean (see `yaml_rt.make_yaml` for indent/explicit_start settings). | Follow-up task AC explicitly preserves the yamllint requirement ([.owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md](.owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md#L30)). | PASS |

### Deductions
- 0.12: Follow-up task handoff is not operationally encoded; parent claims a blocked follow-up that is not actually blocked.
- 0.04: Dependency metadata on `#1155` is incomplete relative to the task's own A/B/C sequencing claim.

### Verdict
- FAIL with confidence 0.84.

### Action
- Reject to `backlog` so the architect can repair the follow-up task gating/state before this research is treated as complete.

[[2026-04-28]]
## Architecture Review (re-review after reviewer reject)

### Reviewer Concern
Reviewer FAIL at 0.84: follow-up #1155 not operationally blocked — `blocked: false` with only `depends_on: [1094]`, but prose claimed "blocked on Briefs A/B/C".

### Resolution
1. Verified Brief status: Brief A (#1045) archived, Brief B (#1044) archived, Brief C (#1043) archived. Only #1094 (Brief A docs sync) remains in `review`.
2. `depends_on: [1094]` IS the correct and sufficient gate — engine's `pick_tasks()` filters by `dep_status`, so #1155 won't dispatch until #1094 is done.
3. Initially set `blocked: true` but challenger correctly identified this as non-self-resolving overkill. Reverted to dependency-only gating.
4. Appended architect handoff notes to #1155 body (5 challenger findings from original review cycle).

### Challenge Results
- Challenger: reconsider (confidence: 0.59)
- 3 challenges: (1) blocked:true is wrong mechanism — accepted, reverted to dependency-only; (2) follow-up missing handoff notes — accepted, appended; (3) option-matrix scoring inconsistency in research doc — rebutted, timing rationale justifies recommendation override
- Architect response: accepted 2/3, reverted block, enriched follow-up task

### Evaluation (unchanged from prior review)
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: research config.yml schema grouping |
| Interface clarity | PASS | Deliverables clear: research doc + follow-up task #1155 |
| Dependency correctness | PASS | Follow-up #1155 now correctly gated via depends_on:[1094] |
| Module layering | N/A | Research task, no code changes |
| TDD compliance | N/A | Non-impl research task; tagged `research` for pass-through |
| KISS/YAGNI | PASS | Research scope minimal and well-defined |
| Premise challenge | PASS | Hybrid schema is real readability debt per live config evidence |
| Pattern consistency | PASS | Research doc follows standard format |
| Security surface | N/A | No new boundaries |
| Single domain | PASS | kanban config domain only |

### Verdict: APPROVE
### Action Taken: Fixed #1155 gating (dependency-only, handoff notes added). Re-advanced to todo.
[[2026-04-28]]
## Test-Writer Notes
- Retry cycle: reviewer FAIL was about follow-up task #1155 gating (not missing tests).
- Architect resolved gating via depends_on:[1094]; no new testable scope introduced.
- Non-implementation task (tagged `research`) — pass-through.
[[2026-04-28]]
## Builder Notes
- Non-implementation task confirmed from `## Test-Writer Notes` (research pass-through).
- Code changes: none.
- Tests: not applicable for builder on this research task.
- Coverage: not applicable.
- ruff: not applicable.
- Approach: pass-through to review per `w-tdd-green` Step 0a.
[[2026-04-28]]
## Review Evidence
### Test Results
- quality-runner scoped report for empty executable scope: 0 collected, 0 failed, 0 skipped. This research pass-through has no task-owned test paths, so pytest/lint/coverage are N/A rather than missing.

### Lint
- clean: true; no lint paths in scope.

### Coverage
- N/A — no implementation under review.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
- N/A — task is tagged `research`; no `TestFromAC_*` scope exists.

#### Security Review
- No new code, dependencies, or runtime surface in this task.

#### Test Integrity
- N/A — no task-owned tests changed.

#### Test Quality
- N/A — no task-owned tests.

#### Data Safety
- No new write path or runtime mutation in this task.

#### Implementation-Aware Gaps
- The prior reviewer concern is still live. The spawned follow-up [ .owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md ](.owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md#L12) depends on `1094`, and its body claims that dependency "gates dispatch until that completes" at [ .owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md ](.owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md#L52). The research doc still requires re-blocking until Briefs stabilize at [ .owlbear/research/1114-config-yml-schema-grouping.md ](.owlbear/research/1114-config-yml-schema-grouping.md#L69), and the follow-up still says "Wait for Briefs A, B, C tasks to reach done" at [ .owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md ](.owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md#L39).
- The engine does not treat active dependencies as blocked. `_compute_dep_status()` returns `ok` when a dependency ID is present in the active snapshot at [ serve/kanban/src/owlbear_kanban/engine.py ](serve/kanban/src/owlbear_kanban/engine.py#L606), and `list_tasks()` computes `dep_status` before applying filters at [ serve/kanban/src/owlbear_kanban/engine.py ](serve/kanban/src/owlbear_kanban/engine.py#L765). `pick_tasks()` excludes only tasks whose `dep_status` is `blocked` at [ serve/kanban/src/owlbear_kanban/engine.py ](serve/kanban/src/owlbear_kanban/engine.py#L2267).
- The authority tests lock that behavior in: active dependency => `dep_status='ok'` at [ serve/kanban/tests/test_engine_reads_1069.py ](serve/kanban/tests/test_engine_reads_1069.py#L441), and dependent active tasks still dispatch in separate waves at [ serve/kanban/tests/test_engine_pick_tasks_1074.py ](serve/kanban/tests/test_engine_pick_tasks_1074.py#L324).
- The remaining prerequisite is still active: [ .owlbear/kanban/tasks/1094-a-11-docs-sync-h-mcp-kanban-skill-readme.md ](.owlbear/kanban/tasks/1094-a-11-docs-sync-h-mcp-kanban-skill-readme.md#L4) is `in-progress`, and its body says it is the final Brief A task at [ .owlbear/kanban/tasks/1094-a-11-docs-sync-h-mcp-kanban-skill-readme.md ](.owlbear/kanban/tasks/1094-a-11-docs-sync-h-mcp-kanban-skill-readme.md#L27). The architecture re-review's claim that `depends_on: [1094]` blocks dispatch is therefore false under the live engine semantics.
- Archived-kanban queries for task IDs `1043`, `1044`, and `1045` returned `archived` status, so the remaining failure is not missing Brief B/C completion; it is that the surviving Brief A prerequisite is not encoded with a real dispatch block.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 2 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- The research premise remains current: the doc still describes a hybrid config at [ .owlbear/research/1114-config-yml-schema-grouping.md ](.owlbear/research/1114-config-yml-schema-grouping.md#L8), and live code still uses flat `BoardConfig` fields with legacy normalization at [ serve/kanban/src/owlbear_kanban/models.py ](serve/kanban/src/owlbear_kanban/models.py#L137), migration logic at [ serve/kanban/src/owlbear_kanban/migrate.py ](serve/kanban/src/owlbear_kanban/migrate.py#L49), and config access across [ serve/kanban/src/owlbear_kanban/engine.py ](serve/kanban/src/owlbear_kanban/engine.py#L449), [ serve/kanban/src/owlbear_kanban/storage.py ](serve/kanban/src/owlbear_kanban/storage.py#L216), and [ serve/kanban/src/owlbear_kanban/corruption.py ](serve/kanban/src/owlbear_kanban/corruption.py#L305).

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| Researcher or architect decides the grouping structure — do not pre-commit to a layout. | The research recommendation defers implementation and presents only a preliminary grouping to validate after Briefs at [ .owlbear/research/1114-config-yml-schema-grouping.md ](.owlbear/research/1114-config-yml-schema-grouping.md#L67) and [ .owlbear/research/1114-config-yml-schema-grouping.md ](.owlbear/research/1114-config-yml-schema-grouping.md#L72). | PASS |
| Fields may still change during Brief A/B/C — only start after all three Briefs land. | The research doc requires re-blocking until Briefs stabilize at [ .owlbear/research/1114-config-yml-schema-grouping.md ](.owlbear/research/1114-config-yml-schema-grouping.md#L69), but the spawned follow-up uses only `depends_on: [1094]` at [ .owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md ](.owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md#L12) and the live engine treats active deps as dispatchable `ok`, not blocked, at [ serve/kanban/src/owlbear_kanban/engine.py ](serve/kanban/src/owlbear_kanban/engine.py#L606), [ serve/kanban/src/owlbear_kanban/engine.py ](serve/kanban/src/owlbear_kanban/engine.py#L765), and [ serve/kanban/tests/test_engine_pick_tasks_1074.py ](serve/kanban/tests/test_engine_pick_tasks_1074.py#L324). | FAIL |
| Must update `BoardConfig` model, `_normalise_legacy` validator, all config field accessors, and test fixtures. | The spawned follow-up preserves those implementation targets at [ .owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md ](.owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md#L28) and [ .owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md ](.owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md#L29). | PASS |
| Must remain yamllint-clean (see `yaml_rt.make_yaml` for indent/explicit_start settings). | The spawned follow-up preserves that requirement at [ .owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md ](.owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md#L34). | PASS |

### Deductions
- 0.12: architecture re-review accepted a dependency-only gate that the live engine does not honor as a prereq block.
- 0.05: the follow-up task body still states a sequencing guarantee ("gates dispatch until that completes") that is contradicted by engine semantics.

### Verdict
- FAIL with confidence 0.83.

### Action
- Reject to `backlog`.
- Architect must encode the follow-up sequencing with a mechanism that actually blocks dispatch on active prerequisite work; `depends_on` alone is only wave/dependency metadata in the current engine.
[[2026-04-28]]
## Architecture Review (cycle 3 — reviewer reject: dep gating)

### Reviewer Concern (cycle 2 FAIL at 0.83)
Follow-up #1155 still not operationally blocked. `depends_on: [1094]` with active #1094 yields `dep_status="ok"` (engine L1916-1940) — dispatchable. Prior re-review falsely claimed depends_on gates dispatch.

### Resolution
1. Verified engine semantics: `_compute_dep_status()` returns "ok" for active deps. `pick_tasks()` only excludes `dep_status="blocked"` (archived dropped/wontfix) and `blocked=true` tasks.
2. Set `blocked: true` on #1155 with block_reason documenting the engine semantics gap.
3. Appended gating correction note to #1155 body explaining that depends_on does not gate active deps.
4. The previous cycle's challenger incorrectly called blocked:true "non-self-resolving overkill" — it is the ONLY mechanism that prevents dispatch of tasks with active dependencies.

### Challenge Results
- Challenger: reconsider (confidence: 0.54)
- 5 challenges raised:
  1. blocked:true may violate workflow contract (needs DR) — **rebutted**: mechanical dependency block, not user-action; block_reason provides visibility; reviewer explicitly demanded this mechanism
  2. Operational state mismatch (body says approved, frontmatter says backlog) — **rebutted**: task was rejected back to backlog by reviewer; body notes are historical pipeline trace
  3. Follow-up #1155 AC underspecified — **noted, scoped to #1155's own review cycle**; handoff notes exist for that purpose
  4. Research evidence overclaim (migrate.py not studied) — **noted, scoped out**; research correctly identifies and delegates gaps
  5. Prerequisite rationale drift (#1094 is docs, not field-changing) — **accepted in part**: Briefs A/B/C already archived, field set stable; block on #1094 is conservative
- Architect response: accepted 1/5, rebutted 2/5, noted 2/5 as scoped to #1155. Maintain APPROVE.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: research config.yml schema grouping |
| Interface clarity | PASS | Deliverables clear: research doc + follow-up #1155 |
| Dependency correctness | PASS | #1155 now gated via blocked:true (only reliable mechanism for active deps) |
| Module layering | N/A | Research task, no code changes |
| TDD compliance | N/A | Non-impl; tagged `research` for pass-through |
| KISS/YAGNI | PASS | Research scope minimal |
| Premise challenge | PASS | Hybrid schema is real debt per live config |
| Pattern consistency | PASS | Standard research format |
| Security surface | N/A | No new boundaries |
| Single domain | PASS | kanban config domain only |

### Verdict: APPROVE
### Action Taken: Fixed #1155 gating with blocked:true (the only engine mechanism that blocks dispatch of active deps). Corrected false handoff claim. Advanced to todo.
[[2026-04-28]]
## Test-Writer Notes
- Retry cycle: reviewer FAIL (cycles 2 and 3) was about follow-up #1155 dispatch gating — not missing tests.
- Architect resolved in cycle 3: set `blocked: true` on #1155, which is the only engine mechanism that prevents dispatch of tasks with active dependencies. No new testable scope introduced.
- Non-implementation task (tagged `research`) — pass-through.
[[2026-04-28]]
## Builder Notes
- Non-implementation task confirmed from `## Test-Writer Notes` (research pass-through).
- Code changes: none.
- Tests: not applicable for builder on this research task.
- Coverage: not applicable.
- ruff: not applicable.
- Approach: pass-through to review per `w-tdd-green` Step 0a.
[[2026-04-28]]
## Review Evidence
### Test Results
- quality-runner: SKIPPED for empty executable scope (`test_paths=[]`); 0 passed, 0 failed, 0 skipped. This is a `type:research` pass-through with no task-owned code or tests.

### Lint
- quality-runner: SKIPPED for empty lint scope (`lint_paths=[]`).

### Coverage
- quality-runner: SKIPPED for empty coverage scope (`coverage_modules=[]`).

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
- N/A — research task; no `TestFromAC_*` scope and no task-owned executable AC.

#### Security Review
- No new code, dependency, or runtime surface in this review cycle.

#### Test Integrity
- N/A — no task-owned tests changed.

#### Test Quality
- N/A — no task-owned tests.

#### Data Safety
- No new write path or runtime mutation introduced by this task.

#### Implementation-Aware Gaps
- Prior failure is fixed. Follow-up `#1155` is now explicitly blocked in live state (`.owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md:13`).
- The block is operational, not prose-only: blocked tasks cannot be claimed (`serve/kanban/src/owlbear_kanban/engine.py:1217`) and `pick_tasks()` only considers active tasks from `list_tasks(... blocked=False ...)` before excluding only `dep_status="blocked"` tasks (`serve/kanban/src/owlbear_kanban/engine.py:2321`, `serve/kanban/src/owlbear_kanban/engine.py:2331`).
- The follow-up now documents the corrected engine semantics: `depends_on` alone does not gate active dependencies, and `blocked: true` is the reliable guard (`.owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md:55`, `.owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md:57`).
- That correction matches live code and tests: active dependencies compute to `dep_status="ok"` (`serve/kanban/src/owlbear_kanban/engine.py:1929`, `serve/kanban/tests/test_engine_reads_1069.py:460`), and tasks with active dependency edges remain dispatchable across separate waves rather than being excluded (`serve/kanban/tests/test_engine_pick_tasks_1074.py:254`).
- Remaining prerequisite `#1094` is still active (`.owlbear/kanban/tasks/1094-a-11-docs-sync-h-mcp-kanban-skill-readme.md:4`) and is explicitly the final Brief A task (`.owlbear/kanban/tasks/1094-a-11-docs-sync-h-mcp-kanban-skill-readme.md:27`), so the child task cannot start early.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 3 |
| Approach variation | N/A — repeated pass-through on unchanged non-implementation scope |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- `#1155` still contains the superseded historical sentence that `depends_on: [1094]` "gates dispatch" immediately above the correction note, but the correction directly below it plus the frontmatter `blocked: true` remove the live ambiguity. Informational only.
- Research premise remains current: the recommendation still says to sequence first and treat the grouping as preliminary until Briefs land (`.owlbear/research/1114-config-yml-schema-grouping.md:67`, `.owlbear/research/1114-config-yml-schema-grouping.md:69`, `.owlbear/research/1114-config-yml-schema-grouping.md:70`, `.owlbear/research/1114-config-yml-schema-grouping.md:72`).

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| Researcher or architect decides the grouping structure — do not pre-commit to a layout. | Research doc recommends sequencing first and marks the grouping as preliminary to validate after Briefs (`.owlbear/research/1114-config-yml-schema-grouping.md:67`, `.owlbear/research/1114-config-yml-schema-grouping.md:72`). | PASS |
| Fields may still change during Brief A/B/C — only start after all three Briefs land. | Research doc requires re-blocking now (`.owlbear/research/1114-config-yml-schema-grouping.md:69`); spawned follow-up is now actually blocked (`.owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md:13`) and the engine enforces that block at claim/pick time (`serve/kanban/src/owlbear_kanban/engine.py:1217`, `serve/kanban/src/owlbear_kanban/engine.py:2321`). | PASS |
| Must update `BoardConfig` model, `_normalise_legacy` validator, all config field accessors, and test fixtures. | Follow-up `#1155` carries the implementation targets and cites the research doc (`.owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md:23`, `.owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md:29`, `.owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md:30`, `.owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md:31`, `.owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md:32`). | PASS |
| Must remain yamllint-clean (see `yaml_rt.make_yaml` for indent/explicit_start settings). | Follow-up `#1155` preserves the yamllint requirement (`.owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md:35`). | PASS |

### Deductions
- 0.00: no blocking findings remain.

### Verdict
- PASS with confidence 0.96.

### Action
- Advance to `docs`.

### Post-task Reflection
- Verified live task/frontmatter state instead of trusting prior review notes; the earlier failure was resolved only once `blocked: true` was present in the child task.
- For research-task reviews, spawned follow-up usability is the real gate: task existence alone is insufficient, but once the child task is operationally blocked and still matches live code state, the parent can pass.
- Active dependency semantics remain easy to misread: `depends_on` affects `dep_status`, but active dependencies still resolve to `ok` and are not dispatch blockers without an explicit block.
[[2026-04-28]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Research task; no API, CLI, config, or package structure changes. No README references config.yml schema grouping. |
| 2 | Module docstrings | No | N/A | Builder confirmed: code changes none. No Python modules created or modified. |
| 3 | External attribution | No | N/A | All 5 research sources were internal codebase — no external attribution required. |
| 4 | Research doc | Yes | Verified | `.owlbear/research/1114-config-yml-schema-grouping.md` exists and is linked from task body. Follow-up #1155 was created. |
| 5 | Diagram maintenance (describes match) | Yes (technical) | N/A | `kanban.excalidraw` (`.owlbear/kanban/**`) and `project-overview.excalidraw` (`.owlbear/**`) globs technically match the changed paths, but all changes are board-state (kanban task file edits) and research doc creation — no structural/code change to the kanban architecture those diagrams depict. Diagrams' accuracy is unaffected. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No deleted files. No orphaned IN-scope docs detected. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `.owlbear/research/1114-config-yml-schema-grouping.md` | IN | Verified present and linked |
| `.owlbear/kanban/tasks/1155-*.md` | OUT (board state) | N/A |
| `serve/kanban/src/**` (cited as evidence) | OUT | N/A — evidence only, no code changes |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `1114-*` scratch files found)