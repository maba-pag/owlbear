---
id: a7266466-6568-45f8-9367-da275286e9d7
title: Separate background quality debt from task failures
categories:
- pitfall
- process
- tool-usage
confidence: 0.9
state: approved
scope_agents:
- reviewer
- auditor
source_agent: copilot
created_at: '2026-05-17T01:34:12.345749Z'
updated_at: '2026-05-17T03:02:34.942388Z'
approved_at: '2026-05-17T03:02:34.942395Z'
---

When a broad quality run surfaces failures outside the builder's changed files, run a scoped pass on the changed paths before gating. Use the broad run for regression context, but decide task ownership from scoped evidence so legacy or background quality debt does not become a false task failure.
