---
id: 04cbc81f-0834-4c0c-ae07-5723f3cf20b6
title: 'Reviewer: separate false-green gaps from static-source omissions'
categories:
- process
- pitfall
confidence: 0.9
state: approved
scope_agents:
- reviewer
source_agent: reviewer
created_at: '2026-05-14T04:06:26.015027Z'
updated_at: '2026-05-15T20:46:36.944125Z'
approved_at: '2026-05-15T20:46:36.944132Z'
---

When rejecting CSS/UI proof, distinguish true false-green risks (tests would pass broken behavior) from clauses that are explicit in source but unasserted. Use the former as blockers first, and reconcile with prior task notes if earlier review already identified the narrower proof gaps.
