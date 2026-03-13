---
id: 723
title: Implement ConsolidationService (feature-flagged)
status: todo
priority: nice-to-have
created: 2026-03-10T17:13:15.2876702+01:00
updated: 2026-03-13T20:20:23.3730379+01:00
tags:
    - scope:core
    - memory
    - knowledge
    - consolidation
depends_on:
    - 721
    - 789
class: standard
---

## Goal

Build a ConsolidationService that periodically synthesizes cross-document insights from the knowledge graph. Feature-flagged off by default.

## AC

- [ ] `ConsolidationService` class in `src/owlbear/memory/knowledge/consolidation.py`
- [ ] Constructor: `(conn: sqlite3.Connection, graph_store: GraphStore, model: str | Model)`
- [ ] `async consolidate(batch_size: int = 50) -> int` -- queries chunks where `consolidated = 0` (up to batch_size), synthesizes cross-document insights via PydanticAI Agent with structured output, stores rows in `consolidations` table with `source_ids` JSON-array back-linking chunk IDs, sets `consolidated = 1` on processed chunks, returns insight count
- [ ] `schedule_periodic(interval: int) -> None` -- asyncio timer loop following `GraphEnricher._background_tasks` pattern; runs `consolidate()` on interval; logs and continues on LLM failures (never crashes the loop)
- [ ] `consolidation_enabled: bool = False` added to `OwlBearSettings` in config.py
- [ ] `consolidation_interval: int = 1800` added to `OwlBearSettings` in config.py
- [ ] Bootstrap: when `consolidation_enabled`, construct `ConsolidationService` in `_build_knowledge_toolset()` and start periodic timer in daemon event loop
- [ ] Export `ConsolidationService` from `src/owlbear/memory/knowledge/__init__.py`

## Pattern references

- `GraphEnricher` in `src/owlbear/memory/knowledge/enrichment.py` (background task scheduling)
- `KnowledgeQueryService` in `src/owlbear/memory/knowledge/query_service.py` (dependency injection pattern)

## References

- docs/research/always-on-memory-integration.md section 5b
- GCP pattern: docs/research/gcp-always-on-memory-agent.md section 6.3

## Dependencies

- Schema v8 migration (#721) -- archived
- Tests for ConsolidationService (#789) -- TDD RED phase

[[2026-03-13]] Fri 20:20
## Architecture Review
**Verdict:** APPROVED (with split)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| ConsolidationService in consolidation.py | Clear -- specific file path | Kept, refined with constructor signature |
| Reads unconsolidated chunks, uses LLM | Vague -- no interface spec | Refined: explicit method signature, PydanticAI Agent, batch_size |
| Stores insight records with back-links | Clear -- schema exists | Kept |
| Marks source chunks as consolidated | Clear -- sets consolidated=1 | Kept |
| Configurable interval (default 30min) | Vague -- no field names | Refined: consolidation_interval: int = 1800 in OwlBearSettings |
| Feature-flagged: consolidation_enabled | OK | Refined: explicit config.py field name |
| KnowledgeQueryService includes insights | **Domain violation** -- touches query_service.py | **Split to #790** |
| Tests with mocked LLM | Belongs in test task | **Moved to #789** |

### Architecture Notes
- Follows GraphEnricher pattern (enrichment.py) for background task scheduling
- Module layering OK: memory/ layer, no upward imports needed
- Config changes are ancillary (standard feature-flag pattern)
- Bootstrap wiring in _build_knowledge_toolset() follows existing pattern
- Schema v8 (#721) already archived -- consolidations table, chunks.consolidated, entities.importance all exist
- Security: no new external boundaries. LLM calls use existing PydanticAI infra with retry/circuit-breaker
- YAGNI guard: feature-flagged off by default, as research recommended

### Changes Made
- Refined #723 body: removed AC7 (query integration) and AC8 (tests), tightened AC with explicit interfaces
- Added depends_on: 789
- Created #789: Tests for ConsolidationService (TDD RED) at todo
- Created #790: Include consolidation insights in KnowledgeQueryService (backlog) -- split from AC7
- Moved #723 to todo

### Dependencies
- Verified: #721 (Schema v8) -- archived
- Added: #789 (test task) as dependency
- Created: #790 depends on #723
