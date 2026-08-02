---
task_id: 1899
agent: researcher
request_type: decision
created: '2026-05-27'
response: pending
---

## Consolidation Migration vs CP1 Deletion

Task #1899 asks to migrate `_consolidation.py` into `EnrichmentStore`. However, CP1 (Canonical Identity) in the v2 knowledge architecture explicitly eliminates consolidation workflows.

### Options

| Option | Description | Confidence |
|--------|-------------|------------|
| A | **Delete consolidation entirely** — remove `_consolidation.py`, `get_consolidation_candidates` tool, phase-2 `store_enrichment` branch, set stats field to 0. Aligns with CP1. | 0.80 |
| B | **Keep at MCP layer only** — don't migrate, leave as-is until legacy tables are removed in B2. Then delete. | 0.55 |
| C | **Migrate as task says** — move into EnrichmentStore despite CP1 conflict. | 0.25 |

### Key Facts
- `_consolidation.py` queries legacy `entities`/`edges` tables (not v2 `graph_entities`/`graph_edges`)
- CP1: "No SAME_AS edges, no consolidation workflows"
- v2 canonical identity makes consolidation structurally impossible (same-name entities = same row)
- Zero dedicated test coverage for consolidation
- 3 call sites in server.py

See: `.owlbear/research/consolidation-migration-conflict.md`

### Recommendation
Option A — delete consolidation. Rewrite #1899 as a deletion task or archive and create a new one.