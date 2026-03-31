---
id: 460
title: Update researcher agent and research-workflow skill with tier classification
status: backlog
priority: needed
created: 2026-03-31T03:40:02.1287985+02:00
updated: 2026-03-31T04:12:42.757486+02:00
tags:
    - process
    - scope:agents
    - quality
claimed_by: architect
claimed_at: 2026-03-31T04:12:42.757486+02:00
class: standard
---

Add mandatory tier classification step to research-workflow Step 5 and researcher agent boundaries. After completing analysis, researcher must classify outcome as T1/T2/T3 using deterministic triggers. T3 outcomes MUST create a blocking decision request. T1 proceeds directly. See docs/research/mandatory-user-decision-gate.md. AC: - [ ] research-workflow Step 5 has tier classification decision tree - [ ] researcher agent boundaries list T3 triggers explicitly - [ ] researcher critical_rules updated: T3 outcomes require blocking DR - [ ] Red flag added: creating follow-up tasks for T3 outcome without DR

[[2026-03-31]] Tue 03:54
## Research
Researcher validation (2026-03-31): All 6 mandatory checklist items pass. Parent research (docs/research/mandatory-user-decision-gate.md, #385) provides complete backing with 9 sources. No novel research needed.
Changes target: skills/research-workflow/SKILL.md (Step 5 decision tree) and agents/researcher.agent.md (boundaries, critical_rules, red flags).
Builder should reference parent research S4 for exact T1/T2/T3 triggers.
