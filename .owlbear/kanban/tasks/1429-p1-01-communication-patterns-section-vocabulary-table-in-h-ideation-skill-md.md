---
id: 1429
title: 'P1-01: Communication Patterns section + vocabulary table in h-ideation/SKILL.md'
status: todo
priority: critical
created: 2026-05-08T01:00:48.444590+00:00
updated: 2026-05-08T01:01:49.007101+00:00
tags:
- phase-1
- scope:shared
- ideation
- ux
parent: 1428
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective

Add a new "Communication Patterns" section to `share/skills/h-ideation/SKILL.md` containing the canonical vocabulary table, narration principles, transition patterns, boundary heuristic, depth-control verbal cues, and 6 before/after example pairs.

Brief: see parent #1428. Full brief at `.owlbear/briefs/draft-ideation-ux/brief.md`.

## Scope

**In:** New section in h-ideation/SKILL.md only. Content sourced from brief §Communication Patterns, §Canonical Vocabulary Table, §Before/After Examples.

**Out:** Directive rewrites in workflow skills (#1430, #1431). Agent file changes (#1432). Panel cleanup (#1433).

## Acceptance Criteria

- [ ] New `## Communication Patterns` section exists in `share/skills/h-ideation/SKILL.md`
- [ ] Vocabulary table present with all entries from brief (18 rows: internal name → user-visible label → first-mention pattern)
- [ ] "Repeated-mention rule" stated (first mention = full form + parenthetical; subsequent = descriptor only)
- [ ] Narration Principles subsection with 6 bullet points from brief (results not mechanisms, conditional gates never announced, purpose before process, labels with context D4, attribution with explanation D6, compliance = explanation quality)
- [ ] Transition Patterns table with 6 rows (problem→outcomes, outcomes→challenge, landscape→decision×2, brief→handoff, tier calibration)
- [ ] Boundary Heuristic table (4 rows: procedural/direction/depth/correction)
- [ ] Depth-Control Verbal Cues table augmenting Disclosure Ladder (3 levels: default/concrete/verbatim)
- [ ] 6 before/after example pairs included (conditional gate, panel roster, permission-seeking, status narration, phase handoff, correction/rerun)
- [ ] Grep verification: `grep -n "M3.5\|O15" share/skills/h-ideation/SKILL.md` — any hits appear only inside example "Before:" blocks or with explanatory context
- [ ] Section placement: after existing shared rules, before any workflow-specific content