# Working Context — Ideation Overhaul

**Working Directory:** `.owlbear/briefs/draft-ideation-overhaul-2026-04-20/`
**Started:** 2026-04-20
**Project type:** Existing — meta-refactor of the OwlBear ideation system itself.

**Files in scope (current ideation system):**
- `share/agents/ideator.agent.md` — Mediator (single user-facing voice)
- `share/skills/w-ideation/SKILL.md` — Canonical 6-moment workflow
- `share/skills/h-ideation-panel/SKILL.md` — Panel handbook
- `share/agents/ideation-{critic,pragmatist,architect,data,enduser,security}.agent.md` — All 6 ideation agents
- `share/instructions/agent-common.instructions.md` — Shared instructions (currently auto-loaded into ideator with mostly irrelevant content)

---

## Investment Tier
**Studio.** Multi-file refactor of pipeline-critical machinery. Architectural choices ahead. Not Sprint (too entangled), not Scratch (real architectural decisions).

---

## Problem Statement (M1 locked)

The OwlBear ideation system fails in four distinct ways, all amplified by a single root cause.

### Four failure mechanisms (heterogeneous)
1. **Discretionary protocol.** Ad-hoc Critic checks are "may not must"; silent resolution allowed. Within-moment Mediator drift escapes challenge.
2. **Opacity-by-design.** Single-voice mediation explicitly hides subagent reasoning and raw research from the user. Subagent influence on Mediator decisions is structurally invisible.
3. **Lossy decision artifacts.** `decisions.md` records only chosen options. Rejected options + rationale evaporate.
4. **Brownfield verification blindfold.** M1 pre-flight is a header skim; deep code reading is delegated to Explore, summarized into research-notes, then hidden from the Mediator by context-economy rules.

### Root-cause amplifier
**Instruction load / attention-budget collapse.** Even unambiguous rules from `w-ideation` (multi-option presentation, per-decision user approval, brownfield discipline) fail in practice because:
- Rules spread across 6+ files (`ideator.agent.md`, `agent-common.instructions.md`, `owlbear-system.instructions.md`, `w-ideation/SKILL.md`, `h-ideation-panel/SKILL.md`, `h-agent-structure/SKILL.md`, user memory).
- In-context artifacts accrete (memory, research, synthesis, decisions, panelist outputs) pushing original protocol rules deeper into context.
- By M4–M5, compliance with M1 rules degrades because attention budget cannot sustain them.

This is what the prior session's "authority fragmentation" framing was actually pointing at — not "rules unclear" but "rules don't survive the attention budget."

### Symptoms (user-observable)
1. Critic under-cadence — no within-moment trigger for drift challenge.
2a. Opaque decisions — Mediator drafts and asks yes/no instead of presenting options with pros/cons/risks/confidence.
2b. Invisible decisions — subagent feedback silently absorbed into Mediator's next move.
3. Late research / brownfield failure — Brief drifts from code reality (cf. Brief B kanban-engine: 41 discrepancies caught at M5).

---

## Outcomes (M2 V4 locked — see `decisions.md` D3)

| # | Outcome |
|---|---|
| **O1** | No user input lost or paraphrased; verbatim preservation. |
| **O2** | Single append-only working log replaces multi-file blackboard. Sequential discussion record — basis for the brief, not a formal registry. Per-turn sections: user input verbatim / agent proposals / subagent feedback / user decisions (with rejected options + rationale). |
| **O4** | Challenge user input by default; agreement requires earned justification. |
| **O6** | Idea-challenge panel (First-Principles + Simplifier + Outsider) invoked at end of M2 covering both M1 problem and M2 outcomes before M3. |
| **O10** | 6-moment structure preserved. |
| **O11** | Every Mediator question to user uses fixed format: context/status-quo + problem + proposal(s) + per-proposal pro/con/risk/confidence + recommended option. |
| **O12** | Always assume brownfield. Research subagent runs at M1 by default. |
| **O13** | Filter/synthesizer agents applied selectively to verbose subagent output. `ideation-pragmatist` is canonical example. |
| **O14** | Mediator drift within a moment must be made visible to the user (not auto-corrected). Mechanism deferred to M4. |

**Design principle (binds M4):** *Solutions must respect attention-budget. Do not fix attention failures by adding more rules. Reduce instruction surface; defer/extract roles; structure artifacts so re-reading is cheap.*

**Implications:** Mediator role shrinks (capture/append/present/invoke; never lock unilaterally). Blackboard becomes a single sequential markdown log. Critic standalone-call compression is *cosmetic* (most Critic load is inside panelist loops — see M3 finding F3) — only O14 matters for Critic-related compliance.

---

## Landscape (M3 — see `research-notes.md` for full evidence)

### Critical findings about the current system
- **F1 — Contradiction in `ideator.agent.md`** lines 21–35: "Transparent by default" vs "Never expose internal deliberation" — actively conflict; structural opacity is built in.
- **F2 — Dead instruction load:** `agent-common.instructions.md` (~70 lines, pipeline-only content) is auto-loaded into ideator context with zero relevance.
- **F3 — Critic compression is cosmetic:** Each panelist runs ≤5 embedded Critic cycles. 4 panelists = up to 20 Critic invocations *inside* deliberation, plus 4 standalone. Compressing standalone Critic to M4/M5 saves 2 of ~22. **Negligible.** O14 is the real Critic outcome.
- **F4 — Hooks already exist:** `allow-stances-only.py`, `deny-writes.py` are PreToolUse safety hooks on panelists/Critic. O9's "no hooks" needs sharper read: forbids *new compliance hooks on Mediator behavior*; existing safety hooks stay.
- **F5 — Per-panelist debate logs** are precedent for "raw debate to file, only synthesis surfaces" — reusable for O6 idea panel.

### Sizing the attention-budget leak
Estimated baseline static load before user input: **~2000+ lines** (mode + 5 instruction files + user memory). Plus on-demand `w-ideation` (~600), `h-ideation-panel` (~300). Concrete optimization targets exist.

### Prior art availability
- **O2 (append-only log):** File-discipline pattern exists (`activity_log.py`, `JsonlStore` proposal, audit log) — all JSONL. Markdown narrative log is novel — must design schema.
- **O6 (idea panel):** Panelist agent template + invocation patterns are mature. Insertion-point precedent: `.owlbear/research/997-skill-preflight-ideation-m1.md`.
- **O13 (filter agents):** Three production examples — `ideation-pragmatist`, `memory-curator`, `code-reader→reviewer`.

---

## Open at M4 design (panel addresses these)

1. **How to architect the single append-only working log** — schema, retrieval, who writes when, what about turn boundaries.
2. **Mediator instruction-surface reduction** — what instructions to strip; how to make `w-ideation` more self-contained.
3. **O14 mechanism** — within-moment drift visibility without adding hooks.
4. **O13 application rules** — when to apply filter agents, when to pass through.
5. **O6 panel mechanics** — three new agent files, model assignment, invocation pattern, output format.
6. **Resolve F1 contradiction** — pick transparency or opacity; V4 implies transparency.
7. **Phasing** — does the overhaul ship as one Brief, or quick wins first (e.g., strip dead instructions immediately) then deeper architecture later?
# Working Context — Ideation Overhaul

**Working Directory:** `.owlbear/briefs/draft-ideation-overhaul-2026-04-20/`
**Started:** 2026-04-20
**Project type:** Existing — meta-refactor of the ideation system itself (`share/agents/ideator.agent.md`, `share/skills/w-ideation/`, `share/skills/h-ideation-panel/`, related instructions).

## Salvage state

Prior session did M1 work and stopped at the root cause. User has handed over salvage notes (see `input/salvage-notes.md`).

## Confirmed (from salvage)

### Symptoms (4)
1. **Critic under-cadence** — bound to fixed moment boundaries; within-moment drift not caught.
2a. **Opaque decisions** — yes/no on pre-drafted choice = decision-laundering.
2b. **Invisible decisions** — Mediator acts on subagent feedback without asking user.
3. **Late research / brownfield failure** — no forced read of existing code at M1/M3.

### Root cause (Critic-validated)
- **Authority fragmentation** — rules scattered across `ideator.agent.md`, `w-ideation/SKILL.md`, `h-ideation-panel/SKILL.md`, `agent-common.instructions.md`, user memory, research notes. No canonical source.
- **Role bloat** — Mediator does dialogue + orchestration + decision drafting + blackboard writes + Critic invocation + summary + Brief drafting. Single point of failure.

## M1 outcome (locked — see decisions.md D1, D2)

**Tier:** Studio.

**Root cause (synthesized after fresh Critic pass + user reframe):** Four distinct failure mechanisms (discretionary protocol, opacity-by-design, lossy artifacts, brownfield blindfold) — each with its own surface — **amplified by instruction-load / attention-budget collapse** that erodes compliance with explicit rules as the conversation deepens.

The original "authority fragmentation + role bloat" framing was rejected; "fragmentation" was renamed and re-scoped as "attention-budget collapse from rule-spread + accreting artifacts."

## Still open
- Scope boundary: does the overhaul touch only `share/agents/ideator.agent.md` + `share/skills/w-ideation/` + `share/skills/h-ideation-panel/`, or does it also touch `share/instructions/agent-common.instructions.md`, the panelist agents, blackboard/artifact format, and pipeline handoff to planner?
- Whether to keep single-Mediator architecture or split (M2 will explore).
- Tension to surface in M2: "transparent by default" vs. "never expose internal deliberation" — these contradict in `ideator.agent.md`.

## M2 raw input (2026-04-20)

### What user wants from the overhauled system
- **No context compression that loses user input.** Files-as-memory has not worked well — but the failure mode is **lost navigation / stale files**, NOT lack of granularity. Mediator got confused and found outdated info with no overview of what was where. Fix is fewer-files / better-sequence / clearer canonicality, not "no files."
- **User input must be challenged more.** Mediator's default agreeableness is a failure mode. Need pushback as default behavior.
- **Extract the questioner role.** Mediator should become more of a passive listener. Questioning role should be a separate agent (constraint: user cannot interact with subagents directly).
- **An idea-challenge panel/agent EARLY (M1 or M2)** — focused on the idea/problem itself, not implementation. Sits before the technical panel.
- **Likely panel candidates** (from popular boards, not locked): Contrarian, First Principles Thinker, Expansionist, Outsider. **First Principles ≈ Critic** — could expand Critic's personality or replace its early-moment role. Same possible overlap with Expansionist depending on whether it's challenging problem or solution.
- **No single agent rotating personas.** Mediator is already overwhelmed; can't carry multiple personas. Need separate agents.

### Structural concerns surfaced
- **Panel weighting is uneven.** Security is "often far off and has little value" but **dominates** because it's dramatic and requests big changes. Other panelists get drowned. User wants to keep Security but rebalance influence. → Suggests panel-weighting / mediator-arbitration is its own design problem.
- **Mediator role-extraction.** Removing questioner from Mediator clarifies: what *should* Mediator still do? (User: more passive listener.) This is different framing from "split Mediator into N agents" — it's "shrink Mediator's job, let other agents speak louder."

### Preserved
- 6-moment structure.
- Panel pattern (some form).

### Tensions still open for M2 outcomes
- **T1/T2 (resolved direction):** Keep blackboard but fix navigation/staleness. NOT remove files. NOT add separate writer agent.
- **T3 (open):** Where does idea-panel sit? M1 or M2 (user said "early"). Replaces Critic at those moments? Supplements?
- **T4 (open):** Which idea-panel personas? The 4 are examples, not locked. Need to pick or design.
- **T5 (open):** What does "passive listener Mediator" actually do? (Reflect/capture/present-options? Yes. Draft decisions? No. Invoke Critic? Maybe — or that role moves out too.)
- **New T6:** Panel-weighting — how to prevent dominant panelists (Security) from drowning quieter ones?
