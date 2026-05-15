---
id: a8665438-d50f-4f7c-972e-f4942840690c
title: Refresh gather can false-green success
categories:
- pitfall
- domain-knowledge
confidence: 0.89
state: curated
scope_agents:
- reviewer
- architect
- builder
- test-writer
source_agent: reviewer
created_at: '2026-05-15T07:05:52.432515Z'
updated_at: '2026-05-15T09:11:19.168630Z'
approved_at: null
---

In serve/knowledge IngestPipeline.ingest(), asyncio.gather(..., return_exceptions=True) can hide refresh embedding failures if the code ignores the embed coroutine result slot and only filters extraction exceptions. Review refresh success ACs for side-effect coroutines whose exceptions are captured but not checked.
