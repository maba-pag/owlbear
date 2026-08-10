# User Observations on MCP Memory Tools

Date: 2026-05-03  
Source: Direct user feedback after reviewing exposed tool schemas

---

## Per-tool observations

### `store_learning`

- **Naming:** Functional but odd for a "memory" system. Works as a description of what you're doing ("documenting what we learned") but feels detached from the domain.
- **`title` param:** From data POV it's a title, but from user POV there's no guidance on what goes here. Should communicate: "this is used to decide whether to read the entry later — make it a summary or a recognizable identifier." Examples: "python only via uv", "never pip without uv".
- **`content`:** Is markdown okay/encouraged/forbidden? Target or max length?
- **`categories`:** Enum or free text? If enum (preferred): can agents propose new ones? Suggestion: "if existing categories don't fit, propose a new one in memory text — curator will handle it."
- **`confidence`:** Range unclear from schema (0.0–1.0? 0–100?).
- **`scope_agents`:** Enum unknown.

### `query_memory`

- **`states`:** Enum unclear. Default behavior when null is invisible (actually defaults to curated+approved, hiding pending).
- **`min_confidence` / `limit` defaults:** Undocumented.
- **`limit`:** Is this number of entries returned? (Yes, but not stated.)
- **Strategy question:** Always returns full entries including content. Should there be a lightweight "list titles/IDs" mode, then read individual entries? Current approach is fine for small stores but doesn't scale. Worth a design decision.
- **Name mismatch:** "query" implies search/filter, but it's really "get all matching entries with full text." Not wrong, but sets wrong expectations.

### `update_entry`

- **Description:** "Update mutable fields of an entry (curator-only)" — restates the name, adds no value.
- **Curated entries modifiable:** Surprising. Expected approved=immutable, but didn't expect curated to also be editable. Is this intentional?
- **State transition hiding:** The only way to curate an entry is `update_entry(state="curated")`. This makes curation a side-effect of "updating", not a deliberate workflow step.

### `delete_entry`

- **Missing context:** Description should explain this is soft-delete (removes from default query, doesn't erase from disk). Final deletion happens after user review.
- **Missing param:** Should have optional `reason` field. Makes user review much easier ("why was this flagged for deletion?").
- **Can deleted entries be queried?** Yes (via `states=["deleted"]`), but not documented.

### `approve_entry`

- **Should work on pending:** Current requirement for curated state adds a mandatory curator step between agent creation and user approval. If the user wants to approve a pending entry directly, they can't.
- **Is it just a wrapper?** `approve_entry` is essentially a restricted state transition. If `update_entry` can already change state, why does `approve_entry` exist as a separate tool? Answer: to prevent agents from self-approving. But the implementation is clunky.

---

## Architectural concerns

### Access control model is broken

- `OWLBEAR_MEMORY_CALLER` is a per-process env var, not per-request.
- Only ONE server instance runs — so either ALL callers are curator or NONE are.
- The role distinction (curator vs user vs agent) can't work with a single shared server.
- **Must be rethought:** either remove roles entirely, or find a different enforcement mechanism.

### Lifecycle is over-engineered

- Three-step lifecycle (pending → curated → approved) forces every entry through a curator before the user can approve.
- In practice, the human user IS the curator AND the approver in a single-user VS Code setup.
- **Proposal:** Single "promote" tool that moves an entry up one state, restricted to curator role. This replaces both the state field in `update_entry` AND `approve_entry`. Reduces tool count for general agents.
  - Optional `reason` text param on promote (and on delete).
  - General agents only see: `store_learning`, `query_memory`.
  - Curator agents see: `store_learning`, `query_memory`, `update_entry` (no state field), `delete_entry`, `promote_entry`.
  - This separates content editing from state transitions cleanly.

### Pending entries — return or hide?

- Current: hidden from default query.
- User preference: don't return uncurated entries to general agents.
- But agents should be able to check their own submissions exist (via ID returned from `store_learning`).
- **Open question:** Should `query_memory` support querying by ID? Or is filtering by `states=["pending"]` sufficient?

---

### Revised tool split: `update_entry` (agent) vs `curator_update` (curator)

Instead of a dedicated promote/approve tool, the cleaner pattern is:

- **`update_entry`** (general agents): Can only edit `pending` entries. Cannot change state. Used for correcting content before curation.
- **`curator_update`** (curator only): Same fields as `update_entry` but NO state restriction. Can edit any entry in any state, can change `state`, AND can set `deleted: true` to soft-delete. This is how curation, approval, deletion, and re-opening all happen.
- **`delete_entry` removed** — deletion is just `curator_update(entry_id=..., deleted=true)` (or `state="deleted"`).

Benefits:
- No special "promote", "approve", or "delete" tools needed — all state/lifecycle operations are `curator_update`.
- Smallest possible tool surface for general agents: `store_learning`, `query_memory`, `update_entry` only (3 tools).
- Curator gets ONE powerful tool instead of juggling 3+ restricted tools.
- No extra lifecycle logic — the state machine stays the same, just the access surface changes.
- Tool visibility controlled via agent `tools:` list in `.agent.md` files — agents simply don't list `curator_update`.

### `MEMORY_TOOLS_EXCLUDE` is a deletion candidate

- Low value: if a tool shouldn't be exposed to an agent, the agent's `tools:` list in its `.agent.md` controls that, not an env var on the server.
- Adds complexity to server startup (module-level side effect in tools.py).
- Only useful if you want to hide tools from ALL agents globally — but that's better done by not registering them in the first place.
- **Recommendation:** Remove `MEMORY_TOOLS_EXCLUDE` and `OWLBEAR_MEMORY_CALLER`. Use agent-level tool whitelisting instead of server-level tool blacklisting.

Open questions:
- Should `curator_update` have an optional `reason` field for audit trail on state changes?
- Naming: `curator_update` vs `manage_entry` vs `admin_update`?

---

## Summary of proposed directions

1. **Kill `OWLBEAR_MEMORY_CALLER` env var** — no replacement needed; access control via agent tool lists.
2. **Kill `MEMORY_TOOLS_EXCLUDE`** — low value, replaced by agent-level `tools:` whitelisting.
3. **Replace `approve_entry` + `delete_entry` with `curator_update`** — one tool for all lifecycle + edit operations, unrestricted.
4. **Restrict `update_entry` to pending entries only** — agents can correct their own submissions but can't touch curated/approved content.
5. **Enrich descriptions** with valid values, ranges, defaults, lifecycle context.
6. **Expose schema constraints** (enum, min/max) if FastMCP supports it.
7. **Consider adding `fields` param to `query_memory`** for lightweight mode (titles/IDs only) vs current get-all.
