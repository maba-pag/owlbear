---
id: 3d09b76a-e2ad-46db-ae26-134487e904ff
title: Exact DI ACs need full arg proof
categories:
- pitfall
- process
confidence: 0.89
state: curated
scope_agents:
- verifier
- builder
source_agent: reviewer
created_at: '2026-05-27T00:23:36.549612Z'
updated_at: '2026-05-27T00:29:14.193101Z'
approved_at: null
---

When an AC names exact constructor dependencies, do not PASS on partial identity checks alone. Require tests to assert every named injected dependency that the constructor stores, or a wiring drift can false-green.
