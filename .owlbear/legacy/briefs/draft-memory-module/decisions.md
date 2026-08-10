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
- Phase 2 scope: storage layout, tool API, data model

## Phase 2 Decisions (M4)

### D1: Directory Structure — Flat

- **Chosen:** Flat `.owlbear/memory/` directory, no subdirectories.
- **Rejected:** Category subdirs (knowledge/, behavior/, etc.)
- **Rationale:** One entry may span multiple categories — subdirs would force single-category assignment. Flat matches kanban pattern exactly.

### D2: Filename Convention — slug-first

- **Chosen:** `{slug}-{id6}.md` — human-readable slug, 6-char unique suffix.
- **Rejected:** `{uuid}.md` (unreadable), `{uuid8}-{slug}.md` (less scannable)
- **Rationale:** Most readable in git log and directory listing. Slug frozen at creation (never renamed on content edit).

### D3: Delete Strategy — Hard delete with grace period

- **Chosen:** Mark `state: deleted` first; purge (rm) after next curation cycle.
- **Rejected:** Pure soft delete (zombie files), immediate hard delete (no undo window)
- **Rationale:** Best of both — recoverable within one curation cycle, clean directory afterward. Git history preserves permanently.

### D4: Migration — None required

- **Scope correction:** The mcp-memory SQLite server was never used in production. No data to migrate.
- **VS Code memory entries** (`/memories/repo/`) exist but will be manually curated/promoted by the user during a curation run — not auto-migrated.
- **Implication:** No migration tooling needed. Module starts fresh.

### D5: Category Field — Multi-value list

- **Chosen:** `categories: [knowledge, behavior]` — list field in frontmatter.
- **Rejected:** Single-value `category:` field.
- **Rationale:** One entry can span multiple categories. Flat directory already chosen because of this.

### D6: Grace Period Trigger — Manual curation

- **Chosen:** Purge happens during manual curation run. Last step of the curator agent asks user if old (state=deleted) entries should be purged.
- **Rejected:** Time-based auto-purge, automatic on curation cycle without user consent.
- **Rationale:** User controls what disappears. Curator surfaces deleted entries for review before removal.

### D7: Slug Generation — From title field

- **Chosen:** Agent provides a `title` field in frontmatter; slug is derived from title (kebab-case, truncated). Title is required.
- **Rejected:** Auto-generating slug from content body.
- **Rationale:** Cleaner filenames, explicit naming by the creating agent. Slug frozen at creation.

### D8: State Machine — Four states with quality ladder

- **Chosen:** `pending` → `curated` → `approved` → `deleted`
  - `pending` — agent-created, unreviewed
  - `curated` — mem-curator approved (possibly slightly aggregated)
  - `approved` — user-approved, may be further aggregated
  - `deleted` — marked for purge (grace period)
- **Rejected:** Simple 3-state (pending/approved/deleted), superseded state.
- **Rationale:** Quality ladder: agent → curator → user. Each promotion level increases trust. Mirrors the existing pipeline's quality gates.

### D9: Dedup Strategy — Curator responsibility

- **Chosen:** No engine-level dedup. Store whatever is given. Curator merges/deletes during curation runs.
- **Rejected:** Engine-level fuzzy-match warnings at write time.
- **Rationale:** Keeps engine simple. Curator already has merge/consolidate as a core capability. False-positive dedup at write time would slow agent workflows.

### D10: Canonical Store — MCP replaces thematic files

- **Chosen:** Atomic MCP entries ARE the memory. Thematic files (`/memories/repo/`) are retired. Agents query MCP tools for retrieval.
- **Rejected:** Feed model (entries promoted into thematic outputs), hybrid view.
- **Rationale:** Single source of truth. Eliminates dual-store drift. Curator still aggregates/merges entries, but output is better atomic entries (not separate thematic files).

### D11: Category Enum — 9 values

- **Chosen:** `knowledge`, `behaviour`, `pitfall`, `process`, `tool`, `goal`, `personality`, `preference`, `context`
- **Multi-value:** Yes, entries can span multiple categories.
- **Rationale:** Superset of old and new proposals. Covers all pipeline reflection buckets plus curator-observed patterns.

### D12: Retrieval Semantics (from Critic triage)

- `curated` + `approved` entries returned by default queries
- `pending` entries excluded from default retrieval (only visible to curator)
- `deleted` entries excluded from all queries
- Rationale: curated = curator-approved, safe for agent consumption. Pending = unreviewed, should not influence agent behavior.

### D13: Reload Strategy (from Critic triage)

- Mtime-based reload using `MtimeScanCache` pattern from kanban
- Skips re-parse when directory mtime unchanged
- Rationale: handles manual file edits between queries without full OCC complexity.

### D14: Mutation Access (from Critic triage)

- `store_learning`: any agent (creates `pending` entries)
- `update_entry`: curator agent only (state promotion, content edits)
- `delete_entry`: curator agent only (marks `state: deleted`)
- State promotion: only curator can promote `pending` → `curated`; only user can promote `curated` → `approved`
- Enforcement: tool-level `allowed_agents` config (same pattern as current h-mcp-memory exclusion)
- Rationale: quality ladder requires restricted mutation. Prevents any agent from rewriting approved knowledge.
