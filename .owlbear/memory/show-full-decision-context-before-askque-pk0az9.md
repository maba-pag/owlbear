---
approved_at: null
categories: [preference, process]
challenges: []
confidence: 0.9
created_at: '2026-05-17T01:33:34.605237Z'
didnt_use_count: 253
id: ecaa14f0-6497-4407-889c-3854c36152f3
outstanding_count: 10
scope_agents: ['*']
score: 1.8299999999999998
source_agent: copilot
state: curated
title: Frame substantive user decisions before asking
unremarkable_count: 7
updated_at: '2026-10-11T14:41:49.006960+00:00'
---

When using `vscode/askQuestions` or asking inline for a substantive user decision, present exactly one decision item with Status quo, Problem (plain words plus a concrete scenario), Options with what each means for the user's journey, each option's Pro/Con/Risk/Confidence, sources researched, a recommendation with reasoning, and Expected outcome. Mark best-practice and recommended options with `(bp:)` and `(rec:)` when useful. Do not rely on a question dialog or tool output to carry the decision context, and never bury a decision as a one-line question at the end of a report. If a mechanic would deviate from an approved or decided design statement, raise it before building, not after; check the approved journey docs end to end before treating an as-built constraint as fixed.
