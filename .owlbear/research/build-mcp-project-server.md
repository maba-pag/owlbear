# Build mcp-project Server — Research

> **Owning task:** #17 — Build mcp-project server
> **Date:** 2026-03-28 **Status:** Complete

## 1. Context and Question

Task #17 requires a full MCP server in `packages/mcp-project/` exposing project
metadata to agents: 2 tools (`project_info`, `project_list`), 2 resources
(`project://readme`, `project://structure`), owlbear-project.json consumption,
stdio transport, VS Code registration, and a SKILL.md.

The package scaffold exists (pyproject.toml, `__init__.py`). RED-phase tests
for the Pydantic model exist in `test_models.py` (#74). This research validates
the full 10-item AC and maps implementation approaches.

## 2. Sources Studied

| # | Source | URL | Rel. |
|---|--------|-----|------|
| 1 | MCP Python SDK v1 README | github.com/modelcontextprotocol/python-sdk | .95 |
| 2 | MCP Resources Spec (2025-06-18) | modelcontextprotocol.io/specification/2025-06-18/server/resources | .90 |
| 3 | OwlBear MCP SDK deep-dive | docs/research/mcp-python-sdk.md | .95 |
| 4 | Scaffold mcp-project research | docs/research/scaffold-mcp-project-server.md | .90 |
| 5 | owlbear-project.json schema | docs/research/owlbear-project-json-schema.md | .95 |
| 6 | v1 ProjectStore/toolset | v1/src/owlbear/projects/ | .85 |
| 7 | Build mcp-kanban research | docs/research/build-mcp-kanban-server.md | .85 |
| 8 | VS Code MCP Config Reference | code.visualstudio.com/docs/copilot/reference/mcp-configuration | .90 |

## 3. Analysis

### 3a. AC Feasibility Matrix

| # | AC Item | Feasible | Pattern | Risk |
|---|---------|----------|---------|------|
| 1 | MCP server in packages/mcp-project/ | Yes | FastMCP v1, scaffold exists | None |
| 2 | project_info tool | Yes | Read owlbear-project.json, return structured data | None |
| 3 | project_list tool | Yes | Scan registry dir for project JSON files | Low — needs registry design |
| 4 | project://readme resource | Yes | `@mcp.resource()`, read README.md from CWD | None |
| 5 | project://structure resource | Yes | `@mcp.resource()`, `os.walk` with depth limit | None |
| 6 | Read owlbear-project.json | Yes | OwlbearProjectFile Pydantic model (#68/#74) | Blocked on #68 impl |
| 7 | JSON schema | Yes | Already specified in #53, model in #74 | None |
| 8 | stdio transport | Yes | `mcp.run()` default | None |
| 9 | .vscode/mcp.json registration | Yes | stdio config with `uv run` | None |
| 10 | SKILL.md | Yes | Documentation deliverable | None |

### 3b. Tool Design: project_info

Returns project metadata from `owlbear-project.json` in CWD. VS Code spawns the
server in the workspace folder, so `Path("owlbear-project.json")` resolves correctly.

| Field | Source | Type |
|-------|--------|------|
| name | owlbear-project.json | str |
| type | owlbear-project.json | str (enum) |
| owlbear_path | owlbear-project.json | str (relative path) |
| project_path | CWD (runtime) | str (absolute path) |
| created_at | owlbear-project.json | str (ISO 8601) |

Returns structured dict. If `owlbear-project.json` missing, returns error message.

### 3c. Tool Design: project_list

**Design question:** How to discover all projects using this owlbear installation?

| Approach | Pros | Cons | KISS |
|----------|------|------|------|
| A: Central registry dir | Fast lookup, v1 pattern proven | Requires registration step | .85 |
| B: Filesystem scan | No registration needed | Slow, unbounded scope | .40 |
| C: Config file list | Simple, explicit | Manual maintenance | .70 |

**Recommendation (.85):** Option A — central registry modeled on v1 `ProjectStore`.
Each project registers as `{owlbear_dir}/data/projects/{slug}.json` during setup.
The `project_list` tool reads all JSON files from that directory. The v1
`ProjectStore` (Source 6) validates this pattern with `list_active()` and
`list_all()` methods. The setup script (#12) handles registration.

### 3d. Resource Design: project://readme

```python
@mcp.resource("project://readme")
def project_readme() -> str:
    path = Path("README.md")
    if not path.exists():
        return "No README.md found in project root."
    return path.read_text(encoding="utf-8")
```

Custom URI scheme `project://` is valid per MCP spec §6.4 (Source 2). Returns
`text/markdown` content. Read-only, no side effects — fits MCP resource model.

### 3e. Resource Design: project://structure

Returns a directory tree summary. Depth-limited walk to avoid huge output.

| Approach | Max depth | Excludes | KISS |
|----------|-----------|----------|------|
| `os.walk` with depth filter | 3 levels | `.git`, `node_modules`, `__pycache__`, `.venv` | .85 |
| `tree` subprocess | System-dependent | Requires tree binary | .50 |
| Custom walker using `pathlib` | Configurable | Configurable patterns | .90 |

**Recommendation (.85):** Use `pathlib.Path.iterdir()` with recursive depth limit
(default 3). Exclude hidden dirs and common noise (`.git`, `__pycache__`,
`node_modules`, `.venv`, `.mypy_cache`). Output as indented text tree. This is
~30 LOC, no external deps, KISS-aligned.

### 3f. Lifespan and AppContext

```python
@dataclass(slots=True)
class AppContext:
    project_file: OwlbearProjectFile | None
    project_root: Path
    owlbear_root: Path


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    project_root = Path.cwd()
    owlbear_root = Path(os.environ.get("OWLBEAR_ROOT", ".."))
    project_path = project_root / "owlbear-project.json"
    project_file = None
    if project_path.exists():
        project_file = OwlbearProjectFile.model_validate_json(project_path.read_text(encoding="utf-8"))
    yield AppContext(
        project_file=project_file,
        project_root=project_root,
        owlbear_root=owlbear_root,
    )
```

Load once at startup. If the file is missing, `project_file` is `None` and
tools return a clear error. No cleanup needed (no connections to close).

### 3g. Package Structure

```
packages/mcp-project/
├── pyproject.toml          # exists — add mcp[cli] dep
├── src/owlbear_mcp_project/
│   ├── __init__.py         # exists
│   ├── __main__.py         # entry point: python -m owlbear_mcp_project
│   ├── models.py           # OwlbearProjectFile (task #68)
│   ├── server.py           # FastMCP instance + lifespan + tools + resources
│   └── tree.py             # Directory tree helper (~30 LOC)
├── tests/
│   ├── test_models.py      # exists (RED phase from #74)
│   └── test_server.py      # tool/resource unit tests
└── SKILL.md                # agent usage documentation
```

### 3h. Dependencies

```toml
dependencies = ["pydantic>=2.10.0", "mcp[cli]>=1.26"]
```

`pydantic` already listed. Add `mcp[cli]` for FastMCP. No other deps needed.

### 3i. VS Code Registration

```json
{
  "owlbearProject": {
    "type": "stdio",
    "command": "uv",
    "args": ["run", "--directory", "${workspaceFolder}/../owlbear",
             "python", "-m", "owlbear_mcp_project"],
    "dev": { "watch": "packages/mcp-project/**/*.py" }
  }
}
```

### 3j. Testing Strategy

| Layer | What | How |
|-------|------|-----|
| Unit | project_info with mock file | Temp owlbear-project.json, call tool fn |
| Unit | project_list with mock registry | Temp dir with project JSONs |
| Unit | project://readme resource | Temp README.md, call resource fn |
| Unit | project://structure resource | Temp dir tree, verify output format |
| Unit | Missing file edge cases | No owlbear-project.json, no README |
| Integration | MCP protocol | `mcp.server.fastmcp.testing` if available |

### 3k. Prerequisite Status

| Dep | Task | Status | Impact |
|-----|------|--------|--------|
| MCP SDK research | #2 | Archived | Ready |
| Monorepo skeleton | #7 | Archived | Ready |
| Pydantic model | #68 | Backlog | Builder needs to implement before #17 |
| Test RED phase | #74 | Done | Tests exist, waiting for #68 |

## 4. Recommendation (.85 confidence)

Implement `packages/mcp-project/` using FastMCP v1 with:
- **2 tools:** `project_info` (reads local `owlbear-project.json`) and
  `project_list` (reads registry dir at `{owlbear_root}/data/projects/`)
- **2 resources:** `project://readme` and `project://structure` (depth-limited tree)
- **Lifespan** loads project file once; `AppContext` with `project_file`,
  `project_root`, `owlbear_root`
- **stdio transport** via `mcp.run()`
- **Entry point** `__main__.py` for `python -m owlbear_mcp_project`
- **SKILL.md** documenting tool/resource usage for agents

Risk: `project_list` depends on a registry directory populated by the setup
script (#12). If the registry doesn't exist yet, the tool returns an empty list.
This is acceptable — the setup script creates the registry entries.

**Dependency:** #68 (Pydantic model) must be implemented before #17's builder
can use `OwlbearProjectFile` in `server.py`. The RED tests (#74) are ready.

## 5. Follow-up Tasks

Task #17 itself is the primary implementation target. The decomposition into
test-writer/builder subtasks happens via the architect gate, not here.

No new tasks needed — the prerequisite chain (#68 model, #74 tests) already
exists on the board.
