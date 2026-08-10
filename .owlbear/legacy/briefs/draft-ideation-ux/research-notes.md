# Ideation UX — Research Notes

## Verified Findings

### F1: Vocabulary Starvation (65 sections across 6 files)
Every internal concept has exactly one name — always the internal one. No alternative phrasings are provided anywhere. When agents need to refer to "the step where we check if competing approaches exist," the only vocabulary available is "M3.5 gate."

### F2: Explicit Narration Instructions (3 critical instances)
Three sections directly instruct agents to narrate internal routing to users:
- `w-ideation-discovery/SKILL.md`: "End Phase 1 by naming `@ideation-mediator`"
- `w-ideation-mediation/SKILL.md` Step 1.5: "Tell the user you are switching to a proposal comparison path"
- `w-ideation-mediation/SKILL.md` Step 2: "Tell the user which late-domain panelists you are invoking and why"

These are not vocabulary problems — they're instructions that REQUIRE narrating internal routing.

### F3: Protocol Codes as Labels (O15, M3.5)
- O15 appears in 4 locations (both Critic validation sections in mediation skill + mediator agent critical_rules)
- M3.5 appears in 3 locations (mediation skill Step 1.5, panel skill Propose Mode, verification checklist)
- Neither is ever explained or given a descriptive alternative

### F4: Section Headers Agents Echo
Step headers like "Step 1 — M1: Understanding — 'What's really going on?'" become the framing agents produce. The moment code and tagline leak verbatim.

### F5: Internal Turn Primitives in Shared Rules
"Structured context header," "anchor-recall," "Investigator Mode," "Facilitative Mode" — all named and described in `h-ideation/SKILL.md` Shared Interaction Contract, used by agents as explicit labels in their output.

### F6: Investment Tier as Explicit Taxonomy
Step 1.5 in discovery skill tells agents to "Present the 4 tiers as askQuestions options." Users learn the full Scratch/Tool/Shared/Production taxonomy as a choice, when they only need to express "how deep should we go?"

## Candidate Implications

### I1: Fix Categories
| Category | Count | Fix type |
|----------|-------|----------|
| Structural — remove/restructure narration instructions | 27 sections | Change WHAT agents narrate |
| Communication — provide vocabulary alternatives | 23 sections | Change HOW agents name things |
| Both | 10 sections | Combined |

### I2: Highest-Impact Changes (ranked)
1. **Remove explicit narration instructions (F2)** — 3 edits eliminate the worst user-facing jargon
2. **Replace section headers (F4)** — step headers drive the framing agents produce
3. **Add vocabulary alternatives (F1)** — provide user-facing phrasings alongside internal labels
4. **Replace protocol codes (F3)** — O15, M3.5 become descriptive names
5. **Contextualize internal turn primitives (F5)** — "anchor-recall" becomes invisible protocol

### I3: Before/After Examples Needed
Both challengers agreed: abstract rules don't change style behavior. The fix must include 3-4 concrete before/after pairs showing what user-facing communication looks like vs. internal narration.

### I4: Compliance Signaling Risk
Agents use jargon to prove protocol compliance. The fix must make user-friendly language THE compliance signal, not an alternative. This means the verification checklists and examples sections need to show user-friendly language as correct, not jargon narration.

## Open Research Questions (for Mediation)

1. Should moment labels be REMOVED from section headers entirely, or KEPT with user-facing alternatives? (User said "exposing internal structure is fine" but first-principles challenger questioned whether this was accommodation)
2. Should investment tier names be replaced with plain descriptions, or kept as-is with context? (Scratch/Tool/Shared/Production vs. "quick spike / standard analysis / full treatment / production-grade")
3. How should panelist attribution work if agents don't narrate which panelists were consulted? (The insight attribution is valuable; the internal agent naming is not)
4. What's the verification method for these changes? (How do we know the UX improved? Manual testing? Golden conversation scenarios?)
5. Should the previous overhaul's golden scenarios be updated to reflect the new UX expectations?
6. Do subagent personas need modification, or is the fix entirely in the user-facing agent instructions?
7. Should h-ideation-panel/SKILL.md change at all? (It's panel-facing, not user-facing — but mediator rules reference its terminology when talking to users)
