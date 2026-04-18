---
id: 1010
title: Implement topic-chunk walkthrough + Mediator commentary in w-ideation
status: research
priority: nice-to-have
created: 2026-04-18T21:57:35.503430+00:00
updated: 2026-04-18T21:57:35.503430+00:00
tags:
- type:improvement
- scope:skills
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Context
Implements findings from #999 research. See `.owlbear/research/brief-walkthrough-chunks-999.md`.

## Changes Required
Edit `share/skills/w-ideation/SKILL.md` — `## Brief Walkthrough Protocol` section:

1. **Replace Walkthrough Loop** — Change from 7-8 per-section iterations to 5 topic chunks:
   - Chunk 1 "The Why": Problem + Outcomes
   - Chunk 2 "The How": Approach + Alternatives Considered + Context
   - Chunk 3 "The Boundary": Scope (In/Out) + Key Decisions
   - Chunk 4 "The Honesty": Risks & Mitigations
   - Chunk 5 "The Next Step": Decomposition preview (new walkthrough-only content)

2. **Add 6-slot Mediator Commentary template** per chunk:
   - Summary (restatement in own words)
   - Opinion (strengths + weaknesses)
   - Decision trail (which user/panelist decisions shaped this)
   - Trade-offs (what was accepted, given up, dropped)
   - Why this shape (why optimal vs. alternatives)
   - Honest negatives (risks, gaps, concerns)

3. **Add a worked example** showing one complete chunk walkthrough (e.g., "The Why" chunk).

4. **Update Post-Walkthrough Summary** table to use chunk names instead of section names.

5. **Keep existing Walkthrough Metrics** (Fidelity, Readiness, Risk) — apply per-chunk.

## Acceptance Criteria
- Walkthrough Loop uses 5 topic chunks instead of 7-8 sections.
- Commentary template has explicit slots for all 6 items per chunk.
- One worked example demonstrates the new style.
- Post-Walkthrough Summary table uses chunk names.
- Existing metrics preserved.

## Files Affected
- `share/skills/w-ideation/SKILL.md`