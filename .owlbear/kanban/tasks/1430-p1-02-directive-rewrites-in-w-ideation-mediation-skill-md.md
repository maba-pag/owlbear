---
id: 1430
title: 'P1-02: Directive rewrites in w-ideation-mediation/SKILL.md'
status: todo
priority: needed
created: 2026-05-08T01:00:48.467318+00:00
updated: 2026-05-08T01:01:49.023105+00:00
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

Rewrite 3 narration directives in `share/skills/w-ideation-mediation/SKILL.md` to replace jargon-narrating instructions with purpose-framed alternatives. Add co-located `**Narrate as:**` annotations.

Brief: see parent #1428. Full brief at `.owlbear/briefs/draft-ideation-ux/brief.md`.

## Scope

**In:** 3 directive rewrites in w-ideation-mediation/SKILL.md:
1. Step 1.5 — currently instructs "Tell the user you are switching..." → rewrite to purpose-framed announcement
2. Step 2 — currently instructs "Tell the user which late-domain panelists..." → rewrite to purpose-framed roster introduction
3. Disclosure Ladder — add depth-control verbal cues from h-ideation § Communication Patterns

**Out:** Discovery workflow (#1431). Agent files (#1432). h-ideation foundation (#1429).

## Acceptance Criteria

- [ ] Step 1.5 directive rewritten: no longer instructs agent to name internal switching mechanism; instead instructs purpose-framed announcement (what's happening + why)
- [ ] Step 2 directive rewritten: no longer instructs agent to enumerate panelist agent names; instead instructs purpose-framed introduction (which reviews + why those angles)
- [ ] Disclosure Ladder updated with verbal cues from h-ideation § Depth-Control Verbal Cues
- [ ] Each rewritten directive has a co-located `**Narrate as:**` annotation with a concrete example phrase
- [ ] Behavioral equivalence: same information reaches the user (which reviews, what's happening next) — only framing changes
- [ ] Grep verification: `grep -n "M3.5\|O15\|ideation-architect\|ideation-security" share/skills/w-ideation-mediation/SKILL.md` — hits in narration guidance positions carry explanatory context or appear in technical routing (not user-facing phrasing)
- [ ] References h-ideation § Communication Patterns for vocabulary (cross-reference, not duplication)