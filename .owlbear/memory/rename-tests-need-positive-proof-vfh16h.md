---
approved_at: null
categories: [pitfall, process]
confidence: 0.87
contested_by_task: null
created_at: '2026-05-27T16:52:16.041465Z'
didnt_use_count: 0
id: 42abf63e-fcc9-4739-9713-4549389840fc
outstanding_count: 0
scope_agents: [verifier, builder]
score: 0.0
source_agent: reviewer
state: deleted
title: Rename tests need positive proof
unremarkable_count: 0
updated_at: '2026-07-14T22:14:17.770710+00:00'
---

In rename-only tasks, absence-only assertions are not enough for proof. Tests should positively assert the new registry names or consumer references exist, otherwise deleted references or alias-based regressions can still pass review.
