---
id: 586
title: 'Research: harshkedia177/axon'
status: archived
priority: important
created: 2026-03-05T23:50:40.2984491+01:00
updated: 2026-03-07T18:08:09.4587425+01:00
started: 2026-03-06T21:12:53.1341266+01:00
completed: 2026-03-07T18:08:09.4587425+01:00
tags:
    - research
    - phase-research
    - scope:agent
parent: 580
class: standard
---

**Source:** https://github.com/harshkedia177/axon
**License:** MIT | **Status:** Research complete

## Findings

Axon is a **code intelligence engine** (not a multi-agent system). It indexes codebases into a structural knowledge graph (KuzuDB) via a 12-phase pipeline and exposes it through MCP tools + CLI.

### Patterns Relevant to OwlBear

1. **MCP next-step hints (.80)** -- Each tool response appends guidance (e.g. query->context->impact chain). Adoptable in KnowledgeToolset.
2. **Hybrid search with RRF (.75)** -- BM25+vector+fuzzy fused via Reciprocal Rank Fusion (k=60). Validates OwlBear's approach.
3. **StorageBackend Protocol (.70)** -- runtime_checkable Protocol abstraction for storage. Validates our concrete approach.
4. **Progress callbacks (.65)** -- Pipeline reports phase progress via callback. Clean pattern for status reporting.

### Patterns NOT Applicable

- Community detection (Leiden) -- GPL-licensed, already rejected in #274
- tree-sitter AST parsing -- Different domain (code vs documents)
- Dead code detection, change coupling -- Code-specific

See docs/research/axon-code-intelligence.md for full analysis.

## Follow-up Tasks (pending creation)

1. Add next-step hints to KnowledgeToolset (nice-to-have)
2. Evaluate Axon as external MCP server for code intelligence (someday)
