# Architectural Stance — Decision Request Data Model

## Position

The decision request system is a structured intent/resolution pipeline across four layers. The architecture must enforce: (1) a single writer for file mutations, (2) discriminated validation by kind, (3) safe multi-request semantics, and (4) consistent retry behavior across all resolution surfaces.

## Structural Reasoning

### Module Structure

Split into two modules in `serve/kanban/src/owlbear_kanban/`:

- **`decision_models.py`** — Pydantic models (`DecisionRequest`, `Option`, `Resolution`). This is the shared storage contract. Zero dependencies on engine internals.
- **`decisions.py`** — Engine operations (`create_request`, `resolve_request`, `list_requests`, `get_request`). Sole file writer. Imports models.

Presentation schemas (Cockpit response models with `body_preview`, computed display fields) live in `owlbear_cockpit`, NOT in the kanban package. MCP tool input schemas live in `mcp-kanban`. Each layer owns its interface shape; only the storage contract is shared.

### Dependency Flow

```
decision_models.py    ← storage contract (zero upward imports)
       ↑
decisions.py          ← engine operations, sole file writer
       ↑              ↑
mcp-kanban tools      cockpit API routes
(validates input,     (thin HTTP→engine adapters,
 calls engine)         owns presentation models)
                           ↑
                      Frontend (TS types mirror Cockpit API)
```

**Critical rule:** Cockpit stops mutating files directly. All file I/O — create, resolve, move pending→resolved, append to task body, set blocked/unblocked — goes through engine operations. Cockpit routes become thin adapters that call `resolve_request()` and map results to HTTP responses.

### API Contract

```python
create_request(
    task_id: str, kind: Literal["decision", "action"],
    title: str, summary: str, options: list[Option] | None,
    agent: str, body: str = ""
) -> DecisionRequest
    # Side effects: write to pending/, set task.blocked=True
    # Raises: TaskNotFound, ValidationError

resolve_request(
    request_id: str, resolution: Resolution
) -> DecisionRequest
    # Side effects: rewrite frontmatter, move to resolved/,
    #   append ID-tagged summary to task body, conditionally unblock
    # Raises: RequestNotFound, AlreadyResolved, InvalidResolution, TaskMutationFailed
    # Retry: re-submitting identical resolution returns success (idempotent)
    # Conflict: different resolution on already-resolved request → AlreadyResolved error

list_requests(
    status: Literal["pending", "resolved"] | None = None,
    task_id: str | None = None
) -> list[DecisionRequest]
    # Ordered by created_at descending

get_request(request_id: str) -> DecisionRequest | None
```

### Option Shape

```python
class Option(BaseModel):
    option_id: str        # ^[a-z0-9][a-z0-9-]{0,48}[a-z0-9]$
    label: str            # human display, max 120 chars
    confidence: float     # 0.0–1.0
    recommended: bool     # at most one True per request
    rationale: str        # max 500 chars
```

Integrity rules: duplicate `option_id` within a request rejected at creation. Option IDs immutable after creation. Resolution validates `selected_option_id ∈ request.options[].option_id`.

### Discriminated Resolution Validation

| Kind | Valid statuses | `selected_option_id` | `free_text` |
|------|---------------|---------------------|-------------|
| `decision` | `approved`, `rejected`, `needs-info` | Required for `approved`/`rejected`; None for `needs-info` | Optional |
| `action` | `completed`, `failed`, `rejected` | Must be None | Optional (execution notes / failure reason) |

Both kinds: `resolved_by` required, `resolved_at` auto-set.

Illegal state combinations (e.g., `kind=action` with `selected_option_id`, or `kind=decision` with `status=completed`) are rejected by the model validator, not left to callers.

### Filename/ID Strategy

**Filename = `{request_id}.md`** where `request_id` is UUID4.

- Canonical identity = filesystem path (O(1) lookup by ID)
- No collision handling needed
- Task affinity via `list_requests(task_id=...)` or `grep -l "task_id:" pending/`
- Trade-off: worse `ls` ergonomics, but all programmatic access is engine-mediated

### Multi-Request Blocking Semantics

A task may have multiple pending requests (sequential creation is common; parallel is allowed).

**Blocking rule:** `create_request` sets `task.blocked=True`. `resolve_request` unblocks the task ONLY IF no other pending requests exist for that task. Engine checks `list_requests(status="pending", task_id=...)` before unblocking.

This is the simplest invariant that prevents premature dispatch.

### Resolution Non-Atomicity and Idempotency

Resolution is NOT atomic — it spans multiple file writes with crash windows:
1. Rewrite DR frontmatter with resolution data
2. Move file from `pending/` to `resolved/`
3. Append summary to task body
4. Conditionally unblock task

**Idempotency guard:** The summary written to task body includes an HTML comment marker: `<!-- dr:{request_id} -->`. Before appending, the engine checks if this marker exists. This is a stable identity check (request-ID-based, not content-based) that survives human edits to the task body.

**Crash recovery:** The batch sweep detects partially-resolved files (in pending/ but with resolution data in frontmatter) and completes the remaining steps idempotently.

### Resolution Paths

1. **Inline (primary):** Cockpit API or MCP tool calls `resolve_request()`. All side effects happen in one engine call.
2. **Sweep (fallback):** `resolve_pending_drs()` detects manually-edited files with resolution data in frontmatter. Processes them through the same idempotent engine codepath. Exists for "edit in vim" power users and crash recovery.

Both paths produce identical outcomes because both funnel through the same engine logic.

### Who Can Resolve

Both humans (via Cockpit) and agents (via MCP `resolve_request` tool). `resolved_by` records identity as a plain string (agent name or `"user"`). Trust boundary: an agent SHOULD NOT resolve its own request — enforced by agent instructions, not engine code. Over-engineering identity verification for a single-user system violates YAGNI.

### Size Limits

| Field | Max |
|-------|-----|
| `title` | 120 chars |
| `summary` | 500 chars |
| `rationale` (per option) | 500 chars |
| `free_text` (resolution) | 2000 chars |
| `body` (markdown) | 10000 chars |

These prevent resolution summaries from pushing task bodies past the existing 500 KB ceiling.

### First Useful Step Phasing

Aligned with the brief's expectation signal:

```
Phase 1 (First Useful Step):
  decision_models.py + decisions.py + MCP tools + Cockpit API routes
  = full programmatic contract, testable end-to-end

Phase 2 (Remaining):
  Cockpit frontend (option cards, adapted controls)
  + agent instruction updates
  = presentation layer
```

Phase 1 is independently deliverable and validates the entire data flow without UI changes.

## Key Trade-offs

| Decision | Gains | Costs |
|----------|-------|-------|
| UUID filenames | O(1) lookup, no collision logic | Worse `ls` readability |
| Single engine writer | Consistent invariants, testable | Cockpit loses direct file control |
| Discriminated validation | Impossible illegal states | More complex model code |
| Conditional unblock | Safe multi-request | Extra query per resolution |
| ID-marker idempotency | Crash-safe, content-independent | Marker in task body (invisible to users) |
| Slug-safe option IDs | Human-readable in YAML, stable | Agents must generate valid slugs |

## Warnings

1. **The sweep must not become a primary path.** If agents or humans routinely resolve by editing files directly instead of using the API, the system loses validation guarantees. The sweep is a recovery mechanism, not a workflow.
2. **Presentation models must stay in Cockpit.** If computed display fields creep into `decision_models.py`, the storage contract becomes polluted with API concerns.
3. **Size limits must be enforced at creation, not just resolution.** Otherwise agents create requests that cannot be resolved without truncation.

## Confidence

0.78
