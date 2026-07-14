---
approved_at: null
categories: [pitfall, process]
confidence: 0.89
contested_by_task: null
created_at: '2026-05-25T23:49:19.614154Z'
didnt_use_count: 0
id: a907f958-c817-421b-b536-6843bcd6c5f5
outstanding_count: 0
scope_agents: [builder]
score: 0.0
source_agent: builder
state: deleted
title: 'Builder: reject when TestFromAC contract conflicts'
unremarkable_count: 0
updated_at: '2026-07-14T23:00:22.723115+00:00'
---

In GREEN phase, if source-only fix required by AC causes additional failures because existing TestFromAC assertions are stale (e.g., parent mock called vs method call), do not edit TestFromAC tests; restore probe change and reject to shape with Required Follow-up for shaper.
