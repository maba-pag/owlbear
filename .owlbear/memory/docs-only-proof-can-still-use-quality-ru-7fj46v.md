---
id: aee494d1-3a73-46df-bcb1-f4f8f72574a0
title: Docs-only proof can still use quality-runner
categories:
- pitfall
- process
- tool-usage
confidence: 0.84
state: deleted
scope_agents:
- reviewer
- doc-writer
- auditor
source_agent: copilot
created_at: '2026-05-17T01:34:16.428895Z'
updated_at: '2026-05-17T03:04:11.281816Z'
approved_at: null
---

A docs-only `Proof bundle: skip` review can still use quality-runner with empty `test_paths` and markdown `lint_paths`. Try the runner before assuming docs-only or td:0 evidence is `TOOL_UNAVAILABLE`.
