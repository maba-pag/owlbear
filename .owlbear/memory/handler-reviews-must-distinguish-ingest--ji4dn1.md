---
approved_at: null
categories: [pitfall, domain-knowledge]
confidence: 0.88
contested_by_task: null
created_at: '2026-05-18T12:31:50.126109Z'
didnt_use_count: 0
id: 87f059ab-4602-4b0d-a228-4d7f7fc505f5
outstanding_count: 0
scope_agents: [verifier, builder]
score: 0.0
source_agent: reviewer
state: deleted
title: Handler reviews must distinguish ingest_text from ingest(IntakeResult) 
  metadata behavior
unremarkable_count: 0
updated_at: '2026-07-14T23:53:45.966838+00:00'
---

When reviewing knowledge refresh metadata claims, do not infer handler persistence behavior from IngestPipeline.ingest_text(). The handler paths in refresh.py call ingest(IntakeResult), which persists intake.metadata directly and does not backfill fetched_at; ingest_text() has separate source_type/fetched_at defaults that can create a false blocker in reviews.
