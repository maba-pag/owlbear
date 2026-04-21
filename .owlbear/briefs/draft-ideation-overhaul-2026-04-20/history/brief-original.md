# Brief — Ideation System Overhaul

**Investment tier:** Studio
**Phasing:** Single Brief, no Sprint phase
**Scope:** OwlBear ideation pipeline — `share/agents/ideator.agent.md`, `share/agents/ideation-*.agent.md`, `share/skills/w-ideation/`, `share/skills/h-ideation-panel/`, `share/instructions/agent-common.instructions.md` (ideation scope only)

---

## 1. Problem

The OwlBear ideation pipeline produces drift-laden briefs. Four distinct failure mechanisms — amplified by an attention-budget collapse — caused Brief B (kanban engine refactor, 2026-04-19) to fail with 41 reality-vs-design discrepancies discovered only at M5.

**Symptoms reported by user:**
1. **Critic under-cadence + over-trust when used** — adversarial challenge fires seldom, often skipped at decision moments. When it does fire, its output is taken unquestioned and verbatim even though empirically ~50% fails basic plausibility checking (see fifth mechanism below).
2. **User input used unquestioned** — Mediator accepts user statements as ground truth; no challenge, no probing of assumptions, no "did you really mean X?". Compounds with #1 because if Critic IS skipped, nothing earns the user's framing.
3. **Opaque deliberation / invisible decisions** (merged from prior symptoms 2+3) — Mediator presents conclusions without surfacing how subagents shaped them; rejected options evaporate; "decide" turns happen with no explicit user-approval gate; user only sees the chosen path.
4. **Late research / brownfield blindfold** — code reality is summarized through Explore and hidden from the decision-maker by context-economy concerns. M3 Landscape becomes optional.

**Failure mechanisms (4 surfaces):**
1. **Discretionary protocol** — "may not must" for ad-hoc Critic; silent resolution permitted.
2. **Opacity-by-design** — single-voice mediation structurally hides subagent influence and raw research from user.
3. **Lossy decision artifacts** — only chosen option recorded; rejected options + rationale evaporate.
4. **Brownfield verification blindfold** — code reality summarized through Explore, hidden from decision-maker.

**Why explicit rules get violated — the root amplifier:**
**Instruction load / attention-budget collapse.** w-ideation already mandates multi-option presentation, per-decision user approval, brownfield discipline. Rules are unambiguous. Yet they fail because:
- Rules spread across `ideator.agent.md` + `agent-common.instructions.md` + `owlbear-system.instructions.md` + `w-ideation/SKILL.md` + `h-ideation-panel/SKILL.md` + `h-agent-structure/SKILL.md` + user memory (~2000+ lines baseline before any conversation tokens).
- In-context artifacts (memory, research, synthesis, decisions, panelist outputs) accrete across moments, pushing original protocol rules deeper into context.
- By M4–M5, compliance with M0/M1 rules degrades because attention budget cannot sustain them.

**Plus a fifth mechanism discovered during this M4:**
**Critic-rubber-stamping.** Mediator currently treats ~100% of Critic findings as truth. Empirical user observation: ~25% are nonsense, ~50% have minor merit, ~25% warrant material change. The Mediator's failure to validate Critic findings individually has caused significant drift in past sessions.

---

## 2. Design Principles

Two principles bind all mechanism design in this Brief:

**P1 — Attention-budget.** Solutions must respect the Mediator's finite attention. Do not fix attention failures by adding more rules. Reduce instruction surface; defer/extract roles; structure artifacts so re-reading is cheap.

**P2 — SNR optimization at the subagent→Mediator boundary.** Subagent output reaching the Mediator must be denoised at the boundary, not raw. Auto-context-compression (when context fills) is content-agnostic and destroys signal preferentially (long outlier text = sharpest insights). Boundary-denoising via a purpose-built filter agent preserves SNR. Compression for its own sake is unnecessary if input is all signal; the goal is noise removal, not size reduction.

---

## 3. Outcomes

10 outcomes. All must be satisfied by the implementation.

| # | Outcome |
|---|---|
| **O1** | No user input lost or paraphrased; verbatim preservation in working log. |
| **O2** | Single append-only `working-log.md` replaces multi-file blackboard (`context.md` + `decisions.md` eliminated). Sequential discussion record — basis for the brief, not a formal registry. Per-turn sections: user input verbatim / agent proposals / subagent feedback / user decisions (with rejected options + rationale). |
| **O4** | Challenge user input by default; agreement requires earned justification. |
| **O6** | Idea-challenge panel (**First-Principles + Simplifier + Outsider**) invoked at end of M2 covering both M1 problem and M2 outcomes before M3. Output passes through denoise filter before reaching Mediator. |
| **O10** | 6-moment structure preserved (M1 Understanding → M6 Handoff). |
| **O11** | Every Mediator question to user uses fixed format: context / problem / proposal(s) / per-proposal pro/con/risk/confidence / recommended option. Applies to all turns; chain stays helpful — recommendations are not anchoring when user actively steers. |
| **O12** | Always assume brownfield. Research subagent runs at M1 by default. No topic-gated branching. |
| **O13** | Filter/denoise agents applied at every subagent→Mediator boundary with non-trivial volume (refined from "verbose-only"). `ideation-pragmatist` is the canonical filter; parameterized by mandate (denoise vs. converge-synthesize). **Boundary mapping:** *Already operationalized:* M3→M4 panel (existing pragmatist converge-mode), Critic boundary (O15 validation pass), research boundary (existing Explore digest). *New in this Brief:* M2 idea-panel boundary (see 4.3). |
| **O14** | Mediator drift within a moment must be detected and surfaced to the user with honest acknowledgment when it occurs — not auto-corrected, but also not silently tolerated. Detection is passive (working-log anchor-recall field checked against prior turn); surface is active (Mediator tells user "I notice we shifted from X to Y") only when mismatch detected. No ceremonial recital of anchors in every turn. |
| **O15** | Mediator validates each Critic finding individually before accepting/rejecting/modifying. Per-finding classification (nonsense/minor/material) with reasoning, recorded inline in working log, presented to user as one O11-format question per finding (no clustering). **No bulk acceptance. No silent absorption.** Special case of O16 specifically for Critic. |
| **O16** | **Independent Reasoning Gate.** Before acting on any subagent's output (Pragmatist synthesis, panelist digest, research subagent, Critic), Mediator must write an independent reading: agree / disagree / partial + reasoning. Recorded inline in working log at the turn where the subagent output is referenced. **No silent acceptance of any subagent output.** Addresses the general rubber-stamping pathology beyond Critic alone. |

---

## 4. Concrete Design

### 4.1 Working log (replaces blackboard)

**File:** `working-log.md` in the working directory. Append-only. Markdown with rigid header grammar.

**Per-turn structure (mandatory sections; missing section = malformed turn):**
```markdown
## [TIMESTAMP] — [MOMENT] — [SUB-TOPIC]

**Anchor-recall:** still in [moment], still on [sub-topic]; prior anchor was [prior].

**User input (verbatim):**
> [exact user text]

**Mediator challenge (O4 enforcement; Gap B forcing function):**
[agreed-trivial | agreed-because-... | challenged-because-... | probed-because-...]

**Agent proposal (O11 format):**
- Context: ...
- Problem: ...
- Options: A | B | C
- Per-option: pro / con / risk / confidence
- Recommendation: [option] because ...

**Subagent feedback (if any):**
- [agent]: [denoised digest excerpt with attribution]

**Mediator reading of subagent output (O16 enforcement; Gap C forcing function; only if subagent feedback present):**
- [subagent]: [agree | disagree | partial] because [1-line reasoning]

**Critic considered (S1 cadence forcing function; only on user-decision turns):**
[yes-with-findings F1..FN | no-because-...]

**User decision:**
- Chose: [option]
- Rejected: [other options + rationale per option]

---
```

**Moment-boundary checkpoints:** at end of M1, M2, M3, write a `## CHECKPOINT — M[N] END` section summarizing the moment's locked state. Panelists subsequently invoked read the latest checkpoint section (immutable in append-only history).

**Checkpoint schema (mandatory at moment-end):**

```markdown
## CHECKPOINT — M[N] END — [TIMESTAMP]

**Snapshot type:** full (not delta). Every checkpoint is a complete locked-state snapshot at that moment, designed for standalone read by panelists.

**Mandatory sections:**
- **Problem (lock):** the M1 problem statement frozen at this checkpoint
- **Outcomes (lock):** all locked outcomes with their final wording
- **Decisions (lock):** all locked decisions D1..D[N] with one-line summary each
- **Open questions:** any decisions deferred to next moment
- **Supersession notes:** any prior-checkpoint claims now invalidated by later user reversals (with explicit reference, e.g., "supersedes M2 checkpoint outcome O7")
- **Critic invoked (S1 cadence forcing function):** `YES @ [timestamp] | findings: [F1..FN]` OR `YES @ [timestamp] | findings: none (position solid, confidence X.XX)` — MANDATORY at every moment-end checkpoint. If Critic was skipped, checkpoint is malformed.
```

**Supersession rule:** Append-only never deletes; supersession is recorded explicitly in the latest checkpoint. Panelists are instructed by `w-ideation` to read ONLY the latest checkpoint, never earlier ones (the checkpoint already integrates supersessions). Checkpoint reflects final locked state at moment-end. Intra-moment reversals are recorded in the turn log (chronological record of changes) but checkpoint does not enumerate them — it carries only the final state.

**Eliminated artifacts:** `context.md`, `decisions.md` (absorbed into working-log inline records).
**Surviving artifacts:** `stances/*.md`, `synthesis.md`, `research-notes.md`, `brief.md`, `input/*`.

### 4.2 Three new idea-panel agents

Add three new panelist agents in `share/agents/`:

- `ideation-firstprinciples.agent.md` — strips the problem to atoms; challenges every assumed structure.
- `ideation-simplifier.agent.md` — challenges complexity; demands the simplest mechanism that works.
- `ideation-outsider.agent.md` — challenges from analogous-but-different domains.

**Standardized template:** same structure as existing `ideation-architect.agent.md` etc. Same model (Claude Opus 4.7). Same Critic loop (≤5 cycles). Same `allow-stances-only.py` write hook. Stance file written to `stances/{name}.md`; debate log to `stances/{name}-debate.md`.

**Invocation:** at end of M2 (after outcomes locked, before M3 Landscape). Three panelists run in parallel on the integrated M1 problem + M2 outcomes content.

### 4.3 Idea-panel denoise filter

After the three idea-panel stances complete, `ideation-pragmatist` is invoked in **denoise mode** (parameterized invocation; no new agent needed).

**Denoise mandate (encoded in pragmatist prompt parameterization):**
- Strip: filler, hedging, restated context, cross-panel redundancy.
- Preserve verbatim: every distinct claim, every divergence, every reasoning chain.
- **Forbidden: convergence, paraphrasing, ranking by importance, summary-style compression.**

Output: `synthesis-idea-panel.md` — a denoised digest, NOT a converged summary. Mediator reads only this digest. Raw stances remain on disk for Level-2 drill-in.

### 4.4 Anchor-recall (drift detection — internal)

Every Mediator turn's working-log entry includes an **Anchor-recall** field: current moment, current sub-topic, prior turn's anchor (~1 sentence). **This is an internal working-log field, not a user-facing chat element.** Mediator writes it every turn for self-discipline and post-hoc review.

**Drift detection:** before composing the next turn, Mediator compares current anchor claim with prior turn's anchor. On mismatch (or sub-topic shift not signaled by the user), Mediator explicitly surfaces it in chat: *"I notice we've shifted from [X] to [Y] — intentional or should we return?"* Only surfaces on detected drift. No ceremonial recital every turn.

Implements O14 as a structural forcing function (the mandatory working-log field) without adding chat noise.

### 4.5 Critic-validation pass (O15 mechanism)

When Critic returns N findings, Mediator MUST:
1. **Validation pass** — classify each finding: `nonsense` (with reason for dismissal) / `minor` (with proposed adjustment) / `material` (with proposed change).
2. **Append validation** to working log inline (raw Critic text + classification + reasoning preserved on disk).
3. **Present each finding to user as ONE separate O11-format question.** No clustering, no batching. Even for N=15 findings, that's 15 user turns. Discipline of per-finding seriousness.
4. **Each finding turn uses 3-level progressive disclosure (D10):**
   - **L0 (default):** Mediator's management-brief — what the finding claims (in Mediator's words), classification, recommended response. Plus take/reject/modify/reclassify options.
   - **L1 (drill 1):** Concrete specifics — exact section/line of Brief affected, exact proposed edit, tradeoff.
   - **L2 (drill 2):** Raw Critic claim verbatim + attribution.
5. **User can reclassify** (e.g., override Mediator's "minor" tag with "material") in addition to take/reject/modify.
6. Only validated-and-user-approved findings shape Mediator's next move.

**Bulk acceptance is forbidden.** Silent absorption is forbidden. Verbatim-by-default is also forbidden — verbatim is L2 detail, not L0 default. Mediator's L0 abstraction earns trust by being concrete and accurate, verifiable on user's drill-down.

### 4.6 Three-level progressive disclosure (user-facing presentation)

Subagent material reaching the user passes through Mediator-side abstraction:

| Level | Content shape | Triggered by |
|---|---|---|
| **L0** (default) | Management brief: situation / problem / options / recommendation / effect | Default for all turns |
| **L1** (drill 1) | Concrete specifics + tradeoffs: exact names, settings, failure modes, mechanism. Brownfield claims must cite file:line. | User selects "more detail" askQuestions option |
| **L2** (drill 2) | **Attribution + verbatim opinion** inline: panelist's actual claim text, raw Critic finding text, brownfield evidence (quoted code excerpts with file:line). Self-contained in chat — not a pointer to "go read X". | User selects "more detail" again |

**Rules:**
- askQuestions on any turn surfacing subagent-derived material includes a "more detail" option advancing one level.
- L1 must be **concrete and named** — vague abstractions ("call times out", "switch type A to type B") forbidden at L1.
- L2 must be **inline verbatim** — excerpts and quoted content reproduced in chat. For content > ~500 tokens, Mediator selects the decision-relevant passage inline with attribution. User can request expansion ("show more", "expand this section", "show the next part") — additional content is then fetched and inlined by Mediator.
- **Never redirect the user to files.** File paths may be mentioned for archival completeness, but the user must never be asked to open a file to obtain information needed for a decision. All drill-down is inline in chat. (Mediator does the file-reading work; user sees the content.)
- **Never surface internal labels to the user** — finding-numbers, level-numbers, decision-numbers, outcome-numbers are internal tracking only. User-facing prose refers to findings and decisions by descriptive content ("the rubber-stamping finding", "the bottom level of detail", "the denoise-filter decision"), not by tags. Labels may appear in working-log records but not in user-facing chat.
- Mediator never auto-skips levels; user controls depth.
- Forbidden: jumping straight to bottom-level detail on first drill-in; bundling levels; substituting file paths for inline verbatim at the bottom level; surfacing internal labels in user-facing chat.

### 4.7 Instruction-surface reduction (~370 lines)

**Three cuts (revised by SNR principle):**
1. **Resolve F1 contradiction in `ideator.agent.md` lines 21–35.** Current text says both "single user-facing voice" + "transparent by default" + "never expose internal deliberation." Delete the opacity directive; keep transparency-with-attribution. The opacity directive structurally caused Symptom 3.
2. **Inline `h-ideation-panel/SKILL.md` into `w-ideation/SKILL.md`; deprecate the handbook.** Mediator no longer needs to load a separate file mid-session. Saves ~300 lines of cross-file navigation overhead.
3. **SNR audit of `w-ideation/SKILL.md`.** While inlining (cut #2) and adding new content (anchor-recall, O15 mechanism, denoise mandate, checkpoint schema, 3-level disclosure), audit the entire file for noise — redundancy, restated principles, historical commentary, examples that don't add binding rules. **Optimize for ratio of binding-rules to total content (P2 turned inward).** Hard line limits are forbidden — they compress signal alongside noise.

**Dropped:** prior "strip `agent-common.instructions.md` (~70 lines)" was sleight-of-hand. ~70 lines is rounding noise vs ~600-line w-ideation; the real instruction-load weight is in the skill file itself.

### 4.8 Surviving structure

Unchanged in this Brief: `stances/*.md` files, existing `synthesis.md` (M3→M4 panel synthesis), `research-notes.md`, `brief.md`, `input/` directory. Existing safety hooks (`allow-stances-only.py`, `deny-writes.py`) unchanged.

New artifact introduced (per 4.3): `synthesis-idea-panel.md` — denoised digest of the M2 idea panel. Written by parameterized pragmatist; read by Mediator only.

### 4.9 Agent contract migrations

Every ideation-touching agent file must be updated to read from `working-log.md` (latest checkpoint section) instead of the eliminated `context.md` / `decisions.md`. **Without this, sections 4.1–4.7 land while agents read nonexistent files.** Implementer must update:

- **`share/agents/ideator.agent.md`** — replace `context.md` / `decisions.md` / `synthesis.md` reads with `working-log.md` (latest checkpoint anchor). Retain `synthesis.md` (M3→M4 panel synthesis) and `research-notes.md` reads. **Add read of `synthesis-idea-panel.md`** (M2 idea panel digest, per 4.3). Remove opacity directive (per 4.7 cut #1).
- **`share/agents/ideation-pragmatist.agent.md`** — same checkpoint-read migration; add denoise-mode parameterization (per 4.3). In denoise mode, writes `synthesis-idea-panel.md` instead of `synthesis.md`.
- **`share/agents/ideation-architect.agent.md`, `ideation-data.agent.md`, `ideation-enduser.agent.md`, `ideation-security.agent.md`** — replace `context.md` reads with checkpoint-section reads from `working-log.md`. Read instructions must reference the checkpoint anchor convention.
- **`share/agents/ideation-critic.agent.md`** — same checkpoint-read migration.
- **NEW agents `ideation-firstprinciples.agent.md`, `ideation-simplifier.agent.md`, `ideation-outsider.agent.md`** — bake correct working-log + checkpoint contract from the start (no migration needed; greenfield).

---

## 5. Acceptance Criteria

The implementation is complete when:

1. **Working log replaces blackboard.** New ideation sessions produce `working-log.md` with the rigid header grammar AND checkpoint schema (per 4.1) at every moment-end; `context.md` and `decisions.md` are not created.
2. **Three idea-panel agents exist** at `share/agents/ideation-{firstprinciples,simplifier,outsider}.agent.md`, follow standardized template, write only to `stances/`.
3. **`ideation-pragmatist` supports denoise mode** via prompt parameterization. Invocation in `w-ideation` at end of M2 with explicit denoise mandate.
4. **Anchor-recall (internal) + drift-surface rule** is mandatory in `w-ideation`. Skill text requires every working-log turn to include an Anchor-recall field (moment + sub-topic + prior anchor); requires Mediator to check for mismatch before composing next turn; requires surfacing mismatches to user in chat when detected; forbids ceremonial recital of anchors in every user-facing turn.
5. **Critic-validation pass (O15)** is mandatory in `w-ideation`. Skill text explicitly forbids bulk acceptance, requires per-finding O11 question to user, requires 3-level disclosure per finding (no verbatim-default).
6. **Three-level progressive disclosure** is encoded in `w-ideation`. Each level's shape rules documented (L0 brief / L1 named-specifics / L2 inline-verbatim); askQuestions "more detail" pattern shown.
7. **Instruction-surface changes applied:** F1 contradiction in `ideator.agent.md` resolved (opacity directive removed); `h-ideation-panel/SKILL.md` inlined into `w-ideation/SKILL.md` and deprecated; `w-ideation/SKILL.md` SNR-audited (binding rules preserved, redundancy/historical commentary cut). No hard line cap.
8. **A test-pass ideation session** runs M1→M6 producing a Brief. Working log inspected by a human reviewer; concrete check: every user-decision turn records rejected options with per-option rationale (O2 + O11 evidence). Session demonstrates per-finding O15 handling at least once and anchor-recall in every Mediator turn.
9. **Agent contract migrations complete (per 4.9).** `share/agents/ideator.agent.md` and every `share/agents/ideation-*.agent.md` references `working-log.md` (with checkpoint anchor convention) and does NOT reference `context.md` or `decisions.md`. Grep-verifiable.
10. **Cadence forcing function (Gap A).** Every `## CHECKPOINT — M[N] END` section in a test-pass working log includes a non-empty `**Critic invoked:**` line. Scripted parser check: count of CHECKPOINT sections equals count of Critic-invoked lines.
11. **User-challenge forcing function (Gap B / O4).** Every user-input turn in a test-pass working log includes a non-empty `**Mediator challenge:**` line. Scripted parser check: count of user-input turns equals count of Mediator-challenge lines.
12. **Independent-reading forcing function (Gap C / O16).** Every turn with `**Subagent feedback:**` in a test-pass working log includes a corresponding `**Mediator reading of subagent output:**` line. Scripted parser check: count of subagent-feedback turns equals count of Mediator-reading lines.

---

## 6. Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Working-log header grammar drifts in practice | Medium | Encode regex patterns in `w-ideation`; provide template snippet at top of skill |
| Denoise-mode pragmatist over-compresses (re-introduces convergence) | Medium | Explicit "preserve verbatim" mandate in prompt parameterization; debate log captures pragmatist's reasoning |
| Anchor-recall becomes performative ("still on M2" written without real self-check) | Low-Medium | Drift detectable post-hoc in working log via anchor mismatch; if Mediator skips the self-check, the mismatch simply won't be surfaced to user at the moment of drift, which is the cost of self-reporting. Test-pass session review can sample entries for depth. |
| O15 validation pass adds friction perceived as bureaucratic | Low | User explicitly requested this; per-finding O11 is fast (one question per finding) |
| L1 specifics become vague despite the rule | Medium | Provide example pairs (vague vs. concrete) in `w-ideation`; Critic at any turn can flag vague L1 |
| New idea-panel agents add Mediator load | Low | Output goes through denoise filter; Mediator reads digest only |
| SNR audit of `w-ideation` (4.7 cut #3) is subjective; reviewer might cut signal not noise | Medium | Mitigated at task review — reviewer sanity-checks with grep for binding-rule keywords ("must", "MUST", "forbidden", "required") before/after; ratio should not decrease |
| Forcing functions (anchor-recall, Mediator challenge, Mediator reading, Critic invoked) are self-reported — Mediator could satisfy schema with shallow content ("agreed-trivial", "partial because mixed") without actually doing the reasoning work | Medium | Artifact-schema compliance is necessary but not sufficient. Heavier enforcement (3rd-party auditor agent reading the log) is out of scope for this Brief. Primary target of the forcing function is the common failure mode — silent skip — which IS structurally prevented. Semantic quality is verified by the test-pass session acceptance criterion (reviewer inspects content depth). |

---

## 7. Out of Scope

- Pipeline agents (`architect`, `builder`, `reviewer`, etc.) — this Brief touches only ideation agents.
- The kanban or memory MCP servers — no changes.
- Changes to existing M3→M4 deliberation panel (architect/data/enduser/security/pragmatist). Only the new M2 idea panel + denoise filter is added; existing panel keeps its converge-synthesis pragmatist invocation.
- Changes to `ideation-critic.agent.md`'s **adversarial behavior**. O15 is a Mediator-side discipline, not a Critic-side change. (Critic's **read contract** IS updated per §4.9 — checkpoint-read migration applies to all ideation subagents uniformly.)
- Backporting these changes to in-flight ideation sessions.

---

## 8. Handoff

On Brief approval, Mediator:
1. Creates parent kanban task (priority: needed; tags: ideation, infrastructure) with this Brief in body.
2. Invokes `planner` for subtask decomposition. Suggested decomposition axes: per-section of `4. Concrete Design` (4.1 working log + checkpoint schema, 4.2 idea agents, 4.3 denoise filter, 4.4 anchor-recall, 4.5 O15, 4.6 progressive disclosure, 4.7 SNR-audit + F1 fix + h-ideation-panel inline, 4.9 agent contract migrations) — likely 8–10 atomic TDD-paired tasks.

---

## Appendix A — M3 Landscape findings (reference)

- **F1:** `ideator.agent.md` lines 21–35 contains contradiction (opacity + transparency).
- **F2:** ~70 lines of `agent-common.instructions.md` are dead instruction load for ideation agents.
- **F3:** Critic-loop compression in handbook is cosmetic — actual loop is verbose.
- **F4:** Safety hooks (`allow-stances-only.py`, `deny-writes.py`) already exist and work; no new infrastructure needed.
- **F5:** Append-only debate logs precedent exists in panelist agents (`stances/*-debate.md`).

## Appendix B — Decision lineage

See `decisions.md` D1–D10 for full decision history. Key references:
- D1=D6.1: context.md elimination
- D5: single-Brief phasing
- D6: panel-converged elements
- D7→O15: Critic-rubber-stamping pathology
- D8: idea-panel denoise filter + SNR principle
- D9: anchor-recall (O14 implementation)
- D10: 3-level progressive disclosure
