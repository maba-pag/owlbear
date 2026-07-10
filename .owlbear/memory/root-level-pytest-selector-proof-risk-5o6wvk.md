---
id: 2110335a-8024-41cc-b379-faaffb4784ad
title: Root-level pytest selector proof risk
categories:
- pitfall
- process
confidence: 0.89
state: curated
scope_agents:
- verifier
- shaper
- builder
source_agent: reviewer
created_at: '2026-05-27T22:47:19.568286Z'
updated_at: '2026-05-27T22:49:39.402980Z'
approved_at: null
---

When an AC requires a root-level `pytest tests/ -k ...` command, unrelated collection errors can block the proof even if the task’s own slice is green. Treat that as a proof-plan/AC defect, not an implementation defect, and prefer path-scoped proof surfaces for reviewable contracts.
