---
id: e8c980ad-61cb-4dd3-9a32-1981bc583c47
title: Delete patch may not remove files on disk
categories:
- tool-usage
- pitfall
confidence: 0.82
state: curated
scope_agents:
- builder
source_agent: builder
created_at: '2026-05-28T08:17:07.705626Z'
updated_at: '2026-05-28T09:11:07.353478Z'
approved_at: null
---

In owlbear-dev, apply_patch Delete File reported success for a 13-file batch but files still existed. For deletion-heavy tasks, verify filesystem immediately and fall back to explicit rm with per-file ABSENT checks before running quality gates.
