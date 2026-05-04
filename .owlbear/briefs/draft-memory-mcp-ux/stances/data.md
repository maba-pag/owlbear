# Data Quality Stance — Full Design Evaluation

## Position

The design is **data-sound with two critical under-specifications** that must be resolved before implementation. The state machine, schema, deletion model, and scope semantics are well-formed. The two gaps — auto-downgrade trigger definition and the D18/D29/D30 contract collision on pending curation — will produce implementation ambiguity or silent corruption if left unresolved.

## State Machine Completeness

### Transitions (well-formed)

| From | To | Trigger | Gate |
|------|----|---------|------|
| pending | curated | curate_memory | scope_agents ≠ [] |
| curated | approved | approve_memory | — |
| approved | curated | curate_memory (auto-downgrade) | actual value change in mutable field set |
| pending | ∅ (hard-delete) | delete_memory | — |
| curated | deleted | delete_memory | — |
| approved | deleted | delete_memory | — |

No curated→pending path (C10). Deleted is terminal. These are correct — "reject" semantics are handled by delete + re-store, which leaves a cleaner audit trail than sub-state cycling.

### Critical Gap: D18/D29/D30 Contract Collision

D29 states curate_memory **always** results in state=curated. D18 requires scope_agents ≠ [] for pending→curated. D30 allows partial-update (None = no change). These three cannot simultaneously hold for a pending entry when scope_agents is not provided.

**Resolution required:** curate_memory on pending entries MUST require `scope_agents` as a mandatory parameter for that specific transition. This reconciles all three:
- D29 satisfied: operation always results in curated
- D18 satisfied: scope gate passes
- D30 still applies: content, title, categories, confidence remain partial-update

For curated→curated and approved→curated transitions, scope_agents follows D30's partial-update semantics (optional, None = no change).

This means pending entries cannot be incrementally improved without also providing scope. The curator's workflow becomes: read_memory → construct full curation (content + scope) → single curate_memory call. This is acceptable — it matches the intended workflow where curation is a deliberate, complete act.

## Schema and Validation Reasoning

### Field Set (correct and minimal)

| Field | Type | Constraint | Mutability |
|-------|------|-----------|------------|
| id | UUIDv4 | unique | immutable |
| title | string | required | mutable |
| categories | list[enum] | ≥1 from 9 values | mutable |
| confidence | float | 0.7–1.0, required, no default | mutable |
| state | enum | {pending, curated, approved, deleted} | system-managed |
| scope_agents | list[string] | [] / ["*"] / [names] | mutable (curator-only) |
| source_agent | string | required | immutable |
| content | string (body) | ≤1KB | mutable |
| created_at | timestamp | set once | immutable |
| updated_at | timestamp | set on every mutation | system-managed |
| approved_at | timestamp | set on approve, cleared on downgrade | system-managed |

No redundant fields. `modified_by` correctly dropped (D21) — no identity mechanism exists post-D10. `updated_at` serves as implicit `deleted_at` for soft-deleted entries.

### Critical Gap: Auto-Downgrade Comparison Domain

D20 says "any field change on approved entry" triggers downgrade. The design never defines what constitutes a "field change." Without an explicit boundary:

**Required definition — USER-MUTABLE field set:** {title, content, categories, confidence, scope_agents}. Only changes to these trigger downgrade.

**Excluded from comparison:** {state, created_at, updated_at, approved_at, id, source_agent} — these are system-managed and cannot be submitted by the curator.

**Normalization rules required:**
- scope_agents: compared as sorted sets (["a","b"] == ["b","a"])
- categories: compared as sorted sets
- content: compared after trailing-whitespace trim (not full normalization — formatting is meaningful)
- confidence: exact float equality (no epsilon)
- title: exact string equality

**Identical resubmission:** If curator calls curate_memory on an approved entry and all mutable fields match stored values after normalization, the operation succeeds with NO state change. This is idempotent-safe and prevents accidental downgrade from a no-op edit.

### Content Limit (1KB — correct per D8 philosophy)

D22 locks 1KB. D8 establishes that mixing categories in one entry is a quality smell — entries should be atomic knowledge units. Under this philosophy, 1KB is correct: if you need more, you're cramming multiple learnings into one entry.

The validation error message must be actionable: guide the agent to split the entry by category, not just reject with a size error.

### Confidence Range (0.7–1.0 — correct)

No default prevents quality inflation. 1.0 is valid for heavily-confirmed learnings. The minimum 0.7 prevents agents from hedging with low-confidence "maybe" entries that waste curator bandwidth.

### Category Enum (9 values — sound)

domain-knowledge, behaviour, pitfall, process, tool-usage, goal, personality, preference, env-context. The three renames (D24) eliminate genuine ambiguity. ≥1 required forces categorization discipline. Multi-category allowed for entries that span domains (though D8 encourages splitting).

## Scope Data Model

### Three-State Semantics (sound)

- `[]` = unscoped, awaiting curator assignment. Cannot leave pending state.
- `["*"]` = universal, visible to all agents on recall.
- `[names]` = targeted, visible only to named agents.

The validation gate (D18: reject pending→curated if scope=[]) prevents silent leakage of unscoped entries into production reads. This is the single most important data integrity gate in the system.

### Scope Observability

recall_memory returns body-only (D27). Consuming agents cannot observe their own scope membership. This is intentional — agents receive knowledge, not memory-management metadata. The scope model serves the CURATOR's routing function, not the consumer's self-awareness.

The curator's read_memory tool returns full metadata including scope. This asymmetry is correct: different actors need different views of the same data.

### Binary Scope (D28 — correct)

Per-agent confidence was correctly rejected. It mixes entry quality (confidence field) with routing relevance (scope), creates O(agents × entries) complexity, and has no proven need in a system with zero production data.

## Timestamp Semantics

- **created_at**: Write-once at store time. Never changes. Provenance anchor.
- **updated_at**: Set on every mutation including state transitions. Serves as "last touched" signal and implicit deleted_at for soft-deleted entries.
- **approved_at**: Set when state transitions to approved. Cleared on downgrade to curated.

### approved_at Clearing: Intentional, Not Data Loss

When content changes post-approval, the prior approval no longer applies to the current content. Clearing approved_at is the honest current-state representation. The previous timestamp is recoverable via git history (D25: batch commits preserve frontmatter evolution). This is adequate for the expected audit depth of a single-user system.

If mutation debugging proves painful post-launch, `previous_approved_at` is a cheap additive field. Do not pre-add it — YAGNI.

## Deletion Model

### State-Dependent (D19 — correct)

- **Pending → hard-delete:** File removed from disk. Never committed to git (D25). No trace. Correct — these are ephemeral, never-reviewed entries. A tombstone would require committing something that was deliberately never committed.
- **Curated/Approved → soft-delete:** State set to `deleted`, file retained. Terminal state. Audit trail preserved in git.

### Stale-ID Observability

After pending hard-delete, a cached entry ID from list_memories returns "not found." This collapses three causes (deleted, wrong ID, never existed) into one observable. This is acceptable because:
1. UUIDs make collision astronomically unlikely
2. Pending entries are short-lived (curator runs every 5th cycle)
3. The curator's next list_memories returns fresh state

The error response SHOULD use a specific message ("entry not found or was deleted") rather than a generic 404, but formal tombstones for pending entries contradict D25's intent.

### Soft-Delete Accumulation

Deleted files accumulate without defined garbage collection. Acceptable for launch (zero data). Backlog item: periodic prune of entries in deleted state older than N days.

## Critic Findings — Data Perspective

| Finding | Assessment | Resolution |
|---------|-----------|------------|
| 1. Scope gate + auto-state atomicity | **Critical gap.** D18/D29/D30 collision. | curate_memory on pending requires scope_agents as mandatory param. Whole-call rejection if missing. |
| 2. Auto-downgrade trigger definition | **Critical gap.** No comparison domain defined. | Explicit mutable-field set + normalization rules + idempotent no-op on identical values. |
| 3. approved_at cleared = data loss? | **Intentional.** Current-state truth. Git is the audit trail. | No change. Document git-recovery path. |
| 4. Stale ID after pending hard-delete | **Acceptable.** UUID + short lifecycle + fresh list = low risk. | Informative error message, no tombstone. |
| 5. Admin vs substantive edit same path | **Correct.** All mutable-field changes trigger downgrade. | Scope change = audience change = needs re-approval. One rule, no exceptions. |

## Warnings

1. **The D18/D29/D30 collision will produce implementation bugs if not resolved in the spec.** Implementer will face an impossible contract and make an ad-hoc choice. Specify: scope_agents mandatory on pending→curated; partial-update on already-curated entries only.

2. **Auto-downgrade without normalization rules will produce false downgrades.** Scope list reordering, trailing whitespace in content, or category list shuffling will trigger spurious re-approval cycles. Normalization must be specified in the implementation contract.

3. **No OCC means list→read→mutate can race.** Accepted system-wide (prior brief). The curator is the only mutator, reducing race probability to near-zero. Not a launch blocker.

4. **1KB content cap will frustrate agents initially.** The validation error must teach splitting (reference D8 philosophy), not just reject. Otherwise agents retry with truncation instead of decomposition.

5. **Soft-deleted entries accumulate.** No garbage collection defined. Low priority — single-user, low volume. Backlog item.

## Confidence

**0.80**

- State machine is complete and correct (0.90)
- Schema fields are minimal and sound (0.88)
- Deletion model is well-reasoned (0.85)
- Scope semantics are clean internally (0.85)
- Two critical under-specifications identified and resolutions proposed (0.75 — depends on whether spec adopts the resolutions)
- Reduced by: no OCC, no GC, approved_at audit trail relies on git discipline
