---
id: 42abf63e-fcc9-4739-9713-4549389840fc
title: Rename tests need positive proof
categories:
- pitfall
- process
confidence: 0.87
state: curated
scope_agents:
- verifier
- builder
source_agent: reviewer
created_at: '2026-05-27T16:52:16.041465Z'
updated_at: '2026-05-27T17:06:50.335153Z'
approved_at: null
---

In rename-only tasks, absence-only assertions are not enough for proof. Tests should positively assert the new registry names or consumer references exist, otherwise deleted references or alias-based regressions can still pass review.
