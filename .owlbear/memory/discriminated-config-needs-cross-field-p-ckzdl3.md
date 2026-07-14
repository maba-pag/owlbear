---
approved_at: null
categories: [pitfall, process, domain-knowledge]
confidence: 0.9
contested_by_task: null
created_at: '2026-05-25T19:09:59.691755Z'
didnt_use_count: 0
id: cfbaecb0-3a3c-4b7d-a27e-2cd226ffc05f
outstanding_count: 0
scope_agents: [shaper, builder, verifier]
score: 0.0
source_agent: reviewer
state: deleted
title: Independently stored discriminators need mismatch proof
unremarkable_count: 0
updated_at: '2026-07-14T23:55:20.600548+00:00'
---

When a config discriminator and a top-level kind are independently accepted or persisted, validate that mismatches are rejected. Without negative-path proof, the model can admit an impossible state even when each field is individually valid.
