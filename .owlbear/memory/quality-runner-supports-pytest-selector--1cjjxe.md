---
id: a2b6b6a9-79d4-43f4-9a4e-02c962595996
title: quality-runner supports pytest selector strings in test_paths
categories:
- tool-usage
- process
confidence: 0.82
state: curated
scope_agents:
- builder
source_agent: builder
created_at: '2026-05-28T08:41:24.861707Z'
updated_at: '2026-05-28T09:11:00.140530Z'
approved_at: null
---

For proof_bundle=existing tasks, quality-runner mode=scoped accepts a full pytest selector string (including -k and --ignore flags) inside a single test_paths entry, which is useful for AC-locked regression gates.
