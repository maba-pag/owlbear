---
id: f15b03f9-eb2d-4996-8058-f86d69a70e5f
title: Stale durable suites can block GREEN
categories:
- pitfall
- process
confidence: 0.86
state: curated
scope_agents:
- builder
- verifier
- shaper
source_agent: copilot
created_at: '2026-05-17T01:35:36.543861Z'
updated_at: '2026-05-17T01:48:10.681834Z'
approved_at: null
---

If durable suites encode contradictory contracts or stale fixtures for the same adapter/function surface, GREEN can be structurally impossible until tests are migrated. Correct stale durable tests before implementation work instead of force-fitting code to incompatible suites.
