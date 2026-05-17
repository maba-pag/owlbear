---
id: 3ff45f6d-8b10-483e-b82c-1ca7edc7d3ed
title: Quote negated globs in zsh
categories:
- pitfall
- tool-usage
confidence: 0.8
state: deleted
scope_agents:
- builder
- reviewer
- test-writer
- doc-writer
source_agent: copilot
created_at: '2026-05-17T01:35:02.122852Z'
updated_at: '2026-05-17T03:29:04.882077Z'
approved_at: null
---

In zsh, commands containing negated globs such as `--glob '!path/**'` can trigger history expansion errors unless history expansion is disabled or the pattern is safely quoted/escaped. Quote negated glob patterns before running ripgrep or shell commands.
