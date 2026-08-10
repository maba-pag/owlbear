# Context — Memory MCP Tool UX Refactor

## Problem Statement

The MCP Memory server's tool interface is hostile to its consumers and architecturally non-conformant. Four compounding layers:

1. **Structural non-conformity.** All other domains follow a two-package pattern (`serve/{domain}/` engine + `serve/mcp-{domain}/` MCP wrapper). Memory has no standalone engine — models, persistence, and business logic live inside `serve/mcp-memory/`, making them untestable without MCP and unimportable by non-MCP consumers.

2. **Broken access control.** `OWLBEAR_MEMORY_CALLER` is a per-process env var, but one MCP server instance serves all callers. Three of five tools require either "curator" or "user" role — impossible to satisfy both from one process. Default `"unknown"` blocks everything.

3. **Agent-hostile tool interface.** Valid categories, confidence range (0.7–1.0), state transitions, and default query behavior are enforced by Pydantic but not exposed in tool descriptions or JSON Schema. Agents fail on first call with cryptic validation errors.

4. **Over-scoped tool surface for general agents.** General agents have 5 tools but only 2 have valid use cases: `store_learning` (create) and `query_memory` (read). `update_entry` has no use case for general agents — they can't see their own pending entries by default, and shouldn't edit curated/approved content. The remaining tools are curator/admin operations.

## Desired Outcomes

**Best:** A memory MCP server that follows the two-package architecture, has a 2-tool surface for general agents where every parameter is self-documenting (no lookups needed), a powerful curator tool for lifecycle management, and updated consumers. The design is deliberate and quality-gated for cross-project shipping.

**Minimum:** Broken access control resolved, schema constraints exposed, tool surface split clarified (agent vs. curator).

**Scope boundary:** Covers tool interface, architecture split, consumer updates, and potential frontmatter field additions. Does NOT revisit storage type (markdown+frontmatter settled) or lifecycle model (3-step stays: pending→curated→approved).

## Affected Consumers

| Consumer | Dependency |
|----------|------------|
| `w-mem-curation` skill | Expects `update_entry`, `approve_entry`, `delete_entry` |
| `memory-curator.agent.md` | Dispatches curation workflow tools |
| `h-mcp-memory` skill | Tool reference handbook |
| `h-memory-structure` skill | Entry structure, reflection format |
| `r-pipeline-protocol` skill | Pre-flight `query_memory`, post-task `store_learning` |
| `tests/test_mcp_memory_1266.py` | AC tests for 5-tool surface |
| `tests/test_memory_tools_1272.py` | Tool error wrapping tests |

## Project Type

`existing-feature/refactor` — pre-rollout audit of an existing, coded MCP server.

## Relationship to Prior Brief

`draft-memory-module` established markdown+frontmatter storage direction (shipped). This brief addresses the tool interface layer and architectural conformity surfaced during pre-rollout audit.

## Active Tensions

1. ~~Architecture: engine extraction deferred (D6).~~ Not in scope.
2. Curator tool surface: what's the right shape? One powerful tool (curator_update) vs. multiple focused tools? Phase 2 decision.
3. Frontmatter may need new fields — storage type is fixed, but schema can evolve.
4. `OWLBEAR_MEMORY_CALLER` and `MEMORY_TOOLS_EXCLUDE` are deletions (D10).
5. General agent tool surface: 2 tools (`store_learning`, `query_memory`). Curator tool surface: TBD.
6. Agent instructions should guide entry-splitting when categories mix (D8 note).

## Early Challenger Corrections

- **Architecture split:** deferred (no current second consumer). Simplifier + first-principles agreed.
- **3-step lifecycle:** challengers wrong. Curator agent runs every 5th cycle and provides measurable quality gate. Human review adds domain knowledge. Both steps are load-bearing.
- **Category enum:** challengers wrong. Categories serve writing discipline (force reflection) and curation routing, not just retrieval filtering.
- **Access control:** challengers right. Delete env vars, use agent `tools:` lists. Sufficient for single-user threat model.

## Research Findings (summary)

1. **MCP memory is dormant.** Zero production data has flowed through the MCP tools. The file-based system (`/memories/repo/`) is the only working memory. This is a pre-production quality audit, not a refactor of a running system.
2. **Only 2/12 pipeline agents have `ob-memory/*` in their tools: array.** Rollout never completed.
3. **memory-curator lacks MCP tools.** Uses `vscode/memory` (file-based) only. Cannot call update_entry, delete_entry, approve_entry.
4. **No migration burden.** Tool surface can be freely reshaped — no production usage to preserve.

## Key Design Directions (for Phase 2)

1. **MCP as single read path.** `query_memory(scope_agents=["agent_name"])` becomes the one-call pre-flight for all agents. Returns curated+approved entries relevant to that agent directly into context. Replaces reading dozens of individual files.
2. **VS Code memory is a big-bang replacement.** When agents get `ob-memory/*`, `vscode/memory` is removed simultaneously. No coexistence. One tool, no ambiguity. Data migration is out of scope (user handles separately).
3. **Tool naming must pass the discoverability test.** Agents find tools via `tool_search`. Current `store_learning` fails — an agent who solved a problem and wants to save it would search for "memory", "save", "remember", "record" — not "store" or "learning." Phase 2 must pick names that match natural search behavior.
4. **Curator needs MCP tools in its tools: array.** Currently missing. Activation includes wiring the curator.
5. **All pipeline agents get `ob-memory/*` in their tools: arrays.** This is activation, not migration.
