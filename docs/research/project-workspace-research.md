# Project Workspace Management — Research

> **Owning task:** #303 — Project workspace management — create and manage project repos
> **Date:** 2026-03-01
> **Status:** Complete

## 1. Context and Question

Task #303 proposes a `ProjectWorkspace` class that scaffolds new project
directories (git init, templates, kanban board) and a CLI/tool surface for
agents to create projects. The **key question**: how much of the AC is already
covered by existing `ProjectStore`, `ProjectToolset`, and `bearclaw project`
commands?

### Gap analysis

| AC item | Already exists? | What's missing |
|---------|----------------|----------------|
| `ProjectWorkspace.create_project(name, template) → Path` | No | Entirely new — scaffolds filesystem |
| Templates: python-uv, python-pip, node, bare | No | Template definitions + rendering |
| Git repo init with .gitignore, README, structure | No | `git init` + file creation |
| Kanban board init via kanban-md | No | Shell out to `kanban-md init` |
| Configurable project root dir (default: ~/projects/) | No | `project_root` config field |
| `bearclaw project new <name> --template <t>` | Partial | `project create` exists but only writes JSON metadata — no scaffolding |
| Agent tool `workspace_create_project` | No | New tool on `ProjectToolset` |
| Workspace switching: CWD + context + session | Partial | `switch_project` updates session path but not CWD or context reload |
| Unit tests | Partial | Tests exist for store/toolset, none for scaffolding |

**Verdict:** ~70% of the AC is new work. The existing `ProjectStore.create()`
registers metadata only. The core gap is **filesystem scaffolding** (git init,
templates, kanban init) and a config field for the project root directory.

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| cookiecutter | <https://github.com/cookiecutter/cookiecutter> | .70 | Jinja2 templates from repos, `cookiecutter.json` config |
| copier | <https://github.com/copier-org/copier> | .75 | Template lifecycle (scaffold + update), `copier.yml` questions |
| kanban-md init | <https://github.com/antopolskiy/kanban-md> | .90 | `kanban-md init --name NAME --statuses s1,s2` creates `kanban/` dir |
| OwlBear ProjectStore | (codebase) `src/owlbear/projects/store.py` | 1.0 | JSON-based CRUD, `create()` takes name + path |
| OwlBear ProjectToolset | (codebase) `src/owlbear/projects/toolset.py` | 1.0 | `switch_project`, `list_projects` FunctionToolset |
| OwlBear GitLocalToolset | (codebase) `src/owlbear/tools/git_local.py` | .80 | Subprocess git wrapper — has status/diff/add/commit/push but no `init` |

## 3. Analysis

### 3.1 Template system design

| Approach | Complexity | Dependencies | KISS score | Recommendation |
|----------|-----------|--------------|-----------|----------------|
| cookiecutter/copier dependency | High | +12 packages | Low | Overkill — YAGNI |
| Jinja2 templates in `data/templates/` | Medium | jinja2 (already in deps) | Medium | Unnecessary for 4 fixed templates |
| **Hardcoded Python functions** | Low | None | **High** | Each template is a function writing files directly |
| Template registry (plugin-based) | High | None | Low | Over-engineered for 4 templates |

**Recommendation (.85 confidence):** Hardcoded template functions. Each template
is a `_scaffold_bare()`, `_scaffold_python_uv()`, etc. function that creates
directories and writes files. No template engine needed — the files are static
with only the project name interpolated. This is ~50–100 LOC per template. When
a fifth template is needed, refactor to a registry pattern (third repetition
rule).

### 3.2 Architecture placement

```
src/owlbear/projects/
    __init__.py
    models.py           # existing — Project model
    store.py            # existing — JSON CRUD
    toolset.py          # existing — agent tools (extend with create_project)
    workspace.py        # NEW — ProjectWorkspace class
```

`ProjectWorkspace` is a pure orchestrator:

1. Resolve target directory from config `project_root` + slugified name
2. Create directory, run scaffold function for chosen template
3. `git init` + initial commit
4. `kanban-md init` (subprocess)
5. Register in `ProjectStore`
6. Return the `Path`

### 3.3 Template contents

| Template | Creates | Notes |
|----------|---------|-------|
| `bare` | `.gitignore`, `README.md`, `kanban/` | Minimal — just git + kanban |
| `python-uv` | Above + `pyproject.toml` (uv-style), `src/{slug}/`, `tests/`, `.python-version` | Mirrors OwlBear's own structure |
| `python-pip` | Above + `pyproject.toml` (pip-style), `src/{slug}/`, `tests/`, `requirements.txt` | Traditional Python layout |
| `node` | Above + `package.json`, `src/`, `tsconfig.json` | Bare Node/TS scaffold |

All templates share: `.gitignore`, `README.md`, `kanban/` (via kanban-md init).

### 3.4 Git init feasibility

`gitpython` would add a dependency; `subprocess.run(["git", "init"])` is
trivial and consistent with `GitLocalToolset`'s approach (asyncio subprocess).
Since `ProjectWorkspace.create_project()` is called once per project (not in a
hot path), synchronous `subprocess.run` is fine — no need for async.

### 3.5 kanban-md init feasibility

`kanban-md init --name "Project Name"` creates `kanban/config.yml` + `kanban/tasks/`.
We need to pass `--dir {project_path}/kanban`. Confirmed via `--help` output:
`--dir` flag points to the kanban directory. The OwlBear-specific config
(custom statuses, priorities) can be written as a post-init step by
overwriting `config.yml` with our standard board config.

### 3.6 Config field for project root

Add `project_root: Path = Path.home() / "projects"` to `OwlBearSettings`.
The CLI `bearclaw project new` derives the workspace path as
`settings.project_root / slugify(name)`.

### 3.7 Workspace switching gap

Current `switch_project` tool:

- Updates session path ✓
- Updates `last_active` timestamp ✓
- Does NOT change CWD ✗
- Does NOT reload `ContextManager` ✗

CWD change in a daemon is meaningful only for subprocess calls. The fix is to
update `ContextManager.workspace_root` and any toolsets that hold a
`workspace_root` reference. This is a separate task from scaffolding.

## 4. Recommendation (.85 confidence)

**Build a thin `ProjectWorkspace` class** in `src/owlbear/projects/workspace.py`
with hardcoded template functions, subprocess git/kanban-md calls, and
`ProjectStore` integration. Add `project_root` to config. Extend
`ProjectToolset` with `create_project` tool. Add `bearclaw project new` CLI
command. Defer workspace-switching improvements to a separate task.

**Risks:**

- `kanban-md.exe` binary must exist at a known path (mitigate: config field or PATH lookup)
- `git` must be on PATH (reasonable assumption for a dev tool)
- Template drift if OwlBear conventions change (mitigate: templates are ~20 lines each, easy to update)

## 5. Follow-up Tasks

See kanban commands below. Split into 5 tasks:

1. **Config + ProjectWorkspace core** — `project_root` field, `ProjectWorkspace` class with `bare` template
2. **Templates** — python-uv, python-pip, node template functions
3. **CLI command** — `bearclaw project new`
4. **Agent tool** — `workspace_create_project` on `ProjectToolset`
5. **Workspace switching improvements** — CWD, context reload (separate concern)
