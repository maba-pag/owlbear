# Brief — Memory MCP Tool UX Refactor

**Tier:** Shared (C)
**Type:** existing-package/refactor — MCP server tool surface redesign

---

## Problem

The MCP Memory server (`serve/mcp-memory/`) has 4 compounding issues that block production use:

1. **Structural non-conformity** — no standalone engine package; deferred until a non-MCP consumer exists (D6)
2. **Broken access control** — `OWLBEAR_MEMORY_CALLER` env var defaults to `"unknown"`, blocking all role-gated tools; one MCP instance serves all callers, making per-caller env vars impossible
3. **Agent-hostile tool interface** — mandatory categories, confidence range, and state rules hidden from tool schemas; first-call failures guaranteed
4. **Over-scoped tool surface** — general agents see all 5 tools including curator-only `update_entry`, `delete_entry`, and user-only `approve_entry`

The system is **dormant** — zero production data. The file-based path (`/memories/repo/`) is the only working memory. This gives design freedom: the tool surface can be freely reshaped with no migration burden.

## Scope

Reshape the MCP memory tool surface into 7 audience-separated tools with schema-enforced constraints, code-managed state machine, and self-documenting parameters. Delete broken access control. Establish the MCP path as the single agent read/write interface.

**In scope:**
- 7-tool surface (2 general + 4 curator + 1 user) with full parameter redesign
- State machine with code-enforced transitions (auto-promote, auto-downgrade)
- State-dependent deletion (hard-delete pending, soft-delete curated/approved)
- Scope model (curator-assigned, three-state: unscoped/universal/targeted)
- Access control via per-tool registration in agent `.agent.md` files
- Category enum rename (3 ambiguous names)
- Guided approval prompt (`memory-review.prompt.md`)
- Consumer updates (agent wiring, skills, instructions)
- Big-bang replacement of VS Code `vscode/memory` path

**Out of scope:**
- Standalone `serve/memory/` engine package (D6 — deferred until non-MCP consumer)
- Automated garbage collection of soft-deleted entries (user-directed cleanup only)
- Per-agent confidence scores (binary scope: in/out per agent)
- Seed data migration from `/memories/repo/` (D39 — start fresh)
- Cockpit UI for memory management

---

## Tool Surface — 7 Tools, 3 Audiences

### General Agent Tools (2)

#### `save_memory` — Write a new pending memory entry

| Parameter | Type | Required | Constraints |
|-----------|------|----------|-------------|
| `title` | `string` | Yes | Non-empty |
| `content` | `string` | Yes | ≤1024 characters |
| `categories` | `list[MemoryCategory]` | Yes | ≥1 from enum |
| `confidence` | `float` | Yes | ∈ [0.7, 1.0] |
| `source_agent` | `string` | Yes | Immutable after creation |

**Behavior:** Creates a new entry with `state=pending`. File created on disk but **not committed** to git (D25). No `scope_agents` parameter — scope is curator-assigned (D18).

**Tool description (for MCP schema):** "Save a memory entry for future reference. Provide title, content body (max 1024 chars), one or more categories ({category_list}), confidence (0.7–1.0), and your agent name as source_agent. Entry is created as pending for curator review."

**Validation errors teach:**
- Missing category → "Provide at least one category from: {list}"
- Content too long → "Content exceeds 1024-character limit. Split into focused entries by category."
- Confidence out of range → "Confidence must be between 0.7 and 1.0"

#### `recall_memory` — Retrieve relevant memories

| Parameter | Type | Required | Constraints |
|-----------|------|----------|-------------|
| `agent` | `string` | Yes | Free string. `"*"` code-blocked |
| `categories` | `list[MemoryCategory]` | No | Filter by category |
| `limit` | `int` | No | Default 20 |

**Behavior:** Returns entries where the calling agent is in `scope_agents` (or `scope_agents=["*"]` for universal entries). Priority ordering: **approved entries first**, then curated entries fill remaining slots (D37). Entries with `scope_agents=[]` (unscoped) are excluded. `"*"` as agent value is **code-blocked** (D32).

**Return format:** Body only with title as heading. No metadata (no id, categories, confidence, state, timestamps). Agents get knowledge, not memory management data (D27).

```
## Entry Title 1
Body content of the first entry...

## Entry Title 2
Body content of the second entry...
```

### Curator Tools (4)

#### `list_memories` — Scan entries with metadata

| Parameter | Type | Required | Constraints |
|-----------|------|----------|-------------|
| `state` | `list[MemoryState]` | No | Default excludes `deleted` |
| `categories` | `list[MemoryCategory]` | No | Filter |
| `scope_agents` | `list[string]` | No | Filter |

**Return:** Full metadata per entry (id, title, categories, confidence, state, scope_agents, source_agent, created_at, updated_at, approved_at). **No body.** Results sorted by curation priority (pending first, then by created_at).

#### `read_memory` — Read full entry by ID

| Parameter | Type | Required | Constraints |
|-----------|------|----------|-------------|
| `entry_id` | `string` | Yes | Valid UUIDv4 |

**Return:** Full entry including body, all frontmatter fields.

**Error:** "Entry not found" for invalid IDs, hard-deleted entries, or stale IDs.

#### `curate_memory` — Edit entry fields (auto-state logic)

| Parameter | Type | Required | Constraints |
|-----------|------|----------|-------------|
| `entry_id` | `string` | Yes | Valid UUIDv4 |
| `title` | `string` | No | Non-empty if provided |
| `content` | `string` | No | ≤1024 chars. Full body replacement |
| `categories` | `list[MemoryCategory]` | No | ≥1 if provided |
| `confidence` | `float` | No | ∈ [0.7, 1.0] |
| `scope_agents` | `list[string]` | Conditional | **Required** when entry is `pending`. Optional for `curated`/`approved` |

**Auto-state logic (code-enforced, D29):**
- `pending` + all fields valid + `scope_agents` provided → `curated` (auto-promote)
- `pending` + `scope_agents` missing → **entire call rejected** (atomic, D36). Error: "Provide scope_agents to promote this entry."
- `curated` + any edit → stays `curated`
- `approved` + any edit → `curated` (auto-downgrade, unconditional, D31). `approved_at` cleared

**Auto-downgrade is unconditional (D31).** Any `curate_memory` call on an approved entry triggers downgrade. No equality comparison — even a no-op edit downgrades.

**Partial update:** Only provided fields are modified. `None` = no change. This is full body replacement for `content` — curator reads via `read_memory`, constructs improved body in context, submits complete new content (D30).

**Return:** Updated entry metadata + guidance hint. Examples:
- "Entry promoted to curated. Scope: builder, reviewer."
- "Entry downgraded from approved to curated. Present to user for re-approval."
- "Entry updated. State: curated."

#### `delete_memory` — State-dependent deletion

| Parameter | Type | Required | Constraints |
|-----------|------|----------|-------------|
| `entry_id` | `string` | Yes | Valid UUIDv4 |

**Behavior (D19):**
- `pending` → **hard-delete from disk**. File removed. Never committed, no trace in git history.
- `curated` / `approved` → **soft-delete**. State set to `deleted`, file retained on disk. Terminal — no recovery.

**Return:** Confirmation + guidance hint. "Entry hard-deleted (was pending, never committed)." or "Entry soft-deleted. File retained for audit."

### User Tool (1)

#### `approve_memory` — Promote curated entry to approved

| Parameter | Type | Required | Constraints |
|-----------|------|----------|-------------|
| `entry_id` | `string` | Yes | Entry must be in `curated` state |

**Behavior:** Sets `state=approved`, `approved_at=now`. Only callable during the guided review workflow (D17).

**Error:** "Entry must be in curated state" if pending, approved, or deleted.

---

## State Machine

```
                    curate_memory
            ┌──── (scope provided) ────┐
            │                          ▼
    save_memory ──► PENDING ──────► CURATED ──────► APPROVED
                      │                │  ▲            │
                      │   curate_memory│  │approve     │
                      │   (any edit)   │  │_memory     │ curate_memory
                      │                ▼  │            │ (any edit,
                      │              CURATED ◄─────────┘  unconditional)
                      │
                delete_memory         delete_memory
                (hard-delete)         (soft-delete)
                      │                    │
                      ▼                    ▼
                 [REMOVED]            DELETED (terminal)
```

**States:** pending, curated, approved, deleted
**Transitions:**
- `pending → curated` — via `curate_memory` with `scope_agents` provided
- `curated → approved` — via `approve_memory` (user-only)
- `approved → curated` — auto-downgrade on any `curate_memory` edit (unconditional)
- `pending → [removed]` — hard-delete via `delete_memory` (file deleted from disk)
- `curated/approved → deleted` — soft-delete via `delete_memory` (terminal)
- No `curated → pending` (no reject path; delete + re-store instead)
- `deleted` is terminal (no recovery; user-directed cleanup during review prompt)

---

## Schema

### Frontmatter Fields

| Field | Type | Set by | Mutable | Notes |
|-------|------|--------|---------|-------|
| `id` | UUIDv4 | System | No | Generated on creation |
| `title` | string | Agent (save) / Curator (curate) | Yes | Non-empty |
| `categories` | list[MemoryCategory] | Agent (save) / Curator (curate) | Yes | ≥1 |
| `confidence` | float | Agent (save) / Curator (curate) | Yes | ∈ [0.7, 1.0] |
| `state` | MemoryState | System (auto-state) | No (code-managed) | pending/curated/approved/deleted |
| `scope_agents` | list[string] | Curator (curate) | Yes | []=unscoped, ["*"]=universal, [names]=targeted |
| `source_agent` | string | Agent (save) | No | Immutable. Self-declared (D21) |
| `created_at` | ISO 8601 | System | No | Set on creation |
| `updated_at` | ISO 8601 | System | Auto | Updated on every mutation |
| `approved_at` | ISO 8601 \| null | System | Auto | Set on approve, cleared on downgrade (D21) |

### Body

Markdown content. ≤1024 characters (D22). Limit **not stated in tool description** — only in validation error message.

### Category Enum (9 values, 3 renamed per D24)

`domain-knowledge`, `behaviour`, `pitfall`, `process`, `tool-usage`, `goal`, `personality`, `preference`, `env-context`

---

## Scope Model

Three-state semantics (D18):

| Value | Meaning | Set by |
|-------|---------|--------|
| `[]` | Unscoped — awaiting curator assignment | Default on creation |
| `["*"]` | Universal — visible to all agents | Curator |
| `["builder", "reviewer", ...]` | Targeted — visible to named agents | Curator |

**Scope validation gate (D36):** `pending → curated` transition requires `scope_agents` to be non-empty. Atomic rejection if missing.

**Query behavior:** `recall_memory(agent="builder")` returns entries where `"builder"` is in `scope_agents` OR `scope_agents=["*"]`. Entries with `scope_agents=[]` are excluded from all recall queries.

---

## Access Control

**Server-side identity deleted (D10).** `OWLBEAR_MEMORY_CALLER` and `MEMORY_TOOLS_EXCLUDE` env vars removed.

**Access via per-tool registration (D34).** Each agent's `.agent.md` lists specific tool names — no wildcards.

| Audience | Tools in `tools:` array |
|----------|------------------------|
| General agents | `ob-memory/save_memory`, `ob-memory/recall_memory` |
| Curator | `ob-memory/list_memories`, `ob-memory/read_memory`, `ob-memory/curate_memory`, `ob-memory/delete_memory` |
| Review prompt | `ob-memory/list_memories`, `ob-memory/read_memory`, `ob-memory/approve_memory`, `ob-memory/curate_memory`, `ob-memory/delete_memory` |

**Identity model:** Self-declared (`source_agent` on save, `agent` on recall). Accident prevention, not adversarial security. Single-user laptop deployment (D10 rationale).

---

## Git & Commit Strategy

| Operation | Commit behavior |
|-----------|----------------|
| `save_memory` | File created, **not committed** (D25). Pending entries stay uncommitted until curation |
| `curate_memory` (curation run) | **Batch commit** at end of curator's curation cycle (D25) |
| `delete_memory` on pending | File removed from disk, nothing to commit (never was committed) |
| `delete_memory` on curated/approved | Soft-delete committed in curation batch |
| `approve_memory` / `delete_memory` (review workflow) | **Batch commit** at end of review prompt session (D38) |

Hard-deleted nonsense never enters git history. Two batch-commit points: curation runs and review prompt sessions.

---

## Activation & Rollout (D35)

Staged, curator-first:

1. **Phase 1 — Curator activation:** Wire curator agent with 4 MCP memory tools. Verify full lifecycle: list → read → curate → delete. Remove `vscode/memory` from curator.
2. **Phase 2 — Pilot agents:** Wire 2–3 pilot agents (e.g., builder, reviewer) with `save_memory` + `recall_memory`. Verify save → curator processes → recall flow.
3. **Phase 3 — Full rollout:** Wire all pipeline agents. Remove `vscode/memory` from all agents. Big-bang replacement complete (D12).
4. **Phase 4 — Review prompt:** Create `memory-review.prompt.md`. User can now approve curated entries.

Each phase: affected agents switch completely (no coexistence of old and new paths for any single agent).

---

## Consumer Updates Required

### Agent files (`.agent.md`)

| Agent | Change |
|-------|--------|
| All ~12 pipeline agents | Add `ob-memory/save_memory`, `ob-memory/recall_memory` to `tools:`. Remove `vscode/memory` |
| `memory-curator` | Add `ob-memory/list_memories`, `ob-memory/read_memory`, `ob-memory/curate_memory`, `ob-memory/delete_memory`. Remove `vscode/memory` |

### Skills

| Skill | Change |
|-------|--------|
| `h-mcp-memory` | Full rewrite — new tool names, parameters, descriptions, usage patterns |
| `h-memory-structure` | Update entry format, new fields (source_agent, approved_at), renamed categories |
| `w-mem-curation` | Update curator workflow for new MCP tools, auto-state logic, guidance hints |
| `r-pipeline-protocol` | Update pre-flight/post-task instructions for `save_memory`/`recall_memory` |

### Prompts

| Prompt | Change |
|--------|--------|
| `memory-review.prompt.md` | **Create new.** Guided approval workflow. Presents curated entries, user approves/rejects/requests changes. Agent calls `approve_memory`, `curate_memory`, `delete_memory` as directed. Batch commit at session end (D38) |

### Instructions

| Instruction | Change |
|-------------|--------|
| `agent-common.instructions.md` | Update memory pre-flight pattern for `recall_memory` |

### Tests

| Test file | Change |
|-----------|--------|
| Existing MCP memory tests | Update for renamed tools, new parameters, new state machine |
| New tests | Auto-state logic, scope gate, deletion model, recall ordering, guidance hints |

---

## Guidance Hints (Return Messages)

All mutation tools return structured guidance hints (kanban MCP pattern):

| Tool | State transition | Hint |
|------|-----------------|------|
| `curate_memory` | pending → curated | "Entry promoted to curated. Scope: {agents}." |
| `curate_memory` | curated → curated | "Entry updated. State: curated." |
| `curate_memory` | approved → curated | "Entry downgraded from approved to curated. Present to user for re-approval." |
| `curate_memory` | pending + no scope | "Provide scope_agents to promote this entry." (rejection) |
| `delete_memory` | pending → removed | "Entry hard-deleted (was pending, never committed)." |
| `delete_memory` | curated/approved → deleted | "Entry soft-deleted. File retained for audit." |
| `approve_memory` | curated → approved | "Entry approved. Now visible to scoped agents." |
| `save_memory` | → pending | "Memory saved as pending. Curator will review." |

---

## Known Tradeoffs

| Tradeoff | Decision | Rationale |
|----------|----------|-----------|
| 1KB limit hidden from tool description (D22) | User choice | Prevents "fill the budget" agent behavior. 3/4 panelists opposed. Error message teaches splitting |
| Recall strips trust signals (D27) | User choice | Agents get knowledge, not metadata. Confidence/state discarded in recall. Enduser panelist opposed (wants confidence). Additive later if needed |
| Admin = substantive edit for downgrade (D31) | Simplification | Both trigger unconditional downgrade. Low volume makes spurious re-approval cheap. Separation adds complexity for marginal benefit |
| Architecture split deferred (D6) | Intentional | No non-MCP consumer exists. Standalone engine package is YAGNI until then |
| Self-declared identity (D10/D21) | Design ceiling | `source_agent` and `agent` are self-reported. Accident prevention, not security. Server-side identity impossible in shared MCP instance |

---

## Testing Strategy

### Unit — State Machine

- All valid transitions produce correct state
- Invalid transitions rejected (e.g., pending→approved, deleted→any)
- Auto-promote: curate pending with scope → curated
- Auto-downgrade: curate approved → curated (unconditional)
- Scope gate: curate pending without scope → atomic rejection
- approved_at set on approve, cleared on downgrade

### Unit — Scope Filtering

- recall with agent name → entries where agent in scope_agents
- recall with agent name → entries where scope_agents=["*"] included
- recall → entries with scope_agents=[] excluded
- recall with "*" → rejected (code-block)

### Unit — Deletion

- delete pending → file removed from disk
- delete curated → state=deleted, file retained
- delete approved → state=deleted, file retained
- delete deleted → idempotent or error

### Unit — Recall Ordering

- approved entries returned before curated entries
- within same state, ordered by relevance/recency

### Unit — Validation

- Categories: at least 1, from enum
- Confidence: 0.7–1.0
- Content: ≤1024 chars
- source_agent: required, immutable

### Component — Guidance Hints

- Each state transition returns correct hint text
- Rejection hints teach corrective action

### Integration — Full Lifecycle

- Agent saves → curator lists → curator reads → curator curates (with scope) → user approves → agent recalls
- Full cycle produces correct state transitions and git commits

---

## Implementation Sequence

1. **Schema changes** — Update models (rename categories, add source_agent, approved_at). Update frontmatter serialization.
2. **State machine** — Implement auto-state logic in engine. Auto-promote, auto-downgrade, scope gate, state-dependent deletion.
3. **Tool surface** — Replace 5 tools with 7. New parameter schemas, descriptions, validation, guidance hints.
4. **Access control removal** — Delete OWLBEAR_MEMORY_CALLER, MEMORY_TOOLS_EXCLUDE env vars and all role-check code.
5. **Recall redesign** — Priority-ordered response (approved first, then curated). Body-only return format. Agent filter. Wildcard block.
6. **Git integration** — Batch commit hooks for curation runs and review sessions.
7. **Consumer updates (Phase 1)** — Curator agent wiring + skill updates.
8. **Consumer updates (Phase 2–3)** — Pilot agents, then full rollout. Agent files + instruction updates.
9. **Review prompt** — Create `memory-review.prompt.md` for guided user approval.
10. **Test suite** — Unit tests for state machine, scope, deletion, recall ordering, validation. Integration test for full lifecycle.

---

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Agents search "remember"/"learn" but tool is "save_memory" | Medium | Tool description includes "Save a memory" — matches "memory" and "save" search terms. Test with `tool_search` |
| Curator batch commit fails mid-run | Low | Atomic git operations. Partial batch = partial commit (recoverable) |
| 1KB limit causes first-call failures for verbose agents | Medium | Error message teaches splitting. Curator can consolidate entries |
| Unconditional downgrade causes approval fatigue | Low | Low entry volume. Curator shouldn't call curate_memory on approved without intent |
| Big-bang cutover breaks agent workflows | Medium | Staged rollout (D35). Curator first, then pilot, then full. Each phase verified before next |
