---
id: 999
title: 'Brief Walkthrough: chunk by topic + Mediator commentary'
status: research
priority: nice-to-have
created: 2026-04-18T21:26:18.205271+00:00
updated: 2026-04-18T21:57:42.046824+00:00
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
## Problem
The current Brief Walkthrough Protocol (w-ideation Step 5) walks the user through the Brief one section header at a time. In practice this is mechanical — eight back-to-back one-section askQuestions calls feel like form-filling.

## Fix (per user direction)
Two improvements:

1. **Chunk by topic, not by header.** Tightly coupled sections walk together:
   - Problem + Outcomes (the "why")
   - Approach + Architecture (the "how")
   - Scope (in) + Out of scope (the "boundary")
   - Risks + Acceptance criteria (the "honesty + verifiability")
   - Decomposition preview (the "next step")

2. **Add Mediator commentary, not just recitation.** For each chunk, the Mediator should:
   - Summarize what the section says (not just quote it).
   - Give the Mediator's opinion: pro/con/risk.
   - Reference decisions made along the way and why this section reflects them.
   - Surface negatives: tradeoffs accepted, risks acknowledged, things explicitly out of scope, dropped options.
   - Justify why THIS shape is optimal vs. alternatives considered.
   - Avoid pure affirmation; honest critique included.

## Acceptance Criteria
- w-ideation Step 5 Brief Walkthrough Protocol updated with topic-chunk approach (4-5 chunks instead of 8 sections).
- Walkthrough template includes explicit slots for Mediator opinion / tradeoffs / dropped options / accepted risks per chunk.
- One worked example showing the new walkthrough style.

## Context
Surfaced during ideation session for #973. User feedback verbatim: "by topic is great, but also give your opinion, the pro/con/risk for each section, maybe reference the decisions we made on the way. give it more life, more reason why THIS is the optimal brief. but not only affirming. also list the negatives, what the tradeoffs are, whats out of scope, what was accepted as a risk or given status."


---

## Extension (added from ideation session for #984 — agent-audit prompt rewrite)

### Additional fix
The rule "offer a walkthrough before Brief approval" currently lives at `w-ideation` Step 5 sub-step 5 — buried 5 deep into one of 6 moments. Easy to miss. During the ideation session for #984, the Mediator dumped the full Brief and asked "approve?" without offering a walkthrough; user had to call it out: *"arent you supped to ask me if you should walk me through it? thats a hard read tbh"*.

### Additional acceptance criteria
- "**Never present a Brief without first offering a walkthrough via askQuestions**" appears as a top-level rule, either:
  - In `ideator.agent.md` critical_rules, OR
  - As the FIRST sub-step of `w-ideation` Step 5 (before any other Brief-presentation activity).
- The rule is unambiguous: presenting the Brief content (even partial) before offering the walkthrough is a protocol violation.
- One worked example shows the askQuestions call shape ("Walk me through it" / "I'll read it myself" / etc.).

### Context
This pairs with the topic-chunking + Mediator commentary improvements already in this task — the walkthrough must both (a) be offered unmissably, and (b) be valuable when accepted (chunked + commentary).
