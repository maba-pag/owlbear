# Simplifier Stance — Memory MCP Tool UX Refactor

## Verdict

This brief bundles four loosely-coupled concerns into one delivery. Two are urgent, two are deferrable. Shipping them together inflates risk, review surface, and the "all or nothing" blast radius. Decompose into P1 (tool UX) and P2 (architecture conformity + consumer rollout).

## Cut 1: Defer the architecture split

**What:** Extracting `serve/memory/` as a standalone engine package (Layer 1 in the problem statement).

**Why defer:** The engine, models, and tools are already separate *modules* inside `serve/mcp-memory/src/owlbear_mcp_memory/`. The code is factored correctly — `engine.py`, `models.py`, `tools.py`. The only consumer of the engine is the MCP server itself. There is no second consumer waiting on a standalone `serve/memory/` package today.

"Architectural conformity with other domains" is a pattern preference, not a functional requirement. The kanban domain has a heavy engine because the Cockpit backend imports it independently of the MCP server. Memory has no Cockpit route, no REST consumer, no second importer. Creating a package to satisfy a naming convention adds: a new `pyproject.toml`, a new test suite, cross-package import wiring, and a package rename in every consumer — all for zero functional gain right now.

**When it matters:** If a second consumer (e.g., Cockpit memory dashboard, CLI tool) needs to import the engine without MCP. That's a concrete trigger, not a speculative one.

**Confidence:** 0.90 — this is the clearest cut.

## Cut 2: Defer consumer updates to a separate brief

**What:** Updating 5 skills, 1 agent, and 2 test files to match the new tool surface.

**Why defer:** Consumer updates are mechanically coupled to the new tool names/signatures but intellectually independent. They're a rollout task, not a design task. Bundling them into the design brief means the brief can't ship until every downstream file is touched — and those files may change for other reasons in the interim.

A separate "Memory MCP Consumer Migration" brief (or even a simple task batch) would be smaller, faster to review, and independently shippable once the new tool surface is stable.

**Counterpoint:** If the new tool surface isn't consumed, it's not tested in context. Mitigation: P1 ships the new tools with tests. P2 migrates consumers and validates end-to-end.

**Confidence:** 0.75 — the argument for shipping atomically is real but doesn't outweigh the scope reduction.

## Cut 3: Simplify access control — don't redesign, just split visibility

**What:** The access control problem (Layer 2) is framed as needing a new mechanism to replace `OWLBEAR_MEMORY_CALLER`. D5 in decisions.md already has the answer: tool-visibility via agent `tools:` lists.

**Why this is simpler than it looks:** If general agents only see `store_learning` and `query_memory` in their `tools:` frontmatter, they *can't call* curator tools. No runtime role check needed. No env var needed. `OWLBEAR_MEMORY_CALLER` and `MEMORY_TOOLS_EXCLUDE` become dead code — delete them. The MCP server doesn't need to know who's calling; it just exposes all tools and lets VS Code agent config handle visibility.

This is not a "design" — it's removing broken machinery and relying on existing infrastructure (agent frontmatter `tools:` arrays). The brief shouldn't frame this as a design decision; it should frame it as a deletion.

**Confidence:** 0.85 — depends on whether MCP tool visibility via agent frontmatter is sufficient (it is for all other MCP servers in the project).

## Decomposition Recommendation

| Phase | Scope | Deliverables | Why separated |
|-------|-------|--------------|---------------|
| **P1: Tool UX fix** | Layers 2–4 only | Delete env-var access control; collapse 5 tools to 2 agent + 1 curator; enrich schema descriptions with constraints | Urgent, self-contained, shippable |
| **P2: Consumer migration** | Blast radius items | Update 5 skills, 1 agent, 2 test files to new tool names/sigs | Mechanical, fast, independently reviewable |
| **P3: Architecture split** | Layer 1 only | Extract `serve/memory/` when a second consumer exists | Deferred until concrete trigger |

P1 is the brief. P2 is a task batch (possibly inline with P1 review). P3 goes on the backlog with a trigger condition, not a date.

## Scope Inflation Flags

1. **"Quality-gated for cross-project shipping"** is a reasonable bar for tool *design* but risks gold-plating the *rollout*. The tool interface quality is P1. The consumer migration quality is P2. Don't let shared-tier quality gates delay the fix for the broken access control.

2. **"Potential frontmatter field additions"** is mentioned in scope boundary but has no concrete requirement driving it. If no field addition is needed for the tool UX fix, drop it from scope entirely. Don't leave the door open for scope creep through "potential" work.

3. The brief says "updated consumers" as a best-case outcome alongside "2-tool agent surface" and "powerful curator tool." Those are two different projects wearing one brief's trenchcoat.

## What stays in P1

- Tool surface split: 2 general-agent tools, 1 consolidated curator tool
- Schema enrichment: all constraints (categories, confidence range, state transitions) in tool descriptions and JSON Schema
- Access control deletion: remove `OWLBEAR_MEMORY_CALLER`, `MEMORY_TOOLS_EXCLUDE`, and all role-checking code
- Tests for the new tool surface

## Confidence

**0.82** — The architecture split deferral and consumer-update separation are high-confidence cuts. The access control simplification via deletion (not redesign) is the strongest signal: the existing decisions already contain the answer, the brief just hasn't acknowledged how simple it is.
