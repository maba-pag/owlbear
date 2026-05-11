---
id: 1482
title: 'P1-01: Define proof-bundle taxonomy in r-pipeline-protocol'
status: todo
priority: critical
created: 2026-05-11T08:58:34.021832+00:00
updated: 2026-05-11T09:20:43.648119+00:00
tags:
- pipeline
- convention
- scope:skills
- agent
parent: 1481
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

1. `r-pipeline-protocol` defines the 5-value proof-bundle enum (skip | existing | smoke | behavioral | critical) with complete routing table (test-writer, challenger, code-reader, reviewer-scope columns)
2. Escalation modifiers (+challenge, +reader) documented with expansion rules, redundancy normalization, and invalid-token rejection
3. Legacy (td:N) compatibility mapping table for in-progress tasks present in same file

## Scope

- In: `share/skills/r-pipeline-protocol/SKILL.md`
- Out: Consumer skill changes (separate tasks)

Proof bundle: skip
Brief: see parent #1481
[[2026-05-11]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Defines taxonomy in one file only; consumer skill updates are separate tasks (#1483–#1487) |
| Interface clarity | PASS | AC names all 5 enum values, all 4 routing-table columns, both modifiers, and 3 modifier aspects (expansion, normalization, rejection) |
| Dependency correctness | PASS | No dependencies; this is the foundational task — all layer-2 tasks (1483–1487) depend on it |
| Module layering | N/A | Pure Markdown documentation change, no code imports |
| TDD compliance | PASS | Proof bundle: skip — no executable code produced. Pass-through tag `agent` present |
| KISS/YAGNI | PASS | Minimal scope: one section replacement in one file. No speculative features |
| Premise challenge | PASS | Brief documents concrete friction points with td:N (overload, coarse routing, unnecessary subagent overhead). Replacement taxonomy is well-motivated |
| Pattern consistency | PASS | Follows existing skill-file section conventions (tables, pipeline routing tables, subsection structure) |
| Security surface | N/A | No system boundaries affected |
| Single domain | PASS | Pipeline convention domain only |

### Codebase Context
- Target file: `share/skills/r-pipeline-protocol/SKILL.md` — existing "Test-Depth Convention" section at lines 124–147 defines td:N enum, routing table, and default rules
- Brief: `.owlbear/briefs/draft-proof-bundle-taxonomy/brief.md` — complete design with routing table, modifier rules, behavioral/critical discriminator, and legacy mapping
- The builder should replace the existing "Test-Depth Convention" section with the new "Proof-Bundle Taxonomy" section, retaining the legacy mapping as a subsection for backward compatibility with in-progress tasks

### Design Diverge
- Skipped — single clear approach from the approved brief; no competing designs

### Challenge Results
- Challenger: SKIPPED — all AC lines are td:0 equivalent (proof bundle: skip)

### Test Depth
- Proof bundle: skip (planner assignment confirmed correct)
- Test-writer: SKIP

### Verdict: APPROVE
### Action Taken: Advanced to todo. AC is precise and verifiable against the brief. Pass-through tag `agent` already present.