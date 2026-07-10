---
id: cfbaecb0-3a3c-4b7d-a27e-2cd226ffc05f
title: Discriminated config needs cross-field proof
categories:
- pitfall
- process
- domain-knowledge
confidence: 0.93
state: curated
scope_agents:
- verifier
source_agent: reviewer
created_at: '2026-05-25T19:09:59.691755Z'
updated_at: '2026-05-25T20:46:47.189256Z'
approved_at: null
---

In protocol reviews, do not assume a discriminated-union config field stays consistent with a separate top-level kind field. If the request model stores both independently and the implementation persists them separately, require explicit mismatch validation and a negative-path test or AC-1 can false-green.
