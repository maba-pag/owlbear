# Implementation — Rename TaskRecord → Task in Engine Internals

> **Owning task:** #800 — Rename TaskRecord → Task with compat alias
> **Date:** 2026-04-11 **Status:** Complete

## 1. Context and Question

Phase 1, Chain 1 step 2. The `Task` class and `TaskRecord = Task` compat alias already exist in `models.py`. The remaining work is updating internal engine references in `engine.py` and `task_io.py` from `TaskRecord` → `Task`.

**Question:** What is the scope and risk of updating all internal engine references from `TaskRecord` to `Task`?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | `models.py` (lines 59–90) | Codebase | 1.0 — `Task` class + `TaskRecord = Task` alias already in place |
| S2 | `engine.py` (lines 1–555) | Codebase | 1.0 — 23 `TaskRecord` refs: 1 import, 1 constructor, 10 type annotations, 11 docstrings |
| S3 | `task_io.py` (lines 30–196) | Codebase | 1.0 — 7 `TaskRecord` refs: 1 import, 1 constructor call, 2 type annotations, 3 docstrings |
| S4 | `__init__.py` (lines 1–17) | Codebase | 0.9 — exports both `Task` and `TaskRecord`; no change needed |
| S5 | `server.py` (MCP adapter, lines 19–200) | Codebase | 0.8 — 3 `TaskRecord` refs; boundary code, keep as-is per O4 |
| S6 | `test_rename_taskrecord_to_task_799.py` | Codebase | 0.9 — RED tests verifying `Task` importable, alias identity, CRUD returns `Task` |
| S7 | Brief `draft-kanban-web-gui-prep/brief.md` Phase 1 table | Codebase | 0.9 — specifies rename + compat alias |

## 3. Analysis

### 3.1 Current State

| File | `TaskRecord` refs | Categories |
|------|-------------------|------------|
| `engine.py` | 23 | 1 import, 1 constructor (`TaskRecord(...)`), 10 return type annotations, 11 docstring `:class:\`TaskRecord\`` |
| `task_io.py` | 7 | 1 import, 1 `TaskRecord.model_validate()`, 2 param/return annotations, 3 docstrings |
| `server.py` | 3 | 1 TYPE_CHECKING import, 1 param annotation, 1 docstring |
| `__init__.py` | 2 | 1 import, 1 `__all__` entry — keeps alias export |
| `models.py` | 2 | 1 comment, 1 alias definition — keeps alias |

### 3.2 Feasibility

| Criterion | Assessment |
|-----------|------------|
| Risk | Zero — `TaskRecord is Task` (same object), rename is cosmetic |
| Breakage potential | None — alias ensures all external consumers continue working |
| Scope | `engine.py` + `task_io.py` only; `server.py` unchanged (O4 constraint) |
| Mechanical complexity | Find-and-replace within 2 files; no logic changes |
| Test coverage | #799 tests verify `Task` importable, alias identity, CRUD returns `Task` instances |

### 3.3 Implementation Approach

1. **`engine.py`**: Change import `TaskRecord` → `Task`. Replace all annotations `-> TaskRecord` → `-> Task`, constructor `TaskRecord(...)` → `Task(...)`, and docstring references.
2. **`task_io.py`**: Change import `TaskRecord` → `Task`. Replace `TaskRecord.model_validate(data)` → `Task.model_validate(data)`, annotations, docstrings.
3. **`models.py`**: No change — alias stays.
4. **`__init__.py`**: No change — exports both.
5. **`server.py`**: No change — boundary consumer, keeps `TaskRecord` import via alias.

## 4. Recommendation

Proceed with mechanical rename in `engine.py` and `task_io.py`. Confidence: **0.95**.

Challenge: skipped — trivial rename, no design decision involved.

Tier: **T1 — Autonomous** (rename/refactor within existing codebase).

## 5. Follow-up Tasks

None — #800 itself is the implementation task. The builder changes 2 files with find-and-replace.
