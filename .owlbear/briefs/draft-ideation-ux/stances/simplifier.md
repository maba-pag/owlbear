# Simplifier Stance — Ideation UX

## Verdict

5 outcomes are too many. Two of them are duplicates and one is a style modifier, not an outcome. The file scope is wider than necessary if the rules land in the right shared layer. The core fix is small — but it must be specific enough to stick.

## Outcome Collapse: 5 → 3

| Current | Proposed merge | Rationale |
|---------|---------------|-----------|
| 1 (Labels visible, contextualized) + 4 (Opaque codes get context) | **A: Contextualize internal terminology on first use.** | Same rule applied to the same problem. "M2" and "O15" and "M3.5" are all jargon tokens that need explanation. One outcome covers all of them. |
| 3 (WHY-WHAT-EFFECT) + 5 (Transitions have weight) | **B: Significant actions and transitions get concise WHY-WHAT-EFFECT.** | Transitions ARE significant actions. A transition is just the most visible case. One outcome with examples covering both. |
| 2 (Announce confidently, not verbose) | **C: Direct tone — confident, concise, not permission-seeking.** | This is real but it's a style constraint, not a structural outcome. It modifies HOW A and B are delivered. Could be a sub-rule of B instead of a standalone outcome. |

If C folds into B as a style constraint, this is **2 outcomes**. I'd keep it at 3 for clarity, but 5 is over-specified and creates redundant instruction surface that the model has to reconcile.

## File Scope: 5 → 3

The user-facing language rules belong in **one shared location** that both agents inherit. That's `h-ideation/SKILL.md`.

| File | Keep? | Why |
|------|-------|-----|
| `h-ideation/SKILL.md` | **Yes — primary target** | Both workflow skills reference this. A new "User-Facing Communication" section here is DRY and covers both agents. |
| `ideation-discoverer.agent.md` | **Yes — reinforcement** | 2-3 lines in `critical_rules` pointing to the shared rules. Agent-level rules have highest priority. |
| `ideation-mediator.agent.md` | **Yes — reinforcement** | Same. |
| `w-ideation-discovery/SKILL.md` | **Cut from scope** | If h-ideation carries the rules and the agent file reinforces them, touching this file is redundant. Only revisit if post-implementation testing shows the rules aren't cascading. |
| `w-ideation-mediation/SKILL.md` | **Cut from scope** | Same. |

**Risk of cutting the workflow skills:** If the workflow skills have moment-specific turn shapes that actively contradict the new rules (e.g., "say 'M2:' and then probe"), those lines need editing too. But that's a targeted fix in those files, not a full "add UX guidance to every workflow skill."

## "Communication-only changes" — realistic?

Yes, conditionally. LLMs follow style/tone instructions reliably **when the rules are specific and have examples**. The current outcomes are too abstract ("appropriate weight," "concise explanation"). The implementation must include:

- A short list of **before/after examples** (3-4 covering moment transitions, panel dispatch, jargon first-use)
- **Specific banned patterns** ("Do not say 'M3.5 gate' without explaining what it means")

Without examples, the agent will interpret "appropriate weight" as whatever its training distribution suggests, which is probably verbose ceremony — the opposite of what the user wants.

## Simplest intervention

One new section in `h-ideation/SKILL.md` titled "User-Facing Communication" with:
1. The jargon-on-first-use rule (with 2-3 before/after examples)
2. The WHY-WHAT-EFFECT rule for transitions and significant actions (with 2-3 examples)
3. The tone constraint (direct, confident, not permission-seeking)

Plus 2-3 lines in each agent's `critical_rules` saying "follow h-ideation User-Facing Communication rules."

Total new content: ~30-40 lines in one file, ~3 lines in two others.

## What to cut

1. **Cut outcomes 1+4 into one.** They're the same rule.
2. **Cut outcomes 3+5 into one.** Transitions are significant actions.
3. **Cut w-ideation-discovery and w-ideation-mediation from initial scope.** Add them back only if testing shows rules aren't cascading.
4. **Do not create a "jargon glossary" or "translation table."** The rule is "explain on first use" — the agent can generate the explanation. A static glossary is maintenance debt for marginal value.

## Confidence

**0.85** — The core problem (jargon leak + no transition framing) is real and narrowly scoped. The fix (add communication rules to the shared handbook + reinforce in agent files) is proportionate. The main risk is that the rules need to be in the workflow skills too because of how turn shapes are structured, but that's a P2 if initial placement doesn't cascade.
