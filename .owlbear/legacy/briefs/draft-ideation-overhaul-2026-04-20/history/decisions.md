# Decisions — Ideation Overhaul

## D1 — Investment tier: Studio
**Date:** 2026-04-20
**Rationale:** Multi-file refactor of pipeline-critical machinery. Architectural choices ahead (e.g., possibly split Mediator, restructure protocol enforcement). Sprint would be too entangled; Scratch would not address root cause.
**Rejected:** Sprint (0.20), Scratch (0.05).

## D2 — Root cause framing (synthesized after fresh Critic challenge)
**Date:** 2026-04-20

**Failure mechanisms** (4 distinct surfaces — Critic was right these are heterogeneous):
1. **Discretionary protocol** — "may not must" for ad-hoc Critic; silent resolution permitted. → Symptom 1.
2. **Opacity-by-design** — single-voice mediation structurally hides subagent influence and raw research from the user. → Symptom 2b.
3. **Lossy decision artifacts** — only chosen option recorded; rejected options + rationale evaporate. → Symptom 2a (partially).
4. **Brownfield verification blindfold** — code reality summarized through Explore, hidden from decision-maker by context-economy. → Symptom 3.

**Why explicit rules get violated (user's reframe of "fragmentation"):**
- **Instruction load / attention budget collapse.** w-ideation already mandates multi-option presentation, per-decision user approval, and brownfield discipline. These are unambiguous. Yet they fail in practice because:
  - Rules spread across `ideator.agent.md` + `agent-common.instructions.md` + `owlbear-system.instructions.md` + `w-ideation/SKILL.md` + `h-ideation-panel/SKILL.md` + `h-agent-structure/SKILL.md` + user memory.
  - In-context artifacts accrete (memory, research, synthesis, decisions, panelist outputs) pushing original protocol rules deeper into context.
  - By M4–M5, compliance with M0/M1 rules degrades because attention budget cannot sustain them.
- This is what "authority fragmentation" was actually pointing at — not "rules unclear" but "rules don't survive the attention budget."

**Implication for the overhaul:**
- Fixing the four mechanisms is **necessary but not sufficient**.
- Any solution must also: (a) reduce instruction surface area, OR (b) move enforcement out of attention (hard structural gates, out-of-band verification, forcing functions that don't depend on the Mediator remembering).

**Rejected framings:**
- Pure "single root cause = authority fragmentation + role bloat" (prior session) — overfit, conflates 4 mechanisms, and "fragmentation" mislabels the real attention-budget issue. (confidence 0.10)
- Pure Critic reframe (no role/attention concern at all, just protocol defects) — ignores why explicit rules are violated when they are clear. (confidence 0.20)

**Critic challenge result:** prior framing rejected at 0.22 confidence; this synthesized framing supersedes it.

## D3 — M2 outcome set (V4 final, locked 2026-04-20)

9 outcomes + 1 design principle. User-confirmed after Critic challenge (Critic returned 0.18 confidence rejecting V3; user pushed back on me to NOT over-listen — see D4).

| # | Outcome |
|---|---|
| **O1** | No user input lost or paraphrased; verbatim preservation. |
| **O2** | Single append-only working log replaces multi-file blackboard. Sequential discussion record — basis for the brief, not a formal registry. Per-turn sections: user input verbatim / agent proposals / subagent feedback / user decisions (with rejected options + rationale). |
| **O4** | Challenge user input by default; agreement requires earned justification. |
| **O6** | Idea-challenge panel (**First-Principles + Simplifier + Outsider**) invoked at end of M2 covering both M1 problem and M2 outcomes before M3. Contrarian dropped — that's Critic v2. |
| **O10** | 6-moment structure preserved. |
| **O11** | Every Mediator question to user uses fixed format: context/status-quo + problem + proposal(s) + per-proposal pro/con/risk/confidence + recommended option. Applies to all turns; the chain has to be helpful — recommendations are not anchoring when the user actively steers. |
| **O12** | Always assume brownfield. Research subagent runs at M1 by default. No topic-gated branching. |
| **O13** | Filter/synthesizer agents applied **selectively** to verbose subagent output (e.g., parallel panels, dense Critic). `ideation-pragmatist` remains canonical example. Compact subagent output goes through unchanged. |
| **O14** | Mediator drift within a moment must be made visible to the user (not auto-corrected). Mechanism deferred to M4. Closes Symptom 1. |

**Design principle (binds M4 design, not an outcome):**
*Solutions must respect attention-budget. Do not fix attention failures by adding more rules. Reduce instruction surface; defer/extract roles; structure artifacts so re-reading is cheap.*

**Implications baked in:**
- Critic role compresses to M4/M5 (M1/M2 → idea panel; M3 → always-research; within-moment drift → O14 mechanism).
- Mediator role formally shrinks: capture verbatim, append to log, present in fixed format, invoke subagents, never decide unilaterally. Drafting allowed; locking forbidden.
- Blackboard: multi-file → single sequential log (no formal manifest — KISS).

**Outcomes explicitly dropped (with rationale):**
- O3 (rejected options recorded) — folded into O2.
- O5 ("Mediator does not draft decisions") — too restrictive; drafting OK, locking-without-asking is the sin. Replaced by O11.
- O7 ("Panel influence balanced") — slogan with no testable mechanism; if needed, M4 designs it without an explicit outcome.
- O8 ("Forced brownfield code reads") — replaced by O12 (asymmetrically safer).
- O9 ("Preserve context budget") — became design principle, not outcome.

## D4 — Critic-listening discipline (locked 2026-04-20)

User intervention: "we earlier listened to the critic and followed its advice and that's WHY we landed on our face in M5, not because we skipped it. we listened too much."

**Locked behavioral rule:** Critic findings are *inputs to user decision*, not directives. Mediator walks through each Critic-proposed change individually with honest reasoning + recommendation; user decides each independently. Bulk adoption of Critic recommendations is the same anti-pattern as ignoring Critic.

**Rejection of changes Critic proposed (V3 → V4 transition):**
- Rejected: O11 scope to decision turns only (Critic over-thinking; user: "exact reason why we should avoid the critic in m1 and m2").
- Rejected: O11 optional recommendations (Critic assumption about user; user: "the chain has to be helpful").
- Rejected: O2 manifest mechanism (Critic over-engineering; user: "log is sequential discussion record, not a formal document to register for the olympic games").
- Rejected: O7 keep-with-deferred-mechanism (user: drop O7 entirely; slogans don't earn their keep).

**Adopted (with user modification):**
- O13 → selective not universal.
- O9 → design principle, not outcome.
- O14 → added (Symptom 1 closure).
- O6 → swap Contrarian for Simplifier (Contrarian = Critic v2).

## D5 — Phasing (locked 2026-04-20)
**Single Studio Brief covering all changes.** User chose against two-phase Sprint+Brief. Architect's Phase 1/Phase 2 split is rejected; the validation data point is sacrificed for end-to-end speed.

## D6 — M4 panel-converged design (locked 2026-04-20)

**Source:** `synthesis.md` (Pragmatist 0.72) reading Architect/Data/End-User stances (each 0.82).

### Locked converged elements (no user dissent)
1. **`working-log.md`** — append-only markdown, rigid header grammar, regex-scannable. Replaces multi-file blackboard.
2. **`decisions.md` absorbed** into working log as inline per-turn records.
3. **O11 universal.** Every Mediator turn uses the format; density scales naturally (one-line context for follow-ups, full table for multi-option choices).
4. **3 new idea-panel agents:** First-Principles, Simplifier, Outsider. Same panelist template, same model (Claude Opus 4.7), same Critic loop ≤5 cycles, same `allow-stances-only.py` safety hook.
5. **Idea panel placement:** end of M2, covering both M1 problem statement AND M2 outcomes before M3 begins.
6. **Instruction-surface reduction (~370 lines):**
   - Strip `agent-common.instructions.md` from ideation agents (~70 lines, irrelevant pipeline content).
   - Resolve F1 contradiction in `ideator.agent.md` lines 21–35 — delete opacity directive ("Never expose internal deliberation"), keep transparency with attribution.
   - Make `w-ideation/SKILL.md` self-contained so Mediator never needs to load `h-ideation-panel/SKILL.md` (~300 lines).
7. **O14 = detection, not prevention.** No hooks. Working log makes drift discoverable post-hoc.
8. **Surviving files:** `stances/*.md`, `synthesis.md`, `research-notes.md`, `brief.md` unchanged.

### D6.1 — context.md elimination (D1 resolution)
**LOCKED: Architect (D1a).** No `context.md`. Panelists read the latest moment-boundary checkpoint section of `working-log.md`. Checkpoints written at M1-end, M2-end, M3-end; immutable in history (append-only). Regex/anchor convention encoded in `w-ideation` for panelist read-discipline.
- Rejected D1b (mutable context.md): re-introduces fragmentation, staleness is most-likely failure (Data's own warning).
- Rejected D1c (auto-derived context.md): adds tooling complexity for no structural gain over D1a.

### D6.2–D6.4 — OPEN (D2, D3, D4 still need user resolution)
- **D2 Pragmatist for idea panel** (Architect: no, Mediator reads directly; Data + End-User: yes, synthesis-first).
- **D3 Drift mechanism** (Architect: scheduled every 3 turns; End-User: event-driven on detected shift; Data: silent).
- **D4 Filter presentation** (Architect: synthesis-only; End-User: dual-view raw headlines + synthesis).

## D7 — NEW: Mediator-Critic rubber-stamping pathology (2026-04-20)

**User-reported in M4:**
> *"the mediator just takes any feedback from the critic and rubber stamps it. it doesnt validate, question, anything. in 90%+ of cases it just accepts it as the truth. but in reality, after i push them, they notice that 25% is nonsense, 50% have some merit and lead to minor adjustments, and only 25% have actual full worth. this needs to be addressed and i think this has lead to a lot of drift in the past."*

**Empirical breakdown (user observation):**
- ~25% of Critic findings: nonsense (should be rejected outright)
- ~50%: some merit (lead to minor adjustments)
- ~25%: full worth (warrant material change)

**Implication:** D4 (Critic-listening discipline) was a behavioral rule but not a structural one. Need a structural mechanism that forces Mediator to **validate each Critic finding individually** before accepting/rejecting/modifying — and to record the validation reasoning in the working log.

**Proposed mechanism (to be designed in remaining M4 / Brief):** When Critic returns N findings, Mediator must produce a validation pass that classifies each finding as nonsense / minor / material with reasoning, presented to user as a single O11-format question (per-finding take/reject/modify). User decides each. NO bulk acceptance. NO silent absorption.

**This is the MAIN drift cause** per user's observation. Probably more important than O14 (within-moment drift visibility) because it addresses the *source* of drift (over-trusting Critic) rather than the *symptom* (drift accumulating).

**Add as O15 to outcomes (TBD).** Or fold into D4 as the structural enforcement.


### D7 LOCKED — O15 added (2026-04-20)

**O15 (locked):** Mediator must validate each Critic finding individually before accepting/rejecting/modifying. Validation appended inline to working log (per-finding classification: nonsense / minor / material + reasoning). Findings presented to user as single O11-format question with per-finding take/reject/modify options. **No bulk acceptance. No silent absorption.** Mechanism encoded in `w-ideation`. O14 remains as drift-visibility backstop; O15 is the source-treatment.

## D8 — D2 resolved + design principle elevation (locked 2026-04-20)

### D8.1 — Idea panel synthesis (D2 resolution)
**LOCKED: D2b with denoising mandate.** Idea panel (First-Principles, Simplifier, Outsider) output passes through a synthesizer (parameterized `ideation-pragmatist` invocation) before reaching Mediator. Synthesizer mandate is **denoise**, not summarize:
- Strip: filler, hedging, restated context, cross-panel redundancy.
- Preserve verbatim: every distinct claim, every divergence, every reasoning chain.
- Forbidden: convergence, paraphrasing, ranking by importance.

Raw stances remain on disk for on-demand drill-down. Mediator reads only the denoised digest.

### D8.2 — Design principle: SNR optimization at subagent→Mediator boundary
**Elevated alongside attention-budget principle:**

> *Subagent output reaching the Mediator must be denoised at the boundary, not raw. Auto-compression (when context fills) is content-agnostic and destroys signal preferentially (long outlier text = sharpest insights). Boundary-denoising via a purpose-built filter agent preserves SNR. Compression for its own sake is unnecessary if the input is all signal; the goal is noise removal, not size reduction.*

**Applies to:** M2 idea panel (D8.1), M3→M4 deliberation panel (already implements via Pragmatist), Critic validation pass (O15 mechanism — see D7), M3 research output (already implicit via Explore).

**Implication:** O13 trigger refines from "verbose subagent output" to "any subagent→Mediator boundary with non-trivial volume". Filter is denoise-first; convergence-synthesis is optional and only when explicitly mandated for a specific purpose (e.g., M3→M4 cross-discipline synthesis genuinely benefits from convergence; idea panel does not).

### D8.3 — Rationale (user-derived reasoning)
User reframed the argument from "save tokens" (static cost) to "preserve signal under future auto-compression risk" (dynamic risk). Auto-compression is mechanical; synthesizer-compression is purpose-aware. Same input volume, vastly different signal preservation. Generalizes the same logic that justifies `memory-curator` over raw memory retention.


## D9 — D3 resolved (drift mechanism, locked 2026-04-20)

**LOCKED: D3d — Anchor-recall baked into O11.** Every Mediator turn's O11 "context" header must explicitly recall: current moment, current sub-topic, prior turn's anchor (~1 sentence). Drift surfaces inline as anchor mismatch when reviewing working-log. No separate mechanism, no scheduled cadence, no reliance on Mediator "noticing" — it's mandatory recall, attention-anchoring rather than attention-consuming.

Implements O14. Supersedes Architect (every-3-turns), End-User (event-driven), Data (silent).

## D10 — D4 resolved (presentation, locked 2026-04-20)

**LOCKED: 3-level progressive disclosure.** User-facing presentation goes through:

| Level | Content shape |
|---|---|
| **L0** (default) | Management brief: situation / problem / options / recommendation / effect |
| **L1** (drill 1) | Concrete specifics + tradeoffs: exact names, settings, failure modes, mechanism |
| **L2** (drill 2) | Panelist attribution + raw stance file paths |

**Rules:**
- askQuestions on any subagent-derived turn includes a "more detail" option advancing one level.
- L1 must be **concrete and named** — vague abstractions ("call times out", "switch type A to type B") are forbidden at L1.
- Mediator never auto-skips levels; user controls depth.
- Forbidden: jumping L0→L2 on first drill-in; bundling levels.

**Two-stage compression chain:**
```
panel raw stances → denoise (D8) → digest [Mediator reads]
                                       ↓
                       Mediator forms L0 brief [User sees]
                                       ↓
                              user drill-in: L1 → L2
```

Both compressions are intentional and run in fresh contexts (denoise in subagent, abstract by Mediator immediately after reading digest, before context fills). Auto-context-compression risk minimized at both layers.

Encoded in `w-ideation` as the 3-level ladder + per-level shape rules.

## M4 status: COMPLETE

All 4 design tensions resolved (D1=D6.1, D2=D8, D3=D9, D4=D10). D5 phasing locked. D7 produced O15. Ready for M5 Brief drafting.

