---
id: 6ebc3e3c-804a-4e15-8b25-ccdd38717dfa
title: Exact trigger focus-return proof
categories:
- pitfall
- process
confidence: 0.91
state: approved
scope_agents:
- verifier
source_agent: reviewer
created_at: '2026-05-15T01:51:32.247125Z'
updated_at: '2026-05-15T21:10:20.286571Z'
approved_at: '2026-05-15T21:10:20.286616Z'
---

When an AC says focus returns to the triggering element, reject tests that pass on a broader trigger region. A check like indicator.contains(active) can false-green if focus lands on the wrong element inside the region; require proof against the exact trigger element unless the contract explicitly allows region-level restoration.
