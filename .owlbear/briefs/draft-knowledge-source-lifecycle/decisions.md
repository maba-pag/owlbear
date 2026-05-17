# Decisions — Knowledge Source Lifecycle Ownership

## D0 — 2026-05-17 — Project Type

**Status quo:** No prior project-type decision for this ideation.
**Decision to make:** Classify work as net-new, existing-feature/refactor, or uncertain.

**Options considered:**

- A: Net-new — treating source lifecycle as a new feature
- B: Existing-feature/refactor — the data model, store, and partial tool surface exist; this decides ownership and fills gaps

**Chosen:** B (existing-feature/refactor)

**Rejected:**

- A because the KnowledgeSource model, KnowledgeSourceStore CRUD, manifest loader, and partial MCP tool surface already exist. This is about deciding which surfaces own lifecycle operations and filling the gaps, not building from scratch.

**Source inputs:**

- Codebase: `models.py`, `source_store.py`, `refresh.py`, `loader.py`, `server.py` all exist with working source management primitives.
- Prior briefs: Knowledge Activation and Browser Knowledge Extraction both assumed source management exists.

## D1 — 2026-05-17 — Investment Tier

**Status quo:** No tier decision yet.
**Decision to make:** Calibrate depth of ideation analysis.

**Options considered:**

- A: Scratch — quick spike
- B: Tool — standard depth, single user
- C: Shared — full panel, research bridge, thorough analysis
- D: Production — maximum rigor

**Chosen:** C (Shared)

**Rejected:**

- A, B because the decisions shape the tool surface consumed by multiple agents and the operator. Multi-consumer, external integration complexity (authenticated corporate sources).
- D because this is an internal system, not external-facing. Shared rigor is sufficient.

**Source inputs:**

- User confirmed Shared tier.

## D2 — 2026-05-17 — Scope After Early Challenge

**Status quo:** Original framing asked "where does source lifecycle belong: MCP tools, manifest, Cockpit, or hybrid?"
**Decision to make:** Accept the challengers' narrow reframing or stick with the broader lifecycle management framing.

**Options considered:**

- A: Narrow scope — fix bugs (refresh honesty, direct-ingest semantics), expose hidden health data in `list_sources`, add `remove_source` tool. ~4 focused tasks.
- B: Medium scope — A plus a `register_source` tool and a plan for manifest/file-based source declaration.
- C: Full lifecycle management system — formal register/edit/toggle/inspect/remove tools, manifest format, Cockpit UI plan.

**Chosen:** A (narrow scope)

**Rejected:**

- B because `ingest_document` already creates source records. A separate `register_source` tool is premature at 10-50 sources.
- C because both challengers (simplifier @ 0.85 confidence, first-principles @ 0.80) independently concluded the real problems are 3 bugs/gaps, not a missing management system. Enterprise lifecycle patterns don't apply at this scale.

**Source inputs:**

- Simplifier stance: "the gap is consistency, not ceremony"
- First-principles stance: "the ownership question dissolves" when you fix bugs and expose data
- User: accepted narrow scope
