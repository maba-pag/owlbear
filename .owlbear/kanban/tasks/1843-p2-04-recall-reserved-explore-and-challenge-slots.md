---
id: 1843
title: 'P2-04: Recall — reserved explore and challenge slots'
status: backlog
priority: needed
created: 2026-05-24T19:01:24.850020+02:00
updated: 2026-05-25T01:48:30.201817+02:00
tags:
  - phase-2
  - scope:memory
  - feature
parent: 1839
depends_on:
  - 1840
  - 1841
ac:
  - '`recall_memory` returns `limit` entries (default 20): `limit - 4` highest-score
    in-scope entries, 2 explore slots (lowest `outstanding_count + unremarkable_count
    + didnt_use_count`), 2 challenge slots (lowest `outstanding_count`). Named constants
    `SLOT_EXPLORE = 2` and `SLOT_CHALLENGE = 2` define reserved slot counts.'
  - 'Dedup priority: an entry selected for explore is not duplicated in challenge
    or regular slots; an entry selected for challenge is not duplicated in regular.
    When fewer in-scope entries exist than `limit`, all qualifying entries are returned
    without padding.'
  - The final returned list is sorted by `(state_rank, -score, id)` regardless 
    of which pool each entry was selected from. Callers receive a single ordered
    list, not categorized blocks.
  - 'Tiebreaker for pool selection: when multiple entries have identical qualifying
    metric (e.g., all total_assessments=0 at bootstrap), select by lowest `id` (oldest
    entries first). This guarantees deterministic slot assignment.'
  - Recall state filter includes approved, curated, contested; excludes 
    disputed, stale, deleted, pending.
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1839

## Scope

Replace the current recall sort (state_rank, -confidence, id) with score-based sorting and add reserved explore/challenge slot allocation.

### In Scope
- Recall sorted by (state_rank, -score, id)
- Reserved slot allocation: limit-4 regular + 2 explore + 2 challenge
- Explore: lowest total assessment count
- Challenge: lowest outstanding_count
- Dedup across slot categories
- State visibility filtering (uses new states from P2-01)
- Named constants SLOT_EXPLORE=2, SLOT_CHALLENGE=2

### Out of Scope
- Score computation (P2-02)
- State machine definitions (P2-01)
- Assessment tool (P2-07)
- Slot-efficiency check (P2-05)

## Domain
serve/mcp-memory/

[[2026-05-25T01:48:25+02:00]]
## Research
- Research doc: .owlbear/research/memory-recall-explore-challenge-slots.md
- Sources: 8 studied, 6 high-relevance
- Recommendation: T1 implementation — three-pool selection (explore→challenge→regular) in tools.py recall_memory, constants in MCP layer (confidence: 0.92)
- Key findings: fixed-slot allocation is KISS-aligned over probabilistic epsilon-greedy; algorithm is ~30 LOC change; all required model fields already exist from #1840/#1841; limit<4 edge case needs max(0,…) guard
- Challenge: skipped — prescriptive ACs, single implementation path, no alternatives

[[2026-05-25T01:48:30+02:00]]
Research complete. T1 — straightforward algorithmic change to recall_memory in tools.py. Three-pool selection (explore→challenge→regular) with dedup via id sets. All model fields available from completed deps #1840/#1841. No follow-up tasks needed — decomposition already complete in parent #1839.
