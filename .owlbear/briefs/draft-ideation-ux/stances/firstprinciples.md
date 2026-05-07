# First-Principles Stance — Ideation UX

## Irreducible Core

The user's complaint reduces to one claim: **the agent treats the user as a co-maintainer of the pipeline, not as a participant in a design conversation.** Everything else — jargon, no transitions, no WHY-WHAT-EFFECT, no ceremony — is a manifestation of this single failure mode.

The irreducible requirement is: *a user who has never read a skill file should be able to follow an ideation session without asking "what does that mean?" about any agent label, transition, or dispatch decision.*

## Assumptions Challenged

### 1. "The root cause is instruction language."

**Partially earned, but under-specified.** LLMs don't mechanically parrot instruction vocabulary. They do, however, use the only vocabulary available for a concept. When the instructions provide exactly one label for a concept — "M3.5 gate" — and provide no alternative, the agent has nothing else to reach for. This isn't instruction copying; it's **vocabulary starvation**. The instructions offer one name per concept, and it's always the internal name.

But there's a second mechanism the framing misses: **compliance signaling.** When an agent says "M3.5 gate: I see one dominant approach... Skipping M3.5," it's demonstrating to the system prompt that it followed the protocol. Agents echo internal structure to prove they're following instructions. UX rules need to actively override this impulse, not just suggest alternatives — because compliance signaling competes with user-friendliness.

**Test:** If vocabulary starvation is the real driver, then providing explicit alternative phrasings in the instructions should substantially reduce jargon in output. If compliance signaling is the driver, you'd need to make user-friendly language THE compliance signal (e.g., "a correctly executed M3.5 never mentions M3.5 by name to the user").

### 2. "Five symptoms require five outcomes."

**Not earned.** The five symptoms are five observations of one behavior: the agent narrates its internal state instead of explaining its purpose to a human. The five outcomes overlap heavily:

- O1 (labels contextualized) and O4 (opaque codes get context) are the same requirement.
- O2 (announces confidently) and O5 (transitions have weight) both describe tone at transitions.
- O3 (WHY-WHAT-EFFECT) subsumes most of the others.

A single outcome — *"The agent explains its actions in terms of purpose and benefit, using descriptive language; internal labels may appear only if immediately explained"* — covers the full complaint surface. Five outcomes risk five instruction paragraphs competing for attention in an already-dense prompt. Agent instructions have finite attention budget; adding five directives where one suffices dilutes all of them.

**Irreducible form:** One outcome about purpose-driven communication. One outcome about transition ceremony. That's two, not five.

### 3. "Communication-only changes are low risk."

**Not earned.** The "communication-only" framing implies safety: we're not touching architecture, just how agents talk. But:

- Style changes to agent instructions are **among the hardest changes to validate.** There's no unit test for "did the agent explain M3.5 in plain language?" You can only evaluate through live sessions.
- There's a real **compliance vs. friendliness tension.** The current jargon-heavy output is a signal that the agent IS following the protocol correctly. Making it friendlier might make it less compliant — the agent might skip internal evaluation steps it used to narrate, not just stop narrating them.
- Dense instructions with competing priorities (follow the protocol AND translate it for the user) can produce **erratic behavior** — sometimes jargon-heavy, sometimes over-friendly, depending on attention distribution in that turn.

The "communication-only" frame is scope control, not risk control. The actual risk profile is: medium probability of inconsistent behavior, low probability of protocol regression, high difficulty of verification.

### 4. "The pipeline concepts need user-visible names."

**Questionable.** The user said labels are OK if explained. But test whether that's the user accommodating the system rather than stating a preference. A design conversation can flow as:

> "Good — the problem is sharp. Now let's define what success looks like."

vs.

> "Moment 2: Outcomes — the problem is clear, now we define success."

The first is shorter, clearer, and requires zero explanation. The second demands the user absorb a naming system they'll encounter 6+ times per session. The user accepted labels-with-context, but the irreducible question is: **what information do moment labels carry that a plain-language transition doesn't?** If the answer is "nothing the user needs," then contextualizing labels is a patch, not a fix.

The one exception: if the user wants to refer back to a specific phase ("go back to M2"), labels provide a shared reference. But this is solvable with descriptive names ("go back to the outcomes discussion") without internal codes.

### 5. "Adding UX rules to instructions will reliably change behavior."

**Conditionally earned.** Style directives DO work when they meet three conditions:
1. **Specific** — not "be user-friendly" but "before dispatching subagents, state what expertise you're consulting and what it will produce"
2. **Positioned for attention** — in persona, critical rules, or turn-shape sections, not in reference tables the agent may not attend to
3. **Demonstrated** — with before/after examples showing the exact transformation

The current instructions have NO style directives for user-facing language. The jargon isn't happening despite UX instructions; it's happening because there are none. That's the strongest argument for this approach: we're not fighting existing instructions, we're filling a vacuum.

But there's a risk: the instructions are already long. Adding UX guidance that competes with protocol guidance for attention could produce inconsistency. The fix needs to be **integrated into the existing turn shapes and transition rules**, not bolted on as a separate section the agent may not attend to when it's deep in protocol execution.

### 6. "The problem is communication, not structural complexity."

**Partially earned, with a caveat.** The pipeline has ~15 named internal concepts (6 moments, 4 tiers, 5+ panel roles, multiple protocols). Most of these don't need user visibility and can be hidden by communication changes alone. But there's a structural issue the framing avoids:

**The M3.5 example is a narrated internal routing decision.** The agent evaluated a conditional gate and announced the evaluation result. If the protocol's turn-shape guidance says "evaluate M3.5 and report your decision," then communication rules saying "don't mention M3.5" create a contradiction. You can't resolve contradicting instructions with more instructions — you need to change the turn-shape to make the routing decision silent.

This is a small structural change (modify which protocol steps get narrated vs. which are internal), not a communication change. The "communication-only" scope should be tested against each protocol step: is this step's narration required by turn-shape guidance, or is the agent voluntarily narrating it? If any are required, those need structural modification.

## What Survives Reduction

1. **One core behavior change:** agents explain purpose and benefit instead of narrating pipeline state. This is real, necessary, and the actual user need.
2. **Style directives can fill the vacuum,** but only if integrated into existing turn shapes with specific examples, not bolted on as a separate section.
3. **Some structural modification is likely needed** for steps where the protocol requires user-facing narration of internal routing (M3.5 gate announcements, tier selection mechanics, panel dispatch logistics).

## What Should Be Dropped or Merged

- Five outcomes → two: (a) purpose-driven communication with label contextualization, (b) transitions get brief orientation.
- "Communication-only" as a safety claim → acknowledge that turn-shape modifications for internal routing steps are structural, not cosmetic.
- Treating instruction vocabulary as the sole root cause → add compliance signaling as a co-driver, which affects WHERE in the instructions the fix goes (it needs to be in compliance-critical sections, not advisory ones).

## Confidence

**0.82** — High confidence that the irreducible problem is correctly identified (purpose vs. pipeline narration). Moderate confidence that instruction-level changes can fix it, contingent on integration quality. The five-to-two outcome reduction is the highest-value finding; the compliance-signaling mechanism is the highest-risk blind spot.
