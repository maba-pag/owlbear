---
approved_at: '2026-05-17T02:23:22.882387Z'
categories: [preference, process]
confidence: 0.98
contested_by_task: null
created_at: '2026-05-17T01:33:34.605237Z'
didnt_use_count: 125
id: ecaa14f0-6497-4407-889c-3854c36152f3
outstanding_count: 8
scope_agents: ['*']
score: 1.73
source_agent: copilot
state: approved
title: Use decision context template before askQuestions
unremarkable_count: 5
updated_at: '2026-07-24T15:38:13.317481+00:00'
---

Before calling `askQuestions` for a substantive decision or action request, present the decision inline using the user's standard frame: Status quo, Problem, Options labeled `(bp:)` for best practice, an `(rec:)` for your recommendation, each with Pro/Con/Risk/Confidence, and Expected outcome. Ask about exactly one decision item at a time, and do not rely on tool output or file notifications as the user-visible context.
