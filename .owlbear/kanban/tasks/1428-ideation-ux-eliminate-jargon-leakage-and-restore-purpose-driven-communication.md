---
id: 1428
title: 'Ideation UX: eliminate jargon leakage and restore purpose-driven communication'
status: todo
priority: important
created: 2026-05-08T00:58:29.125370+00:00
updated: 2026-05-08T01:02:01.676803+00:00
tags:
- ideation
- ux
- shared-tier
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective\n\nRewrite vocabulary and narration directives in ideation agent instruction files to eliminate jargon leakage and restore purpose-driven communication.\n\n## Brief\n\nFull brief at `.owlbear/briefs/draft-ideation-ux/brief.md`\n\n## Acceptance Criteria\n\n- [ ] New \"Communication Patterns\" section in `h-ideation/SKILL.md` with vocabulary table, narration principles, transition patterns, boundary heuristic, depth-control cues\n- [ ] 4 narration directives rewritten (3 in mediation, 1 in discovery) with co-located annotations\n- [ ] 6 before/after pairs included as behavioral specification\n- [ ] One critical_rule line added to both user-facing agent files\n- [ ] Verification criteria in both workflow skills updated (\"explains purpose\" not \"names component\")\n- [ ] Light \"Panel Output Phrasing\" section added to h-ideation-panel\n- [ ] Grep-based check: no protocol codes (M3.5, O15) appear in narration guidance without context\n- [ ] All changes are behavioral-equivalent (same information reaches user, different framing)\n\n## Files in Scope\n\n- `share/skills/h-ideation/SKILL.md`\n- `share/skills/w-ideation-mediation/SKILL.md`\n- `share/skills/w-ideation-discovery/SKILL.md`\n- `share/agents/ideation-mediator.agent.md`\n- `share/agents/ideation-discoverer.agent.md`\n- `share/skills/h-ideation-panel/SKILL.md`\n\n## Context\n\n- Research grounding: `.owlbear/research/thinking-companion-framework.md`\n- Prior overhaul: `.owlbear/briefs/draft-ideation-overhaul-2026-04-20/`\n- Decisions: `.owlbear/briefs/draft-ideation-ux/decisions.md` (D1-D12)
[[2026-05-08]]
## Planning\n### Decomposition: Ideation UX jargon elimination\n- Tasks created: 5\n- Dependency layers: 2\n- Phase: 1\n\n### Task List\n| ID | Title | Priority | Depends On | Tags |\n|----|-------|----------|------------|------|\n| #1429 | P1-01: Communication Patterns section + vocabulary table in h-ideation/SKILL.md | critical | — | phase-1, scope:shared, ideation, ux |\n| #1430 | P1-02: Directive rewrites in w-ideation-mediation/SKILL.md | needed | #1429 | phase-1, scope:shared, ideation, ux |\n| #1431 | P1-03: Directive rewrite + tier presentation in w-ideation-discovery/SKILL.md | needed | #1429 | phase-1, scope:shared, ideation, ux |\n| #1432 | P1-04: Agent enforcement lines + verification criteria updates | needed | #1429 | phase-1, scope:shared, ideation, ux |\n| #1433 | P1-05: Panel Output Phrasing section in h-ideation-panel/SKILL.md | important | — | phase-1, scope:shared, ideation, ux |\n\n### Dependency Graph\n```mermaid\ngraph TD\n  1429[\"#1429 Communication Patterns\"]\n  1430[\"#1430 Mediation rewrites\"]\n  1431[\"#1431 Discovery rewrite\"]\n  1432[\"#1432 Agent enforcement\"]\n  1433[\"#1433 Panel phrasing\"]\n  1429 --> 1430\n  1429 --> 1431\n  1429 --> 1432\n```\n\n### Notes\n- All tasks are markdown prose edits (no code, no traditional tests). Verification via grep-based lint (AC #7 of parent).\n- #1429 is the foundation — all directive/enforcement tasks depend on the vocabulary table existing first.\n- #1433 is independent (panel phrasing is self-contained, no vocabulary dependency).\n- Status set to `todo` (brief provides all source content; no further research needed).\n- Skipped backlog column intentionally — content is fully specified in brief.