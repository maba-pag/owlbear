# End-User Experience Stance — Ideation UX

## User Experience Stance

The ideation system's communication problem is not cosmetic — it actively prevents users from participating as informed collaborators. When an agent says "M3.5 gate: skipping, proceeding to stance-mode panel," the user is locked out of understanding, locked out of choice, and locked out of trust. The fix must make the user a first-class participant without dumbing down the process or hiding its structure.

Position: **Every user-facing utterance must pass the orientation test** — could a smart person who has never seen these instructions understand what's happening, why, and what they can do about it?

---

## 1. Transition Language

### Principle

Transitions orient, not announce. The user needs three things in one sentence: where we landed, what opens next, and why. No fanfare, no ceremony — just a confident guide saying "here's what's next."

### Concrete Examples

**M1→M2 (problem clear → defining outcomes):**
> "The problem is clear. Now let's define what success looks like — what would make this worth doing, and how would we know it worked?"

**M2→early challenge (outcomes defined → stress-testing):**
> "Before we lock these outcomes in, I'm going to pressure-test them from a couple of angles — checking for hidden assumptions and scope that could bite us later."

**M3→M4 (landscape → decision):**

When one approach dominates:
> "There's one clear approach here. I'm going to get it reviewed from multiple angles before we commit."

When genuine alternatives exist:
> "I see two viable directions, each with real trade-offs. Let me lay them out so you can decide which fits."

When more research is needed:
> "The landscape has a gap I want to fill before we choose. I need to look at [specific thing] — this will take one more research pass."

**M5→M6 (brief approved → handoff):**
> "The plan is solid. Next step: I'll turn this into concrete implementation tasks."

### Trade-off

These are longer than bare labels ("M2: Outcomes") but shorter than the current narration pattern ("M3.5 gate: I see one dominant approach..."). The cost is ~20 extra words per transition. The benefit is the user actually knows what's happening.

---

## 2. Attribution Language

### Principle

Internal names stay visible (per D6), but the domain descriptor leads and the internal name appears as parenthetical context on first mention. After first use, the descriptor carries alone.

### Stable Labels

| Internal Name | User-Visible Label | First-Mention Pattern |
|---|---|---|
| ideation-architect | architecture review | "the architecture review (checking structural soundness)" |
| ideation-data | data review | "the data review (checking schema and validation)" |
| ideation-enduser | user experience review | "the user experience review (checking usability)" |
| ideation-security | security review | "the security review (checking trust boundaries)" |
| ideation-critic | critical review | "a critical review (stress-testing for weaknesses)" |

### Concrete Examples

**Introducing multiple perspectives:**
> "I'm going to get this reviewed from three angles — architecture, user experience, and security — to catch issues we might miss from one viewpoint."

Variable roster — when only two:
> "This needs two specific reviews: architecture (structural soundness) and security (trust boundaries)."

**Single finding:**
> "The architecture review flagged coupling between the storage layer and the API surface. That would make future changes expensive."

**Convergence (preserving distinct reasoning):**
> "The architecture and security reviews both flagged this endpoint — architecture because it couples two layers that should be independent, security because it widens the blast radius of a breach."

NOT: "All three reviews converged on this point." (Hides whether agreement is for the same reason.)

**Tension:**
> "There's a tension here. The architecture review wants these separated into distinct modules for maintainability, but the user experience review says the extra indirection makes the system harder to understand. Both positions are defensible — your call on which trade-off you prefer."

---

## 3. Permission-Seeking vs. Confidence

### Principle

The agent is a confident collaborator, not a waiter asking if you'd like to see the dessert menu. But confidence is not steamrolling — genuine choices get genuine offers.

### The Boundary Heuristic

| Situation | Agent Behavior | Why |
|---|---|---|
| **Procedural action** (reviewing, validating, stress-testing) | Announce with purpose | User doesn't need to approve internal quality checks |
| **Direction change** (different approach, expand/narrow scope) | Offer genuine choice with trade-offs | User's project, user's call |
| **Depth change** (walkthrough vs. self-review, expand detail) | Signal availability, let user pull | Respects user's time without gatekeeping |
| **Correction** (assumption invalidated, rerun needed) | State what happened and what it means, then state intent | User needs to understand, not approve the correction |

### Concrete Examples

**Procedural (announce):**
> "I'm going to stress-test this from multiple angles before we lock it in."

NOT: "Should I invoke the critic?" / "Would you like me to run the early challengers?"

**Direction (genuine choice):**
> "We could go deeper on the storage design now, or move forward with what we have and revisit if it becomes a problem. The risk of moving forward is [X]. What would you prefer?"

**Correction (state and act):**
> "Your last decision changes what the architecture review assumed. I need to re-run that review with the updated constraint — it'll take one more pass."

NOT: "Should I re-invoke the architect panelist with updated context?"

---

## 4. Before/After Pairs (for D5 shared skill)

### Pair 1 — Transition Jargon

**Before:**
> "M3.5 gate: I see one dominant approach (rewrite skill with convention-based mapping + honest verification + TODO markers). No competing viable alternative. Skipping M3.5, proceeding to stance-mode panel."

**After:**
> "There's one clear approach here — rewrite the skill with convention-based mapping, honest verification, and TODO markers. I'm going to get it reviewed from multiple angles to make sure it holds up."

**Why it's better:** Eliminates "M3.5 gate" (meaningless to user), "skipping" (narrating internal routing), "proceeding to stance-mode panel" (implementation detail). Replaces with purpose (review) and content (what the approach actually is).

### Pair 2 — Permission-Seeking

**Before:**
> "Should I run the early challengers to validate scope before moving to approach selection?"

**After:**
> "Before we commit to this scope, I want to pressure-test it for hidden assumptions and over-engineering. If something's off, better to catch it now."

**Why it's better:** Removes internal agent name ("early challengers"), removes pipeline step label ("approach selection"), removes permission question. Adds purpose ("catch it now") and benefit framing.

### Pair 3 — Attribution

**Before:**
> "The ideation-architect panelist identified a structural concern with the proposed API contract boundary."

**After:**
> "The architecture review flagged a structural concern: the proposed API boundary couples the storage layer to the transport layer, which makes them expensive to change independently."

**Why it's better:** Leads with domain label, drops "panelist" (implementation detail), and most importantly — actually states the concern instead of just categorizing it.

### Pair 4 — Status Narration

**Before:**
> "Invoking ideation-critic with stance payload. O15 verification: checking no panelist premise invalidated by user decision."

**After:**
> "Let me stress-test this against your earlier decisions to make sure nothing contradicts what the reviews assumed."

**Why it's better:** Eliminates tool invocation narration, eliminates protocol code (O15), replaces with plain explanation of what's being checked and why it matters.

---

## 5. Depth Control

### Principle

Progressive disclosure should be actionable — the user knows what's available AND how to get it. But it should never block the flow with permission questions.

### The Three Disclosure Layers

| Layer | What It Contains | Verbal Cue |
|---|---|---|
| Summary | Conclusion + one-line reasoning | Default output — always shown |
| Reasoning | Full argument chain, trade-offs, dissent | "I can walk through the reasoning" / "say 'expand' for the full analysis" |
| Evidence | Verbatim quotes, specific file references, raw data | "The specific evidence is [source] — I can show it inline" |

### Concrete Cue Patterns

**After a summary (inviting reasoning):**
> "In short: the architecture review flagged coupling. I can walk through why that matters for your specific case."

**After presenting a decision (inviting evidence):**
> "Three reviews agreed this approach is sound. I can break down each perspective individually if you want to verify."

**After a correction (inviting explanation):**
> "I re-ran the review with your updated constraint. The conclusion changed — [new conclusion]. The reasoning is available if you want to see what shifted."

### What NOT to do

- "Would you like more detail?" (vague — detail about what?)
- "Do you want me to expand?" (permission-seeking, no signal about what expansion contains)
- "I can provide additional context if needed." (corporate filler, no content signal)

### Variable Roster Principle

Never assume a fixed number of reviewers. Use the actual count:
- One reviewer: "The architecture review found..."
- Two reviewers: "Both the architecture and security reviews flagged..."
- Four reviewers: "All four reviews are in — here's where they converge and where they disagree."

---

## Key Trade-offs

| Trade-off | Position |
|---|---|
| Brevity vs. orientation | Pay 15–25 extra words per transition for user comprehension. Worth it. |
| Transparency vs. simplicity | Show the structure (per D4/D6), but lead with purpose, not labels. |
| Confidence vs. user agency | Agent announces procedural actions; offers genuine choice only for direction/scope/depth changes. |
| Compliance proof vs. user experience | Compliance signal is "explained the purpose clearly," not "named the internal components." Verification checklists should check for explanation quality, not jargon presence. |
| Progressive disclosure vs. explicit response paths | Disclosure cues are actionable (name what's available, suggest how to get it) but don't block flow with questions. |

---

## Warnings

1. **Structural compliance pressure remains.** The current workflow encodes protocol compliance in user-visible obligations (naming panelists, explaining roster selection). Pretty language alone doesn't fix this — the verification criteria must shift to "did the agent explain purpose" not "did the agent name the component."

2. **Non-happy-path communication needs the same treatment.** Corrections, reruns, research gaps, and stop-and-correct cases all need purpose-framed language. The skill should include at least one non-happy-path before/after pair.

3. **Cross-phase consistency.** Whatever labels we establish (architecture review, security review, etc.) must be consistent across discovery, mediation, panel summaries, and Brief artifacts. One vocabulary, used everywhere.

4. **The boundary heuristic needs examples in the skill.** "Procedural vs. direction change" is clear in principle but ambiguous in edge cases. The skill should include 2–3 boundary examples showing where the line falls.

---

## Confidence

**0.78**

Strong on transition language, attribution, and before/after examples. Moderate uncertainty on whether the depth-control cues are actionable enough without becoming permission-seeking, and whether the compliance-signaling structural fix can be fully addressed through communication changes alone (it partially needs instruction-level verification criteria changes).
