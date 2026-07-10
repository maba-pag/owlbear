---
id: 99e06211-10c6-44c7-b6e8-9130f12ab9fa
title: Removed focus triggers need explicit fallback targets
categories:
- pitfall
- process
confidence: 0.86
state: approved
scope_agents:
- verifier
- shaper
- builder
source_agent: reviewer
created_at: '2026-05-15T07:16:07.292293Z'
updated_at: '2026-05-17T00:13:41.289554Z'
approved_at: '2026-05-17T00:13:41.289561Z'
---

When a modal/dialog opener is removed before close, do not treat ancestor containment as focus-return proof. Architecture must name the explicit fallback target, and tests/review should prove focus returns to that exact replacement element rather than a broader region.
