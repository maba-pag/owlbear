---
id: 4c9d597c-49d2-48b9-948e-ebf54030f995
title: Playwright nav overflow from PDS host scroll width
categories:
- domain-knowledge
- tool-usage
confidence: 0.8
state: curated
scope_agents:
- builder
source_agent: builder
created_at: '2026-05-14T22:04:47.509569Z'
updated_at: '2026-05-15T03:02:46.075581Z'
approved_at: null
---

Cockpit nav rail overflow guard (scrollWidth > clientWidth) can fail because p-button host scrollWidth exceeds its clientWidth even after width clamping. Applying overflow:hidden on the nav button host class removed horizontal overflow in E2E.
