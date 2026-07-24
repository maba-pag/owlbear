---
approved_at: '2026-05-15T20:51:09.473959Z'
categories: [process, tool-usage, pitfall]
confidence: 0.93
contested_by_task: null
created_at: '2026-05-14T09:42:10.168958Z'
didnt_use_count: 52
id: 4b304f82-6904-4af0-b7c1-7d350ebe0baf
outstanding_count: 1
scope_agents: [verifier, collector]
score: 1.0
source_agent: reviewer
state: approved
title: Vite config path fixes need build proof
unremarkable_count: 3
updated_at: '2026-07-24T15:38:13.450330+00:00'
---

When reviewing Cockpit frontend vite.config.ts changes that fix Vitest importability or path resolution, do not PASS on Vitest-only evidence if the AC mentions build-time behavior. Run quality-runner from serve/cockpit/web with both the scoped Vitest surface and npm run build. process.cwd()-based fixes can be acceptable in OwlBear because CI/docs standardize that cwd, but only after fresh build proof.
