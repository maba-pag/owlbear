# Synthesis — Knowledge Source Lifecycle Fixes

## Summary

Four panelists (architect, data, enduser, security) evaluated the 4-outcome plan. Strong convergence on priority (O2 first), on the O4 Qdrant prerequisite, and on error sanitization for O1. The primary unresolved tension is O3: whether to retype direct-ingest sources (architect: yes; data: no; enduser/security: neutral-with-caveats). A secondary tension exists on the O2 update state model (3-state vs. 4-state).

**Recommendation confidence: 0.80**

---

## Convergences

| Position | Supporting stances |
|----------|-------------------|
| O2 is highest-priority — lying timestamps destroy trust in the knowledge base | All four |
| O4 must NOT ship without Qdrant vector cleanup — `delete_cascade` currently orphans embeddings | All four |
| `destructiveHint=True` is the correct primary safety gate for `remove_source` | All four |
| O1 should expose exactly: `last_refreshed_at`, `last_error`, `enabled`, `fetch_method` | architect, data, enduser, security |
| `config` must NOT appear in `list_sources` (URL credential/endpoint leakage) | architect (implicit), security (explicit) |
| `last_error` must be sanitized at write time — raw exception strings leak paths/URLs | architect, enduser, security |
| Soft-delete/undo for O4 is over-engineering at 10–50 source scale | architect, enduser, security |
| Outcomes are structurally independent (touch separate code paths) | architect, data |
| O2 fix belongs in `_update_source_record`, not upstream | architect, data |
| Best-effort Qdrant cleanup (matching existing `delete_chunk_embeddings` pattern) is acceptable | architect, data, security |

---

## Tensions

### T1 — O3: Retype direct-ingest sources to `URL_LIST` or keep `AUTHENTICATED_WEB`?

| Stance | Position | Rationale |
|--------|----------|-----------|
| **architect** | Retype | `URL_LIST` has its own simpler handler; current typing routes through unnecessary content-fetcher injection; no migration needed for existing records |
| **data** | Do NOT retype | Dispatch is by `source_type` — retyping changes the runtime handler path, not just a label; existing tests assert `AUTHENTICATED_WEB`; both paths work, so stability > accuracy |
| **enduser** | Moderate priority, flags coupling | Agent contract-trust matters (agents read `source_type` semantically), but acknowledges this is a behavior change masquerading as a label fix |
| **security** | Low risk either way | No trust boundary or access control impact; correctness concern, not security concern |

**Core disagreement:** Architect sees the retype as eliminating a spurious dependency (content-fetcher requirement for plain HTTP). Data sees it as introducing unnecessary risk by switching a working handler dispatch path.

### T2 — O2: 3-state vs. 4-state update model

| Stance | "Skipped-only" case (0 refreshed, 0 failed, N skipped) | Rule |
|--------|--------------------------------------------------------|------|
| **architect** | Not addressed — 3-way table has no skipped row | Implicitly falls into "leave unchanged" bucket |
| **data** | Distinct state — bump timestamp | "Source was checked, found current" counts as verification |
| **enduser** | Bump timestamp | `refreshed + partial + skipped > 0` → bump |
| **security** | Not addressed | Defers to data semantics |

**Core disagreement:** Architect's 3-way model treats skipped-only as a no-op (timestamp preserved). Data and enduser argue that "checked and found current" is a successful verification that should update `last_refreshed_at`.

### T3 — O1: Include `enrich` in the expanded `SourceInfo`?

| Stance | Position |
|--------|----------|
| **architect** | Include — low cost, operationally useful |
| **enduser** | Exclude — processing config, not health; dilutes "at a glance" purpose |
| **data**, **security** | No position taken |

### T4 — O4: Dry-run mode?

| Stance | Position |
|--------|----------|
| **enduser** | Yes — defense-in-depth showing deletion counts before commit |
| **architect** | Return deletion counts after execution (audit, not preview) |
| **security** | Audit logging pre-commit (source_id, name, timestamp, counts) |
| **data** | No position taken |

**Core disagreement:** Enduser wants a preview-before-execute step. Architect and security achieve similar goals through post-execution reporting/logging.

---

## Per-Outcome Summary

### O1 — Expose source health in `list_sources`

**Panel recommends:** Add `last_refreshed_at`, `last_error`, `enabled`, `fetch_method` to `SourceInfo`. Sanitize `last_error` at write time (strip raw exception text to error class + safe context). Do NOT add `config`. The `enrich` field is contested (include vs. exclude) — decide based on whether agents need it for operational decisions.

**Prerequisite:** O2 should ship first or concurrently — exposing `last_refreshed_at` before fixing its dishonesty surfaces known-bad data.

### O2 — Fix refresh honesty

**Panel recommends:** Make `_update_source_record` conditional. The minimum consensus rule:

| Condition | `last_refreshed_at` | `last_error` |
|-----------|---------------------|--------------|
| `refreshed > 0` or `partial > 0` | Bump | Set from errors+warnings if any |
| `skipped > 0` (no refresh/partial) | **Contested** — bump (data, enduser) vs. preserve (architect) | Clear |
| `failed > 0`, nothing succeeded | Preserve | Set from errors |
| All counters zero | Preserve | Preserve previous (do not clear) |

**Implementation note:** Counter contamination from `_record_ingest_outcome` status aliasing is a known pre-existing issue. The O2 fix operates on already-contaminated counters; this is acceptable and does not block O2.

### O3 — Clean direct-ingest source semantics

**Panel split.** Architect recommends retyping to `URL_LIST`. Data recommends keeping `AUTHENTICATED_WEB`. Both paths work today; the question is whether semantic accuracy or handler-path stability takes priority.

**If retyping:** Change `_direct_source_config` in `ingest.py` for new sources only. Existing records remain `AUTHENTICATED_WEB`. Verify the `_handle_url_list` handler produces equivalent results for `fetch_method="http"` sources.

**If keeping:** Document the semantic mismatch. Accept that `source_type` is not a reliable classification signal for direct-ingest HTTP sources.

### O4 — Add `remove_source` MCP tool

**Panel recommends:** Wire as MCP tool with:
1. Qdrant vector cleanup added to cascade (hard prerequisite — all four stances agree)
2. `destructiveHint=True` annotation
3. Return deletion counts (documents, chunks, entities removed)
4. Audit log entry before commit (source_id, name, timestamp, counts)
5. Inline/non-recoverable sources: docstring must warn that data is not recoverable
6. Scope tool access to `knowledge-ingestor` agent by default

**Dry-run mode:** Enduser advocates; others achieve similar goals via post-execution reporting. Decision needed: is preview-before-execute worth the implementation cost at 10–50 sources?

---

## Open Questions Resolved

### Q1 — Should direct-ingest sources use `URL_LIST` instead of `AUTHENTICATED_WEB`?

**Panel split — no consensus.** Architect: yes (eliminates spurious handler complexity). Data: no (changes runtime behavior, not just label; existing tests break). Enduser: flags coupling risk. Security: indifferent.

**Remaining decision for user/mediator:** Is the semantic accuracy of `URL_LIST` worth the handler-path change and test updates? Or is the current "works correctly despite wrong label" state acceptable?

### Q2 — What about Qdrant vector cleanup in `delete_cascade`?

**Resolved — unanimous.** Qdrant cleanup is a hard prerequisite for O4. All stances agree on the approach: add best-effort vector cleanup to `source_store.delete_cascade` (collect chunk IDs → delete from Qdrant → proceed with SQLite cascade). Keep the single-commit transaction for SQLite. Do NOT fragment into per-document commits.

**Follow-up (data):** Add vector-level orphan detection to `integrity.py` — out of scope for O4 but acknowledged as a gap.

### Q3 — Should `_update_source_record` distinguish "all failed" from "nothing to do"?

**Resolved — convergent.** Both cases preserve `last_refreshed_at`. They diverge on `last_error`: "all failed" sets error text; "nothing to do" preserves previous state (does not clear a previously-recorded error). Data adds: log a warning on all-zero counters to surface silent misconfiguration.

---

## Recommended Implementation Order

```
O2 (refresh honesty)
 └─► O1 (expose health — depends on honest data from O2)
O4 prerequisite: fix delete_cascade to include Qdrant cleanup
 └─► O4 (wire remove_source MCP tool)
O3 (direct-ingest semantics — independent, contested, lowest urgency)
```

**Rationale:**
- O2 first because O1 exposes timestamps that O2 makes honest. Shipping O1 without O2 surfaces known-bad data.
- O4's Qdrant fix is a prerequisite, not the tool itself. The prerequisite can be developed in parallel with O2/O1.
- O3 is independent but contested. Defer until Q1 is resolved by user/mediator. Lowest risk if skipped entirely.

**Risk ordering:** O4 carries the highest implementation risk (Qdrant dependency injection into `source_store`). O2 is medium (state model decisions). O1 and O3 are low.
