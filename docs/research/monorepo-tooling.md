# uv Workspace Monorepo Tooling

> **Owning task:** #6 — Monorepo tooling research
> **Date:** 2026-03-26 **Status:** Complete

## 1. Context and Question

OwlBear v2 needs a multi-package Python monorepo with 5 packages under `packages/`
(orchestrator, knowledge, mcp-kanban, mcp-knowledge, mcp-project). The question:
how should uv workspaces be configured so packages can cross-import, share a
lock file, and MCP servers can run as standalone processes?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| uv workspaces docs | https://docs.astral.sh/uv/concepts/projects/workspaces/ | 1.0 |
| uv dependency management docs | https://docs.astral.sh/uv/concepts/projects/dependencies/ | .95 |
| uv project config docs | https://docs.astral.sh/uv/concepts/projects/config/ | .90 |
| uv project init docs | https://docs.astral.sh/uv/concepts/projects/init/ | .85 |
| pydantic-ai monorepo | https://github.com/pydantic/pydantic-ai | .90 |
| MCP Python SDK monorepo | https://github.com/modelcontextprotocol/python-sdk | .85 |
| pydantic/logfire monorepo | https://github.com/pydantic/logfire | .80 |

## 3. Analysis

### 3.1 Workspace Configuration

Root `pyproject.toml` needs `[tool.uv.workspace]` with a `members` glob. Each member
has its own `pyproject.toml`. A single `uv.lock` file lives at the workspace root.

All three prior-art repos (pydantic-ai, MCP SDK, logfire) confirm this pattern.
The `members = ["packages/*"]` glob covers OwlBear's planned layout exactly.

### 3.2 Editable Installs

Workspace member dependencies are **always editable** — confirmed by uv docs:
> "Dependencies between workspace members are editable."

No `--editable` flag needed. Declare `{ workspace = true }` in `tool.uv.sources`
and the member is installed as editable automatically. pydantic-ai and MCP SDK
both use this pattern.

Practical validation evidence is recorded in section 3.8.

### 3.3 Shared Dependency Resolution

Single `uv.lock` at workspace root. All members share one virtual environment.
uv enforces a single `requires-python` (intersection of all members). For
OwlBear v2 with `>=3.12` everywhere, this is a non-issue.

**Risk:** uv cannot guarantee a package only uses its own declared dependencies
(Python has no module isolation). Documented in uv docs as a known limitation.
Mitigation: CI can run `uv build --no-sources` per package to verify published
dependency declarations.

Practical validation evidence is recorded in section 3.8.

### 3.4 Dev Dependency Isolation

| Approach | Scope | Prior Art |
|----------|-------|-----------|
| `[dependency-groups]` in root | Shared dev deps (pytest, ruff, etc.) | pydantic-ai, MCP SDK |
| `[dependency-groups]` in member | Package-specific dev deps | Supported but rarely needed |
| `--group`/`--only-group` flags | Selective install at sync time | uv docs |

Recommendation (.90): Place shared dev deps (pytest, ruff, coverage) in root
`[dependency-groups].dev`. Package-specific test fixtures stay in the package's
own group only if needed. Start simple; split later per YAGNI.

### 3.5 Build Backend

| Criterion | uv_build (.85) | hatchling (.80) |
|-----------|----------------|-----------------|
| Deps | 0 (bundled with uv) | 1 (hatchling) |
| Maturity | New (v0.11.1, 2026) | Stable (2+ years) |
| Ecosystem | uv default for new projects | Used by pydantic-ai, MCP SDK, logfire |
| src layout | Yes | Yes |
| Footprint | ~0 MB (part of uv) | ~5 MB |
| KISS | Higher (no extra dep) | Slightly lower |

Recommendation (.85): Use `uv_build` (>=0.11.1,<0.12). It's the uv default for
new `--package` projects, zero extra dependencies, and handles src-layout
packages. If a package later needs hatchling features (dynamic metadata, custom
hooks), it can switch independently — build backends are per-package.

### 3.6 MCP Servers as Standalone Processes

MCP servers need `project.scripts` entries so they can be invoked standalone.
The `uv run --package <name>` command runs a command in the context of a
specific workspace member. Example:

```toml
# packages/mcp-kanban/pyproject.toml
[project.scripts]
owlbear-mcp-kanban = "owlbear_mcp_kanban:main"
```

Then: `uv run --package owlbear-mcp-kanban owlbear-mcp-kanban` or just
`uv run owlbear-mcp-kanban` from the package directory. MCP SDK uses this
exact pattern for its example servers. Validated by both uv docs and MCP SDK.

Practical validation evidence is recorded in section 3.8.

### 3.7 Cross-Package Imports

packages/knowledge/ can be imported by mcp-knowledge by declaring it as a
workspace dependency:

```toml
# packages/mcp-knowledge/pyproject.toml
[project]
dependencies = ["owlbear-knowledge"]

[tool.uv.sources]
owlbear-knowledge = { workspace = true }
```

This pattern is confirmed by pydantic-ai (pydantic-ai depends on pydantic-ai-slim)
and verified in uv workspace docs ("workspace = true" source type).

Practical validation evidence is recorded in section 3.8.

### 3.8 Practical Validation (Local Prototype)

To satisfy AC lines that require real validation (not only prior-art analysis),
I created a disposable prototype workspace at
`docs/scratch/6-uv-workspace-validation/` with three minimal packages:

- `owlbear-knowledge`
- `owlbear-mcp-knowledge` (depends on `owlbear-knowledge` via `{ workspace = true }`)
- `owlbear-mcp-kanban` (standalone script target)

All checks were run on 2026-03-27 from that workspace root.

| Validation Target | Command | Result | Evidence |
|-------------------|---------|--------|----------|
| Shared lock file | `uv lock` | Pass | `Resolved 10 packages`; root `uv.lock` created |
| Shared dependency sync | `uv sync --all-extras` | Pass | Sync completed with lock satisfaction and package install |
| Single lock location | PowerShell check for `uv.lock` files | Pass | Root `uv.lock` exists; package-level `uv.lock` count = `0` |
| Editable member install | `uv run --package owlbear-mcp-knowledge python -c "import inspect, owlbear_knowledge as k; print(k.identity('editable-ok')); print(inspect.getfile(k))"` | Pass | Output: `editable-ok`; module path points to `packages/knowledge/src/owlbear_knowledge/__init__.py` |
| Cross-package import | `uv run --package owlbear-mcp-knowledge python -c "from owlbear_mcp_knowledge import probe; print(probe())"` | Pass | Output: `ok` |
| MCP standalone process (knowledge) | `uv run --package owlbear-mcp-knowledge owlbear-mcp-knowledge` | Pass | Output: `ok` |
| MCP standalone process (kanban) | `uv run --package owlbear-mcp-kanban owlbear-mcp-kanban` | Pass | Output: `kanban-standalone-ok` |

Conclusion: the four previously-failed AC checks are now validated by executable
workspace evidence in addition to documentation and prior-art research.

## 4. Recommendation (.90 confidence)

Use uv workspaces with `uv_build` backend and `packages/*` member glob.

**Proposed root pyproject.toml skeleton:**

```toml
[project]
name = "owlbear"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = []

[tool.uv.workspace]
members = ["packages/*"]

[tool.uv.sources]
owlbear-orchestrator = { workspace = true }
owlbear-knowledge = { workspace = true }
owlbear-mcp-kanban = { workspace = true }
owlbear-mcp-knowledge = { workspace = true }
owlbear-mcp-project = { workspace = true }

[dependency-groups]
dev = [
  "pytest>=8.0",
  "pytest-asyncio>=0.25.0",
  "pytest-cov>=6.0",
  "ruff>=0.9.0",
]

[build-system]
requires = ["uv_build>=0.11.1,<0.12"]
build-backend = "uv_build"
```

**Proposed package pyproject.toml (e.g. packages/knowledge/):**

```toml
[project]
name = "owlbear-knowledge"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["qdrant-client>=1.13"]

[build-system]
requires = ["uv_build>=0.11.1,<0.12"]
build-backend = "uv_build"
```

**Risks:**
- `uv_build` is new — if it has bugs, switching to hatchling per-package is trivial
- No module isolation across workspace members — rely on CI validation

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Create monorepo skeleton with uv workspace config" --priority needed --status ideation --tags phase-1,scope:build,type:build --body "## AC\n- Root pyproject.toml with [tool.uv.workspace] members = [\"packages/*\"]\n- 5 member packages under packages/ with stub pyproject.toml (uv_build backend)\n- uv sync succeeds\n- Cross-package import verified\n- MCP server entry points defined in project.scripts"
```

Note: Task #7 already covers this scope — no new task needed. Findings feed
directly into #7's implementation.
