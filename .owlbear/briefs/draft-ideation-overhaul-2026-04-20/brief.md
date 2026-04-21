# Brief — Ideation System Overhaul (Reworked)

**Investment tier:** Studio
**Phasing:** Single design brief, two implementation waves with a validation gate between them
**Scope:** OwlBear ideation pipeline — `share/agents/ideator.agent.md`, `share/agents/ideation-*.agent.md`, `share/skills/w-ideation/`, `share/skills/h-ideation-panel/`

---

## 1. Problem

The OwlBear ideation pipeline produces drift-laden briefs. Four distinct failure mechanisms — amplified by an attention-budget collapse — caused Brief B (kanban engine refactor, 2026-04-19) to fail with 41 reality-vs-design discrepancies discovered only at M5.

**Symptoms reported by user:**
1. **Critic under-cadence + over-trust when used** — adversarial challenge fires seldom, often skipped at decision moments. When it does fire, its output is taken unquestioned and verbatim even though empirically ~50% fails basic plausibility checking.
2. **User input used unquestioned** — Mediator accepts user statements as ground truth; no challenge, no probing of assumptions.
3. **Opaque deliberation / invisible decisions** — Mediator presents conclusions without surfacing how subagents shaped them; rejected options evaporate; decisions happen without explicit user-approval gates.
4. **Late research / brownfield blindfold** — code reality is summarized through Explore and hidden from the decision-maker by context-economy concerns.

**Failure mechanisms (4 surfaces):**
1. **Discretionary protocol** — "may not must" for ad-hoc Critic; silent resolution permitted.
2. **Opacity-by-design** — single-voice mediation structurally hides subagent influence and raw research from user.
3. **Lossy decision artifacts** — only chosen option recorded; rejected options + rationale evaporate.
4. **Brownfield verification blindfold** — code reality summarized through Explore, hidden from decision-maker.

**Why explicit rules get violated — the root amplifier:**
**Instruction load / attention-budget collapse.** w-ideation already mandates multi-option presentation, per-decision user approval, brownfield discipline. Rules are unambiguous. Yet they fail because:
- Rules spread across 6+ files (~2000+ lines baseline before any conversation tokens).
- In-context artifacts accrete across moments, pushing original protocol rules deeper into context.
- By M4–M5, compliance with M0/M1 rules degrades because attention budget cannot sustain them.

**Fifth mechanism (discovered during M4):**
**Critic-rubber-stamping.** Mediator treats ~100% of Critic findings as truth. User observation: ~25% are nonsense, ~50% have minor merit, ~25% warrant material change.

---

## 2. Design Principles

Two principles bind all mechanism design in this Brief:

**P1 — Attention-budget.** Solutions must respect the Mediator's finite attention. Do not fix attention failures by adding more rules. Reduce instruction surface; defer/extract roles; structure artifacts so re-reading is cheap.

**P2 — SNR optimization at the subagent→Mediator boundary.** Subagent output reaching the Mediator must be denoised at the boundary, not raw. Auto-context-compression is content-agnostic and destroys signal preferentially. Boundary-denoising via a purpose-built filter agent preserves SNR.

---

## 3. Outcomes

| # | Outcome | Source |
|---|---|---|
| **O1** | No decision-driving user input lost or silently paraphrased; when exact wording matters, it is preserved verbatim in `context.md` or `decisions.md`. | D3 |
| **O2** | Blackboard remains multi-file, but roles are narrowed: `context.md` is the clean current-state snapshot panelists read; `decisions.md` is an append-only decision record including rejected options + rationale; no `working-log.md` is introduced. | D3, revised |
| **O3** | The workflow splits once at the M2/M3 border. Phase 1 handles discovery through locked problem/outcomes and curates the first research pass; Phase 2 starts in a fresh context from the handoff artifacts and owns M3-M6. | Revised |
| **O4** | Challenge user input by default; agreement requires earned justification. | D3 |
| **O6** | An early challenge lane runs at the end of M2. `ideation-simplifier` and `ideation-firstprinciples` are the default early challengers; `ideation-outsider` is added only when the problem signal suggests domain capture, unclear user value, or framing tunnel vision. Critic is not the default early challenger. | Revised |
| **O10** | 6-moment structure preserved (M1 Understanding → M6 Handoff). | D3 |
| **O11** | User-facing turn structure is mode-aware, not universal. M1-M2 use concise investigative probes; synthesis turns summarize findings and tensions; real decision turns require context / problem / proposal(s) / per-proposal pro/con/risk/confidence / recommended option. | D3, revised |
| **O12** | Project type is made explicit early. M1 confirms whether the work is net-new, existing-feature/refactor, or uncertain; research depth follows that answer instead of assuming brownfield by default. | Revised |
| **O13** | Filter/synthesizer agents are applied **selectively**. `ideation-pragmatist` remains the canonical filter, but early-challenger output is denoised only when multiple challenger outputs together create real volume or redundancy. Compact challenger, Critic, or Explore output passes through unchanged. | D3, D4, D8, revised |
| **O14** | Mediator drift within a moment must be detected and surfaced to the user. Detection uses anchor-recall in the structured context header used for synthesis and decision turns; M1-M2 remain freeform. Surface is active only when mismatch is detected. | D3, D9, revised |
| **O15** | Mediator validates each Critic finding individually before accepting/rejecting/modifying. Critic output is treated as adversarial stress input, not a truth source. Material findings are presented individually; trivial/minor findings may be grouped in thematic bundles of at most 3. **No bulk acceptance by the Mediator. No silent absorption.** User retains full agency to drill down, reject, or reclassify. | D7, revised |

---

## 4. Concrete Design

### 4.1 Artifact contract (keep blackboard, narrow roles)

**Principle:** the stale-file problem is treated as a Mediator load problem, not a file-count problem. This overhaul does **not** introduce a new canonical `working-log.md`. It keeps the existing blackboard files and tightens their contracts so each artifact does one job well.

**Artifact roles:**
- `context.md` — clean current-state snapshot for subagents. Mutable. Contains only the state needed to continue the session: problem, tier, outcomes, landscape summary, active tensions, and the current approach state.
- `decisions.md` — append-only decision record. Every user decision records the status quo, options considered, chosen option, rejected options with per-option rationale, and source inputs when wording matters.
- `research-notes.md` — detailed research output from Explore. Remains a research artifact, not a state store.
- `synthesis.md` and future idea-panel digest artifacts — synthesis-layer outputs, not sources of canonical session state.

**`context.md` rules:**
- Keep it narrow. No turn-by-turn transcript, no raw panel output, no rejected-option history.
- Update it at each moment boundary and after any material direction change.
- If exact user wording becomes a constraint, preserve the relevant quote inline in the specific context section rather than copying whole turns.

**`decisions.md` rules:**
- Append-only. Do not rewrite prior decisions; later decisions may supersede earlier ones explicitly.
- Record rejected options and rationale every time the user makes a real choice.
- Preserve verbatim wording only where the wording itself is decision-relevant.

**Decision entry template:**
```markdown
## D{N} — {YYYY-MM-DD HH:MM} — {Topic}

**Status quo:** ...
**Decision to make:** ...

**Options considered:**
- A: ...
- B: ...

**Chosen:** A because ...

**Rejected:**
- B because ...

**Source inputs (when relevant):**
- User: "..."
- Panel / research: ...
```

**No new checkpoint-read protocol:** panelists continue to read `context.md` and `decisions.md`. We do not shift routine subagent operation onto log parsing.

### 4.1.1 Phase split and research bridge

The redesign no longer assumes one user-facing ideator carries all six moments.

**Phase 1 — Discoverer:**
- Covers M1-M2.
- Runs the freeform, high-bandwidth problem and outcomes work.
- Confirms project type early: net-new, existing-feature/refactor, or uncertain.
- Locks the problem statement and outcomes into `context.md` and `decisions.md`.
- Commissions the first codebase/ecosystem research pass only after the project type and problem/outcomes are sharp enough to brief it well.
- Curates `research-notes.md` into a bounded research handoff.

**Research bridge (owned by Phase 1):**
`research-notes.md` must separate:
- **Verified findings** — concrete brownfield facts, reusable pieces, hard constraints.
- **Candidate implications** — tentative ideas or hypotheses derived from the findings.
- **Open research questions** — what Phase 2 may need to investigate further.

**Research timing rule:**
- M1 performs a lightweight project-type and brownfield-suspicion check, not a full research pass.
- The first substantial research pass happens only after M2 has produced a stable enough brief for the research subagent.
- If the work is clearly net-new, Phase 1 may keep the first research pass narrow and Phase 2 decides whether deeper codebase work is needed.

Candidate implications are allowed; approach decisions are not. Phase 1 can suggest where the evidence points, but it does not lock the plan on behalf of Phase 2.

**Phase 2 — Mediator:**
- Starts in a fresh context after the discovery handoff and research bridge exist.
- Reads `context.md`, `decisions.md`, and `research-notes.md`.
- Owns M3-M6: landscape presentation, panel orchestration, decision support, brief drafting, and handoff.
- May request additional deep-dive research if Phase 1 flagged gaps or Phase 2 encounters new uncertainty.

**User-facing transition:**
- Exactly one intentional phase handoff per ideation session unless the user explicitly restarts discovery.
- This is a real phase change, not an internal subagent call pretending to be a reset.
- Phase 1 and Phase 2 each have their own explicit user-facing entrypoint; keep both start prompts minimal.
- The Phase 1 completion message must name the Phase 2 entrypoint explicitly and list the handoff artifact paths so the user does not have to rediscover them.
- Model and personality specialization across the two phases is allowed, but the brief should describe capability profiles, not lock vendor/model names.

**Capability profiles, not model strings:**
- Phase 1 should favor conversational range, framing agility, and productive probing.
- Phase 2 should favor structured synthesis, disciplined choice architecture, and artifact hygiene.
- Early challengers should favor signal over flourish.
- Later adversarial stress roles benefit from cognitive diversity relative to the role they are challenging.

### 4.2 Early challenger agents

Add three early challenger agents in `share/agents/`:

- `ideation-firstprinciples.agent.md` — strips the problem to atoms; challenges assumed structure.
- `ideation-simplifier.agent.md` — challenges complexity and pushes for scope reduction or decomposition.
- `ideation-outsider.agent.md` — challenges from analogous-but-different domains when relevance, audience, or framing may be tunnelled.

**Default early challenger set:**
- Always invoke `ideation-simplifier` and `ideation-firstprinciples` at the end of M2.
- Invoke `ideation-outsider` only when the discovery agent sees signs of domain capture, unclear user value, or overfamiliar framing.
- Do not use `ideation-critic` as the default early challenger. Reserve Critic for later approach and Brief stress tests.

**Output contract:** early challenger outputs must be short and bounded. Each challenger returns only the strongest challenges needed to improve scope and framing, not an essay. The point is signal, not volume.

**Standardized template:** same structural base as existing ideation agents. Avoid hardcoded `model:` fields unless implementation evidence later proves a specific dependency. Same `allow-stances-only.py` write hook. Output written to `stances/{name}.md`; debate log to `stances/{name}-debate.md` only if the challenger itself runs an embedded Critic loop.

### 4.3 Early-challenge denoise filter

When Phase 1 invokes multiple early challengers and their combined output creates real redundancy or volume, `ideation-pragmatist` may be invoked in **denoise mode** (parameterized invocation; no new agent needed). If the challenger outputs are already compact, the discovery agent reads them directly.

**Denoise mandate (encoded in pragmatist prompt parameterization):**
- Strip: filler, hedging, restated context, cross-panel redundancy.
- Preserve verbatim: every distinct claim, every divergence, every reasoning chain.
- **Forbidden: convergence, paraphrasing, ranking by importance, summary-style compression.**

Output: `synthesis-idea-panel.md` — a denoised digest, NOT a converged summary. Phase 1 reads only this digest when denoise is actually used. Raw stances remain on disk for drill-in.

### 4.4 Interaction modes and anchor-recall

The brief should not force one user-facing shape onto every turn. Different moments are doing different work.

**Investigative turns (M1-M2):**
- Goal: surface the real problem, hidden assumptions, unconventional framing, and unstated constraints.
- Shape: concise status quo, what is unclear, a focused probe, and why the question matters now.
- Rule: no forced options table unless a real decision is being made.
- Phase mapping: these belong to Phase 1.
- Required early clarification: ask whether the work is net-new, an existing-feature/refactor, or still unclear.

**Synthesis turns (typically M3 and any later turn relaying subagent findings):**
- Goal: summarize what was learned, name tensions, and tee up the next choice.
- Shape: brief context header, findings, tensions, recommendation or next question.
- Rule: attributed findings and drill-down hooks are required; full decision scaffolding is not.
- Phase mapping: these belong to Phase 2.

**Decision turns (M4-M6 and any earlier real choice):**
- Goal: make an explicit user choice with clear trade-offs.
- Shape: full structured format: context / problem / proposal(s) / per-proposal pro / con / risk / confidence / recommended option.
- Rule: if the Mediator is asking the user to choose, this format is mandatory.
- Phase mapping: these belong to Phase 2.

**Anchor-recall:** user-visible anchor-recall lives in the structured context header used for synthesis and decision turns. It is not required on every M1-M2 probe.

**Drift detection:** before composing the next synthesis or decision turn, the Mediator compares the current anchor with the prior anchor. On mismatch (or sub-topic shift not signaled by the user), the Mediator surfaces it: *"I notice we've shifted from [X] to [Y] — intentional or should we return?"* No ceremonial recital on every freeform turn.

Implements O11 and O14 together without turning early ideation into form-filling.

### 4.5 Critic-validation pass (O15 mechanism)

The Critic is intentionally adversarial and may overshoot. The Mediator must treat Critic output as a stress test of the current position, not as authoritative truth. Overshoot is expected; automatic acceptance is forbidden. Automatic dismissal is also forbidden.

When Critic returns N findings, Mediator MUST:
1. **Validation pass** — classify each finding: `nonsense` (with reason for dismissal) / `minor` (with proposed adjustment) / `material` (with proposed change).
2. **Append validation** to working log inline (raw Critic text + classification + reasoning preserved on disk).
3. **Present findings to user as O11-format questions.** Material findings are always presented individually. Trivial/minor findings may be grouped thematically (≤3 per question) when the Mediator's assessment is clear.
4. **Use a disclosure ladder per finding:** start with the Mediator's assessment and recommended response; provide concrete specifics when needed; provide inline verbatim Critic text when the decision depends on the exact wording or the user asks for it.
5. **User can reclassify** (override Mediator's classification) or batch-approve remaining trivial findings after seeing per-finding assessment.
6. Only validated-and-user-approved findings shape Mediator's next move.

**Bulk acceptance by the Mediator is forbidden.** Silent absorption is forbidden. The user retains full agency including batch-approving trivials.

**Interpretation rule:** the Mediator may never accept or reject a Critic finding based on tone, intensity, or rhetorical force alone. Classification must be grounded in the actual claim, the relevant evidence, and the trade-off at stake.

**Internal labels:** First mention of each finding uses descriptive text — e.g., "the brownfield-blindfold finding (F3)." Subsequent references within the same context may use the short label.

### 4.6 Disclosure ladder (user-facing presentation)

Subagent material reaching the user should be disclosed in the lightest form that still supports a good decision.

**Default summary:**
- Situation / problem / options / recommendation / effect.
- Use this by default when the user does not need raw detail yet.

**Concrete specifics:**
- Exact names, settings, failure modes, mechanism, and trade-offs.
- Provide this when the user asks for more detail **or** when omitting it would only force a pointless follow-up.

**Inline verbatim evidence:**
- Attributed panelist wording, raw Critic text, or quoted brownfield evidence.
- Provide this when the decision depends on the exact wording, when the user asks for source-level detail, or when the Mediator's summary is being challenged.

**Rules:**
- Do not dump raw material by default.
- Do not make the user open a file to access decision-critical information.
- Prefer concise summaries first, but do not withhold obvious specifics if they are already necessary.
- When verbatim evidence is needed, inline the relevant passage with attribution rather than redirecting the user elsewhere.

**Critic check at moment-end:** not mandatory. Mediator may offer a Critic check at any moment-end, with its assessment of whether it would be helpful. User decides.

### 4.7 Instruction-surface reduction

This overhaul should reduce instruction load by **role separation**, not by trying to perfect one giant workflow file.

**Required structure:**
1. **Split the workflow skills by phase.**
	- `w-ideation-discovery` — loaded by the early user-facing agent only.
	- `w-ideation-mediation` — loaded by the later user-facing agent only.
2. **Keep `h-ideation-panel` panelist-facing only.** Panelists load it; the two user-facing phase agents do not.
3. **Keep `w-ideation` only as a thin overview/router** or retire it after migration. It should describe the phase map and handoff artifacts, not carry the full operating procedure for both phases.
4. **Resolve F1 contradiction** in the user-facing mediation agent. Keep transparency-with-attribution; remove the opacity directive.
5. **Drop line-count and "binding-rule density" pseudo-metrics** from the redesign. The quality test is role fit: each agent loads only what it needs.

**Net effect:**
- Discovery agent loads discovery rules only.
- Mediation agent loads mediation rules only.
- Panelists load panel rules only.
- The system stops treating one heroic self-contained file as the goal.

### 4.8 Surviving structure

Unchanged in this Brief: `context.md`, `decisions.md`, `stances/*.md`, existing `synthesis.md` (M3→M4 panel synthesis), `research-notes.md`, `brief.md`, and the `input/` directory. Existing safety hooks (`allow-stances-only.py`, `deny-writes.py`) remain unchanged.

New artifact introduced (per 4.3): `synthesis-idea-panel.md` — optional denoised digest of the M2 early challenge lane. Written by parameterized pragmatist only when denoise is warranted.

Artifact explicitly **not** introduced: `working-log.md`.

### 4.9 Agent contract updates

This rework deliberately avoids a large artifact migration. Ideation agents keep the current `context.md` / `decisions.md` contract, but those files get clearer roles and stronger write discipline. Implementer must update:

- **`share/agents/ideator.agent.md`** — keep reads of `context.md`, `decisions.md`, and `synthesis.md`. Update write discipline so `context.md` remains a narrow snapshot and `decisions.md` captures rejected options + rationale. Add `synthesis-idea-panel.md` read only if issue-panel denoise survives later review.
- **`share/agents/ideation-pragmatist.agent.md`** — keep `context.md` / `decisions.md` / `stances/*.md` read path. Denoise-mode behavior, if retained, writes `synthesis-idea-panel.md` only when multiple early challenger outputs actually need synthesis.
- **`share/agents/ideation-architect.agent.md`, `ideation-data.agent.md`, `ideation-enduser.agent.md`, `ideation-security.agent.md`** — keep reading `context.md` and `decisions.md`, optionally `research-notes.md`. No checkpoint-parse contract introduced.
- **`share/agents/ideation-critic.agent.md`** — keep reading `context.md` as the engagement snapshot. Do not expand it to log parsing.
- **NEW agents `ideation-firstprinciples.agent.md`, `ideation-simplifier.agent.md`, `ideation-outsider.agent.md`** — follow the same `context.md` + `decisions.md` contract from the start and keep outputs bounded.

---

## 5. Acceptance Criteria

The implementation is complete when:

1. **Blackboard stays multi-file, with tightened roles.** New ideation sessions keep `context.md` and `decisions.md`; no `working-log.md` is introduced. `context.md` remains a narrow current-state snapshot, and `decisions.md` records chosen and rejected options with rationale.
2. **Early challenger agents exist** at `share/agents/ideation-{firstprinciples,simplifier,outsider}.agent.md`, follow standardized template (no `model:` field), and write bounded outputs to `stances/`.
3. **Capability profiles are explicit; model strings are not the contract.** Discovery, mediation, challenger, and Critic roles each describe the capabilities they need. Exact model names are implementation choices unless a later implementation proves a hard dependency.
4. **`ideation-pragmatist` supports denoise mode** via prompt parameterization. Invocation in `w-ideation` is conditional: use it only when multiple early challenger outputs create real redundancy or volume.
5. **Mode-aware interaction contract + anchor-recall** is mandatory in `w-ideation`. Skill text distinguishes investigative, synthesis, and decision turns; only synthesis and decision turns require the structured context header and anchor-recall. M1-M2 are explicitly freeform unless a real decision arises.
6. **Critic-validation pass (O15)** is mandatory in `w-ideation`. Skill text frames the Critic as intentionally adversarial and prone to overshoot, forbids bulk Mediator acceptance, requires evidence-based classification, allows thematic grouping of trivial findings (≤3 per question), and requires material findings presented individually.
7. **A disclosure ladder is encoded in `w-ideation`.** The skill documents default summary, concrete specifics, and inline verbatim evidence, and makes clear when each is appropriate.
8. **Instruction-surface changes applied:** discovery and mediation have separate workflow skills; `h-ideation-panel` remains panelist-facing only; the opacity contradiction in the user-facing mediation agent is resolved. Acceptance checks verify role-appropriate loading, not line-count or density proxies.
9. **Agent contracts remain explicit and narrow (per 4.9).** Ideation agents continue to reference `context.md` and `decisions.md`; no ideation agent introduces `working-log.md` or checkpoint-read conventions. Grep-verifiable.
10. **Validation is scenario-driven, not one-session-driven.** Implementation evidence includes at least three named golden scenario classes: (a) net-new work, (b) existing-feature/refactor, and (c) an overscoped request that should be reduced or split in Phase 1.
11. **Each golden scenario produces artifact evidence.** For every scenario, `context.md`, `decisions.md`, and any `research-notes.md` / early-challenge artifacts are inspected. Concrete checks: rejected options are recorded where real choices existed, `context.md` stays concise enough for subagent read use, and the phase-appropriate interaction style is visible.
12. **Phase split is real, not cosmetic.** At least one golden scenario shows Phase 1 ending after problem/outcomes lock plus first-pass research curation, and Phase 2 starting from `context.md`, `decisions.md`, and `research-notes.md` in a fresh context. Additional research remains possible but is not mandatory.
13. **Project type is explicit before deep research.** At least one golden scenario shows M1 recording whether the work is net-new, existing-feature/refactor, or uncertain. Full research is not triggered by default in M1.
14. **Early simplification is validated directly.** In the overscoped golden scenario, the early challenge lane must materially reduce, split, or bound the request before Phase 2 begins; this is verified in `decisions.md`, not inferred from the final Brief alone.
15. **Critic handling is validated under stress.** At least one golden scenario demonstrates O15 on a non-trivial Critic pass, including evidence-based classification, individual handling of material findings, and bounded grouping of minor findings where appropriate.
16. **Human review remains as the final layer, not the only layer.** One full end-to-end scenario is reviewed qualitatively by a human for clarity, drift handling, and overall usefulness after the scenario evidence is already present.
17. **The phase handoff UX is explicit.** Phase 1 ends with a message that names the Phase 2 entrypoint and points to the handoff artifacts (`context.md`, `decisions.md`, `research-notes.md`) so Phase 2 can start without delay.

---

## 6. Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| `context.md` regresses into narrative bloat | Medium | Encode a narrow snapshot template in `w-ideation`; keep history and rejected options out of `context.md` |
| User framing hides whether the work is new or a rework | Medium | Require explicit project-type confirmation in M1 before sizing research depth |
| Research bridge becomes covert synthesis | Medium | Separate `research-notes.md` into verified findings, candidate implications, and open questions; forbid Phase 1 from locking approach decisions |
| Mediator overcompensates and starts dismissing the Critic too easily | Medium | State explicitly that Critic overshoot is expected but not a reason to ignore valid claims; require evidence-based triage |
| Capability guidance is too vague and leads to poor model choices | Medium | State the role capabilities crisply and keep model selection as an implementation decision subject to scenario validation |
| Golden scenarios devolve into demo scripts instead of real protection | Medium | Tie each scenario class to a known failure mode and require artifact evidence for that specific failure |
| The disclosure ladder collapses into either over-sharing or over-withholding | Medium | Encode when specifics and verbatim evidence are actually required; review at least one scenario for conversational usefulness |
| Early challenger outputs drift beyond their bounded contract | Medium | Encode a short-output contract in the challenger prompts and verify it in review |
| Denoise-mode pragmatist over-compresses (re-introduces convergence) | Medium | Explicit "preserve verbatim" mandate in prompt parameterization; debate log captures pragmatist's reasoning |
| Early moments relapse into form-filling | Medium | Encode separate investigative-turn rules in `w-ideation`; reserve full structure for real synthesis and decision work |
| Anchor-recall becomes performative | Low-Medium | Keep it on synthesis and decision turns only, where the context header is already justified |
| O15 validation pass adds friction | Low | User explicitly requested per-finding handling. Thematic grouping of trivial findings keeps it manageable. |
| New idea-panel agents add Mediator load | Low | Output goes through denoise filter; Mediator reads digest only |
| Phase-specific skills drift apart or duplicate each other | Medium | Keep a thin overview/router for shared terminology and the phase map; keep panel rules in the panel handbook |
| `decisions.md` stays lossy in practice | Medium | Encode a required decision-entry template with chosen + rejected options + rationale |
| Forcing functions are self-reported | Medium | Primary target is silent-skip prevention (structurally addressed by mandatory log fields). Semantic quality verified by test-pass session (AC #10). |

---

## 7. Out of Scope

- Pipeline agents (`architect`, `builder`, `reviewer`, etc.) — this Brief touches only ideation agents.
- The kanban or memory MCP servers — no changes.
- Changes to existing M3→M4 deliberation panel (architect/data/enduser/security/pragmatist). Only the new Phase-1 early challenge lane is added; existing panel keeps its converge-synthesis pragmatist invocation.
- Changes to `ideation-critic.agent.md`'s adversarial behavior. O15 is a Mediator-side discipline, not a Critic-side change. (Critic's read contract IS updated per §4.9.)
- Backporting these changes to in-flight ideation sessions.

---

## 8. Handoff

On Brief approval, Mediator:
1. Creates parent kanban task (priority: needed; tags: ideation, infrastructure) with this Brief in body.
2. Invokes `planner` for subtask decomposition across **two implementation waves**.

**Wave 1 — Foundations + validation harness:**
- artifact contract
- phase split + research bridge
- role-based skill split
- agent contract updates needed to make the new architecture real
- scenario-driven validation harness / golden scenarios

**Validation gate:**
- run the golden scenarios against the Wave 1 architecture before Wave 2 starts
- confirm the phase split, artifact discipline, and project-type routing are behaving as intended

**Wave 2 — behavioral refinements on top of the new architecture:**
- early challenge lane
- conditional denoise
- interaction modes + anchor-recall
- Critic handling
- disclosure ladder

Likely 9–12 atomic TDD-paired tasks across the two waves.

---

## Appendix A — Reworked Principles

This reworked brief differs from both earlier versions in a few decisive ways:

1. **It stops optimizing for file-count reduction.** The stale-artifact problem is treated as a role/load problem, so `context.md` and `decisions.md` survive with tighter roles and no `working-log.md` is introduced.
2. **It turns the ideator redesign into a real phase split.** Discovery and mediation are separate user-facing phases with a research bridge between them.
3. **It restores freeform discovery.** M1-M2 are no longer forced into a universal decision-style template.
4. **It replaces blanket brownfield assumptions with explicit project-type confirmation.** Research depth follows what the work actually is.
5. **It keeps early challengers, but only the ones with the best signal profile by default.** Simplifier and First-Principles are default; Outsider is conditional; Critic moves later.
6. **It narrows the Critic fix to the real problem.** Critic output gets evidence-based triage without reviving a universal subagent-validation bureaucracy.
7. **It reduces instruction load by role fit, not by heroic compression.** Discovery, mediation, and panelists stop sharing one monolithic workflow skill.
8. **It validates by scenario class, not by one lucky run.** The acceptance strategy now targets known failure modes directly.

## Appendix B — Lineage Notes

This reworked brief still inherits useful insights from the original decision trail, but it intentionally diverges from several earlier conclusions:

- The original D1/D6.1 move to eliminate `context.md` is rejected here.
- D7's diagnosis of Critic rubber-stamping is preserved and refined into a narrower, higher-signal O15.
- D8's denoise principle survives, but early denoise is now conditional rather than a default ritual.
- D9's drift concern survives, but anchor-recall is tied to structured turns rather than every turn.
- D10's transparency goal survives, but the formal level protocol is replaced with a lighter disclosure ladder.
