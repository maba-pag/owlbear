---
approved_at: '2026-05-15T20:43:03.825816Z'
categories: [pitfall, process, domain-knowledge]
confidence: 0.86
contested_by_task: null
created_at: '2026-05-13T23:47:38.344791Z'
didnt_use_count: 24
id: de291fc9-9aa9-4416-bf56-975fc81e3355
outstanding_count: 0
scope_agents: [verifier, shaper, builder]
score: 0.86
source_agent: reviewer
state: approved
title: 'Verifier: CSS contract tests must prove declarations and search all shared
  imports'
unremarkable_count: 0
updated_at: '2026-07-24T18:52:40.455101+00:00'
---

When reviewing CSS source-contract tests, fail helpers that prove token presence with raw block substring checks or that inspect only the first shared stylesheet import. Raw includes can false-green on comments/non-declaration text, and first-shared-import logic can false-fail compliant implementations when multiple shared CSS files exist. Require declaration-level proof and existential search across all shared imports.
