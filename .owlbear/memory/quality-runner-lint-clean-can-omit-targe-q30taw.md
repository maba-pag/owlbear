---
id: 259fc77a-599b-4d5f-a97a-64a937c3964b
title: Quality-runner lint clean can omit target files
categories:
- pitfall
- tool-usage
- process
confidence: 0.84
state: curated
scope_agents:
- reviewer
- builder
- auditor
source_agent: copilot
created_at: '2026-05-17T01:37:40.203732Z'
updated_at: '2026-05-17T01:48:20.855689Z'
approved_at: null
---

A scoped quality-runner `Lint: clean` result is weak if the lint report omits the task test file or the touched frontend files. Rerun with explicit `lint_paths` for omitted Python files, and use diagnostics/Vitest rather than Python lint output for TypeScript safety.
