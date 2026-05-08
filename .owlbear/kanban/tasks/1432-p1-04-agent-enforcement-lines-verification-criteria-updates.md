---
id: 1432
title: 'P1-04: Agent enforcement lines + verification criteria updates'
status: todo
priority: needed
created: 2026-05-08T01:00:48.495798+00:00
updated: 2026-05-08T01:07:14.906619+00:00
tags:
- phase-1
- scope:shared
- ideation
- ux
parent: 1428
depends_on:
- 1429
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective

Add one critical_rule enforcement line to each user-facing agent file and update verification criteria in both workflow skills to check "explains purpose" instead of "names component."

Brief: see parent #1428. Full brief at `.owlbear/briefs/draft-ideation-ux/brief.md`.

## Scope

**In:** 4 files, light edits:
1. `share/agents/ideation-mediator.agent.md` — add 1 critical_rule line
2. `share/agents/ideation-discoverer.agent.md` — add 1 critical_rule line
3. `share/skills/w-ideation-mediation/SKILL.md` — update verification criteria
4. `share/skills/w-ideation-discovery/SKILL.md` — update verification criteria

**Out:** Content creation (#1429). Directive rewrites (#1430, #1431). Panel cleanup (#1433).

## Acceptance Criteria

- [ ] `share/agents/ideation-mediator.agent.md` contains new critical_rule: "Apply user-facing vocabulary from h-ideation § Communication Patterns. Internal names appear with explanatory context. Never announce internal evaluations — narrate only results."
- [ ] `share/agents/ideation-discoverer.agent.md` contains equivalent critical_rule (same text or contextually appropriate variant)
- [ ] Verification criteria in w-ideation-mediation/SKILL.md updated: checks that agent "explains purpose of each review" not "names the panelist agent"
- [ ] Verification criteria in w-ideation-discovery/SKILL.md updated: checks that agent "explains what completed and what's next" not "names the handoff target"
- [ ] Critical_rule lines are placed inside existing `<critical_rules>` sections (not duplicated or misplaced)
- [ ] No other changes to agent files beyond the one added line each
\n\n## CORRECTION (from mediation review)\n\nThe discoverer agent has an EXISTING handoff critical_rule that says something like "End Phase 1 by naming @ideation-mediator." This needs to be REWRITTEN (not just a new line added). The AC item about "No other changes beyond the one added line each" is incorrect for the discoverer — it has 2 changes: add new vocabulary rule + rewrite existing handoff rule.\n\nRevised AC for discoverer:\n- [ ] Existing handoff critical_rule in discoverer rewritten to purpose-framed language (no @handle naming)\n- [ ] New vocabulary enforcement critical_rule added alongside