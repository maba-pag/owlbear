# Brief — Knowledge Source Lifecycle Fixes

## Problem

The knowledge module's source entity has full health and lifecycle data (`last_refreshed_at`, `last_error`, `enabled`, `fetch_method`, etc.) but hides it behind a minimal `list_sources` response. The refresh system lies about freshness — bumping `last_refreshed_at` unconditionally even when all URLs failed. Direct-ingest HTTP sources are mislabeled as `AUTHENTICATED_WEB`. There is no tool to remove a source and its downstream data.

## Scope

4 focused fixes to the existing knowledge source surface. No new management system, manifest format, or Cockpit UI. Investment tier: Shared.

## Outcomes

### O1 — Expose source health in `list_sources`

Expand the `SourceInfo` TypedDict and `list_sources` MCP tool response to include: `last_refreshed_at`, `last_checked_at`, `last_error`, `enabled`, `fetch_method`.

**Excluded:** `config` (URL/endpoint leak risk), `enrich` (processing config, not health).

**Error format:** Raw strings, matching existing `refresh_source` behavior. No sanitization.

**Depends on:** O2 (honest timestamps must exist before exposing them).

### O2 — Fix refresh honesty (two-field model)

Add `last_checked_at` field to `KnowledgeSource` model. Fix `_update_source_record` in `refresh.py` with conditional logic:

| Condition | `last_checked_at` | `last_refreshed_at` | `last_error` |
|-----------|-------------------|---------------------|--------------|
| `refreshed > 0` or `partial > 0` | Bump | Bump | Set from errors+warnings if any; clear if none |
| `skipped > 0` (no refresh/partial) | Bump | Preserve | Clear |
| `failed > 0`, nothing succeeded | Bump | Preserve | Set from errors |
| All counters zero (misconfigured) | Preserve | Preserve | Preserve previous |

**Semantics:**
- `last_checked_at` = "when did the system last attempt to process this source?" (any non-zero counter)
- `last_refreshed_at` = "when did new or updated content last arrive?" (content acquisition only)

**Touches:** `models.py` (add field), `schema.py` (add column + migration), `source_store.py` (column list + update path), `refresh.py` (`_update_source_record` logic).

### O3 — Retype direct-ingest HTTP sources to `URL_LIST`

Change `_direct_source_config` in `ingest.py` to assign `SourceType.URL_LIST` instead of `SourceType.AUTHENTICATED_WEB` for HTTP URLs.

**Scope:** New sources only. Existing `AUTHENTICATED_WEB` records remain as-is (no migration).

**Gate:** Handler equivalence must be verified before implementation — confirm that `_handle_url_list` produces equivalent refresh results for `fetch_method="http"` sources as `_handle_authenticated_web` does today. If equivalence fails, O3 is dropped from the work package.

### O4 — Add `remove_source` MCP tool

Wire a new `remove_source` MCP tool that performs full cascade deletion.

**Execution order:**
1. Collect chunk IDs from the source's documents
2. Delete vectors from Qdrant for those chunk IDs
3. If vector deletion fails → abort, return error, source stays intact
4. Run `source_store.delete_cascade` (SQLite transaction)
5. Return deletion counts (documents, chunks, entities removed)

**Annotations:** `destructiveHint=True`.

**Tool handler** needs access to both `source_store` and Qdrant client (or `document_store`). The MCP server lifespan already builds both — wire both into the tool context.

**Audit:** Log source_id, name, timestamp, and deletion counts before commit.

**No dry-run mode.** Post-execution counts provide accountability.

## Implementation Order

```
O2 (refresh honesty + new field)
 └─► O1 (expose health — depends on honest data from O2)
O4 (remove_source — can develop in parallel with O2/O1)
O3 (direct-ingest retype — independent, gated on handler equivalence)
```

O2 and O1 are tightly coupled (shared schema/model change). O4 requires composing both stores at the MCP tool level. O3 is independent and lowest priority.

## Constraints

- No `config` in `list_sources` response (URL/endpoint leak)
- No error sanitization (raw strings, single-user system)
- No dry-run for `remove_source` (destructiveHint is the safety gate)
- No migration for existing `AUTHENTICATED_WEB` direct-ingest records
- O3 drops if handler equivalence fails
- `remove_source` aborts entirely if Qdrant cleanup fails (no partial deletes)

## Key Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D2 | Narrow scope (4 fixes, no management system) | Challengers confirmed bugs/gaps, not missing system |
| D3 | Two-field timestamp model | Operator needs both "is system watching?" and "when did content change?" |
| D4 | Retype to URL_LIST (gated) | Semantic accuracy; handler equivalence is the gate |
| D5 | Exclude enrich from SourceInfo | Processing config, not health signal |
| D6 | No dry-run for remove_source | destructiveHint + counts + audit sufficient at scale |
| D7 | Raw error strings | Consistency with refresh_source; single-user system |
| D8 | Vectors-first abort on failure | No half-deleted sources |
