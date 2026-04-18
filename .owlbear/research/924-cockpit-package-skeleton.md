# Cockpit Package Skeleton + Engine Adapter Boundary Test

> **Owning task:** #924 — P1-03: Cockpit package skeleton + engine adapter boundary test
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

Task #924 creates `serve/cockpit/` as a new uv workspace member with FastAPI foundation and a boundary test enforcing D12 (backend exposes only allowed verbs; agent-only engine methods `claim_task`, `start_work`, `end_work`, `pick_dispatchable` must not be imported by cockpit code).

**Question:** What is the correct package structure, dependency configuration, and boundary test approach — and are there any blockers or unknowns?

## 2. Sources Studied

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| S1 | Root `pyproject.toml` workspace config | `pyproject.toml` | Workspace member pattern: `members = ["serve/*"]` — cockpit auto-discovered (0.95) |
| S2 | `serve/mcp-kanban/pyproject.toml` | Codebase | Reference pyproject.toml for workspace member with kanban dep (0.95) |
| S3 | `serve/kanban/pyproject.toml` | Codebase | Core kanban engine package — build config pattern (0.90) |
| S4 | Deleted `test_package_boundary.py` | Git: `ba340cce~1` | AST scanning + `_owlbear_import_roots()` pattern (~120 LOC) (0.90) |
| S5 | Deleted `test_engine_package_boundary_817.py` | Git: `ba340cce~1` | AST scan for forbidden transport imports in engine package (0.85) |
| S6 | Brief decisions D12/D14 | `.owlbear/briefs/draft-cockpit/decisions.md` | Agent-only verbs blocklist; stack: FastAPI + owlbear-kanban (1.0) |
| S7 | `owlbear_kanban/__init__.py` | `serve/kanban/src/owlbear_kanban/__init__.py` | Exports: `KanbanEngine`, `Task`, `TaskSummary`, `BoardConfig`, `pick_dispatchable` (0.95) |
| S8 | `owlbear_kanban/engine.py` | `serve/kanban/src/owlbear_kanban/engine.py` | Methods: `claim_task`, `start_work`, `end_work` confirmed on `KanbanEngine` (0.95) |

## 3. Analysis

### 3.1 Package Structure — No Ambiguity

Root `pyproject.toml` uses `members = ["serve/*"]`, so `serve/cockpit/` is auto-discovered. No root config change needed beyond `uv sync`.

| File | Purpose | Pattern Source |
|------|---------|---------------|
| `serve/cockpit/pyproject.toml` | Workspace member; deps: `owlbear-kanban`, `fastapi`, `uvicorn`, `pydantic` | S2 (mcp-kanban) |
| `serve/cockpit/src/owlbear_cockpit/__init__.py` | Package marker | Standard |
| `serve/cockpit/src/owlbear_cockpit/main.py` | FastAPI app + `/health` | D14 |
| `serve/cockpit/src/owlbear_cockpit/adapter.py` | Engine adapter placeholder | D12 |

The `pyproject.toml` must declare `owlbear-kanban` as workspace dep (`[tool.uv.sources] owlbear-kanban = { workspace = true }`), matching S2 pattern.

### 3.2 Boundary Test — AST Scan for Forbidden Names

D12 forbids cockpit from importing 4 agent-only engine functions: `claim_task`, `start_work`, `end_work`, `pick_dispatchable`.

**Approach:** AST-scan all `.py` files under `serve/cockpit/src/` for `ImportFrom` nodes where specific names are imported from `owlbear_kanban`. This is a **name-level** check (more targeted than S4's namespace-level check).

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Scan scope | `serve/cockpit/src/**/*.py` | Per AC — cockpit source only |
| Detection target | `from owlbear_kanban import claim_task` etc. | D12 blocklist |
| Also check `from owlbear_kanban.engine import claim_task` | Yes — submodule imports bypass `__init__` | Defense in depth |
| Check `import owlbear_kanban; owlbear_kanban.claim_task()` | No — attribute access is runtime, not importable | AST import check is sufficient for this discipline |

Forbidden names (from D12 + S7/S8):

| Name | Where defined | Why forbidden |
|------|--------------|---------------|
| `claim_task` | `KanbanEngine.claim_task()` | Agent-only — cockpit cannot claim |
| `start_work` | `KanbanEngine.start_work()` | Agent-only — cockpit cannot advance |
| `end_work` | `KanbanEngine.end_work()` | Agent-only — cockpit cannot advance |
| `pick_dispatchable` | `owlbear_kanban.dispatch` | Agent-only — cockpit cannot dispatch |

### 3.3 Root pyproject.toml Update

The AC says "Root `pyproject.toml` updated with workspace member." However, the current config uses `members = ["serve/*"]` (S1), which auto-discovers any directory under `serve/`. No explicit entry needed. The AC item is satisfied by creating the directory + running `uv sync`.

**Caveat for builder:** The root `pyproject.toml` `[tool.ruff] src` list should be extended with `"serve/cockpit/src"` for linting to work correctly on the new package.

### 3.4 Trade-Off Matrix

| Aspect | Option A: Name-level AST scan | Option B: Namespace-level blocklist (S4 pattern) | Option C: Runtime `hasattr` check |
|--------|-------------------------------|---------------------------------------------------|-------------------------------------|
| Precision | Catches exactly the 4 forbidden names | Would block ALL owlbear_kanban imports (too broad) | Runtime-only, misses static analysis |
| False positives | None — only 4 names targeted | High — cockpit MUST import from owlbear_kanban | None |
| Maintenance | Add names if D12 scope grows | N/A (wrong approach) | Fragile |
| Confidence | **0.90** | 0.20 | 0.40 |

## 4. Recommendation

**Option A — Name-level AST scan.** Confidence: **0.90**.

The implementation is straightforward scaffolding following established workspace patterns. The boundary test uses the proven AST-scan approach from S4/S5 but scoped to specific forbidden name imports rather than whole-namespace blocking.

Challenge: N/A — this is deterministic scaffolding following brief decisions and existing codebase patterns. No alternative approaches to evaluate.

## 5. Follow-up Tasks

No additional follow-up tasks needed. The AC is fully specified and self-contained. The `test_package_boundary.py` global boundary test was deleted in the nuclear reset — restoring it with `owlbear_cockpit` entry is out of scope for #924 (separate concern).

**Implementation notes for downstream agents:**
- The `adapter.py` is a placeholder — future tasks (#930, #934) will populate it with allowed engine method wrappers.
- The boundary test at `tests/test_cockpit_boundary.py` should scan for both `from owlbear_kanban import <name>` and `from owlbear_kanban.engine import <name>` patterns.
- The root `[tool.ruff] src` list needs `"serve/cockpit/src"` added.
