---
# >> Your action: set response to approved, needs-info, or rejected
response: approved
decision: "C: Scope Params + Import/Export"
notes: ""
# >> Agent metadata
task_id: 616
agent: researcher
created: 2026-04-06
urgency: blocking
decision_type: approach-selection
impact_tier: 3
---

# Decision: Project-Local Knowledge Architecture — Three-Way Comparison

## Context

Task #616 researched how to add project-local knowledge source support (`.owlbear/knowledge/`) to mcp-knowledge. User requested a proper three-way comparison (prior DRs collapsed Options A/B into a single dismissal). Full analysis: `.owlbear/research/616-three-way-comparison.md`.

## Options

### A: Dual-Stack Facade
- **What:** Open two SQLite connections (global + project). Each tool handler queries both DBs and merges results.
- **Where saved:** Global: `store/knowledge/knowledge.db`. Project: `.owlbear/knowledge/knowledge.db`. Two live files.
- **Pro:** Live access (changes visible immediately), physical isolation, portable (copy the file), conceptually clean.
- **Con:** Qdrant cold-start re-embedding on every restart (~20-55s), all 5+ tool handlers need merge logic, schema drift risk (silently migrates project files), doubles AppContext/testing surface. ~500-800 LOC.

### B: ATTACH DATABASE
- **What:** Use SQLite `ATTACH DATABASE` to add project DB as `local` schema within the single connection. Create UNION views or use qualified table names (`main.documents`, `local.documents`).
- **Where saved:** Same as A — two physical files. Accessed through one connection.
- **Pro:** Live access, physical isolation, single connection (no duplicate AppContext), standard SQLite feature.
- **Con:** All ~20 SQL statements in GraphStore need qualified names or views, same Qdrant cold-start as A, same schema drift as A, WAL mode breaks cross-DB atomicity, dynamic ATTACH/DETACH lifecycle. ~400-600 LOC.

### C: Scope Params + Import/Export — (rec:) recommended
- **What:** Single DB. Expose existing `scope`/`scopes` params on tool handlers. `import_scope` copies project data into main DB under scope `"project:{name}"`. `export_scope` dumps scoped data to a portable file. Both tools already exist in `scope_transfer.py`.
- **Where saved:** ALL data in `store/knowledge/knowledge.db`. Project data identified by scope column. `.owlbear/knowledge/knowledge.db` is a portable snapshot (not live).
- **Pro:** Minimal code (~300 LOC, mostly written), no Qdrant cold-start cost, no schema drift, reuses #135 scope infra, KISS-aligned, content-hash dedup on import.
- **Con:** NOT live — must explicitly import (one tool call). All data in one file (logical, not physical isolation). Must re-import after project DB changes.

### D: Defer
- **Effort:** Zero. Blocks #617/#618. Project-local KB deferred to future phase.

## Key Differentiator

| | A: Dual-Stack | B: ATTACH | C: Scope Params |
|---|---|---|---|
| Qdrant restart cost | 20-55s | 20-55s | None |
| GraphStore changes | Merge logic in all methods | All SQL rewritten | Zero |
| Schema drift risk | Medium | Medium | None |
| Live project access | Yes | Yes | No (import step) |
| LOC delta | ~500-800 | ~400-600 | ~300 |

## Recommendation

.82 confidence — **Option C.** For a single-user laptop system the import step is a negligible one-time call. A/B's live access doesn't justify the Qdrant cold-start cost, SQL rewrite, and schema drift. If live access becomes needed later, Option B is the best upgrade path from C (preserves single-connection model).

## Impact of Deferral (Option D)
Blocks #617 and #618. Project-local knowledge deferred to future phase.
