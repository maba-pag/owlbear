# Concrete Schema Definitions for deer-flow Memory Patterns in memory-mcp

> **Owning task:** #499 — Incorporate deer-flow memory patterns into memory-mcp design (#387)
> **Date:** 2026-03-31 **Status:** Complete

## 1. Context and Question

DR `docs/decisions/resolved/428-adopt-deer-flow-memory-patterns.md` approved adoption of deer-flow memory patterns for OwlBear's memory-mcp (#387) with custom decision: adopt patterns 1 (fact schema), 2 (confidence gating), 6 (category taxonomy) unchanged; customize pattern 4 (soft-delete pruning, user-only actual deletion). Patterns 3 (dedup) and 5 (token-budgeted injection) were not mentioned in the DR — see §3E for gap analysis.

This research translates the approved patterns into concrete schema and interface definitions that #387's architect/builder can consume directly.

## 2. Sources Studied

| # | Source | URL / Path | Relevance |
|---|--------|-----------|-----------|
| S1 | deer-flow deep dive | `docs/research/deer-flow-memory-subagent-deep-dive.md` §3A-3C | .95 |
| S2 | DR #428 (approved) | `docs/decisions/resolved/428-adopt-deer-flow-memory-patterns.md` | 1.0 |
| S3 | #387 task body | kanban task — 4D scoping model, MCP tool interface requirements | .95 |
| S4 | Mem0 memory system | `github.com/mem0ai/mem0` — `Memory.add()`, scoping via user_id/agent_id/run_id | .80 |
| S5 | OwlBear mcp-knowledge server | `packages/mcp-knowledge/src/.../server.py` — existing MCP server pattern | .85 |

## 3. Concrete Schema Definitions

### 3A. Pattern 1 — Fact Entry Schema (adopted unchanged + OwlBear extensions)

deer-flow schema: `id / content / category / confidence / createdAt / source` (S1 §3B).

Proposed OwlBear `MemoryEntry` (extends deer-flow with 4D scoping and approval state from #387):

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `id` | `str` (UUID4) | deer-flow | Unique entry identifier |
| `content` | `str` | deer-flow | The learning/fact itself (plain text conclusion) |
| `category` | `CategoryEnum` | deer-flow (Pattern 6) | See §3D |
| `confidence` | `float` (0.0–1.0) | deer-flow | Agent-assigned quality score |
| `created_at` | `datetime` (UTC ISO) | deer-flow | First creation timestamp |
| `updated_at` | `datetime` (UTC ISO) | OwlBear | Last modification timestamp |
| `source` | `str` | deer-flow | Agent name + task ID (e.g., `builder:#480`) |
| `scope_agent` | `str \| None` | OwlBear #387 | Agent name, or None = all agents |
| `scope_project` | `str \| None` | OwlBear #387 | Project identifier, or None = all projects |
| `approval_state` | `ApprovalStateEnum` | OwlBear #387 | `pending \| approved \| deleted` |
| `deleted_at` | `datetime \| None` | DR custom (Pattern 4) | Soft-delete timestamp; see §3C |
| `content_hash` | `str` | OwlBear (dedup) | Whitespace-normalized hash; see §3E |

**4D scope resolution** — the two nullable scope fields create the 4 dimensions orthogonally (S3):

| `scope_agent` | `scope_project` | Effective scope |
|---------------|-----------------|-----------------|
| `None` | `None` | General (all agents, all projects) |
| `None` | `"myproject"` | Project-specific (all agents, this project) |
| `"builder"` | `None` | Agent-specific (one agent, all projects) |
| `"builder"` | `"myproject"` | Agent+project-specific (one agent, this project) |

### 3B. Pattern 2 — Confidence Threshold Gating (adopted unchanged)

deer-flow: facts below `fact_confidence_threshold` (0.7 default) are discarded at write time (S1 §3B).

OwlBear adaptation:

- **Write-time gate:** `record_learning` rejects entries with `confidence < threshold` (returns error, not silent discard)
- **Default threshold:** 0.7 (same as deer-flow)
- **Configurable per scope:** MCP server config allows override per scope dimension (e.g., lower threshold for agent-specific entries where signal is cleaner)
- **Read-time filter:** `get_knowledge` accepts optional `min_confidence` param for additional filtering

Confidence guidelines for agents (from deer-flow S1 §3A, adapted):

| Confidence | When to use |
|------------|-------------|
| 0.9–1.0 | Verified fact — confirmed by test output or documentation |
| 0.7–0.8 | Strong inference — observed pattern across multiple tasks |
| 0.5–0.6 | Weak inference — single occurrence, may not generalize |

### 3C. Pattern 4 — Soft-Delete Pruning (customized per DR)

deer-flow: when `max_facts` exceeded, lowest-confidence facts are permanently dropped (S1 §3B).

**DR customization (S2):** "no actual pruning, mark for deletion and hide from output, but only user may actually delete, so they can review."

OwlBear adaptation:

- When `max_entries_per_scope` exceeded, entries with lowest confidence get `approval_state = "deleted"` and `deleted_at = now()`
- Entries with `approval_state = "deleted"` are **excluded** from `get_knowledge` results
- Entries with `approval_state = "deleted"` are **visible** via `list_entries(include_deleted=True)` for user review
- Only the user (via CLI) or curator agent (with user approval) may permanently remove entries from storage
- Suggested `max_entries_per_scope`: 100 per scope combination (same as deer-flow's `max_facts`)

### 3D. Pattern 6 — Category Taxonomy (adopted unchanged)

deer-flow categories (S1 §3A): `preference / knowledge / context / behavior / goal`.

| Category | deer-flow meaning | OwlBear agent examples |
|----------|-------------------|------------------------|
| `preference` | User/agent style choices | "builder: always verify tests FAIL before implementing" |
| `knowledge` | Factual knowledge, tool quirks | "uv run python -m pytest is more reliable than uv run pytest" |
| `context` | Project/task conventions | "this project uses Protocol-based DI" |
| `behavior` | Workflow patterns, process habits | "PS 5.1 here-strings split in ArgumentList" |
| `goal` | Objectives, milestones | "target 90% coverage per phase gate" |

**Adaptation note:** Categories are **orthogonal** to the 4D scoping model. A `knowledge` entry can exist in any scope (general, project, agent, agent+project). Categories classify **what** the fact is about; scopes classify **who** it's for and **where** it applies.

### 3E. Gap: Patterns 3 and 5 Not Addressed in DR

The DR (S2) explicitly names patterns 1, 2, 4, 6. Patterns 3 (whitespace-normalized dedup) and 5 (token-budgeted injection) are **not mentioned**.

| Pattern | Recommendation | Confidence | Rationale |
|---------|---------------|------------|-----------|
| 3: Dedup | Adopt (.80) | .80 | Basic quality control — prevents duplicate entries. Zero risk, ~10 LOC. Schema already includes `content_hash` field for this. deer-flow (S1) and Mem0 (S4) both deduplicate. |
| 5: Token-budgeted injection | Adopt (.85) | .85 | Core to MCP tool usability — `get_knowledge` must return within token budget for system prompt injection. Without this, agents receive unbounded response. deer-flow (S1) and #387 AC both require it. |

**These are simple quality controls, not architectural decisions.** The #387 architect can include them without a separate DR. If the user disagrees, they can remove them during #387's design review.

### 3F. Proposed MCP Tool Interface (informed by all patterns)

| Tool | Parameters | Returns | Patterns used |
|------|-----------|---------|---------------|
| `get_knowledge` | `agent_id?`, `project_id?`, `max_tokens?`, `min_confidence?`, `categories?` | Token-budgeted list of entries sorted by confidence desc | 2, 5, 6 |
| `record_learning` | `content`, `category`, `confidence`, `agent_id?`, `project_id?` | Created entry ID or validation error | 1, 2, 3 |
| `list_entries` | `agent_id?`, `project_id?`, `status?`, `category?`, `include_deleted?` | Full entry list with metadata (for curation) | 1, 6 |
| `mark_for_deletion` | `entry_id` | Success/error | 4 (customized) |

**Deviations from deer-flow:**

| Aspect | deer-flow | OwlBear | Rationale |
|--------|-----------|---------|-----------|
| Write mechanism | LLM auto-extracts from conversation | Agent explicitly calls `record_learning` | OwlBear is on-demand, no continuous conversation (S1 §3C) |
| Approval workflow | None (auto-accept all) | pending/approved/deleted lifecycle | User oversight per #387 AC |
| Pruning | Permanent deletion | Soft-delete with user review | DR customization (S2) |
| Scope model | Global or per-agent (2D) | 4D: agent × project nullable matrix | OwlBear cross-project requirement (S3) |
| Fact removal | LLM returns `factsToRemove` | Manual via `mark_for_deletion` | No LLM-driven memory management in OwlBear |

## 4. Recommendation (.85 confidence)

Adopt these schema definitions as the concrete design input for #387. The fact schema (§3A), confidence gating (§3B), soft-delete pruning (§3C), and category taxonomy (§3D) are directly derived from the approved DR and ready for implementation. Patterns 3 and 5 (§3E) should be included as basic quality controls — they are non-controversial and required for production quality.

The MCP tool interface (§3F) synthesizes all patterns into a minimal, agent-transparent API aligned with #387's acceptance criteria.

## 5. Follow-up Tasks

No new tasks needed. #387 is the design task that consumes these definitions. The task body should be updated with a reference to this document so the architect/builder has concrete schema inputs.
