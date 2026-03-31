---
id: 459
title: Update decision-requests skill with impact_tier field and T3 indefinite blocking
status: backlog
priority: needed
created: 2026-03-31T03:39:53.0605+02:00
updated: 2026-03-31T04:12:33.247101+02:00
tags:
    - process
    - scope:agents
    - quality
claimed_by: architect
claimed_at: 2026-03-31T04:12:33.247101+02:00
class: standard
---

Add impact_tier (1/2/3) to decision-request frontmatter. T3 decisions block indefinitely (no auto-resolve). T2 keeps 5-day auto-timeout. Update file format section, resolution workflow, and planner integration notes. See docs/research/mandatory-user-decision-gate.md. AC: - [ ] impact_tier field in frontmatter (values: 1, 2, 3) - [ ] T3 decisions do not auto-resolve (planner skips 5-day timer for impact_tier=3) - [ ] T2 decisions keep current 5-day auto-resolve - [ ] Updated file format example showing impact_tier - [ ] Updated blocking behavior section documenting tier differences

[[2026-03-31]] Tue 03:55
## Research
Validated (2026-03-31). See docs/research/impact-tier-decision-requests.md.
Backwards compat: missing impact_tier defaults to T2.
Gap found: dispatch-planning Recipe 0 needs tier-aware auto-resolve (created #464).
