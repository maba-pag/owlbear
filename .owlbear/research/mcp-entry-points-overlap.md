# MCP Entry Points: Overlap Analysis

> **Owning task:** #120 — Add __main__.py entry points to mcp-knowledge and mcp-project
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #120 requests `__main__.py` files for `owlbear_mcp_knowledge` and
`owlbear_mcp_project` so they can start via `python -m`. Research question: what
is the correct implementation approach, and does #120 overlap with existing tasks?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| S1 | MCP Python SDK README | https://github.com/modelcontextprotocol/python-sdk | 1.0 |
| S2 | MCP Quickstart (server) | https://modelcontextprotocol.io/quickstart/server | 0.9 |
| S3 | OwlBear mcp-kanban __main__.py | packages/mcp-kanban/src/owlbear_mcp_kanban/__main__.py | 1.0 |
| S4 | Task #54 AC | kanban/tasks/054-*.md | 1.0 |
| S5 | Task #17 AC | kanban/tasks/017-*.md | 1.0 |
| S6 | Task #104 test_server.py | packages/mcp-knowledge/tests/test_server.py | 0.9 |
| S7 | docs/research/mcp-server-registry.md §3.2 | docs/research/mcp-server-registry.md | 0.8 |

## 3. Analysis

### 3.1 Reference Pattern (S1, S2, S3)

FastMCP entry points follow a standard 8-line pattern (S1, S3):

```python
"""Entry point for ``python -m {package}``."""
from __future__ import annotations
from {package}.server import mcp
if __name__ == "__main__":
    mcp.run()
```

`mcp.run()` defaults to stdio transport (S1, S2). The `__main__.py` requires a
`server.py` module exporting a `FastMCP` instance named `mcp`.

### 3.2 Overlap with Existing Tasks

| AC in #120 | Covered by | Evidence |
|-----------|-----------|---------|
| mcp-knowledge `__main__.py` | #54 AC7 | "\_\_main\_\_.py exists and calls mcp.run()" |
| mcp-knowledge `server.py` (implicit) | #54 AC1-6 | Full server.py with lifespan, tools |
| mcp-project `__main__.py` | #17 AC7 | "Server communicates via stdio transport" (implies entry point) |
| mcp-project `server.py` (implicit) | #17 AC1-6 | Full server with tools and resources |
| `uv run -m` starts without error | #54, #17 | Both require working stdio servers |

**`mcp[cli]` dependency gap:** Neither #54 nor #17 explicitly require `mcp[cli]`
in `pyproject.toml`. This is the only non-overlapping AC in #120.

### 3.3 Stub vs. Full Server Trade-off

| Approach | KISS | YAGNI | Risk | Confidence |
|----------|------|-------|------|-----------|
| **A: Minimal stubs** — create `server.py` with empty FastMCP + `__main__.py` | Low | Fails | Stub server.py replaced by #54; conflicts with #104 tests expecting full lifespan | .40 |
| **B: Merge into #54/#17** — remove #120, add `mcp[cli]` to #54/#17 AC | High | Passes | Entry points delayed until heavier tasks complete | .80 |
| **C: Deps only** — #120 adds `mcp[cli]` to pyproject.toml; `__main__.py` stays with #54/#17 | Medium | Passes | Very thin task; ACs 1-4 still unfulfilled | .60 |

Option A fails because: mcp-knowledge's `test_server.py` (S6) expects imports
like `init_db`, `GraphStore`, `KnowledgeQueryService` from `server.py`. A stub
without these symbols would not satisfy the existing tests. Creating throwaway
code that gets immediately replaced violates KISS.

## 4. Recommendation (.80 confidence)

**Option B: Merge #120 into existing tasks.** Rationale:

1. #54 already covers mcp-knowledge `server.py` + `__main__.py` — adding one
   pyproject.toml line is trivial for the builder
2. #17 already covers mcp-project full server build — same applies
3. Creating stubs that conflict with existing RED tests (#104) is counterproductive
4. The `mcp[cli]` dependency is a one-liner that belongs with the server build

**Architect action:** Add `mcp[cli]>=1.26` to the AC of both #54 and #17.
Then close #120 as subsumed.

Risk: Entry points are delayed until #54 and #17 are built. Acceptable because
VS Code shows clear error indicators for unavailable MCP servers (S7), and the
`mcp.json` template is already correct (#119 fixed module names).

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Add mcp[cli] dependency to mcp-knowledge and mcp-project pyproject.toml" --priority needed --status ideation --tags "phase-1,scope:mcp,type:build" --body "## Objective\nEnsure both packages declare mcp[cli]>=1.26 as a dependency.\n\n## Acceptance Criteria\n- [ ] packages/mcp-knowledge/pyproject.toml lists mcp[cli]>=1.26 in dependencies\n- [ ] packages/mcp-project/pyproject.toml lists mcp[cli]>=1.26 in dependencies\n\n## Context\nIdentified during #120 research (docs/research/mcp-entry-points-overlap.md). Neither #54 nor #17 explicitly include this requirement. Trivial change but blocks server startup."
```
