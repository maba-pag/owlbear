---
id: de291fc9-9aa9-4416-bf56-975fc81e3355
title: 'Verifier: CSS contract tests must prove declarations and search all shared
  imports'
categories:
- pitfall
- process
- domain-knowledge
confidence: 0.86
state: approved
scope_agents:
- verifier
- shaper
- builder
source_agent: reviewer
created_at: '2026-05-13T23:47:38.344791Z'
updated_at: '2026-05-15T20:43:03.825798Z'
approved_at: '2026-05-15T20:43:03.825816Z'
---

When reviewing CSS source-contract tests, fail helpers that prove token presence with raw block substring checks or that inspect only the first shared stylesheet import. Raw includes can false-green on comments/non-declaration text, and first-shared-import logic can false-fail compliant implementations when multiple shared CSS files exist. Require declaration-level proof and existential search across all shared imports.
