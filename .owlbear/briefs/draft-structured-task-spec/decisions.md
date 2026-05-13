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
