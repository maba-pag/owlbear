---
id: 178
title: Execute initial KB data load and verify search quality
status: ideation
priority: important
created: 2026-03-29T19:51:00.9854857+02:00
updated: 2026-03-29T19:51:00.9854857+02:00
tags:
    - phase-2
    - scope:knowledge
    - type:build
depends_on:
    - 16
    - 160
class: standard
---

## Objective
Run the data loader against the real knowledge.db, verify hybrid search returns relevant results, confirm MCP access works.

## Acceptance Criteria
- [ ] Execute loader script against data/knowledge/knowledge.db with BgeM3 embeddings
- [ ] ~80 documents ingested (50 research docs + skills + instructions)
- [ ] get_stats shows expected document/entity/edge counts
- [ ] 5 sample queries via search_knowledge return relevant results (manual spot-check)
- [ ] Hybrid search (dense + sparse) returns better results than dense-only for at least 3/5 queries
- [ ] MCP server serves search results via mcp-knowledge tools

## Context
Phase B of #24. Blocked on #16 (mcp-knowledge server) and #160 (hybrid search). See docs/research/general-kb-initial-data-load.md.
