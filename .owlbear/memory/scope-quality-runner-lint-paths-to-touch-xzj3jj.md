---
id: 3f4ee353-dfd2-48ca-9b85-71565b5e7618
title: Scope quality-runner lint paths to touched files
categories:
- tool-usage
- process
confidence: 0.82
state: curated
scope_agents:
- builder
- reviewer
source_agent: builder
created_at: '2026-05-27T19:48:12.462338Z'
updated_at: '2026-05-27T20:17:36.373028Z'
approved_at: null
---

When running quality-runner for builder verification, linting the whole package path can surface unrelated baseline violations that obscure task evidence. Prefer lint_paths scoped to touched files plus the task test file — this produces clean, attributable proof and avoids noise from pre-existing violations elsewhere in the package.
