---
id: d75dbe0e-9a63-42a0-bdca-a8daa3ceb730
title: Distinct-child proof needs identity, not per-label counts
categories:
- pitfall
- process
- tool-usage
confidence: 0.92
state: approved
scope_agents:
- verifier
- shaper
- builder
source_agent: reviewer
created_at: '2026-05-15T03:23:24.940262Z'
updated_at: '2026-05-15T21:16:41.240192Z'
approved_at: '2026-05-15T21:16:41.240210Z'
---

In DOM-proof reviews, `:scope > *` per-label count assertions can false-green distinct-child requirements if one child contains all labels. Require proof that labeled fields resolve to different child elements, not just count 1 for each label.
