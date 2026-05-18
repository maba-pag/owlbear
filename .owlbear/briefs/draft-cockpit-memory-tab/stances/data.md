# Data Quality Stance — Cockpit Memory Tab

## Core Position

The cockpit memory backend must enforce data integrity through **shared schema shape, explicit cross-field invariants, OCC via expected_updated_at, and duplicate-ID detection**. Engine extraction into `serve/memory/` is the recommended path but not a hard prerequisite if contract tests enforce schema parity.

## Schema and Validation Reasoning

### 1. Schema Sharing Strategy

**Recommended:** Extract memory engine into `serve/memory/` (kanban pattern). Both cockpit and mcp-memory depend on it. Eliminates schema drift at the source.

**Acceptable fallback:** Cockpit defines its own Pydantic read/write models matching the same field shapes. Contract tests in `tests/` import from `owlbear_mcp_memory.models` and assert structural equivalence (field names, types, constraints). This catches drift at CI time, not at write time.

**Rationale:** The duplicated state machine logic is ~100 lines. The real risk is not the volume of code but the invariants that code enforces. With extraction, invariants live in one place. Without it, they must be tested against a canonical source.

### 2. Cross-Field Invariants (Model-Level)

The Pydantic model must enforce these on both read (catching corruption) and write (preventing new corruption):

| Invariant | Rule |
|-----------|------|
| `approved_at` coupling | Non-null if and only if `state == "approved"` |
| `scope_agents` state coupling | Non-empty list if `state` in {curated, approved} |
| `scope_agents` values | Each entry must be non-empty string, no blanks |
| Temporal ordering | `updated_at >= created_at` |
| Temporal ordering | `approved_at >= created_at` (when non-null) |
| Category minimum | `len(categories) >= 1` |
| Confidence range | `0.7 <= confidence <= 1.0` |
| Content length | `0 < len(content.strip()) <= 1024` |

### 3. ID Uniqueness

The engine must detect duplicate UUIDs on load. When two files share an ID, the engine keeps the file with the later `updated_at` and logs a warning for the duplicate. The cockpit response metadata should surface duplicate count alongside parse_errors.

### 4. Malformed File Handling

**Rule:** Skip malformed files on load (matching MCP behavior for read consistency). Never surface fabricated entries for files missing id or state.

**Differentiation:** The backend distinguishes parse-error files from not-found IDs. The GET response includes `metadata.parse_errors: int` so the frontend can display "N files could not be parsed." Mutation attempts against a corrupted file's ID return 404 (same as deleted/never-existed) — the cockpit cannot repair what it cannot parse.

## State Machine Integrity

### Transition Guards

| From | To | Trigger |
|------|----|---------|
| pending | curated | Explicit curate with scope_agents |
| pending | (removed) | Hard-delete: file removed from disk |
| curated | approved | Explicit approve action |
| approved | curated | Any field mutation (downgrade) |
| curated/approved | deleted | Soft-delete: state set to deleted |
| deleted | (none) | Terminal state, no transitions out |

### Edit Downgrade Rule

**Any mutation submitted to an approved entry triggers state→curated and clears approved_at.** This matches current MCP behavior where `curate_memory()` on approved always downgrades. The cockpit does not diff fields to determine whether a "real" change occurred — the act of submitting an edit is the trust signal that re-approval is needed.

**Rationale:** Diff-based downgrade (only downgrade on actual value change) is cleaner but introduces ambiguity about whitespace-only changes, list reordering, and floating-point confidence comparisons. Match existing behavior now; optimize later.

### Auto-Promotion Semantics

Promotion from pending→curated happens **only during explicit curate action** (when scope_agents is provided as part of that action). It does NOT happen automatically on save — the save path defaults `scope_agents` to `[source_agent]` without promoting. The cockpit's edit mutation on a pending entry should not auto-promote unless the user explicitly triggers a "curate" action.

### Approval as Route Policy

"Approve is human-only" is enforced by **not exposing an approve endpoint in MCP tools**, not by a data-level invariant. The stored record has no `approved_by` field and cannot prove provenance. This is acceptable for V1 — approval provenance is a future enhancement, not a current integrity gap.

## Race Condition Handling

### OCC Pattern: `expected_updated_at`

Match the cockpit's existing kanban mutation pattern:

1. Client reads entry, receives `updated_at` value
2. Client submits mutation with `expected_updated_at` field
3. Backend reads file, compares current `updated_at` to expected value
4. If mismatch → HTTP 409 Conflict (another writer modified the entry)
5. If match → execute mutation, set new `updated_at`, atomic write (tmpfile + rename)

**Residual TOCTOU window:** Between step 3 (read) and step 5 (rename), another writer could modify the file. On a single machine with a single user, this window is sub-millisecond. Acceptable risk — not worth file-level locking for a <500 entry system.

### Hard-Delete Conflict

After pending hard-delete (file removed), subsequent mutations return 404. The frontend handles 404 on mutation as "entry was removed by another writer" and triggers a list refresh.

## Key Trade-offs

| Trade-off | Chosen | Cost |
|-----------|--------|------|
| Engine extraction vs duplication | Recommend extraction, accept tested duplication | Extraction adds a package-creation task |
| All-edits-downgrade vs diff-based | All-edits-downgrade | No-op submits strip approval unnecessarily |
| Skip malformed vs surface degraded | Skip + warn count | Corrupted entries invisible as entries |
| OCC vs file locking | OCC (expected_updated_at) | Sub-ms race window remains |
| Approval provenance | Not stored | Cannot audit who approved |

## Warnings

1. **Duplicate IDs are a silent data corruption path today.** The current engine overwrites its ID→path map on duplicates, making behavior non-deterministic on load order. Both cockpit and engine must detect and handle this.
2. **Cross-field invariants are not enforced in the current model.** Adding them will surface existing entries that violate them (e.g., deleted entries with stale `approved_at`). A migration sweep is needed before enabling strict validation on read.
3. **The cockpit's 409 semantics must match exactly.** The frontend already handles 409 for kanban mutations. Memory mutations must use the same response shape and frontend handler.
4. **Auto-promotion is subtle.** The cockpit edit form must distinguish "save edits to a pending entry" (no promotion) from "curate this entry" (adds scope, promotes). These are different API actions, not the same endpoint with different payloads.

## Confidence

**0.78** — High confidence on validation strategy, OCC pattern, and invariants. Moderate uncertainty on engine extraction vs duplication trade-off (depends on architecture ruling that is out of scope for this stance).
