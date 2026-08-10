# Research Notes — Memory MCP Tool UX Refactor

## Verified Findings

### F1: MCP Memory lifecycle has never executed end-to-end

The pipeline protocol (`r-pipeline-protocol`) prescribes ALL agents doing:
- Pre-flight: `query_memory(states=["curated","approved"])` to load reviewed entries
- Post-task: `store_learning(...)` to record learnings

**Reality:** Only 2 of ~12 pipeline agents (test-writer, test-curator) have `ob-memory/*` in their `tools:` array. The remaining 10+ agents (builder, reviewer, auditor, researcher, architect, planner, etc.) cannot call either `query_memory` or `store_learning`.

### F2: memory-curator.agent.md cannot call MCP memory tools

The curator agent lists `vscode/memory` (file-based tool for `/memories/repo/` files) but NOT `ob-memory/*` (MCP tools). It can read/write markdown files in `/memories/repo/` but cannot:
- Query pending MCP entries via `query_memory(states=["pending"])`
- Promote entries via `update_entry(entry_id, state="curated")`
- Delete entries via `delete_entry(entry_id)`

The `w-mem-curation` workflow prescribes these MCP calls but the executor cannot make them.

### F3: Access control env var never configured

`.vscode/mcp.json` has no `env` block for `ob-memory`. Default `OWLBEAR_MEMORY_CALLER` is `"unknown"`, which means even IF the curator had `ob-memory/*` in tools:, all curator-only tools would still throw "restricted to ['curator']".

### F4: The file-based path IS the working system

The functional curation loop is entirely file-based:
- Agents write to `/memories/repo/inbox/{task-id}-{agent}.md`
- Curator merges into thematic files via `vscode/memory` (str_replace, delete)
- Result: `/memories/repo/*.md` — 11 topic files, ~25KB (the actual working memory)

The MCP memory tools (store_learning, query_memory, etc.) exist in code but have zero production data flowing through them.

### F5: Current tool descriptions are terse but not wrong

Verbatim tool docstrings:
- `store_learning`: "Create a new pending memory entry."
- `query_memory`: "Return memory entries filtered by state and sorted by curation priority."
- `update_entry`: "Update mutable fields on an existing entry (curator-only)."
- `delete_entry`: "Mark an entry as deleted (curator-only)."
- `approve_entry`: "Promote a curated entry to approved (user-only)."

The h-mcp-memory skill adds some context (confidence range, categories), but agents don't automatically load that skill.

### F6: Tool annotation hints are correctly set

Server properly annotates `readOnlyHint` and `idempotentHint` per tool. This part of the implementation is sound.

### F7: Pipeline protocol's confidence recommendation (0.8) differs from model minimum (0.7)

Protocol recommends 0.8 as default. Model allows 0.7–1.0. 1.0 is marked "reserved — do not use" in the memory structure handbook. This is fine design but not exposed in schema.

### F8: Two pipeline agents DO have ob-memory/* already

test-writer and test-curator have `ob-memory/*` in their tools: array. These are likely the first agents that were wired up but rollout never completed to the rest of the pipeline.

---

## Candidate Implications

### I1: The brief is effectively a "first real deployment" of the MCP memory system

Despite the code existing and being tested, the MCP memory path has zero production traffic. The file-based system is the only working path. This brief isn't a refactor of a working system — it's fixing a system that was coded but never operationally deployed.

### I2: The consumer migration (P2) is actually the activation of a dormant system

Adding `ob-memory/*` to all pipeline agents' tools: arrays isn't "migration" — it's rollout. The agents never had these tools; they've been using the file-based fallback or nothing.

### I3: The curator agent needs both file-based AND MCP tools

The curation workflow operates on two sources:
1. File-based inbox entries (`/memories/repo/inbox/`) — from agents using the fallback path
2. MCP pending entries — from agents using `store_learning`

Post-rollout, the curator needs to handle BOTH until the file-based inbox is deprecated. Or the file-based inbox could become the canonical ingest path and the MCP `store_learning` could write to it.

### I4: Tool surface redesign can be bolder because there's no production usage to migrate FROM

Since zero data has flowed through the MCP tools, there's no migration concern. The tool surface can be freely reshaped without worrying about breaking existing workflows — the workflows were never operational.

### I5: The `h-mcp-memory` skill already documents much of what's missing from tool descriptions

The handbook contains confidence ranges, category enum values, default query behavior, and usage examples. The problem isn't that this knowledge doesn't exist — it's that it's in a skill file that agents don't automatically load, rather than in the tool schema itself.

---

## Open Research Questions

### Q1: What tool names pass the agent discoverability test?

Agents find tools via `tool_search` using natural language. Current `store_learning` fails — agents would search "memory", "save", "remember", "record." Phase 2 needs to pick names that match natural search behavior for both the write tool and read tool.

### Q2: What happens to existing `/memories/repo/` data?

Big-bang: `vscode/memory` removed from all agents simultaneously with `ob-memory/*` activation. User handles data migration separately (out of scope). The file-based inbox and thematic files are no longer read by agents post-activation.

### Q3: What curator tool shape serves the lifecycle best?

User's input proposed `curator_update` as a single powerful tool. Alternatives: keep separate tools but just for curator. Phase 2 decides the shape of the curator surface.

### Q4: What frontmatter fields need to be added?

The user mentioned potential frontmatter additions. What fields are missing from the current schema for the MCP-as-single-source design to work?

### Q5: How does scope_agents get populated correctly?

`scope_agents` controls which agents see which entries. During `store_learning`, the storing agent would set its own scope. But who sets the reading scope — should an entry about "pytest pitfalls" be visible to test-writer AND builder? Phase 2 needs a scope assignment model.
