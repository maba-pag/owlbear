---
id: cc8b92c9-e208-4541-9a44-1bd570453268
title: Exact PDS control ACs need exact locators
categories:
- pitfall
- process
confidence: 0.9
state: curated
scope_agents:
- reviewer
- test-writer
- architect
source_agent: reviewer
created_at: '2026-05-15T13:47:03.982135Z'
updated_at: '2026-05-15T15:05:01.175729Z'
approved_at: null
---

When a Cockpit AC names an exact PDS host and name attribute, such as p-checkbox[name="blocked-filter"], reject proof that uses a broader fallback locator like `p-switch, p-checkbox`. Broad host unions can false-green selector-type or name regressions even when the current implementation is correct.
