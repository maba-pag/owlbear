# Decisions — AC as Structured Frontmatter

## D1 — 2026-05-12 — Project Type

**Status quo:** New ideation request with pre-prepared input.
**Decision to make:** Classify project type for research depth calibration.

**Options considered:**

- A: net-new — this is a new feature with no existing implementation
- B: existing-feature/refactor — modifies existing kanban engine, MCP tools, and cockpit

**Chosen:** B — existing-feature/refactor

**Rejected:**

- A because the kanban engine, task model, MCP tools, and cockpit UI all exist and must be modified. The AC field is new but the systems it touches are mature.

**Source inputs:**

- Codebase: Task model exists at models.py:404, storage parsing at storage.py:294, MCP show_task at server.py:320
- Input doc: explicitly references existing fields, migration, backward compatibility

## D2 — 2026-05-12 — Bundling Strategy

**Status quo:** Input doc proposes both AC and proof bundle as a single feature.
**Decision to make:** Ship as one feature or split into two.

**Options considered:**

- A: Single feature — they share the same insight, ship together
- B: Two features — proof bundle first (fast), AC second (needs design)
- C: Defer — keep scope unified now, split later if needed

**Chosen:** A — single feature

**Rejected:**

- B because user prefers unified delivery; the shared insight and motivation make a single Brief cleaner
- C because the user has clear intent — no need to defer the decision

**Source inputs:**

- User: "they share the same insight, ship together"

## D3 — 2026-05-12 — Investment Tier

**Status quo:** Need to calibrate ideation depth.
**Decision to make:** Assign investment tier from h-ideation taxonomy.

**Options considered:**

- A: Tool — single-user internal utility
- B: Shared — multi-consumer infrastructure
- C: Production — external-facing, maximum rigor

**Chosen:** B — Shared

**Rejected:**

- A because the kanban engine is consumed by pipeline agents, cockpit UI, and MCP tools — not single-user
- C because this is internal tooling, not external-facing

**Source inputs:**

- Codebase: kanban engine has consumers in mcp-kanban, cockpit, pipeline agents, and skills

## D4 — 2026-05-12 — AC in frontmatter vs body conventions

**Status quo:** First-principles challenger argues AC-in-frontmatter is unearned — no named consumer needs programmatic AC queries, and YAML is ergonomically worse than markdown for AC content. Alternative: enforce body section conventions at zero schema cost.
**Decision to make:** Does AC actually need to move to frontmatter?

**Options considered:**

- A: AC in frontmatter — structural benefit is real even without a named consumer today
- B: Body-convention alternative — enforce AC position in body, zero schema cost
- C: Split — ship proof_bundle, evaluate AC promotion later with evidence

**Chosen:** A — AC in frontmatter

**Rejected:**

- B because user values the structural separation of spec vs ops notes as a design principle, not just a response to breakage
- C because user wants unified delivery and considers the structural benefit self-evident

**Source inputs:**

- Challenger: firstprinciples stance at 0.75 confidence against AC promotion
- User: "the structural benefit is real even without a named consumer"

## D5 — 2026-05-12 — Cockpit UI scope

**Status quo:** Input doc proposed cockpit AC checklist and proof bundle badge as part of this feature.
**Decision to make:** Include cockpit UI or defer?

**Options considered:**

- A: In scope — ship cockpit rendering with engine changes
- B: Follow-up — cockpit display is a separate task

**Chosen:** B — follow-up task

**Rejected:**

- A because the simplifier correctly identified cockpit UI as UX polish, not the structural fix. Smaller blast radius.

**Source inputs:**

- Simplifier: cockpit cut removes ~40% scope, targets `serve/cockpit/` entirely
- User: "drop ui"

## D6 — 2026-05-13 — Proof bundle validation layer

**Status quo:** Panel split 2v2 on where proof_bundle validation lives.
**Decision to make:** Model-level validator vs engine-only vs hybrid.

**Options considered:**

- A: Engine-only — validate membership in create_task/edit_task write path only
- B: Model-level — @field_validator in Pydantic model, fires on read and write
- C: Hybrid — normalize (lowercase, sort modifiers) in model, validate membership in engine only

**Chosen:** C — Hybrid

**Rejected:**

- A because consumers might see non-canonical strings from hand-edited files
- B because model validation fires on deserialization — invalid value on disk triggers CorruptionError → task silently disappears from all views

**Source inputs:**

- Architect + enduser: want canonical form on all surfaces
- Data + security: evidence that model validation = read-path silent exclusion (engine.py:670–715)
- Synthesis: hybrid resolves both concerns

## D7 — 2026-05-13 — Proof bundle migration urgency

**Status quo:** Forward-only migration leaves existing tasks with proof_bundle=None.
**Decision to make:** Optional or recommended first-run migration.

**Options considered:**

- A: Optional — agents improvise for legacy tasks
- B: Recommended first-run — ship migration script, recommend running on upgrade

**Chosen:** B — Recommended first-run

**Rejected:**

- A because proof_bundle controls test scope, challenger dispatch, and review depth — unset values create verification gaps

**Source inputs:**

- Security + enduser: proof_bundle is integrity-relevant routing metadata
- Migration script is ~20 lines (regex extract from body)

## D8 — 2026-05-13 — Skill update timing

**Status quo:** Schema change adds frontmatter fields; agents currently read body text.
**Decision to make:** Ship skill updates with schema or separately.

**Options considered:**

- A: Same release — schema + skill updates ship together
- B: Schema first — skill updates follow in a later task

**Chosen:** A — Same release

**Rejected:**

- B because split-brain is certain between schema and skill update delivery

**Source inputs:**

- Security: "Do not ship schema without skill updates"
- User: non-issue in practice — sync-to-main only happens with empty board

## D9 — 2026-05-13 — AC in list_tasks

**Status quo:** User flagged 55/45 pro. All panelists lean omit.
**Decision to make:** Include AC in TaskSummary or omit.

**Options considered:**

- A: Omit — no consumer identified; additive change if needed later
- B: Include full list — available for future consumers

**Chosen:** A — Omit

**Rejected:**

- B because no concrete consumer; bloats every list_tasks response

**Source inputs:**

- All four panelists lean omit
- User: 55/45 pro but no strong use case

## D10 — 2026-05-13 — Canonical field ordering

**Status quo:** Two proposed orderings.
**Decision to make:** Semantic grouping vs type-shape grouping.

**Chosen:** Architect's semantic grouping — `...depends_on, ac, proof_bundle, blocked...`

**Rejected:**

- Data's type-shape grouping because semantic coherence reads better in raw YAML

## D11 — 2026-05-13 — AC naming convention

**Chosen:** Leave organic — agents and users converge naturally. Not a schema constraint.

## D12 — 2026-05-13 — Defense-in-depth limits

**Chosen:** Include engine-level guardrails — max 500 chars per AC item, max 20 items. Prevents accidental bloat at zero cost.

## D13 — 2026-05-13 — Proof bundle enum (user M3 correction)

**Status quo:** Phase 1 research recommended regex validation.
**Decision to make:** Regex vs enum validation.

**Chosen:** Enum (hardcoded frozenset of valid combinations). Combination space is tiny (~15 values). Internal validation only — not exposed to agents as complexity.

**Source inputs:**

- User: "proof bundle is enum, we are talking about a tiny amount of acceptable combinations"

## D14 — 2026-05-13 — Critic validation triage

**Status quo:** Dual Critic passes produced 15 findings.
**Decision to make:** Which findings are material enough to add explicit rules to the Brief?

**Classification:**

- M1 (frontmatter-wins precedence): downgraded to nonsense — agents will naturally read structured frontmatter over body text
- M2 (invalid proof_bundle on read): downgraded to nonsense — agents will handle unexpected values; explicit fallback rules are overengineering
- 5 minor findings: implementation details for the builder, not Brief items
- 4 nonsense findings: relitigate locked decisions or are artifact-ordering issues

**Chosen:** No additional rules added to the Brief. The design is complete as-is. Edge cases are agent-resolvable.

**Source inputs:**

- User: "an agent will think about this and find a solution. why should we tell it to fall back? what else is it supposed to do?"
