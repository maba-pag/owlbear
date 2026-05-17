## Simplifier Stance — Knowledge Source Lifecycle Ownership

### Scope Inflation

This is a lifecycle management framework for 10–50 records with three consumers. That ratio (infrastructure-to-data) is inverted.

The existing codebase already has a 13-field model, full CRUD store with cascade delete, 5 MCP tools, a RefreshOrchestrator with three strategies, and a manifest loader. For 10–50 sources, this is already over-built.

### Cut 1: Defer Health Status Model

The model already has `last_refreshed_at` and `last_error`. An agent calling `list_sources` and reading those two fields can derive health without a formal status enum. At 10–50 sources, the agent can just *look*. Build formal status thresholds when there's evidence agents are failing to notice broken sources.

Estimated cut: ~40% of the proposed work.

### Cut 2: Don't Add a Fourth Creation Path

The problem identifies 3 disconnected creation paths. Adding a 4th (`register` MCP tool) is additive, not simplifying.

Instead: make `ingest_document` register the source consistently (it already partially does this). Make the manifest loader call the same registration codepath. One entry point in the store layer, two callers.

### Cut 3: Trim the Model

At 10–50 sources: `priority` (only matters when sources compete for ranking — use all), `scope` (only matters in multi-project — hardcode global), `enabled` (cascade delete is cleaner than disable/zombie state). Three fields that could be constants until proven otherwise.

### Recommended Decomposition

**P1 — Unified registration (the real problem):**
- Consolidate creation: every code path goes through consistent defaults
- Expose `remove_source` MCP tool (cascade delete already works — wiring only)
- Extend `list_sources` to include `last_refreshed_at` and `last_error`

**P2 — Health + declarative sources (only if P1 proves insufficient):**
- Formal health status derivation
- Manifest-as-MCP-tool
- Staleness thresholds

### Boundary Correction

The users are agents, not humans. Agents don't need a polished lifecycle UX — they need consistent data and predictable tools. The gap is consistency (3 creation paths with different defaults), not ceremony.

Confidence: 0.85
