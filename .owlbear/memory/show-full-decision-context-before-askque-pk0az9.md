---
approved_at: '2026-05-17T02:23:22.882387Z'
categories: [preference, process]
confidence: 0.98
contested_by_task: null
created_at: '2026-05-17T01:33:34.605237Z'
didnt_use_count: 34
id: ecaa14f0-6497-4407-889c-3854c36152f3
outstanding_count: 0
scope_agents: ['*']
score: 0.97
source_agent: copilot
state: approved
title: Use decision context template before askQuestions
unremarkable_count: 1
updated_at: '2026-07-21T14:26:12.244529+00:00'
---

Before calling `askQuestions` for a substantive decision or action request, present the decision inline using the user's standard frame: Status quo, Problem, Options labeled `(bp:)` for best practice, an `(rec:)` for your recommendation, each with Pro/Con/Risk/Confidence, and Expected outcome. Ask about exactly one decision item at a time, and do not rely on tool output or file notifications as the user-visible context.
