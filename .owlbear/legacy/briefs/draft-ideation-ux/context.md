# Ideation UX — Context

## Project Type

existing-feature/refactor

## Problem Statement

The ideation agents (discoverer, mediator, and their subagents) treat the user as a pipeline engineer who knows the system's internal structure. Internal terminology — moment labels (M1, M2, M3), outcome IDs (O15), investment tiers, panel dispatch — leaks into user-facing conversation without explanation.

Five symptoms:
1. Jargon without explanation — "M2", "O15" used as labels without telling the user what they mean
2. No ceremony at moment transitions — agent jumps into "M2: Outcomes" without explaining what this phase does, why it matters now, and what it will produce
3. Options presented as technical operations — "I will run the critic, agree?" instead of "Would you like a critical review of what we have so far?"
4. No WHY-WHAT-EFFECT framing — agent announces pipeline status instead of explaining purpose and benefit
5. User must already know the pipeline to follow along

## Root Cause (revised after early challenge)

Two co-drivers identified by both challengers:

1. **Vocabulary starvation.** Instructions provide exactly one label per concept — always the internal one. When the agent needs to refer to "the step where we check if competing approaches exist," the only vocabulary available is "M3.5 gate." Fix: provide alternative phrasings directly in the instructions.

2. **Compliance signaling.** Agents echo jargon to PROVE they're following the protocol. "M3.5 gate: skipping, proceeding to stance-mode panel" is the agent demonstrating it evaluated the conditional. Fix: make user-friendly language THE compliance signal.

## Locked Outcomes (3, revised after early challenge)

A. **Purpose-driven communication.** Agent explains actions in terms of purpose and benefit. Internal terminology gets plain-language context on first use. Compliance demonstrated through clear explanation, not jargon narration.

B. **Oriented transitions.** Phase shifts get brief "where we are / what's next" framing. Not ceremony, not status dump — orientation.

C. **Direct tone.** Confident, concise, not permission-seeking. Agent announces what it thinks should happen next.

## Scope (revised after early challenge)

- **Primary:** Communication changes to `h-ideation/SKILL.md` + both agent `.md` files
- **Secondary:** Targeted turn-shape modifications in `w-ideation-discovery/SKILL.md` and `w-ideation-mediation/SKILL.md` where protocol guidance currently requires narrating internal routing decisions
- NOT changing pipeline architecture, NOT removing agents/subagents
- Internal labels remain valid in artifact files, agent-to-agent communication, and debugging

## Fresh Example (from user, 2026-05-08)

Agent output during a live session:
> "M3.5 gate: I see one dominant approach (rewrite skill with convention-based mapping + honest verification + TODO markers). No competing viable alternative. Skipping M3.5, proceeding to stance-mode panel."

User reaction: "what the fuck is M3.5? why is it a gate? what is that? i have no context."

This perfectly illustrates all 5 symptoms: jargon (M3.5), no explanation of what it means, no explanation of WHY it matters, presented as a pipeline status report, and assumes the user understands the internal structure.

## Prior Art

Previous ideation overhaul (`.owlbear/briefs/draft-ideation-overhaul-2026-04-20/`) redesigned the pipeline structure (phase split, challengers, O15, disclosure ladder, etc.). That overhaul focused on *correctness* — preventing drift, opacity, and rubber-stamping. This work focuses on *user experience* — making the same pipeline legible and pleasant for the user.
