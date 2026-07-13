---
id: 149
title: Add GraphStore.get_counts() method
status: archived
priority: medium
created: 2026-03-29 19:04:04.626941+02:00
updated: 2026-03-30 15:36:01.651254+02:00
started: 2026-03-30 15:18:49.051867+02:00
completed: 2026-03-30 15:18:49.051867+02:00
tags:
- phase-1
- scope:knowledge
class: standard
archival_reason: completed
archival_refs: []
---

Add a get_counts() method to GraphStore returning document, entity, and edge counts. ~10 LOC. Needed by mcp-knowledge get_stats tool. Ref: docs/research/build-mcp-knowledge-server.md

[[2026-03-29]] Sun 20:02
## Architecture Review
**Verdict:** Block (already implemented)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Add get_counts() to GraphStore | Already exists at graph_store.py L420-434 | No action needed |
| Return doc, entity, edge counts | Method returns tuple[int, int, int] via SQL COUNT | Already done |
| ~10 LOC | Implemented in 7 LOC | Already done |
| Needed by mcp-knowledge get_stats | Available for import | Already done |

### Architecture Notes
GraphStore.get_counts() already exists in packages/knowledge/src/owlbear_knowledge/graph_store.py (lines 420-434). Tests exist in packages/knowledge/tests/test_graph_store_counts.py (9 tests, all passing). This task is redundant. The method was likely implemented as part of task #55 (Add ingest and graph tools to mcp-knowledge server). Recommend closing/archiving.

### Evidence
- `uv run pytest packages/knowledge/tests/test_graph_store_counts.py -q`: 9 passed in 0.41s
- Method signature: `def get_counts(self) -> tuple[int, int, int]`
- Implementation: 3x SQL COUNT queries, returns (doc_count, entity_count, edge_count)

## Audit (manual archival 2026-03-30) Already implemented: get_counts() at graph_store.py L420-434, 9 tests passing. Confidence 1.0.
