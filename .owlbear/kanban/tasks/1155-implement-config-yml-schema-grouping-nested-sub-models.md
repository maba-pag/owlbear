---
id: 1155
title: Implement config.yml schema grouping (nested sub-models)
status: research
priority: nice-to-have
created: 2026-04-28T16:56:28.330827+00:00
updated: 2026-04-28T18:51:21.544595+00:00
tags:
- scope:kanban
parent:
depends_on:
- 1094
blocked: true
block_reason: 'Wait for #1094 (Brief A docs sync) to reach done. depends_on alone
  does not block dispatch of active dependencies in the engine.'
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
## Context

Research doc: .owlbear/research/1114-config-yml-schema-grouping.md

config.yml uses a hybrid schema: legacy nested groups (board, defaults, tui) coexist with 14 flat Brief-C keys. After Briefs A/B/C stabilize the field set, consolidate into grouped structure.

## Acceptance Criteria

- [ ] BoardConfig uses nested Pydantic sub-models: paths, pipeline, agents, policy
- [ ] _normalise_legacy handles both flat (v10) and grouped (v11) inputs
- [ ] All config field accessors updated (40+ sites in engine.py, storage.py, etc.)
- [ ] All test fixtures updated (110+ matches across tests/ and serve/)
- [ ] Seed template uses new grouped format
- [ ] Live config migrated via version bump (10 → 11)
- [ ] yamllint-clean output (indent/explicit_start via yaml_rt.make_yaml)
- [ ] extra='allow' strategy documented for vendor fields in grouped schema

## Blocked

Wait for Briefs A, B, C tasks to reach done — field set may still change.



## Architect Handoff Notes (from #1114 review)

Review challenger findings from #1114 research. Specifically:
1. `defaults.priority` is actively used in engine.py — grouping must preserve it
2. migrate.py and migration test suite not in research sources — study before implementing version bump
3. storage.py and corruption.py also have config access sites beyond engine.py
4. Tighten dependency metadata to include Brief B/C task IDs not just #1094
5. Evaluate DR requirement for breaking schema change at T3

Brief status at handoff: Brief A (#1045) archived, Brief B (#1044) archived, Brief C (#1043) archived. Only #1094 (Brief A docs sync) remains in review — this task's `depends_on: [1094]` gates dispatch until that completes.
[[2026-04-28]]
## Gating Correction (from #1114 re-review cycle 3)

The prior handoff note incorrectly claimed `depends_on: [1094]` gates dispatch. Engine semantics: active dependencies yield `dep_status="ok"`, which is dispatchable. Only `blocked: true` (set above) reliably prevents dispatch. Unblock when #1094 reaches done.