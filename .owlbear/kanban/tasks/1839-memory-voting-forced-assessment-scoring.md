---
id: 1839
title: Memory voting — forced assessment scoring
status: todo
priority: needed
created: 2026-05-24T18:57:20.675933+02:00
updated: 2026-05-24T19:02:22.445453+02:00
tags:
  - feature
  - memory
  - phase-2
parent:
depends_on:
  - 1848
ac:
  - 'AC1: Memory entries have `score` float field. Score = initial_confidence + (outstanding_count
    × 0.1) - (unremarkable_count × 0.01). Recall sorts by (state_rank, -score, id).
    X=0.1, Y=0.01 are named constants.'
  - 'AC2: `assess_memories` MCP tool accepts [{entry_id, bucket}] where bucket ∈ {outstanding,
    unremarkable, didnt_use, factually_wrong}. Updates counters + score atomically.
    Returns success/failure per entry. Validates: entry exists, voteable state (approved/curated/contested),
    valid bucket.'
  - 'AC3: `recall_memory` returns limit entries (default 20): limit-4 highest-score
    in scope, 2 lowest total assessments, 2 lowest outstanding_count. Dedup priority:
    explore > challenge > regular. Fewer entries than limit → return all.'
  - 'AC4: After assess_memories, check: if didnt_use_count > 50 × max(outstanding_count
    + unremarkable_count, 1) → state transitions to stale. Stale excluded from recall.'
  - 'AC5: First factually_wrong → state contested (still recalled). Second factually_wrong
    from different task → state disputed (excluded from recall).'
  - 'AC6: States contested, disputed, stale added. Contested: normal recall. Disputed
    + stale: excluded from recall. All resolvable by curator.'
  - 'AC7: Migration: existing entries get score=confidence, counters=0, state unchanged.
    Idempotent. Ordering identical pre-migration.'
  - 'AC8: Pipeline end_work protocol includes assessment instruction with opaque bucket
    framing (no scoring explanation).'
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective

Replace static confidence-based recall ordering with self-improving forced assessment scoring. Agents categorize all recalled entries at end-of-task into quality buckets; scores update on evidence only.

## Brief

Full brief: `.owlbear/briefs/draft-memory-voting/brief.md`

## Core Mechanism

1. Recall delivers 20 entries: 16 by score + 2 explore (lowest total assessments) + 2 challenge (lowest outstanding)
2. End-of-task: agent categorizes all 20 → outstanding (+X), unremarkable (-Y), didn't-use (0), factually-wrong (→ contested)
3. Score replaces confidence as sort key
4. Slot-efficiency block at 50× threshold → stale
5. Confirmation cycle: contested → disputed after second agent confirms

## Key Properties

- No time-based decay — moves only on assessment evidence
- Quality over popularity — outstanding is a quality judgment, not exposure count
- Opaque bucketing — agents don't know scoring mechanics
- Proven mediocrity sinks; unknown stays neutral

## Scope

- Model fields: outstanding_count, unremarkable_count, didnt_use_count, score
- States: contested, disputed, stale
- Score: initial_confidence + (outstanding × 0.1) - (unremarkable × 0.01)
- Recall: sort by (state_rank, -score, id) with 16+2+2 reserved slots
- MCP tool: assess_memories (batch entry_id→bucket)
- Slot-efficiency: didnt_use > 50 × max(outstanding + unremarkable, 1) → stale
- Confirmation: first factually_wrong → contested; second from different task → disputed
- Migration: score = confidence, counters = 0
- Instruction update: assessment framing in end_work protocol

## Constants

- X = 0.1 (outstanding boost)
- Y = 0.01 (unremarkable penalty)
- Stale threshold = 50×
- Slot allocation: 16 regular + 2 explore + 2 challenge = 20

## Out of Scope

- Cockpit UI (follow-on)
- Magnitude tuning (follow-on after 2-4 weeks live)
- Confidence deprecation (follow-on after 4-8 weeks)
- Per-agent score variants
- Assessment analytics

[[2026-05-24T19:02:22+02:00]]
## Planning
### Decomposition: Memory voting — forced assessment scoring
- Tasks created: 9
- Dependency layers: 4
- Phase: 2

### Task List
| ID | Title | Priority | Depends On | Tags |
|----|-------|----------|------------|------|
| 1840 | P2-01: State machine — contested, disputed, stale states | critical | — | phase-2, scope:memory, feature |
| 1841 | P2-02: Model fields — assessment counters and score computation | critical | — | phase-2, scope:memory, feature |
| 1842 | P2-03: Migration — score initialization from confidence | needed | 1841 | phase-2, scope:memory, migration |
| 1843 | P2-04: Recall — reserved explore and challenge slots | needed | 1840, 1841 | phase-2, scope:memory, feature |
| 1844 | P2-05: Slot-efficiency — auto-stale transition | needed | 1840, 1841 | phase-2, scope:memory, feature |
| 1845 | P2-06: Confirmation cycle — factually-wrong to contested/disputed | needed | 1840, 1841 | phase-2, scope:memory, feature |
| 1846 | P2-07: assess_memories MCP tool | needed | 1841, 1844, 1845 | phase-2, scope:memory, feature |
| 1847 | P2-08: Pipeline instruction — assessment protocol | needed | 1846 | phase-2, scope:memory, docs |
| 1848 | Consolidation test: memory voting integration | important | 1842-1847 | phase-2, scope:memory, consolidation-test |

### Dependency Graph
```mermaid
graph TD
  1840[\"#1840 State machine\"] 
  1841[\"#1841 Model + score\"]
  1842[\"#1842 Migration\"] --> 1841
  1843[\"#1843 Recall slots\"] --> 1840 & 1841
  1844[\"#1844 Slot-efficiency\"] --> 1840 & 1841
  1845[\"#1845 Confirmation\"] --> 1840 & 1841
  1846[\"#1846 assess_memories\"] --> 1841 & 1844 & 1845
  1847[\"#1847 Instructions\"] --> 1846
  1848[\"#1848 Consolidation\"] --> 1842 & 1843 & 1844 & 1845 & 1846 & 1847
  1839[\"#1839 Parent\"] --> 1848
```
