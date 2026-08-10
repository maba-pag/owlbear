# Ideation UX — Brief

## Investment Tier: Shared

## Problem

The ideation agents expose internal pipeline terminology without explanation, require prior system knowledge to follow, and narrate protocol status instead of explaining purpose. Root causes: vocabulary starvation (no alternative phrasings provided in instruction files) and compliance signaling (agents echo jargon to prove protocol adherence).

## Outcomes

A. **Purpose-driven communication.** Agent explains actions in terms of purpose and benefit. Internal terminology gets plain-language context on first use. Compliance demonstrated through clear explanation, not jargon narration.

B. **Oriented transitions.** Phase shifts get brief "where we are / what's next / why" framing. One sentence, not ceremony.

C. **Direct tone.** Confident, concise, not permission-seeking. Agent announces procedural actions; offers genuine choice only for direction/scope changes.

## Approach

Three mechanisms, in priority order:

1. **Vocabulary map + Communication Patterns** (passive fix for vocabulary starvation). A new section in `h-ideation` provides: canonical attribution labels, transition examples by situation, boundary heuristic (procedural/direction/depth), and depth-control verbal cues augmenting the Disclosure Ladder.

2. **Directive rewrites** (active fix for compliance signaling). The 4 instructions that explicitly require narrating internal routing are replaced with purpose-framed alternatives, co-located with the steps they govern.

3. **Before/after pairs** (behavioral demonstration). 6 concrete examples showing the expected communication style, including non-happy-path cases. These are the primary behavior-change lever — abstract rules alone don't move style.

**Supplementary enforcement:**
- One critical_rule line per agent file: "Apply user-facing vocabulary from h-ideation § Communication Patterns. Internal names appear with explanatory context. Never announce internal evaluations — narrate only results."
- Verification criteria in both workflow skills update from "did the agent name the component" to "did the agent explain the purpose."
- Light cleanup of h-ideation-panel section heading guidance (prevents jargon leakage through panel stances read by mediator).

**Explicit prohibition (jargon laundering guard):** Conditional gates (M3.5, O15, tier checks) and internal verification steps are never announced to the user. The agent narrates what it's DOING (purpose), not what it EVALUATED (mechanism).

## Theoretical Basis

The Moment structure draws from established methodologies documented in `.owlbear/research/thinking-companion-framework.md` §4:

| Source | What it provides | Moment mapping |
|---|---|---|
| Shape Up | Appetite/problem narrowing | M1: Understanding |
| Opportunity Solution Trees | Outcome → opportunity → solution separation | M2: Outcomes |
| Double Diamond | Diverge-converge (problem then solution space) | M3-M4: Landscape → Decision |
| Six Thinking Hats | Deliberate perspective-shifting, attributed reasoning | Panel deliberation |
| Working Backwards | Success narrative as gut-check | M5: Brief |
| JTBD | Outcome over feature thinking | M2: Outcomes |

The UX fix preserves this theoretical intent. The moments exist because each represents a distinct cognitive phase with established methodology behind it. What changes is how these phases are communicated — from protocol codes to purpose-driven language that makes the underlying methodology legible rather than opaque.

**Source reference:** The conversational voice targets the style established in the framework (§3 Design Principles, §6-7 example phrasings). The framework demonstrates how the same structure was originally intended to sound: "This feels like a Tool-tier problem" not "Investment Tier: Tool confirmed."

## Canonical Vocabulary Table

| Internal Name | User-Visible Label | First-Mention Pattern |
|---|---|---|
| ideation-architect | architecture review | "the architecture review (checking structural soundness)" |
| ideation-data | data review | "the data review (checking schema and validation)" |
| ideation-enduser | user experience review | "the user experience review (checking usability)" |
| ideation-security | security review | "the security review (checking trust boundaries)" |
| ideation-critic | critical review | "a critical review (stress-testing for weaknesses)" |
| ideation-simplifier | simplification check | "a simplification check (is this over-engineered?)" |
| ideation-firstprinciples | first-principles check | "a first-principles check (are we solving the right problem?)" |
| ideation-pragmatist | *(never surfaced to user)* | *(synthesis agent — user sees only the synthesized result)* |
| M1 / Understanding | problem framing | "We're in the problem framing phase — what's really going on?" |
| M2 / Outcomes | outcome definition | "Now let's define what success looks like" |
| M3 / Landscape | landscape review | "Let me map what exists and what's possible" |
| M3.5 / Design It Twice | *(never announced — internal gate)* | Result only: "I see two viable approaches, let me get them designed separately" |
| M4 / Decision | approach decision | "Time to choose a direction" |
| M5 / Brief | the plan | "Here's the plan" |
| M6 / Handoff | handoff to pipeline | "Next step: turning this into concrete tasks" |
| O15 | *(never announced — internal mechanism)* | Result only: "The critical review raised a valid concern about X" |
| Investment Tier | depth/rigor calibration | "This feels like a [tier] problem — [what that means for the user]. Sound right?" |

**Repeated-mention rule:** First mention uses the full form with parenthetical context. Subsequent mentions use the descriptor only.

## Communication Patterns (new section in h-ideation)

### Narration Principles

Drawn from the framework's Design Principles (transparent-by-default, conversation not forms):

- **Results, not mechanisms.** Internal verification is silent. The agent narrates what it found ("the critical review raised a concern about coupling"), not what it did ("applying O15 classification to Critic output").
- **Conditional gates are never announced.** M3.5, O15, tier checks are internal quality mechanisms. The agent surfaces only their outcome: "There's one clear approach" or "I see two viable directions" — never "M3.5 gate: evaluating ambiguity."
- **Purpose before process.** For every narration, ask: does the user need to know WHY this is happening? If yes, explain purpose. If no, stay silent.
- **Labels stay visible with context (D4).** When an internal label appears, it carries its explanatory parenthetical on first mention: "the Landscape phase (M3 — mapping what exists and what's possible)."
- **Attribution by name with explanation (D6).** "The architecture review (checking structural soundness) flagged coupling between..."
- **Compliance is explanation quality.** An agent demonstrates protocol compliance by clearly explaining purpose and benefit, not by echoing terminology.

### Transition Patterns

One sentence: where we landed + what opens next + why.

| Transition | Pattern |
|---|---|
| Problem clear → outcomes | "The problem is clear. Now let's define what success looks like — what would make this worth doing, and how would we know it worked?" |
| Outcomes → challenge | "Before we lock these outcomes, I'm going to pressure-test them from a couple of angles — checking for hidden assumptions and scope that could bite us later." |
| Landscape → decision (one approach) | "There's one clear approach here. I'm going to get it reviewed from multiple angles before we commit." |
| Landscape → decision (alternatives) | "I see two viable directions, each with real trade-offs. Let me lay them out so you can decide which fits." |
| Brief approved → handoff | "The plan is solid. Next step: I'll turn this into concrete implementation tasks." |
| Tier calibration | "This feels like a [Tier] problem — [plain description]. That means I'll [what tier means for depth]. Sound right?" |

### Boundary Heuristic (Procedural / Direction / Depth)

| Situation | Agent behavior | Why |
|---|---|---|
| Procedural action (reviewing, validating) | Announce with purpose: "I'm going to get this reviewed from three angles" | User doesn't need to approve quality checks |
| Direction/scope change | Offer genuine choice with trade-offs | User's project, user's call |
| Depth change | Signal availability: "I can walk through the reasoning" | Respects time without gatekeeping |
| Correction | State what happened, what it means, then state intent | User needs to understand, not approve |

### Depth-Control Verbal Cues (augmenting existing Disclosure Ladder)

| Level | Existing name | Verbal cue to signal availability |
|---|---|---|
| Default | Default Summary | Always shown — no cue needed |
| Concrete | Concrete Specifics | "I can walk through the reasoning / trade-offs" |
| Verbatim | Inline Verbatim Evidence | "The specific evidence is [source] — I can show it inline" |

## File Changes

| File | Change Type | What Changes |
|---|---|---|
| `share/skills/h-ideation/SKILL.md` | Major addition | New "Communication Patterns" section: vocabulary table, narration principles, transition patterns, boundary heuristic, depth-control cues. New "Before/After Examples" section. |
| `share/skills/w-ideation-mediation/SKILL.md` | Directive rewrite (3×) | Step 1.5 ("Tell the user you are switching..."), Step 2 ("Tell the user which late-domain panelists..."), Disclosure Ladder verbal cues. Co-located `**Narrate as:**` annotations. |
| `share/skills/w-ideation-discovery/SKILL.md` | Directive rewrite (1×) | Step 3 ("End Phase 1 by naming @ideation-mediator...") + Step 1.5 tier presentation. |
| `share/agents/ideation-mediator.agent.md` | One critical_rule added | Vocabulary enforcement + results-only narration. |
| `share/agents/ideation-discoverer.agent.md` | One critical_rule added | Same + handoff critical_rule rewrite. |
| `share/skills/h-ideation-panel/SKILL.md` | Light cleanup | "Panel Output Phrasing" guidance for stance file section headers. |
| Both workflow skills | Verification criteria update | "Narration explains purpose" replaces "agent names the component." |

**Not changed:** Pipeline architecture, subagent dispatch logic, moment ordering, artifact structure, Critic loop mechanics, pragmatist convergence, Brief template.

**Total scope:** ~6 files, ~4 directive rewrites, ~2 new sections in h-ideation, ~2 verification criteria updates, ~2 critical_rule additions, ~1 panel guidance section.

## Before/After Examples

### Pair 1 — Conditional gate narration (M3.5)

**Before:**
> "M3.5 gate: I see one dominant approach (rewrite skill with convention-based mapping + honest verification + TODO markers). No competing viable alternative. Skipping M3.5, proceeding to stance-mode panel."

**After:**
> "There's one clear approach here — rewrite the skill with convention-based mapping, honest verification, and TODO markers. I'm going to get it reviewed from multiple angles to make sure it holds up."

### Pair 2 — Panel roster introduction

**Before:**
> "Invoking ideation-architect and ideation-security panelists for the late-domain panel deliberation phase. Selection based on: structural concern + trust boundary signal."

**After:**
> "I'll run this past two reviews — architecture (structural soundness) and security (trust boundaries) — because this problem has both a design question and a data-exposure question. Want to adjust?"

### Pair 3 — Permission-seeking → confident announcement

**Before:**
> "Should I run the early challengers to validate scope before moving to approach selection?"

**After:**
> "Before we commit to this scope, I want to pressure-test it for hidden assumptions and over-engineering. If something's off, better to catch it now."

### Pair 4 — Status narration → result narration

**Before:**
> "Invoking ideation-critic with stance payload. O15 verification: checking no panelist premise invalidated by user decision."

**After:**
> "Let me stress-test this against your earlier decisions to make sure nothing contradicts what the reviews assumed."

### Pair 5 — Phase handoff

**Before:**
> "Phase 1 complete. Handoff to @ideation-mediator. Artifacts: context.md, decisions.md, research-notes.md at .owlbear/briefs/draft-foo/."

**After:**
> "The problem and outcomes are sharp. Next step: a fresh synthesis session will take these findings and work through approach options with you. Start it with: `/ideation-mediate .owlbear/briefs/draft-foo/`"

### Pair 6 — Non-happy-path: correction/rerun

**Before:**
> "Re-invoking ideation-architect with updated constraint from D4. Previous stance invalidated by scope change."

**After:**
> "Your last decision changes what the architecture review assumed. I need to re-run that review with the updated constraint — it'll take one more pass."

## Verification Method

**Primary:** Grep-based lint. Any internal term appearing in a narration-guidance position without its vocabulary-table parenthetical is a violation. Protocol codes (`M3.5`, `O15`) appearing in `**Narrate as:**` lines without context, or in transition/attribution patterns without explanation, are bugs.

**Review gate:** The task reviewer checks that:
- Verification criteria in both workflow skills have been updated from "did the agent name the component" to "did the agent explain the purpose"
- The 6 before/after pairs are the behavioral specification — new narration guidance is checked against these
- The 4 directive rewrites convey the same intent (behavioral-equivalent)

**Success indicator:** A user who has never seen the ideation pipeline instructions can follow an ideation conversation without asking "what is M3.5?" or "what does that mean?"

## Scope

**In:**
- Communication vocabulary and narration guidance in 6 files
- 4 directive rewrites (3 in mediation, 1 in discovery)
- Before/after examples as behavioral specification
- Critical_rule additions to both user-facing agent files
- Verification criteria updates
- Light panel output phrasing guidance

**Out:**
- Pipeline architecture changes (moment ordering, subagent dispatch, artifact structure)
- Full panel agent persona rewrites (D7 chose light cleanup only)
- Removing internal labels from agent-to-agent or artifact-to-artifact communication
- Changing the Disclosure Ladder's structure or level definitions
- Creating automated testing infrastructure for communication quality
- Modifying the Brief template or kanban integration
- Updating golden scenarios from the previous overhaul (follow-up task if needed)

## Risks & Mitigations

- **Jargon laundering** (agents replace codes with nicer labels but still give status reports) — mitigated by explicit prohibition against announcing internal evaluations, plus before/after pairs demonstrating results-only narration.
- **Maintenance drift** across 3 vocabulary surfaces (h-ideation primary, workflow annotations, panel guidance) — mitigated by precedence rule: h-ideation is authoritative; co-located annotations specialize; conflicts go to h-ideation.
- **Incomplete non-happy-path coverage** — mitigated by including non-happy-path before/after pairs; remaining gaps are follow-up.

## Key Decisions

- D4: Labels visible with context (user preference: expose structure with explanation)
- D5: Before/after examples non-negotiable (abstract rules don't change style)
- D6: Attribution keeps internal names with context
- D7: User-facing + light panel cleanup scope
- D8: Hybrid placement (co-located for 3 directives, standalone for general patterns)
- D9: Non-happy-path included now
- D10: Align with existing Disclosure Ladder terminology
- D11: Skip three-tier commit model
- D12: Boundary heuristic in h-ideation (shared)

## Context

- Project type: existing-feature/refactor
- Prior art: `.owlbear/briefs/draft-ideation-overhaul-2026-04-20/` (focused on correctness; this work focuses on UX)
- Research grounding: `.owlbear/research/thinking-companion-framework.md` (original design spec, target voice)
- Root causes validated by early challengers (simplifier + first-principles)
