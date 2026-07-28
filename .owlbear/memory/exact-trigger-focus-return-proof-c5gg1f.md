---
approved_at: '2026-05-15T21:10:20.286616Z'
categories: [pitfall, process]
confidence: 0.91
contested_by_task: null
created_at: '2026-05-15T01:51:32.247125Z'
didnt_use_count: 44
id: 6ebc3e3c-804a-4e15-8b25-ccdd38717dfa
outstanding_count: 0
scope_agents: [verifier]
score: 0.91
source_agent: reviewer
state: approved
title: Exact trigger focus-return proof
unremarkable_count: 0
updated_at: '2026-07-28T10:00:19.355105+00:00'
---

When an AC says focus returns to the triggering element, reject tests that pass on a broader trigger region. A check like indicator.contains(active) can false-green if focus lands on the wrong element inside the region; require proof against the exact trigger element unless the contract explicitly allows region-level restoration.
