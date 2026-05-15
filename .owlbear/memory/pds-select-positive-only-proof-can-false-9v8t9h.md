---
id: 1eee0352-1906-4acc-943b-39ba0c88b1f0
title: PDS select positive-only proof can false-green
categories:
- pitfall
- process
- tool-usage
confidence: 0.95
state: curated
scope_agents:
- reviewer
- auditor
- architect
- test-writer
- builder
source_agent: reviewer
created_at: '2026-05-15T02:40:50.715032Z'
updated_at: '2026-05-15T03:03:01.662464Z'
approved_at: null
---

When reviewing Cockpit PDS select migrations, do not accept a Playwright/Vitest assertion that only proves p-select-option exists. If the AC or policy also says 'not native <option>', inspect the source for native option children because a locator like .first().toBeAttached() can pass while the contract is still violated.
