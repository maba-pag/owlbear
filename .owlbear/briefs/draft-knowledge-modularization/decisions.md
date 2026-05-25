# Decisions — Knowledge Module Modularization

## D0 — 2026-05-25 — Project Type

**Status quo:** Knowledge module exists as ~7700 LOC with functioning but tightly-coupled subsystems.
**Decision to make:** What kind of project is this?

**Options considered:**

- A: net-new (start over)
- B: existing-feature/refactor (restructure what exists)

**Chosen:** B — existing-feature/refactor

**Rejected:**

- A because substantial working code exists (chunking, embedding, graph store, vector store, ingest pipeline, query service). The tech stack and core algorithms are validated. The problem is module boundaries and incremental buildability, not the code itself.

**Source inputs:**

- User: "we tried implementing this but i think we failed... trying to implement a monolith. we should probably take a step back and redefine this module."

## D1 — 2026-05-25 — Investment Tier

**Status quo:** No depth calibration yet.
**Decision to make:** How much rigor does this ideation need?

**Options considered:**

- Scratch: throwaway spike
- Tool: internal single-user utility
- Shared: multi-consumer, durable
- Production: durability critical, expensive if wrong

**Chosen:** Production

**Rejected:**

- Shared because: the interfaces have already proven expensive when wrong (5+ audit cycles, multi-day rework each). Getting these right is a prerequisite for all future knowledge work. The cost of another failure justifies maximum rigor.

**Source inputs:**

- User selected Production tier.

## D2 — 2026-05-25 — Early Challenge Findings (recorded, not decided)

**Status quo:** Outcomes defined, early challengers ran.
**Findings to carry into Phase 2:**

1. **"Engine first" = monolith renamed** (simplifier). The engine layer IS the system. It needs to be split into independently-buildable parts, not delivered as one unit.
2. **Domain maturity risk** (first-principles). System has never served real consumers. Interfaces will evolve. The spec's value is making change trackable, not preventing it.
3. **3 contracts may be too coarse** (user + simplifier). The user sees natural boundaries at tech transitions (browser ↔ content transform). Decomposition granularity is a Phase 2 decision.
4. **Spec must prove cascade localization** (critic). The rejection test for the spec is not just "is it modular" but "can each module's AC run independently" and "do failures localize to named interfaces."
5. **Reuse is optional** (user). No sunk cost attachment to existing code.
6. **Protocol contracts vs. documents** (simplifier). Consider typed Protocol classes in code as the living spec rather than (or in addition to) a document artifact.

**No decision taken.** These are inputs for Phase 2 mediation.

## D3 — 2026-05-25 — Consumer Demand Signal Locked

**Status quo:** No concrete consumer scenarios documented.
**Decision to make:** What are the anchoring use cases?

**Chosen:** Three scenarios locked as demand signal:
1. Cross-source ISMS → standards → approvals query
2. Access rights + tool identification query  
3. Design system component properties + CI alignment query

**Common requirements derived:** Multi-source retrieval, exact text preservation, cross-source entity relationships, provenance attribution.

**Source inputs:**

- User provided concrete scenarios from real corporate knowledge needs.
