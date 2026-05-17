---
id: ecaa14f0-6497-4407-889c-3854c36152f3
title: Use decision context template before askQuestions
categories:
- preference
- process
confidence: 0.98
state: approved
scope_agents:
- '*'
source_agent: copilot
created_at: '2026-05-17T01:33:34.605237Z'
updated_at: '2026-05-17T02:23:22.882379Z'
approved_at: '2026-05-17T02:23:22.882387Z'
---

Before calling `askQuestions` for a substantive decision or action request, present the decision inline using the user's standard frame: Status quo, Problem, Options labeled `(bp:)` for best practice, an `(rec:)` for your recommendation, each with Pro/Con/Risk/Confidence, and Expected outcome. Ask about exactly one decision item at a time, and do not rely on tool output or file notifications as the user-visible context.
