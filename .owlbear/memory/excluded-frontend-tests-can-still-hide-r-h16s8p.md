---
id: e04e6639-1d51-4990-89b1-9836a89b01f6
title: Excluded frontend tests can still hide review blockers
categories:
- pitfall
- env-context
confidence: 0.81
state: curated
scope_agents:
- verifier
source_agent: reviewer
created_at: '2026-05-17T15:43:31.228207Z'
updated_at: '2026-05-17T17:03:17.080118Z'
approved_at: null
---

serve/cockpit/web tsconfig excludes *.test.tsx from tsc -b, but VS Code still surfaces TypeScript diagnostics in those files. Passing Vitest and lint evidence is not sufficient if the task-local proof file still has active compile errors in the workspace.
