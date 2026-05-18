# Data Stance — Critic Debate Log

## Cycle 1

### Draft Position

1. Engine extraction is mandatory for data integrity — shared Pydantic model eliminates schema drift
2. State machine belongs in the engine, not tool layer — single enforcement point
3. Optimistic concurrency via mtime — read mtime → mutate → verify mtime unchanged → 409 on conflict
4. Never silently drop malformed files — surface as degraded entries with error metadata
5. Timestamps are server-set — `updated_at` by mutation writer, `approved_at` on approve only
6. Edit downgrade scoped to semantic fields — content/categories/confidence changes downgrade; title/scope_agents don't

### Critic Challenges (Pressure: HIGH, Confidence in position: 0.44)

1. **Engine extraction overstated (moderate):** "Only way" is too strong. MCP package already has separate engine/models/tools modules. ~100 lines of duplication is sized. Contract tests could maintain parity without extraction.

2. **State machine scope under-specified (critical):** Integrity extends beyond transition edges. Read-visibility (exclude deleted), retrieval eligibility (only curated/approved for recall), and actor semantics (approve is human-only) can still drift even with shared transitions.

3. **Mtime OCC has TOCTOU race (critical):** Two writers can observe the same pre-write mtime, both pass the unchanged check, both replace — last-write-wins. The kanban storage shows this repo treats stale-write handling as an explicit OCC contract, not a bare mtime check.

4. **Degraded entries create two truths (critical):** MCP skips malformed files. If cockpit surfaces them as degraded entries, the two systems disagree on what exists. Also, malformed files may lack id — cannot be represented as entries.

5. **Cross-field invariants missing (critical):** `approved_at` not enforced to be non-null only when state==approved. Direct file edits can create logically contradictory states that still validate.

6. **Edit downgrade carve-out unsupported (critical):** Current MCP behavior downgrades on any approved curate. Tests treat title edits as downgrade-worthy. Prior data stance explicitly recorded scope_agents changes as requiring re-approval.

7. **Blind spots:** Single-server clock assumption unstated. Degraded entry identity undefined. Hard-delete conflict semantics collapse corrupted/deleted/never-existed.

### Refinements Made

- Weakened extraction from "mandatory" to "recommended with contract-test fallback"
- Expanded integrity scope to include read-visibility, retrieval eligibility, actor semantics
- Replaced bare mtime check with atomic-write + mtime pre-check, acknowledging residual TOCTOU
- Reversed degraded-entries position: skip + metadata count (matching MCP for consistency)
- Added cross-field invariants (approved_at coupling, temporal ordering, scope validation)
- Dropped semantic-field carve-out: all edits to approved entries trigger downgrade

## Cycle 2

### Refined Position

1. Engine extraction recommended, contract tests as fallback
2. Integrity scope: transitions + read-visibility + actor semantics + auto-promotion
3. OCC: atomic write + mtime pre-check, sub-ms residual TOCTOU acceptable
4. Malformed: skip + parse_errors count in response metadata
5. Cross-field invariants: approved_at coupling, scope coupling, temporal ordering
6. All field edits on approved trigger downgrade
7. Hard-delete → 404 on subsequent mutation
8. Same-machine clock, mtime as concurrency signal

### Critic Challenges (Pressure: HIGH, Confidence in position: 0.43)

1. **Corrupted vs deleted indistinguishable (critical):** Engine drops malformed files and converts ID misses to not-found. A corrupted entry looks identical to a hard-deleted entry after skip. Cockpit mutation returns 404 for both.

2. **Duplicate ID unaddressed (critical):** Engine overwrites path map on duplicate IDs. Two valid files can represent one logical entry with non-deterministic behavior. No uniqueness invariant in the position.

3. **Human-only approval is route policy, not data invariant (moderate):** No `approved_by` field exists. The stored record cannot prove provenance. This is API-layer exposure control, not a data integrity property.

4. **Temporal and scope-token invariants missing (moderate):** `updated_at < created_at` and blank scope entries still validate. Model doesn't catch these.

5. **No-op downgrade edge case (moderate):** Current behavior downgrades approved on any submit, even when no field actually changed. The "all edits downgrade" rule is broader than "meaningful edits."

6. **Auto-promotion ambiguity (moderate):** Save path defaults scope_agents to [source_agent] without promoting. Distinction between save-time presence and curate-time supply unclear.

7. **OCC precedent overclaimed (minor):** Cockpit kanban uses `expected_updated` semantics, not bare mtime. Pattern match weaker than stated.

### Final Refinements

- Added duplicate-ID detection (keep later updated_at, warn)
- Reclassified human-only approval as route policy, not data invariant
- Added temporal invariants (updated_at >= created_at, approved_at >= created_at)
- Added scope-token validation (non-empty strings)
- Acknowledged no-op downgrade as matching current behavior, flagged diff-based as future opt
- Clarified auto-promotion as curate-time only, not save-time
- Switched OCC pattern to `expected_updated_at` (matching cockpit kanban, not bare mtime)

## Exit

Position hardened after 2 cycles. Key integrity gaps (duplicate IDs, cross-field invariants, OCC contract shape) addressed. Remaining uncertainties (engine extraction decision, approval provenance) are explicitly scoped as out-of-band decisions. Confidence: 0.78.
