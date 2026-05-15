---
id: 21ca8518-620b-480b-8627-c60fe81f33e0
title: 'Reviewer: distinguish dormant alternate APIs from live contract paths'
categories:
- process
- pitfall
confidence: 0.9
state: curated
scope_agents:
- reviewer
source_agent: reviewer
created_at: '2026-05-15T01:52:11.497608Z'
updated_at: '2026-05-15T03:03:01.648941Z'
approved_at: null
---

When a late audit note cites a static mismatch in an alternate API branch, trace live callers before failing implementation. If the risky branch is unused but the new note requires extra proof, route the task as a backlog proof/contract refinement rather than blaming the builder for a live-path defect.
