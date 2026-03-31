---
id: 464
title: Update dispatch-planning Recipe 0 to skip auto-resolve for impact_tier=3
status: backlog
priority: needed
created: 2026-03-31T03:54:57.0490464+02:00
updated: 2026-03-31T04:12:34.5984522+02:00
tags:
    - process
    - scope:agents
    - quality
class: standard
---

Recipe 0 in dispatch-planning skill auto-resolves pending decisions after 5 days. With impact_tier (from #459), T3 decisions must NOT auto-resolve. Update Recipe 0 logic: check impact_tier field, skip 5-day timer when impact_tier=3, report T3 pending count separately in JSON output. See docs/research/impact-tier-decision-requests.md. AC: - [ ] Recipe 0 checks impact_tier field in decision request frontmatter - [ ] impact_tier=3 decisions skip 5-day auto-resolve timer - [ ] Missing impact_tier defaults to 2 (current behavior preserved) - [ ] JSON output pending field distinguishes T2 vs T3 pending counts - [ ] Updated Recipe 0 prose documents tier-aware auto-resolution

[[2026-03-31]] Tue 04:12
## Research
Validated (2026-03-31). See docs/research/recipe0-tier-aware-auto-resolve.md.
AC is complete. Change confined to skills/dispatch-planning/SKILL.md (3 sections: Recipe 0 prose, Step 1 paragraph, Step 3 JSON format).
Key: add impact_tier check before 5-day auto-resolve; missing field defaults to T2; pending JSON uses flat keys (decisions_t2, decisions_t3, actions).
No additional follow-up tasks needed.
