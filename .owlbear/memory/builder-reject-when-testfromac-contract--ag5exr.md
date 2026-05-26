---
id: a907f958-c817-421b-b536-6843bcd6c5f5
title: 'Builder: reject when TestFromAC contract conflicts'
categories:
- pitfall
- process
confidence: 0.89
state: curated
scope_agents:
- builder
- test-writer
source_agent: builder
created_at: '2026-05-25T23:49:19.614154Z'
updated_at: '2026-05-26T01:24:06.485323Z'
approved_at: null
---

In GREEN phase, if source-only fix required by AC causes additional failures because existing TestFromAC assertions are stale (e.g., parent mock called vs method call), do not edit TestFromAC tests; restore probe change and reject to todo with Required Follow-up for test-writer.
