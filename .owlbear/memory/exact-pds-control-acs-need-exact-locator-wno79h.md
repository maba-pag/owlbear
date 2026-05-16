---
id: cc8b92c9-e208-4541-9a44-1bd570453268
title: Exact control ACs need exact DOM locators
categories:
- pitfall
- process
confidence: 0.8
state: curated
scope_agents:
- reviewer
- test-writer
- architect
source_agent: reviewer
created_at: '2026-05-15T13:47:03.982135Z'
updated_at: '2026-05-16T03:43:22.770182Z'
approved_at: null
---

When a Cockpit AC names an exact custom-element host, attribute, or selector, do not accept proof that uses a broader fallback locator or host union. A locator such as `p-switch, p-checkbox` can pass while the required host/name contract regresses; require proof against the exact selector named by the AC.
