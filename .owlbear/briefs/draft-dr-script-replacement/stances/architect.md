# Architectural Stance — DR/AR Script Replacement

## Architectural Stance

Replace the scribe agent with a deterministic `decisions.py` module in the kanban engine, a thin `create_dr` MCP tool, and a Cockpit resolve UI. The engine owns file I/O and the resolve state machine. pick_tasks sweeps for file-edit stragglers behind a fail-safe guard. Cockpit is the primary user resolution path.

## Structural Reasoning

### 1. Module Boundary: `decisions.py` in `serve/kanban/`

DR logic gets a dedicated module — not grafted onto the 2300-line engine.py. The module exports:

- `create_decision_request(decisions_dir, task_id, agent, request_type, body, *, engine_ops)` → writes file, blocks task
- `resolve_decision(decisions_dir, file_path, response, *, engine_ops)` → state machine, unblock/move
- `scan_pending_responses(decisions_dir)` → returns list of files with non-empty `response:` field

The `engine_ops` parameter is a protocol/interface (3 methods: `block_task`, `unblock_task`, `append_to_body`). The engine satisfies this protocol. Tests mock it.

### 2. pick_tasks Integration: Fail-Safe Guard, Not Inline Logic

Locked outcome #3 requires pick_tasks to auto-resolve. Implementation:

```python
def pick_tasks(self, ...):
    self._try_resolve_pending_drs()  # fail-safe: catches all exceptions, logs, continues
    # ... existing four-step pipeline unchanged ...
```

The guard function calls `decisions.scan_pending_responses()` then `decisions.resolve_decision()` for each. Any exception is caught and logged — never propagates to dispatch. Partial resolution is fine; retries next cycle.

### 3. Resolve State Machine

The resolver is deterministic with four branches:

| `response:` value | Action |
|---|---|
| `approved` / `completed` | unblock task, append "✓ Decision resolved: {response}" to body, move file to resolved/ |
| `needs-info` | keep blocked, keep in pending/, append "⚠ Needs info: {detail}" to body |
| `rejected` | unblock task, append "✗ Decision rejected: {response}" to body, move file to resolved/ |
| empty/missing | skip — not yet responded |

This replaces the scribe's LLM-based classification with explicit string matching on a controlled vocabulary.

### 4. MCP Tool: Validation-Thin, Always-Block

`create_dr` parameters: `task_id` (str, required), `agent` (str, required), `request_type` (literal "DR" | "AR"), `body` (str, markdown).

The MCP layer validates presence and types. The engine function handles everything else. **Always blocks the task on creation.** No advisory/non-blocking path. Rationale: if the agent doesn't need an answer to proceed, it shouldn't create a DR.

### 5. Cockpit API Surface

| Endpoint | Purpose |
|---|---|
| `GET /api/decisions/pending` | Returns pending DR list with count (polled by frontend for status badge) |
| `POST /api/decisions/{id}/resolve` | Primary user resolution — does full state machine immediately |

Separate from task endpoints. No board endpoint pollution. Frontend polls `/api/decisions/pending` on interval for the status indicator. Resolve is immediate (not deferred to pick_tasks).

### 6. Resolution Authority Model

- **Cockpit resolve endpoint** = primary path. User clicks resolve, backend executes full state machine immediately.
- **pick_tasks sweep** = fallback for file-edit scenario. Detects files with `response:` filled via direct edit, runs same state machine. Idempotent — already-resolved files are in resolved/ and not found by scan.
- No conflict: one is immediate-UI, the other is eventual-consistency for the file-edit fallback.

### 7. Hot-Path: Acceptable Cost

`os.listdir('.owlbear/decisions/pending/')` is O(1) for empty dirs (common case). For 1-3 pending DRs, reading YAML frontmatter of small files is sub-millisecond. No caching needed. The guard's exception handling adds negligible overhead.

## Key Trade-offs

| Choice | Gains | Costs |
|---|---|---|
| Always-block | Eliminates advisory complexity, clear semantics | Loses "informational DR" capability (deemed unused) |
| Side-effect in pick_tasks | No extra MCP tool for orchestrator | Planner does mutations (mitigated by guard) |
| Separate /api/decisions endpoints | Clean API surface, independent polling | Two more endpoints to maintain |
| No OCC on decision files | Simpler implementation | Theoretical last-write-wins race (single-user system) |
| Free-text response field | No template validation complexity | User could write nonsensical response (their problem) |

## Warnings

1. **pick_tasks purity violation is real but contained.** The guard pattern works if and only if the implementation truly swallows all exceptions. A future refactor that removes the try/except breaks dispatch. Add a test that verifies pick_tasks succeeds even when decisions_dir is corrupted.

2. **needs-info loop has no timeout.** A DR in needs-info state stays blocked indefinitely. This is acceptable for a single-user system but worth noting — the user must actively respond.

3. **No query MCP tool means agents can't check DR status programmatically.** They must read files directly or rely on guidance messages. This is acceptable given agents rarely need to check (they fire-and-forget the DR).

4. **Migration is passive.** Old-format files in resolved/ will have extra fields (urgency, impact_tier). Reader code must tolerate these gracefully (read only the fields it needs, ignore extras).

## Confidence

0.78

Position is solid on module boundaries, resolution authority, and API surface. The pick_tasks coupling is the weakest point — architecturally impure but locked and mitigated. The always-block simplification is a judgment call that eliminates real complexity at the cost of a capability nobody used.
