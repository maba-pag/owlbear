# Multi-Project Session Management — Track Concurrent Projects

> **Owning task:** #300 — Multi-project session management — track concurrent projects
> **Date:** 2026-03-01
> **Status:** Complete

## 1. Context and Question

OwlBear sessions are currently flat JSONL files with no project association. The daemon starts with a single `workspace_root` and constructs one `SessionStore`, one `ContextManager`, and one knowledge scope. When OwlBear manages multiple projects concurrently, it needs:

1. A **project model** linking name, workspace path, and metadata.
2. A **project store** for CRUD persistence.
3. **Session–project binding** so conversation history is per-project.
4. **Context isolation** — each project loads its own `context.md` and `MEMORY.md`.
5. **Knowledge scoping** — knowledge graph queries filter by project scope.
6. **CLI commands** to create, list, switch, and archive projects.
7. **Runtime switching** — the agent can change project context mid-conversation.

**Key existing integration points:**

- `SessionStore` (JSONL at `config_dir/sessions/{name}.jsonl`) — no project_id field.
- `ContextManager` — reads `context.md` + `MEMORY.md` from a single `workspace_root`.
- Knowledge graph models already have `scope: str = "global"` fields (Entity, Edge, Document).
- `KanbanToolset` takes `kanban_dir` param — already supports per-directory boards.
- `bootstrap()` takes `workspace_root` and wires everything to one workspace.

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| Devika ProjectManager | github.com/stitionai/devika/blob/main/src/project.py | .90 | SQLite-backed `Projects` model with per-project conversation stacks. `create_project`, `delete_project`, `get_project_list`, `add_message_to_project`, `get_project_path`. Project name → slugified directory. Simple, proven at 18k stars. |
| Devika AgentState | github.com/stitionai/devika/blob/main/src/state.py | .85 | Per-project agent state tracking in SQLite. State keyed by `project: str`. Tracks internal monologue, terminal/browser sessions, token usage, active/completed flags. Shows that project-keyed state management is a solved pattern. |
| Nanobot SessionManager | github.com/HKUDS/nanobot/blob/main/nanobot/session/manager.py | .85 | JSONL sessions keyed by `channel:chat_id`. Workspace-scoped: `SessionManager(workspace)` stores sessions in `workspace/sessions/`. Consolidation writes to `MEMORY.md`/`HISTORY.md`. Cache-friendly append-only design. |
| Nanobot ContextBuilder | github.com/HKUDS/nanobot/blob/main/nanobot/agent/context.py | .80 | Workspace-aware context: loads bootstrap files from workspace dir, memory from `workspace/memory/MEMORY.md`. Shows workspace-as-project-root pattern — switching workspace switches all context. |
| Mem0 memory scoping | github.com/mem0ai/mem0 | .75 | Multi-level memory via `user_id`, `agent_id`, `run_id` metadata. `search(query, user_id=...)` filters at query time. Confirmed: scope-as-filter-parameter is the standard pattern. |
| OwlBear knowledge-scoping-research | docs/knowledge-scoping-research.md | .95 | Column-based scope filtering with `scope: str` on all knowledge models. Format: `"global"`, `"project:{name}"`, `"agent:{name}"`. Already designed and partially implemented (schema v4 has scope columns). |

## 3. Analysis

### 3.1 Project Model — Storage Strategy

| Approach | Description | KISS | Resilience | Confidence |
|----------|-------------|------|------------|------------|
| **A. JSON files in config_dir/projects/** (.85) | One `{slug}.json` per project. CRUD via Pydantic model + file I/O. | **High** | Good (human-readable, git-friendly) | **.85** |
| B. SQLite table | `projects` table in knowledge.db or separate projects.db | Medium | Good (ACID) | .70 |
| C. TOML/YAML config section | Projects listed in owlbear.toml | Low (coupling) | Fragile (one parse error breaks all) | .40 |

**Verdict (.85):** JSON files in `config_dir/projects/`. Follows the file-per-entity pattern already used by kanban tasks and session JSONL. Devika uses SQLite but that's over-engineered for <100 projects. Nanobot uses the filesystem for sessions. File-per-project is simpler, debuggable, and avoids coupling to the knowledge DB.

### 3.2 Project Model Fields

| Field | Type | Required | Source |
|-------|------|----------|--------|
| `id` | `str` (slug) | Yes | Derived from name: `name.lower().replace(" ", "-")` |
| `name` | `str` | Yes | Human-readable display name |
| `workspace_path` | `Path` | Yes | Absolute path to project root |
| `created_at` | `datetime` | Yes | Auto-set on creation |
| `last_active` | `datetime` | Yes | Updated on every context switch or turn |
| `status` | `Literal["active", "archived"]` | Yes | Default: `"active"` |

Devika stores just `project: str` + `message_stack_json`. We need more metadata since OwlBear manages external workspaces (not internal project dirs). The `workspace_path` is the critical field — it determines where `context.md`, `MEMORY.md`, `kanban/`, and `.owlbear/` live.

### 3.3 ProjectStore Design

| Pattern | Description | LOC | Confidence |
|---------|-------------|-----|------------|
| **File-per-project with Pydantic** (.85) | `ProjectStore(config_dir / "projects")`. `create()` writes `{id}.json`. `get()` reads + validates. `list()` scans dir. `update()` rewrites. `archive()` sets status. | ~60 | **.85** |
| SQLModel + SQLite (.70) | Devika's pattern. More familiar but adds coupling. | ~80 | .70 |

**Winner:** File-per-project. Aligns with OwlBear's file-first approach (sessions are JSONL, kanban tasks are markdown, config is TOML).

### 3.4 Session–Project Binding

Currently `_build_chat_session()` creates sessions at `config_dir/sessions/{name}.jsonl`. Two options:

| Approach | Description | Migration | Confidence |
|----------|-------------|-----------|------------|
| **A. Project subdirectory** (.80) | Sessions at `config_dir/projects/{id}/sessions/{name}.jsonl`. Each project owns its sessions. | Old sessions stay in `config_dir/sessions/` (backward compat). | **.80** |
| B. project_id field in meta | Add `project_id` to `.meta` JSON. Sessions stay flat. | Zero migration, filter by meta. | .65 |

**Verdict (.80):** Subdirectory approach (A). Physical isolation is simpler than metadata filtering. Nanobot uses `workspace/sessions/` — workspace-scoped sessions. We scope by project. When you `switch` projects, the `SessionStore` path changes.

### 3.5 Context Isolation

`ContextManager(root)` already reads from `root / "context.md"` and `root / "MEMORY.md"`. Switching projects means:

```python
# Current: one workspace
context = ContextManager(workspace_root)

# Proposed: project-aware
context = ContextManager(project.workspace_path)  # Just change the root
```

No changes to `ContextManager` itself — the caller passes a different root. Same for `MemoryConsolidator(workspace_root)`. This is the nanobot pattern: workspace = project root.

### 3.6 Knowledge Graph Scoping

Already designed (docs/knowledge-scoping-research.md §4). Knowledge models have `scope: str = "global"`. For multi-project:

- Ingest with `scope="project:{id}"`.
- Query with `scopes=["global", "project:{current_id}"]`.
- No additional design needed — the scoping research already covers this use case.

### 3.7 Kanban Board Scoping

`KanbanToolset(kanban_dir=workspace / "kanban")` already accepts a directory parameter. For multi-project:

```python
# Switch kanban board by changing kanban_dir
kanban = KanbanToolset(kanban_dir=project.workspace_path / "kanban")
```

The kanban-md binary supports `--dir` for pointing to different boards. No tool changes needed — just pass the right directory at construction time.

### 3.8 Context Switching — Runtime Design

| Approach | Description | Complexity | Confidence |
|----------|-------------|------------|------------|
| **A. Rebuild agent on switch** (.75) | `switch_project()` calls a mini-bootstrap: new SessionStore, ContextManager, KanbanToolset, knowledge scope. Agent's `session` and inner instructions are updated. | Medium (~40 LOC) | **.75** |
| B. Full re-bootstrap (.55) | Tear down everything, call `bootstrap()` with new workspace_root. | Low code but slow (re-creates model, hooks, all toolsets). | .55 |
| C. Hot-swap individual components (.60) | Replace only session + context on the agent. Toolsets keep pointing to old workspace. | Fragile — toolset workspace mismatch. | .60 |

**Verdict (.75):** Approach A. Rebuild the workspace-dependent components (session, context, kanban dir, knowledge scope) without tearing down the model, hooks, or channel. `OwlBearAgent.session` is already a public attribute that `_chat_async` overrides. Add a `switch_project()` method that:

1. Saves current session.
2. Updates `last_active` on current project.
3. Loads new project's session, context, knowledge scope.
4. Updates agent's `session` and inner agent's `instructions`.

### 3.9 CLI Commands

Following Devika's `ProjectManager.create_project` / `get_project_list` pattern, translated to Typer:

| Command | Description | Args |
|---------|-------------|------|
| `bearclaw project create` | Create a new project | `--name`, `--workspace` (default: CWD) |
| `bearclaw project list` | List all projects with last-active | (none) |
| `bearclaw project switch` | Set active project for next chat/run | `name` positional |
| `bearclaw project archive` | Mark project as archived | `name` positional |

### 3.10 Mid-Conversation Switching (Agent Tool)

The AC requires "Agent can switch projects mid-conversation via tool." This is a `switch_project` tool exposed via a `ProjectToolset`:

```python
async def switch_project(self, project_name: str) -> str:
    """Switch the active project context."""
    project = self._store.get_by_name(project_name)
    # Rebuild workspace-dependent components
    self._agent.session = SessionStore(project_session_path)
    # Update instructions with new context.md + MEMORY.md
    ...
    return f"Switched to project: {project.name}"
```

**Risk:** Mid-conversation switching means the message history changes. The LLM loses prior context. **Mitigation:** Include a brief "You are now working on project X" system message with project summary after switching.

## 4. Recommendation (.80 confidence)

**File-based ProjectStore with workspace-scoped isolation.**

### Design summary

1. **`Project` Pydantic model** — `id`, `name`, `workspace_path`, `created_at`, `last_active`, `status`. Frozen model stored as JSON.

2. **`ProjectStore`** — CRUD over `config_dir/projects/*.json`. Methods: `create()`, `get()`, `list_active()`, `update()`, `archive()`, `get_by_name()`.

3. **Session binding** — Sessions live in `config_dir/projects/{id}/sessions/`. Each project has isolated conversation histories.

4. **Context isolation** — `ContextManager(project.workspace_path)` loads project-specific `context.md` + `MEMORY.md`. No changes to ContextManager.

5. **Knowledge scoping** — Use existing `scope="project:{id}"` pattern from knowledge-scoping-research.

6. **Kanban scoping** — `KanbanToolset(kanban_dir=project.workspace_path / "kanban")`.

7. **CLI commands** — `bearclaw project create|list|switch|archive` via Typer subcommand group.

8. **Agent tool** — `ProjectToolset.switch_project()` for mid-conversation switching.

9. **Bootstrap change** — `bootstrap()` gains optional `project: Project` parameter. When set, workspace-dependent components use `project.workspace_path` instead of `workspace_root`.

### File placement

| File | Purpose | LOC est. |
|------|---------|----------|
| `src/owlbear/projects/models.py` | `Project` Pydantic model | ~30 |
| `src/owlbear/projects/store.py` | `ProjectStore` CRUD | ~80 |
| `src/owlbear/projects/__init__.py` | Package init | ~5 |
| `src/owlbear/tools/project.py` | `ProjectToolset` (switch_project tool) | ~60 |
| `src/bearclaw/cli.py` | `project` subcommand group | ~80 |
| `tests/test_project_store.py` | ProjectStore CRUD tests | ~100 |
| `tests/test_project_session.py` | Session–project binding tests | ~60 |

**Total:** ~415 LOC across 7 files.

### Risks and mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Mid-conversation switch loses context | Medium | Inject project summary system message after switch |
| Toolsets still point to old workspace after switch | Medium | Rebuild workspace-dependent toolsets (FileToolset, TerminalToolset, KanbanToolset) on switch |
| Stale `last_active` if daemon crashes | Low | Update `last_active` on every turn, not just on switch |
| Many projects → slow `list()` | Low | JSON files are small; 100 projects = negligible overhead |

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Project Pydantic model (id, name, workspace_path, status)" --priority needed --tags "phase-12,memory,daemon" --body "## Acceptance Criteria\n- [ ] Create src/owlbear/projects/__init__.py and src/owlbear/projects/models.py\n- [ ] Project model: id (slug), name, workspace_path, created_at, last_active, status (active/archived)\n- [ ] Frozen Pydantic model with JSON serialization\n- [ ] id auto-derived from name (slugify)\n- [ ] Unit tests: valid model, slug generation, status default, JSON round-trip\n\nSee docs/multi-project-session-research.md §3.2"

kanban\kanban-md.exe create "ProjectStore — CRUD for project persistence" --priority needed --tags "phase-12,memory,daemon" --body "## Acceptance Criteria\n- [ ] Create src/owlbear/projects/store.py\n- [ ] ProjectStore(config_dir / 'projects'): create, get, get_by_name, list_active, update, archive\n- [ ] One JSON file per project: config_dir/projects/{id}.json\n- [ ] Archive sets status='archived', does not delete file\n- [ ] get_by_name searches all projects by display name\n- [ ] Unit tests: CRUD cycle, archive, list_active excludes archived, duplicate name prevention\n\nSee docs/multi-project-session-research.md §3.3" --depends-on 300

kanban\kanban-md.exe create "bearclaw project CLI commands (create/list/switch/archive)" --priority needed --tags "phase-12,cli,daemon" --body "## Acceptance Criteria\n- [ ] Add 'project' Typer subcommand group to bearclaw CLI\n- [ ] bearclaw project create --name NAME --workspace PATH (default: CWD)\n- [ ] bearclaw project list — shows name, workspace, last_active, status\n- [ ] bearclaw project switch NAME — writes active project to config_dir/active_project\n- [ ] bearclaw project archive NAME — sets status to archived\n- [ ] bearclaw chat --project NAME starts chat with project context\n- [ ] Unit tests for each subcommand\n\nSee docs/multi-project-session-research.md §3.9" --depends-on 300

kanban\kanban-md.exe create "Session–project binding — per-project session directories" --priority needed --tags "phase-12,memory,daemon" --body "## Acceptance Criteria\n- [ ] Sessions stored at config_dir/projects/{id}/sessions/{name}.jsonl\n- [ ] _build_chat_session respects active project when building session path\n- [ ] Backward compat: existing sessions at config_dir/sessions/ still work (no project = legacy)\n- [ ] bearclaw chat --session NAME uses project-scoped session dir\n- [ ] Unit tests: session creation in project dir, session isolation between projects\n\nSee docs/multi-project-session-research.md §3.4" --depends-on 300

kanban\kanban-md.exe create "ProjectToolset — switch_project agent tool for mid-conversation switching" --priority important --tags "phase-12,memory,daemon,agent" --body "## Acceptance Criteria\n- [ ] Create src/owlbear/tools/project.py with ProjectToolset (FunctionToolset)\n- [ ] switch_project(project_name) tool: loads project, rebuilds session/context, returns confirmation\n- [ ] Injects project summary into agent instructions after switch\n- [ ] list_projects() tool: returns active projects with last_active\n- [ ] Unit tests: switch updates session path, switch to nonexistent project returns error\n\nSee docs/multi-project-session-research.md §3.10" --depends-on 300

kanban\kanban-md.exe create "Bootstrap project-awareness — workspace_root from active project" --priority important --tags "phase-12,memory,daemon" --body "## Acceptance Criteria\n- [ ] bootstrap() reads active_project from config_dir/active_project\n- [ ] When active project exists, workspace_root = project.workspace_path\n- [ ] ContextManager, SessionStore, KanbanToolset, FileToolset all receive project workspace\n- [ ] Knowledge queries include scope 'project:{id}' in addition to 'global'\n- [ ] Fallback: no active project = current behavior (CWD as workspace)\n- [ ] Integration test: bootstrap with project vs without project\n\nSee docs/multi-project-session-research.md §3.8, §4" --depends-on 300
```

## 6. Attribution

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Devika ProjectManager | github.com/stitionai/devika/blob/main/src/project.py | Per-project conversation storage, project list/create/delete CRUD pattern, project-to-directory mapping | docs/multi-project-session-research.md (§3.1–3.3 design), future src/owlbear/projects/ | 2026-03-01 |
| Devika AgentState | github.com/stitionai/devika/blob/main/src/state.py | Project-keyed state management pattern, per-project token tracking | docs/multi-project-session-research.md (§3.8 switching design) | 2026-03-01 |
| Nanobot SessionManager | github.com/HKUDS/nanobot/blob/main/nanobot/session/manager.py | Workspace-scoped JSONL sessions, session key format, cache + persist pattern | docs/multi-project-session-research.md (§3.4 session binding) | 2026-03-01 |
| Nanobot ContextBuilder | github.com/HKUDS/nanobot/blob/main/nanobot/agent/context.py | Workspace-as-project-root, bootstrap files from workspace, memory from workspace dir | docs/multi-project-session-research.md (§3.5 context isolation) | 2026-03-01 |
| Mem0 memory scoping | github.com/mem0ai/mem0 | Multi-level memory with user_id/agent_id filter parameters at query time | docs/multi-project-session-research.md (§3.6 knowledge scoping) | 2026-03-01 |
