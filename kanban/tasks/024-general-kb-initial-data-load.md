---
id: 24
title: General KB initial data load
status: backlog
priority: important
created: 2026-03-26T17:23:17.8229702+01:00
updated: 2026-03-29T19:51:35.0011314+02:00
tags:
    - phase-2
    - scope:knowledge
    - type:build
depends_on:
    - 16
class: standard
---

## Objective
Load initial data into the general knowledge base (company + tech + tooling knowledge shared across all projects).

## Acceptance Criteria
- [ ] Identify initial data sources: internal tooling docs, design patterns, tech standards
- [ ] Ingest v1 research documents as initial corpus
- [ ] Ingest key external references (language docs, framework patterns)
- [ ] Verify hybrid search returns relevant results
- [ ] Document the curation process for adding new sources
- [ ] KB lives in owlbear/data/knowledge/general/
- [ ] Accessible via mcp-knowledge server

## Context
Depends on M3 (mcp-knowledge server). This seeds the shared knowledge layer with useful initial content.
