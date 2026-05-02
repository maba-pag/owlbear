# Decisions — Memory Module

## Project Type

- **Chosen:** `existing-feature/refactor` — this is an existing, fully-coded module being evaluated for keep/restructure/cut.
- **Rationale:** The module exists with full implementation, tests, documentation, and pipeline integration. The question is about its ongoing value, not greenfield design.

## Investment Tier

- **Chosen:** Tool — internal utility, single operator, standard M2, selective panel, full Brief.
- **Rationale:** Strategic decision (keep/restructure/cut) but internal infrastructure scope. No external consumers.

## Outcomes (locked M2)

- Best: operational quality-gated memory → fewer repeated mistakes
- Minimum: firm strategic direction with scoped path for Phase 2
- Boundary: direction only, not implementation; storage format and curator redesign are downstream

## Knowledge-MCP Merge Exploration

- **Rejected:** Merge into mcp-knowledge.
- **Rationale:** Research confirmed fundamentally different systems — semantic graph search vs. scope-based agent memory. No functional overlap, different lifecycles and query models.

## Option C (Cut module) — Rejected

- **Rationale:** Can't change VS Code memory file format. Either use VS Code memory unchanged (with instruction optimization) or build something separate. Cutting the module and modifying VS Code's files is not viable.

## Option D (Unify — MCP-backed repo memory) — Rejected

- **Rationale:** Would interfere with VS Code-managed files, potentially breaking VS Code. VS Code uses its own hidden storage — the /memories/repo/ visible to agents is NOT in the git repo, it's in workspace-storage.

## Option E (Wait for GitHub memory) — Rejected

- **Rationale:** GitHub's `copilotMemory.enabled` is cloud-based with 28-day expiry (per own March 2026 research). It does NOT provide in-repo committable storage. Cross-surface but not local-first. Cannot solve the quality-gated, committable memory requirement.

## Strategic Direction — LOCKED

**Option B: Restructure to markdown+frontmatter (kanban pattern)**

- Replace SQLite with per-entry `.md` files (YAML frontmatter + content body)
- Keep MCP tools for queryable/filtered retrieval (confidence, category, agent-scope)
- Storage in-repo (git-native, diffable, mergeable, human-readable)
- Proven pattern from kanban module
- Phase 2 scope: storage layout, tool API, migration plan, data model
