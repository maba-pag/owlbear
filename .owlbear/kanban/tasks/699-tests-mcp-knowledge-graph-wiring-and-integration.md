---
id: 699
title: 'Tests: MCP knowledge graph wiring and integration'
status: backlog
priority: needed
created: 2026-04-08T21:37:24.4459836+02:00
updated: 2026-04-08T21:37:24.4459836+02:00
tags:
    - scope:mcp-knowledge
    - type:test
parent: 676
depends_on:
    - 689
class: standard
---

## Context
TDD RED phase for #690. Write failing integration tests that verify the MCP server creates LLMExtractor and wires it into EntityExtractor.

## Acceptance Criteria

- [ ] AC1: Test verifies app_lifespan() creates LLMExtractor and passes it as EntityExtractor(extractor=...)
- [ ] AC2: Test verifies ingest produces entity_count > 0 and edge_count > 0 in get_stats
- [ ] AC3: Test verifies search_knowledge returns graph expansion context
- [ ] AC4: Test verifies graceful degradation when OWLBEAR_MODEL is unset
- [ ] AC5: All tests FAIL (RED phase — wiring not yet implemented)

## Affected Files
- serve/mcp-knowledge/tests/test_ingest_graph_wiring.py (new)
