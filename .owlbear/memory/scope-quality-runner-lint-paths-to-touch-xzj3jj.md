---
approved_at: null
categories: [tool-usage, process]
confidence: 0.82
contested_by_task: null
created_at: '2026-05-27T19:48:12.462338Z'
didnt_use_count: 0
id: 3f4ee353-dfd2-48ca-9b85-71565b5e7618
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.0
source_agent: builder
state: deleted
title: Scope quality-runner lint paths to touched files
unremarkable_count: 0
updated_at: '2026-07-14T21:18:11.419263+00:00'
---

When running quality-runner for builder verification, linting the whole package path can surface unrelated baseline violations that obscure task evidence. Prefer lint_paths scoped to touched files plus the task test file — this produces clean, attributable proof and avoids noise from pre-existing violations elsewhere in the package.
