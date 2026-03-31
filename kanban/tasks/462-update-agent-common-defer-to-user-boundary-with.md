---
id: 462
title: Update agent-common defer-to-user boundary with tier classification
status: backlog
priority: needed
created: 2026-03-31T03:40:17.7617381+02:00
updated: 2026-03-31T03:54:54.781271+02:00
tags:
    - process
    - scope:agents
    - quality
class: standard
---

Replace vague defer-to-user triggers with tier classification reference. Per-role triggers table should reference T1/T2/T3 system. Researcher trigger changes from 'finding recommends a feature or direction' to 'T3 outcome per research classification'. See docs/research/mandatory-user-decision-gate.md. AC: - [ ] Defer-to-user boundary references tier classification - [ ] Per-role triggers table updated with tier references - [ ] Researcher row references T3 mandatory gate explicitly

[[2026-03-31]] Tue 03:54
## Research
Validated. See docs/research/agent-common-tier-classification-update.md for full analysis.

Three changes to defer-to-user boundary (lines 40-75):
1. Replace vague bullets 1-2 with tier-aware language (T2 advisory, T3 mandatory)
2. Update per-role triggers table with tier references (Researcher row: T3 mandatory gate)
3. Add inline tier summary before the table for self-contained reference

Soft dependency on #459 (decision-requests skill gets impact_tier field first). Agent-common changes are self-contained enough to land independently.

No additional follow-up tasks needed - #462 is the implementation task.
