# Synthesis — Ideation System Overhaul (M4 Panel)

**Synthesizer:** Pragmatist
**Sources:** Architect stance (0.82), Data stance (0.82), End User stance (0.82)
**Date:** 2026-04-20

---

## Convergences

### Working Log Fundamentals

All three panelists converge on: `working-log.md` as an **append-only markdown file** with rigid header grammar — not JSONL, not free-form prose. Markdown chosen for human-readability and KISS compliance; regex-scannable headers provide navigability without tooling. `decisions.md` is absorbed into the log (decisions become inline per-turn records). All three agree the log is the source of truth for discussion history and decisions.

### Turn Structure

Architect, Data, and End User agree on per-turn sections containing: user input (verbatim, blockquoted — O1), Mediator proposal (O11 format with options table), subagent feedback (with attribution), and user decision (chosen + rejected with rationale). Data provides the most detailed schema; Architect and End User align on the same structural intent.

### O11 Universality

All three reject scoping O11 to decision turns only — the format applies to every Mediator turn, with density scaling naturally. End User emphasizes proportional brevity (one sentence of context for simple follow-ups, full table for multi-option decisions). Architect and Data embed O11 in the turn schema without exemptions.

### Idea Panel (O6) — Three New Agents

All three agree on: First-Principles, Simplifier, Outsider as three new agent files following the existing panelist template. Same model (Claude Opus 4.6), same Critic loop (≤5 cycles), same safety hooks (`allow-stances-only.py`). Placement at end of M2 covering both M1 problem and M2 outcomes before M3. Output as `stances/{name}.md` + debate logs.

### Instruction-Surface Reduction

All three support removing `agent-common.instructions.md` from ideation agent context (~70 lines of dead pipeline content), resolving the F1 transparency contradiction in `ideator.agent.md` (delete opacity directive, keep attribution), and making `w-ideation/SKILL.md` self-contained so the Mediator no longer reads `h-ideation-panel/SKILL.md` (~300 lines saved). Architect provides the most detailed implementation plan.

### Drift Visibility Is Detection, Not Prevention

All three acknowledge that O14 cannot prevent drift — only make it visible. Architect and End User both note the fundamental limitation: the Mediator may not notice its own drift. No hooks (per design principle). The working log makes missed drift checks discoverable after the fact.

### Stances and Synthesis Files Survive

All three: `stances/*.md` (panelist output), `synthesis.md` (pragmatist output), `research-notes.md` (Explore output), and `brief.md` (final deliverable) all survive unchanged.

### All Three at 0.82 Confidence

Identical confidence from all panelists — high on structural proposals, moderate on O14's inherent limitations.

---

## Disagreements

### D1 — Working Log: Single File vs. Dual-Artifact (context.md survival)

**Architect vs. Data**

- **Architect** eliminates `context.md` entirely. Moment-boundary **checkpoints appended to the log** serve as panelist entry context — a self-contained state snapshot (problem, tier, outcomes, landscape, decisions) that supersedes the previous checkpoint. Two files become one. "Keeping separate summary file re-introduces multi-file fragmentation."

- **Data** keeps `context.md` as a **mutable, Mediator-maintained snapshot** alongside the append-only log. Panelists read `context.md` (clean reference), not the log. Canonicality rule: log wins on conflict. Data explicitly calls dual-artifact maintenance the "most likely data failure" (staleness) but accepts the trade-off for panelist usability: "Panelists need a clean snapshot, not a 200-turn log."

- **End User** does not explicitly address `context.md` survival but states "single file > multiple files" and emphasizes one-file searchability, aligning directionally with Architect. However, End User's synthesis-first walkthrough pattern (§2) implicitly assumes panelists get clean context from *somewhere* — which is the need Data's `context.md` serves.

**Nature of the tension:** Architect optimizes for single-source-of-truth purity and reduced file count. Data optimizes for panelist read ergonomics at the cost of a mutable artifact that can go stale. Both acknowledge the trade-off explicitly.

### D2 — Pragmatist Role in O6 Idea Panel

**Architect vs. Data + End User**

- **Architect** says NO pragmatist for the idea panel. "Three short challenge documents don't need convergence/divergence synthesis — they need to be presented as 'here are three angles of attack.'" Mediator reads the three stances directly (~1-2 pages each). Pragmatist remains exclusive to domain-panel synthesis at M4.

- **Data** says the idea panel follows the "same Mediator consumption path (Pragmatist synthesizes), same Pragmatist input expectations." Idea panel stances use identical structure to domain stances precisely so the Pragmatist can handle both without format branching.

- **End User** describes a "synthesis-first, walkthrough on demand" pattern for the idea panel: Pragmatist synthesis arrives first (2-3 sentences), then the Mediator offers to walk through individual positions. Full stances remain available for direct reading.

**Nature of the tension:** Architect sees the idea panel as compact challenges that the Mediator can relay directly (adding Pragmatist adds latency and an unnecessary synthesis layer for ~6 pages of input). Data and End User see the Pragmatist as a consistent filtering interface that gives the user a landscape view before detail — and prevents the Mediator from silently flattening or selectively relaying panelist positions (which is the opacity problem the overhaul targets).

### D3 — O14 Drift Mechanism: Scheduled vs. Event-Driven

**Architect vs. End User**

- **Architect** proposes a **scheduled drift-check every 3 turns** (5 at Scratch tier). The Mediator appends a drift-check entry to the log containing: current focus, exit criteria remaining, turn count. This is a periodic self-audit — fires whether or not the Mediator perceives a direction change.

- **End User** proposes an **event-driven self-report when the Mediator changes direction**. Three mandatory components: previous direction, new direction + reason, cumulative shift counter for the moment. This fires only when a shift occurs — not on a schedule.

- **Data** does not propose a specific O14 mechanism.

**Nature of the tension:** Architect's scheduled approach catches drift the Mediator doesn't notice (because it fires regardless), but adds protocol surface on turns where nothing drifted. End User's event-driven approach is more informative when it fires (captures what changed and why) but depends on the Mediator noticing its own drift — the exact self-awareness limitation End User themselves warns about. These are complementary rather than mutually exclusive, but as stated they are different mechanisms.

### D4 — O13 Filter Scope: Pragmatist-Only vs. Dual-View

**Architect vs. End User**

- **Architect** applies filters (pragmatist) only when 3+ parallel subagents produce overlapping output on the same question AND total output exceeds ~10 pages. In practice: pragmatist for domain panel only. No filter for idea panel, Critic, or Explore. Compact or non-overlapping output passes through unchanged.

- **End User** proposes a **dual-view** for any filtered output: (1) per-source headline pulled from the subagent's own opening line, then (2) pragmatist synthesis. The user sees both — headlines as an audit trail, synthesis as the actionable summary. Mismatches between headlines and synthesis signal dropped content. The filter agent is always named transparently.

- **Data** aligns with the existing synthesis.md format (convergences/disagreements/recommendations) and doesn't propose an additional headline layer, but does expect the Pragmatist to handle both panels (see D2).

**Nature of the tension:** Architect minimizes filter application (only when truly needed). End User adds a transparency layer (raw headlines) whenever filtering does occur, so the user can audit what was synthesized. These are partially orthogonal — one addresses *when* to filter, the other *how to present* filtered output — but they reflect different trust assumptions about the Pragmatist's synthesis fidelity.

### D5 — Phasing: Sprint + Brief vs. Unaddressed

**Architect only**

- **Architect** proposes Phase 1 (Sprint task: kill dead load, fix F1 contradiction, w-ideation self-containment — ~370 lines removed, near-zero risk) followed by Phase 2 (Studio Brief: the structural overhaul with O1/O2/O4/O6/O10-O14). Phase 1 validates the root-cause hypothesis before committing to Phase 2.

- **Data** and **End User** do not address phasing. Their stances describe the target state without sequencing.

**Nature of the non-disagreement:** No panelist opposes phasing — it's simply unaddressed by two of three. The Architect's rationale (quick wins reduce baseline attention budget and validate the diagnosis) is unopposed.

---

## Recommendation

**Ship a two-phase implementation with the following design choices, flagging open tensions where panelists diverge.**

### Phase 1 — Sprint Task (unopposed)

Proceed per Architect's proposal: kill `agent-common.instructions.md` load on ideation agents, resolve F1 transparency contradiction, make `w-ideation` self-contained. ~370 lines of dead/redundant instruction content removed. This is a pre-condition for Phase 2 and validates the attention-budget root cause.

### Phase 2 — Studio Brief (requires user decisions on D1–D4)

Implement the converged elements:
- `working-log.md` append-only with rigid turn schema (converged)
- `decisions.md` absorbed into log (converged)
- O11 universal question format (converged)
- Three new idea-panel agents: First-Principles, Simplifier, Outsider (converged)
- Instruction-surface reduction (converged, delivered in Phase 1)

**Open tensions that must be resolved before the Brief can be written:**

1. **D1 (context.md):** Does context.md survive as a mutable panelist reference (Data) or get replaced by appended checkpoints in the log (Architect)? This affects panelist read contracts and the Working Directory layout.

2. **D2 (Pragmatist for idea panel):** Does the Pragmatist synthesize idea-panel output (Data + End User) or does the Mediator read idea-panel stances directly (Architect)? This affects the M2→M3 transition flow and whether the Pragmatist needs format awareness for challenge-style stances.

3. **D3 (Drift mechanism):** Scheduled self-check every N turns (Architect) or event-driven self-report on direction change (End User)? Or both? This affects the working log schema (drift-check turn type vs. drift-marker entry type) and the protocol surface in `w-ideation`.

4. **D4 (Filter presentation):** Pragmatist synthesis alone (Architect) or dual-view with raw headlines + synthesis (End User)? This affects the Mediator's presentation protocol when relaying filtered output.

### Confidence: 0.72

Strong convergence on fundamentals (log format, O11, idea panel agents, instruction reduction, phasing). Four material disagreements (D1–D4) require user resolution before the Brief can finalize the Working Directory layout, subagent invocation flow, drift protocol, and filter presentation. None of the disagreements are blocking — they represent genuine design trade-offs where reasonable positions conflict. Lowered from the panelists' individual 0.82 because the recommendation cannot commit to a complete design without resolving D1–D4.

---

## Open Questions

1. **Does `context.md` survive?** (D1 — Architect: no, checkpoints replace it; Data: yes, panelists need a clean mutable snapshot.) The user must decide whether panelist read ergonomics justify a second mutable file with staleness risk, or whether appended checkpoints in the log are sufficient.

2. **Does the Pragmatist synthesize idea-panel output?** (D2 — Architect: no, Mediator reads directly; Data + End User: yes, synthesis-first.) The user must decide whether 3 challenge documents (~6 pages) warrant a synthesis pass, or whether the Mediator can relay them faithfully without a filter layer.

3. **Scheduled or event-driven drift checks?** (D3 — Architect: every 3 turns; End User: on detected direction change.) The user may want both (scheduled catches unnoticed drift; event-driven captures what changed). Or one. The self-awareness limitation End User flags is real either way.

4. **Headlines + synthesis, or synthesis alone?** (D4 — End User: dual-view; Architect: synthesis only when filtering is applied.) The user must decide whether raw panelist headlines add enough audit value to justify the extra presentation step, or whether the full stance files being available on demand is sufficient.

5. **Phasing: does the user endorse Phase 1 Sprint before Phase 2 Brief?** (D5 — Architect only; others silent.) No opposition, but the user should confirm the sequencing before the Brief assumes it.
