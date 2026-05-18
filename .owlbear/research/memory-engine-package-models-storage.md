# Memory Engine Package — Models, Errors, and Storage Primitives

> **Owning task:** #1667 — P1-01: Memory engine package — models, errors, and storage primitives
> **Date:** 2026-05-18 **Status:** Complete

## 1. Context and Question

Task #1667 creates `serve/memory/` as a transport-free domain package containing models, error types, and file I/O storage primitives. The existing code in `serve/mcp-memory/src/owlbear_mcp_memory/` provides the extraction source. Questions: (a) what changes are needed vs direct extraction, (b) which YAML library to use, (c) how to structure the security hardening.

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `serve/mcp-memory/src/owlbear_mcp_memory/models.py` | Codebase | 1.0 — direct extraction source |
| `serve/mcp-memory/src/owlbear_mcp_memory/engine.py` | Codebase | 0.9 — storage logic to extract |
| `serve/kanban/pyproject.toml` + `src/owlbear_kanban/` | Codebase | 0.9 — canonical package pattern |
| `.owlbear/briefs/draft-cockpit-memory-tab/brief.md` | Project doc | 1.0 — authoritative specification |
| `serve/kanban/src/owlbear_kanban/yaml_rt.py` | Codebase | 0.7 — ruamel.yaml usage pattern |

## 3. Analysis

### 3.1 Models — Extract + Enhance

| Field | Current state | Required change |
|-------|--------------|-----------------|
| `content: str` | No length validation in model | Add `Field(max_length=1024)` |
| Timestamps (`created_at`, `updated_at`, `approved_at`) | Stored as `str` with ISO validation | Keep as `str` — matches existing disk format |
| `MemoryCategory` | 9 values (StrEnum) | No change |
| `MemoryState` | 4 values (StrEnum) | No change |
| ID validation | UUIDv4 regex | No change |
| `source_agent` | `frozen=True` | Keep frozen — immutable after creation |

Content ≤1024 is currently enforced only in MCP tool layer (`server.py`, `tools.py`). Moving it to the model aligns with "strict on write" principle.

### 3.2 YAML Library — ruamel.yaml vs pyyaml

| Criteria | pyyaml (current) | ruamel.yaml (brief specifies) |
|----------|------------------|-------------------------------|
| Workspace precedent | Used in mcp-memory | Used in kanban (6+ modules) |
| Safe mode support | `yaml.safe_load/safe_dump` | `YAML(typ='safe')` |
| Comment preservation | No | Yes (not needed here) |
| Already a workspace dep | Yes | Yes (via kanban) |
| Brief specifies | — | **Yes** |

**Decision:** Use `ruamel.yaml` with `typ='safe'` for safe load and standard `YAML()` for dump (following kanban pattern). This aligns with the brief specification and workspace convention.

### 3.3 Storage Primitives — Security Hardening

| Security check | Implementation | Justification |
|----------------|---------------|---------------|
| Path containment | `resolved.is_relative_to(memory_dir)` | Prevent path traversal |
| Symlink rejection | `path.is_symlink()` check before read/write/delete | Prevent symlink-based path escape |
| File size bound | `path.stat().st_size > 8192` → skip | Prevent DoS via huge files |
| Atomic write | `tempfile.mkstemp` + `os.rename` | Prevent corruption on crash |

All four are standard patterns already proven in the existing engine.py (atomic write) or straightforward additions.

### 3.4 Error Types

| Error | Use case | Notes |
|-------|----------|-------|
| `NotFoundError` | Entry ID not on disk | Replace current `KeyError` usage |
| `ConcurrencyError` | OCC mismatch | New — used by engine in P1-02 |
| `ValidationError` | Field validation failure | Wraps Pydantic errors at domain layer |
| `TransitionError` | Invalid state transition | New — used by engine in P1-02 |

All four are simple `Exception` subclasses. `ConcurrencyError` and `TransitionError` are defined here but used primarily by P1-02 (MemoryEngine class).

### 3.5 Package Structure

```
serve/memory/
├── pyproject.toml          # name: owlbear-memory, deps: pydantic, ruamel.yaml
└── src/owlbear_memory/
    ├── __init__.py         # public exports
    ├── models.py           # MemoryEntry, MemoryCategory, MemoryState
    ├── errors.py           # NotFoundError, ConcurrencyError, ValidationError, TransitionError
    └── storage.py          # read_entry(), write_entry()
```

Dependencies: `pydantic>=2.13.4`, `ruamel.yaml>=0.19.1`

## 4. Recommendation

**Confidence: 0.90** — Direct extraction with well-defined enhancements. All patterns have workspace precedent.

Proceed with extraction. Key implementation notes:
1. `models.py` — Copy from mcp-memory, add `max_length=1024` to content field
2. `errors.py` — Four one-line exception classes
3. `storage.py` — Extract `_load_file` → `read_entry(path)` and `write` → `write_entry(path, entry)` from engine.py, add symlink/size/containment guards
4. `pyproject.toml` — Follow kanban package pattern, minimal deps

Challenge: FALLBACK — trivial extraction task with full codebase precedent; challenger not invoked.

## 5. Follow-up Tasks

No additional tasks needed — #1667 already has well-defined AC and the implementation path is clear. The downstream tasks (#1668 P1-02, #1669 P2-01) are already planned in the parent decomposition.
