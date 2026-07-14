---
approved_at: null
categories: [pitfall, env-context]
confidence: 0.81
contested_by_task: null
created_at: '2026-05-17T15:43:31.228207Z'
didnt_use_count: 0
id: e04e6639-1d51-4990-89b1-9836a89b01f6
outstanding_count: 0
scope_agents: [verifier]
score: 0.0
source_agent: reviewer
state: deleted
title: Excluded frontend tests can still hide review blockers
unremarkable_count: 0
updated_at: '2026-07-14T23:52:41.782473+00:00'
---

serve/cockpit/web tsconfig excludes *.test.tsx from tsc -b, but VS Code still surfaces TypeScript diagnostics in those files. Passing Vitest and lint evidence is not sufficient if the task-local proof file still has active compile errors in the workspace.
