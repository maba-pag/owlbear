---
id: 1155
title: Implement config.yml schema grouping (nested sub-models)
status: research
priority: nice-to-have
created: 2026-04-28T16:56:28.330827+00:00
updated: 2026-04-29T01:40:59.242759+00:00
tags:
- scope:kanban
parent:
depends_on:
- 1094
- 1170
- 1171
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

[[2026-04-28]]
## Research
- Research doc: .owlbear/research/1155-config-schema-grouping-validation.md
- Sources: 8 studied, 6 high-relevance (all internal)
- Recommendation: Block for pre-implementation resolution (confidence: .45)
- Follow-up tasks created: #1170 (version semantics), #1171 (write path unification), #1172 (MCP bug fix) — all at research
- Decision requests: 1 blocking T3 DR created (.owlbear/decisions/pending/1155-config-schema-grouping.md)

## Challenge Results
- Challenger: block (overall risk: high)
- Confidence in original: .34
- Key challenges accepted: version contract contradiction (critical), defaults.priority taxonomy gap (critical), migration infra gap (moderate), blast-radius understatement (moderate)

## Key Findings
1. Version field contradiction: AC says v10→v11 but engine treats version=legacy (#1170)
2. defaults.priority fragile: save_config strips defaults, works only by model-default coincidence
3. Three divergent config write paths must unify before implementation (#1171)
4. Pre-existing bug: MCP server.py L481 broken on new-schema boards (#1172)
5. All Brief A/B/C tasks are archived — gating condition resolved
[[2026-04-28]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: schema grouping refactor |
| Interface clarity | FAIL | AC line "version bump (10 → 11)" contradicts engine semantics — version field = legacy marker, not schema tracker |
| Dependency correctness | FAIL | Missing deps on #1170 (version semantics) and #1171 (write path unification) — added. #1094 archived (resolved). |
| Module layering | PASS | Config grouping stays within kanban domain |
| TDD compliance | PASS | Would need test task at todo entry |
| KISS/YAGNI | PASS | Grouping is warranted — 14 flat keys is unwieldy |
| Premise challenge | PASS | Consolidation is justified after Brief stabilization |
| Pattern consistency | FAIL | AC assumes version field tracks schema evolution; codebase uses it as legacy detection flag — fundamental mismatch |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | scope:kanban only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| engine.py L471-475 | v11 version field triggers legacy detection | Grouped config treated as legacy | No | Config corruption |
| storage.save_config L250 | Strips version + defaults on write-back | defaults.priority lost after first save | Silently caught | Priority resets to model default |
| migrate._migrate_config | No v10→v11 path exists | Migration skipped or crashes | No | Upgrade failure |

### Design Diverge
- Trigger: skipped — cannot evaluate design approaches while foundational contradictions are unresolved

### Challenge Results
- Challenger: block (confidence .34) — from prior research cycle
- Architect response: accepted — three critical contradictions confirm block

### Verdict: REJECT
### Action Taken
Rejected to research. Three blocking issues prevent implementation:

1. **T3 DR unresolved**: `.owlbear/decisions/pending/1155-config-schema-grouping.md` is still `response: pending`. Per criterion 12, no approved DR for T3 = reject.
2. **Version semantics contradiction** (#1170 at research): AC says v10→v11 but engine treats version field as legacy marker. These are incompatible — resolution needed before AC can be finalized.
3. **Config write path divergence** (#1171 at research): Three independent write paths (config_loader, storage, migrate) have different serialization contracts. Must be unified before grouped schema can be safely implemented.

Added `depends_on: [1170, 1171]`. Task should return to backlog only after:
- T3 DR is resolved (user decision on schema migration strategy)
- #1170 resolves version field semantics
- #1171 unifies config write paths
- AC is rewritten to align with resolved decisions

[[2026-04-29]]

## Clarification Requested

**Decision field mismatch detected.** The DR frontmatter contained `response: approved` but the `decision:` field held meta-commentary ("this is not a valid DR...") instead of a valid option label from the body's Options section.

**Guidance:** This DR was not created by the scribe and lacks proper decision options. Please review the research findings in `.owlbear/research/1155-config-schema-grouping-validation.md` and either:
- Create a properly scoped DR with explicit options (A/B/C with pros/cons), or
- Provide direct guidance on how to proceed with the schema grouping task

Task remains blocked pending your clarification.