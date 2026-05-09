---
id: 1428
title: 'Ideation UX: eliminate jargon leakage and restore purpose-driven communication'
status: todo
priority: important
created: 2026-05-08T00:58:29.125370+00:00
updated: 2026-05-08T15:20:33.685228+00:00
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

## Objective

Rewrite vocabulary and narration directives in ideation agent instruction files to eliminate jargon leakage and restore purpose-driven communication.

## Brief

Full brief at `.owlbear/briefs/draft-ideation-ux/brief.md`

## Acceptance Criteria

- [ ] New \"Communication Patterns\" section in `h-ideation/SKILL.md` with vocabulary table, narration principles, transition patterns, boundary heuristic, depth-control cues
- [ ] 4 narration directives rewritten (3 in mediation, 1 in discovery) with co-located annotations
- [ ] 6 before/after pairs included as behavioral specification
- [ ] One critical_rule line added to both user-facing agent files
- [ ] Verification criteria in both workflow skills updated (\"explains purpose\" not \"names component\")
- [ ] Light \"Panel Output Phrasing\" section added to h-ideation-panel
- [ ] Grep-based check: no protocol codes (M3.5, O15) appear in narration guidance without context
- [ ] All changes are behavioral-equivalent (same information reaches user, different framing)

## Files in Scope

- `share/skills/h-ideation/SKILL.md`
- `share/skills/w-ideation-mediation/SKILL.md`
- `share/skills/w-ideation-discovery/SKILL.md`
- `share/agents/ideation-mediator.agent.md`
- `share/agents/ideation-discoverer.agent.md`
- `share/skills/h-ideation-panel/SKILL.md`

## Context

- Research grounding: `.owlbear/research/thinking-companion-framework.md`
- Prior overhaul: `.owlbear/briefs/draft-ideation-overhaul-2026-04-20/`
- Decisions: `.owlbear/briefs/draft-ideation-ux/decisions.md` (D1-D12)
[[2026-05-08]]
## Planning
### Decomposition: Ideation UX jargon elimination
- Tasks created: 5
- Dependency layers: 2
- Phase: 1

### Task List
| ID | Title | Priority | Depends On | Tags |
|----|-------|----------|------------|------|
| #1429 | P1-01: Communication Patterns section + vocabulary table in h-ideation/SKILL.md | critical | — | phase-1, scope:shared, ideation, ux |
| #1430 | P1-02: Directive rewrites in w-ideation-mediation/SKILL.md | needed | #1429 | phase-1, scope:shared, ideation, ux |
| #1431 | P1-03: Directive rewrite + tier presentation in w-ideation-discovery/SKILL.md | needed | #1429 | phase-1, scope:shared, ideation, ux |
| #1432 | P1-04: Agent enforcement lines + verification criteria updates | needed | #1429 | phase-1, scope:shared, ideation, ux |
| #1433 | P1-05: Panel Output Phrasing section in h-ideation-panel/SKILL.md | important | — | phase-1, scope:shared, ideation, ux |

### Dependency Graph
```mermaid
graph TD
  1429[\"#1429 Communication Patterns\"]
  1430[\"#1430 Mediation rewrites\"]
  1431[\"#1431 Discovery rewrite\"]
  1432[\"#1432 Agent enforcement\"]
  1433[\"#1433 Panel phrasing\"]
  1429 --> 1430
  1429 --> 1431
  1429 --> 1432
```

### Notes
- All tasks are markdown prose edits (no code, no traditional tests). Verification via grep-based lint (AC #7 of parent).
- #1429 is the foundation — all directive/enforcement tasks depend on the vocabulary table existing first.
- #1433 is independent (panel phrasing is self-contained, no vocabulary dependency).
- Status set to `todo` (brief provides all source content; no further research needed).
- Skipped backlog column intentionally — content is fully specified in brief.
[[2026-05-08]]
## Architecture Review

### Context
Parent task decomposed by planner into 5 subtasks (#1429–#1433). Planning section present — advancing parent per decomposition-complete path.

### Subtask Status
| ID | Title | Status | Notes |
|----|-------|--------|-------|
| #1429 | Communication Patterns section | Task record absent | Deliverable verified in h-ideation/SKILL.md lines 115–388 (vocabulary table, narration principles, transition patterns, boundary heuristic, depth-control cues) |
| #1430 | Mediation directive rewrites | done | All AC passed. Reviewer confidence .94 |
| #1431 | Discovery directive rewrite | Task record absent | Deliverable verified: purpose-framed narration at w-ideation-discovery/SKILL.md:131, vocabulary cross-ref at line 119 |
| #1432 | Agent enforcement + verification | Task record absent | Deliverable verified: critical_rule in mediator.agent.md:50 and discoverer.agent.md:41; verification criteria in mediation:150 and discovery:156 |
| #1433 | Panel Output Phrasing | backlog | Implementation exists (h-ideation-panel/SKILL.md:197–204), stuck in reviewer loop on test-quality AC2/AC5 refinement — continues independently |

### Parent AC Verification
| AC | Evidence | Status |
|----|----------|--------|
| Communication Patterns section with 5 components | h-ideation/SKILL.md lines 115–388 | MET |
| 4 narration directives rewritten | mediation: Step 1.5 (:97), Step 2 (:115), Disclosure Ladder (:50-70); discovery: handoff (:131) | MET |
| 6 before/after pairs | h-ideation/SKILL.md lines 207–260 (Pairs 1–6) | MET |
| Critical rule in both agent files | mediator.agent.md:50, discoverer.agent.md:41 | MET |
| Verification criteria updated | mediation:150, discovery:156 | MET |
| Panel Output Phrasing | h-ideation-panel/SKILL.md:197–204 (implementation done, #1433 test-quality cycle continues) | MET (impl) |
| Grep: no uncontextualized protocol codes | M3.5/O15 appear only in vocabulary table and "Before" examples — narration guidance uses purpose-driven language | MET |
| Behavioral equivalence | Pairs 1–6 demonstrate same info, different framing | MET |

### Verdict: APPROVE
Decomposition complete. All parent AC deliverables exist in the codebase. Subtask #1433 continues independently for test-quality refinement (implementation already in place).