---
id: 664
title: Add architect user-action gate rule and post-AR fast-path to w-arch-review
status: research
priority: nice-to-have
created: 2026-04-06T16:39:08.3017247+02:00
updated: 2026-04-06T16:39:08.3017247+02:00
tags:
    - phase-3
    - scope:agent-config
    - type:docs
depends_on:
    - 663
parent: 661
class: standard
---

## Objective\nAdd two rules to w-arch-review skill: (1) detection + AR creation for `type:user-action` tasks, (2) post-AR fast-path for completed action requests.\n\n## Context\nFrom #661 research: architect must block `type:user-action` tasks with an action request and fast-approve after `## Action Completed` is written to the body.\n\n## Acceptance Criteria\n- [ ] w-arch-review Step 3 adds BLOCK verdict for `type:user-action` tasks: create AR via scribe, block, end_work(outcome=\"block\")\n- [ ] w-arch-review adds detection heuristics: AC contains physical actions, references external systems, no testable Python interfaces + requires human observation\n- [ ] w-arch-review adds post-AR fast-path: when body contains `## Action Completed` + `type:user-action` tag → verify AC checkboxes → APPROVE\n- [ ] Detection heuristics are concrete enough for deterministic application (not judgment-based)\n\n## Files Affected\n- share/skills/w-arch-review/SKILL.md
