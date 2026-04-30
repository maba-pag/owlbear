# Data Quality Stance — DR/AR Script Replacement

## Position Summary

The replacement is sound in principle — deterministic engine code is the correct home for file I/O that requires no judgment. However, the proposal has five data integrity gaps that, if unaddressed, will produce silent corruption or data loss under realistic operating conditions.

## Schema and Validation Reasoning

### Structural Validation (fail-fast on read)

Every read from `pending/` must validate:

- YAML parseable
- `task_id` present and non-empty string
- `request_type` present and one of `{decision, action}`
- `agent` present (provenance)

Files failing structural validation: logged error, skipped, never processed. This prevents malformed hand-edits from propagating through the resolve pipeline.

### Semantic Classification (deterministic, closed enum)

The response field drives resolution. The classifier MUST use a closed enum — never an open "anything else resolves as approval" rule:

| `response` value | Action |
|---|---|
| absent / `null` / `""` | Pending — skip |
| `approved` | Resolve: append Decision section, unblock, move to resolved/ |
| `rejected` | Resolve: append Decision Rejected section, unblock, move to resolved/ |
| `needs-info` | Append Clarification Requested section, keep blocked, keep in pending/ |
| `completed` | Resolve (AR path): append Action Completed section, unblock, move to resolved/ |
| Matches an option label from the DR's `options:` list | Resolve with that option as the decision |
| **Anything else** | **Do not resolve. Log warning. Leave in pending/.** |

The "freeform approval" escape hatch is explicitly rejected. Unknown response values are treated as unresolved, not auto-approved. This is the single most important data integrity decision in this design — it prevents the exact misclassification the current scribe contract was designed to catch.

### Dual-Format Read Path

Resolved files from the pre-migration era contain dropped fields (`urgency`, `decision_type`, `impact_tier`, `auto_resolve`). The parser must:

- Accept and ignore unknown frontmatter keys (forward-compatible)
- Not require the dropped fields (backward-compatible)
- This applies to both engine reads and direct agent reads

No file migration is required. The parser handles both formats by design.

## Key Trade-offs

### 1. pick_tasks Gains Mutation Side-Effects (HIGH RISK)

`pick_tasks` is currently published as read-only and idempotent. Adding DR resolution as a side-effect fundamentally changes its contract. Every caller — including future tools, Cockpit polling, or retry logic that assumes harmless repeated calls — becomes a mutation trigger.

**Recommendation:** Either (a) document the contract change explicitly and update the MCP tool description to "read + resolve side-effect," or (b) separate resolution into a distinct internal step triggered by `pick_tasks` but guarded by a file-state lock. Option (b) is preferred.

### 2. Concurrency Guard Must Cover the Full Resolve Sequence (CRITICAL)

The atomic rename only guards the final step (pending→resolved move). The earlier mutations (body append + unblock) are unguarded. Two concurrent callers can both validate, both see "section absent," and both append — producing duplicate write-back content.

**Recommendation:** Use a three-state file rename as the lock:

1. `os.rename(pending/{file}, processing/{file})` — atomic, first-writer-wins
2. Perform body append + unblock
3. `os.rename(processing/{file}, resolved/{file})`

If step 1 fails (FileNotFoundError), another caller already claimed it — skip gracefully. This makes the entire resolve sequence single-writer without requiring file locking primitives.

### 3. Filename Collision — Atomic Create Required (MODERATE)

`{task_id}-{slug}.md` must use `os.open(path, O_CREAT | O_EXCL)` (or Python equivalent: `open(path, 'x')`) rather than glob-then-write. This eliminates the TOCTOU window entirely. On `FileExistsError`, append a sequence suffix and retry.

This applies to BOTH pending/ and resolved/ namespaces. The same task+concern can re-arise after resolution — the resolved/ file from the first resolution must not be overwritten by the second resolution's move.

### 4. Write-Back Idempotency Must Be Content-Aware (MODERATE)

The dedup check for re-resolve recovery must:

- Check for the section heading matching the specific slug: `## Decision: {slug}`, `## Decision Rejected: {slug}`, etc.
- If the heading exists, compare the content payload — do not silently skip if the content differs (this indicates a partial write that needs completion).
- Cover all four terminal section types, not just the happy path.

### 5. Needs-Info Is Ephemeral By Design (ACCEPTABLE)

When response is `needs-info`, the file stays in pending/ and the clarification section is appended to the task body. The user updates the response field when they're ready. This means clarification state lives only in the task body until the user responds. This is acceptable — it matches the interaction model (user reads task body, edits DR file).

## Warnings

1. **Do not ship the freeform escape hatch.** Any design that auto-resolves on unknown response values will reproduce the exact semantic-misclassification risk that the scribe agent was supposed to prevent. The closed enum is non-negotiable.

2. **The `processing/` directory is new infrastructure.** It adds a third state to the file lifecycle (pending → processing → resolved). The Cockpit UI and any file-reading agent must understand this state as "resolution in progress, do not act on this file."

3. **Legacy response values exist.** The current README teaches `response: pending` and `response: completed` (for ARs). The new engine must recognize `pending` as equivalent to null (do not resolve) and `completed` as a valid terminal state. Update the README/skill to document the canonical enum.

4. **Direct-reading agents lack the validation envelope.** Agents that read resolved/ files directly (per Locked Outcome #10) bypass the engine's structural validation. If a resolved file is malformed (e.g., from a partial write during a crash), the reading agent gets garbage. Mitigation: write resolved files atomically (write to temp, rename into resolved/). This ensures files in resolved/ are always complete.

5. **AR path requires parity.** The position and the brief are decision-request-centric but Action Requests follow the same lifecycle. Ensure the engine handles `request_type: action` with the same validation, write-back, and atomicity guarantees. The terminal section is `## Action Completed: {slug}` and the resolution trigger is `response: completed`.

## Confidence

0.78

The position is solid on the critical integrity boundaries (closed enum, three-state resolve, atomic create). Residual uncertainty is around whether the `processing/` directory adds meaningful complexity vs. just documenting the pick_tasks contract change — either approach works but the brief must choose one.
