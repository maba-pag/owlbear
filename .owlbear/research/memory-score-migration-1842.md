# Migration — Score Initialization from Confidence

> **Owning task:** #1842 — P2-03: Migration — score initialization from confidence
> **Date:** 2026-05-25 **Status:** Complete

## 1. Context and Question

Task #1841 added `score`, `outstanding_count`, `unremarkable_count`, `didnt_use_count` fields to `MemoryEntry` with defaults `0.0`/`0`/`0`/`0`. All 111 existing entry files in `.owlbear/memory/` lack these YAML keys — they deserialize with `score=0.0` (not `confidence`). This task must backfill `score=confidence` and counters=0 idempotently, preserving sort order.

Questions: (a) migration function architecture, (b) idempotency predicate design, (c) order-preservation proof, (d) execution boundary and CLI pattern.

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `serve/memory/src/owlbear_memory/models.py` | Codebase | 1.0 — MemoryEntry with defaults |
| `serve/memory/src/owlbear_memory/storage.py` | Codebase | 1.0 — read/write_entry (atomic writes) |
| `serve/memory/src/owlbear_memory/engine.py` | Codebase | 1.0 — compute_score, save() |
| `serve/mcp-memory/src/owlbear_mcp_memory/tools.py:273` | Codebase | 1.0 — recall sort key |
| `serve/kanban/src/owlbear_kanban/migrate.py` | Codebase | 0.9 — prior art: CLI migration, _is_task_migrated |
| `serve/kanban/src/owlbear_kanban/engine.py:502` | Codebase | 0.7 — MigrationRequiredError gate |
| `.owlbear/research/memory-assessment-counters-score.md` | Project | 0.9 — P2-02 research |
| Sanity.io migration principles (web) | External | 0.7 — idempotent scripts |
| `editfrontmatter` PyPI package | External | 0.6 — batch YAML frontmatter update patterns |

## 3. Analysis

### 3.1 Implementation Approaches

| Approach | Description | Pro | Con | Confidence |
|----------|-------------|-----|-----|------------|
| A: Engine method + CLI | `MemoryEngine.migrate_scores()` + `uv run memory-migrate` entry point | Explicit, testable, follows kanban precedent, supports dry-run | Adds ~40 LOC + entry point | 0.82 |
| B: model_validator (read-time) | Set score=confidence when absent from raw dict | Auto-applies; zero operational step | Doesn't persist; caller never sees migration; untestable on-disk | 0.50 |
| C: Load-time side-effect | engine.load() rewrites files | Automatic | Side-effects in read path; breaks SRP; concurrent access risk | 0.30 |

### 3.2 Idempotency Predicate

The kanban migration checks multiple fields (`_is_task_migrated` at migrate.py:153). Challenger flagged single-field check as insufficient.

| Predicate | Mechanism | Robustness |
|-----------|-----------|------------|
| `"score" in data` | Single key presence | Fails on partial writes (score present, counters missing) |
| All 4 keys present | `{"score", "outstanding_count", "unremarkable_count", "didnt_use_count"} <= data.keys()` | Handles partial states; matches write_entry output |

**Recommendation: All-4-keys predicate.** Since `write_entry` always serializes all fields, a properly-migrated entry has all 4. If only some are present (manual edit), the entry is treated as unmigrated and gets a clean write.

### 3.3 Order-Preservation Proof

**Pre-migration recall sort:** `(state_rank, -confidence, id)` (tools.py:273)
**Post-migration recall sort (P2-04):** `(state_rank, -score, id)`
**Migration sets:** `score = confidence`, `counters = 0`

Proof:
- `compute_score(c, 0, 0) = c + (0 × 0.1) - (0 × 0.01) = c`
- Therefore `score = confidence` when counters = 0
- Sort tuple `(state_rank, -score, id) = (state_rank, -confidence, id)` ∎

**Scope note:** AC-3 constrains the proof to "when all counters are 0" — this is a migration-point correctness proof, not a runtime invariant. Post-migration confidence edits diverging from score is a concern for `edit()` (future scope, not this task).

### 3.4 Execution Boundary

| Option | Pattern | Precedent | Fit |
|--------|---------|-----------|-----|
| CLI entry point | `uv run memory-migrate [--dry-run]` | kanban-migrate | Good — explicit operational step |
| Migration gate (error if unmigrated) | MigrationRequiredError on load | kanban engine | Over-engineering — task deps already sequence P2-03 before P2-04 |
| Auto-run on first load | engine.load() detects + runs | None in repo | Too magical for a single-user system |

**Recommendation: CLI entry point without migration gate.** The task dependency graph (#1842 blocks #1843/#1844) provides sequencing. A gate adds complexity without value in a single-operator system.

### 3.5 Challenger Response

| Finding | Severity | Response |
|---------|----------|----------|
| Execution boundary unspecified | Critical | Accepted — add CLI entry point per kanban precedent |
| edit() doesn't recompute score | Moderate | Out of scope — AC-3 proves migration-point correctness only; runtime score maintenance belongs to assessment workflow |
| Single-field idempotency weak | Moderate | Accepted — use all-4-keys predicate |
| Package surface ambiguity | Minor | Clarified — one file pass covers both packages (shared directory) |
| AC ambiguity (which ordering) | Moderate | Clarified — parent #1839 AC7 references recall_memory explicitly |

## 4. Recommendation

**Approach A: Engine method + CLI entry point** (confidence: 0.82)

Implementation plan:
1. `MemoryEngine.migrate_scores() -> int` — reads raw YAML, checks all-4-keys predicate, sets score=confidence + counters=0, writes via `write_entry`, returns count
2. `uv run memory-migrate` CLI in `serve/memory/pyproject.toml` — calls migrate_scores(), prints summary
3. `--dry-run` flag — counts entries needing migration without writing

Challenge: reconsider → addressed critical finding (execution boundary), accepted 2 moderate findings. Confidence in revised recommendation: 0.82.

## 5. Follow-up Tasks

Existing decomposition covers implementation. No new tasks needed — #1842 itself is ready for architecture review and implementation.
