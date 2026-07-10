---
id: 4b304f82-6904-4af0-b7c1-7d350ebe0baf
title: Vite config path fixes need build proof
categories:
- process
- tool-usage
- pitfall
confidence: 0.93
state: approved
scope_agents:
- verifier
- collector
source_agent: reviewer
created_at: '2026-05-14T09:42:10.168958Z'
updated_at: '2026-05-15T20:51:09.473927Z'
approved_at: '2026-05-15T20:51:09.473959Z'
---

When reviewing Cockpit frontend vite.config.ts changes that fix Vitest importability or path resolution, do not PASS on Vitest-only evidence if the AC mentions build-time behavior. Run quality-runner from serve/cockpit/web with both the scoped Vitest surface and npm run build. process.cwd()-based fixes can be acceptable in OwlBear because CI/docs standardize that cwd, but only after fresh build proof.
