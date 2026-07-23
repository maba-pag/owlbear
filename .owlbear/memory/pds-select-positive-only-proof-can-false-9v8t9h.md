---
approved_at: '2026-05-15T21:13:52.892767Z'
categories: [pitfall, process, tool-usage]
confidence: 0.95
contested_by_task: null
created_at: '2026-05-15T02:40:50.715032Z'
didnt_use_count: 51
id: 1eee0352-1906-4acc-943b-39ba0c88b1f0
outstanding_count: 0
scope_agents: [verifier, collector, shaper, builder]
score: 0.95
source_agent: reviewer
state: stale
title: PDS select positive-only proof can false-green
unremarkable_count: 0
updated_at: '2026-07-22T20:08:18.482030+00:00'
---

When reviewing Cockpit PDS select migrations, do not accept a Playwright/Vitest assertion that only proves p-select-option exists. If the AC or policy also says 'not native <option>', inspect the source for native option children because a locator like .first().toBeAttached() can pass while the contract is still violated.
