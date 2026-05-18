---
id: 87f059ab-4602-4b0d-a228-4d7f7fc505f5
title: Handler reviews must distinguish ingest_text from ingest(IntakeResult) metadata
  behavior
categories:
- pitfall
- domain-knowledge
confidence: 0.88
state: curated
scope_agents:
- reviewer
- builder
- test-writer
source_agent: reviewer
created_at: '2026-05-18T12:31:50.126109Z'
updated_at: '2026-05-18T12:42:06.112988Z'
approved_at: null
---

When reviewing knowledge refresh metadata claims, do not infer handler persistence behavior from IngestPipeline.ingest_text(). The handler paths in refresh.py call ingest(IntakeResult), which persists intake.metadata directly and does not backfill fetched_at; ingest_text() has separate source_type/fetched_at defaults that can create a false blocker in reviews.
