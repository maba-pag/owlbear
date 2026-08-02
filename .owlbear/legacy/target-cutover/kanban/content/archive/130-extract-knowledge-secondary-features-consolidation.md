---
id: 130
title: Extract knowledge secondary features (consolidation, evaluator, bookmark 
  pipeline, refresh)
status: archived
priority: medium
created: 2026-03-29 08:06:41.412836+02:00
updated: 2026-03-29 14:52:32.550132+02:00
started: 2026-03-29 14:52:32.550132+02:00
completed: 2026-03-29 14:52:32.550132+02:00
tags:
- phase-1
- scope:knowledge
- type:build
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Extract remaining v1 knowledge modules not covered by #15/#32/#33/#34.

## Acceptance Criteria
- [ ] Extract consolidation.py (LLM-based chunk consolidation) with pluggable LLM interface
- [ ] Extract evaluator.py (LLM-based relevance evaluation) with pluggable LLM interface
- [ ] Extract bookmark_pipeline.py (bookmark ingestion) with pluggable LLM interface
- [ ] Extract bookmark_toolset.py or replace with MCP tool registration
- [ ] Extract refresh.py (source refresh orchestrator)
- [ ] Remove all PydanticAI Agent deps, replace with protocol/ABC
- [ ] Unit tests for each extracted module

## Context
Depends on #33 (ingest pipeline). These are secondary features identified during #15 research audit. See docs/research/extract-knowledge-engine-v1.md S3.7.
