# mcp-memory Scaffold Validation

> **Owning task:** #524 — Scaffold mcp-memory package
> **Date:** 2026-04-01 **Status:** Complete (blocked on DR #387)

## 1. Context and Question

Task #524 scaffolds `packages/mcp-memory/` following existing MCP server patterns. The design is fully specified in `docs/research/memory-mcp-server-design.md` (from parent task #387). This research validates the scaffolding approach against the codebase and confirms the AC is implementable. **Blocked on DR `docs/decisions/pending/387-memory-mcp-architecture.md` (approved: false).** If option C (embed in knowledge-mcp) or D (defer) is chosen, this task is invalidated.

## 2. Sources Studied

| # | Source | Path/URL | Relevance |
|---|--------|----------|-----------|
| S1 | Design doc | `docs/research/memory-mcp-server-design.md` | 1.0 |
| S2 | DR #387 | `docs/decisions/pending/387-memory-mcp-architecture.md` | 1.0 |
| S3 | mcp-kanban server.py | `packages/mcp-kanban/src/owlbear_mcp_kanban/server.py` | .90 |
| S4 | mcp-knowledge server.py | `packages/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | .90 |
| S5 | mcp-project server.py, models.py | `packages/mcp-project/src/owlbear_mcp_project/` | .85 |
| S6 | Root pyproject.toml | `pyproject.toml` | .90 |
| S7 | test_package_boundary.py | `tests/test_package_boundary.py` L40-50 | .90 |
| S8 | setup.py | `scripts/setup.py` L49-86 | .85 |

## 3. Analysis

### 3A. Checklist validation

| Item | Status | Notes |
|------|--------|-------|
| Theoretical validity | Pass | Follows 3 established MCP server patterns (S3-S5) |
| Environment audit | Pass | No mcp-memory package exists; no duplication |
| Prior art | Pass | 3 reference implementations in-repo |
| Technical feasibility | Pass | stdlib `sqlite3`, `mcp[cli]>=1.26`, Python 3.12+ |
| Architecture fit | Pass | 6 integration points verified (see §3B) |
| Implementation approach | Pass | Hybrid of mcp-knowledge (SQLite) + mcp-project (project identity) |

### 3B. Integration touch points

| File | Change needed | Verified |
|------|--------------|----------|
| `packages/mcp-memory/` (new) | Full package: pyproject.toml, `__init__.py`, `__main__.py`, server.py, models.py | S3-S5 |
| Root `pyproject.toml` | `members = ["packages/*"]` auto-discovers — **no edit needed** | S6 L4-5 |
| Root `pyproject.toml` ruff src | Add `"packages/mcp-memory/src"` to `tool.ruff.src` array | S6 L33-38 |
| `tests/test_package_boundary.py` | Add `"owlbear_mcp_memory": set()` to `ALLOWED_IMPORTS` | S7 L40-50 |
| `scripts/setup.py` | Add `owlbearMemory` stdio entry, update docstring count | S8 L49-86 |

### 3C. Pattern reference for builder

**Best template:** mcp-kanban for file skeleton (S3), mcp-knowledge for SQLite lifespan (S4), mcp-project for project identity (S5).

**AppContext:** `conn: sqlite3.Connection` + `project_name: str | None` (hybrid S4/S5).

**Lifespan init:** `OWLBEAR_MEMORY_DB_PATH` env var → default `../owlbear/data/memory/memory.db`. Set `PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000`. Read project name from `owlbear-project.json`. WAL is new vs existing servers — design doc §3A mandates it for concurrent agent sessions.

**Schema:** 12 fields per design doc §3B. `content_hash` included in DDL regardless of pattern 3 approval — additive, no cost.

### 3D. AC completeness check

All 6 AC items are concrete and implementable:

- Package scaffold: follows existing `packages/mcp-*/` structure
- SQLite schema: 12 fields defined in design doc §3B
- AppContext + lifespan: patterns from S4/S5, WAL mode per design
- setup.py: add 5th server entry matching existing pattern
- pyproject.toml: workspace auto-discovers, ruff src needs update
- test_package_boundary.py: add key to ALLOWED_IMPORTS dict

**Missing from AC (minor):** ruff `src` array update. Builder should include this or it will cause lint discovery issues. Recommend adding to AC.

## 4. Recommendation

No novel decision — this is pattern-following scaffolding. Blocked until DR #387 is resolved. If option A or B is approved, implementation is straightforward. Estimated ~150 LOC for scaffold + schema.

Challenge: skipped — no novel recommendation to challenge (pattern-following scaffolding).

## 5. Follow-up Tasks

**No new tasks created.** Task #524 already exists with correct AC. Companion tasks #525, #526 etc. were created by #387 research. The only action is to unblock #524 when DR #387 is approved.

Suggested AC amendment: add "ruff `tool.ruff.src` array updated with `packages/mcp-memory/src`" as 7th AC item.
