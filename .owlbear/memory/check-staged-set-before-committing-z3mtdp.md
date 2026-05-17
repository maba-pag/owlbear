---
id: 373a641d-6db9-4b0b-841b-2233d80e0486
title: Check staged set before committing
categories:
- pitfall
- process
- tool-usage
confidence: 0.88
state: deleted
scope_agents:
- builder
- doc-writer
- reviewer
- auditor
source_agent: copilot
created_at: '2026-05-17T01:34:30.543478Z'
updated_at: '2026-05-17T03:13:08.144792Z'
approved_at: null
---

Before committing task-scoped work, inspect `git diff --cached --name-only`. Adding specific paths does not unstage unrelated files already in the index, so pre-staged changes can slip into the commit unless checked explicitly.
