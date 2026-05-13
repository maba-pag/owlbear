---
id: ecee51b4-81d6-4d64-9676-626610cf6749
title: 'Reviewer: class-specific CSS ACs need selector-scoped proof'
categories:
- pitfall
- process
confidence: 0.89
state: curated
scope_agents:
- reviewer
- test-writer
- architect
source_agent: reviewer
created_at: '2026-05-13T21:09:42.972951Z'
updated_at: '2026-05-13T23:06:58.771024Z'
approved_at: null
---

For CSS source-contract ACs that say a rule must exist on a named class/selector, fail tests that only assert generic class presence plus a file-wide regex. Require evidence that the rendered element uses the expected selector and that the CSS regex is scoped to that same selector, or the suite can false-green when rules move to unrelated selectors.
