# KanbanToolset — Task Execution Pipeline Research

> **Owning task:** #301 — Task execution pipeline — orchestrator drives kanban-based work
> **Date:** 2026-03-01
> **Status:** Complete

## 1. Context and Question

The orchestrator agent can delegate to specialists but has no programmatic interface to the kanban board. It cannot pick tasks, move them through statuses, or track dependencies. We need a `KanbanToolset(FunctionToolset)` that wraps `kanban-md` CLI commands as async tools, plus orchestrator system prompt updates to drive the full task lifecycle.

**Key decisions:**

1. Subprocess wrapper vs. direct task-file parsing?
2. Which commands to expose as tools?
3. How to format output for LLM consumption?
4. How to support both internal and external project boards?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| GitLocalToolset (internal) | `src/owlbear/tools/git_local.py` | .95 | Exact pattern: async subprocess wrapper, `_run_git` helper, hook emission, error-string returns |
| TerminalToolset (internal) | `src/owlbear/tools/terminal.py` | .85 | General subprocess execution with timeout, truncation, hook integration |
| kanban-md CLI v0.33.0 | `kanban/kanban-md.exe --help` | .95 | Full command reference: `--json`, `--compact`, `--dir`, `pick --claim` |
| OpenHands Runtime | `github.com/All-Hands-AI/OpenHands` | .70 | Action-execution pattern, subprocess dispatch, observation loop |
| SWE-agent | `github.com/SWE-agent/SWE-agent` | .65 | YAML-configured CLI tools, tool-equipped agent driving external processes |
| PydanticAI FunctionToolset | `pydantic_ai/toolsets/function.py` | .90 | `add_function()` API, `Tool` registration, timeout support |

## 3. Analysis

### 3.1 Subprocess Wrapper vs. Direct File Parsing

| Criterion | Subprocess CLI (.90) | Direct file parsing (.40) |
|-----------|---------------------|--------------------------|
| Complexity | Low — shell out to binary | High — re-implement YAML parsing, status validation, locking |
| Consistency | Uses kanban-md's own validation | Risk of divergence from CLI semantics |
| Atomicity | `pick --claim` is atomic | Must implement locking ourselves |
| Maintenance | Zero — binary upgrades just work | Must track kanban-md format changes |
| Performance | ~50ms per subprocess call | ~5ms file read |
| KISS | High | Low |
| Proven pattern | GitLocalToolset does this | No existing pattern in codebase |

**Verdict (.90):** Subprocess wrapper. The ~45ms overhead is negligible for LLM-driven workflows (LLM calls take seconds). Direct parsing violates KISS and YAGNI.

### 3.2 Commands to Expose

| Tool name | CLI command | Purpose | Output format |
|-----------|-------------|---------|---------------|
| `kanban_list` | `list --compact` | Overview of tasks by status/tag/priority | Compact text (token-efficient) |
| `kanban_show` | `show ID --json` | Full task details for analysis | JSON (structured) |
| `kanban_create` | `create TITLE --flags` | Create new tasks | Default text (confirmation) |
| `kanban_move` | `move ID STATUS` | Transition task status | Default text (confirmation) |
| `kanban_edit` | `edit ID --flags` | Modify fields, block/unblock, append notes | Default text (confirmation) |
| `kanban_pick` | `pick --claim AGENT` | Atomically claim next task | Default text (full task details) |
| `kanban_context` | `context` | Board summary for context injection | Markdown summary |

Seven tools. `board` and `metrics` are omitted (YAGNI — `kanban_list` and `kanban_context` cover the orchestrator's needs). Can be added later if needed.

### 3.3 Multi-Board Support

The `--dir` flag on every kanban-md command allows pointing to any kanban directory:

- **Internal board:** `KanbanToolset(kanban_dir=workspace / "kanban")`
- **External board:** `KanbanToolset(kanban_dir=Path("/other/project/kanban"))`

The orchestrator gets the internal board by default. For external projects, a second `KanbanToolset` instance with a different `--dir` can be registered.

### 3.4 Output Formatting for LLM Consumption

| Operation | Format | Rationale |
|-----------|--------|-----------|
| List | `--compact` | One line per task, ~20 tokens each, fits context window |
| Show | `--json` | Structured data, LLM can extract fields reliably |
| Create/Move/Edit | Default text | Confirmation messages are short, human-readable |
| Pick | Default (v0.33.0 prints full details) | Self-contained, no follow-up `show` needed |
| Context | Default markdown | Already LLM-optimized |

All commands get `--no-color` to avoid ANSI escape codes in LLM context.

### 3.5 Architecture Integration

**bootstrap.py `build_toolsets()`:** Add `KanbanToolset` as a standard (always-on) toolset, similar to `GitLocalToolset`. Wrapped in `HookedToolset`.

**Tool resolver mapping:** Current `build_agent_registry()` maps by `type(inner).__name__`, so the orchestrator definition would reference `KanbanToolset`. However, the existing orchestrator.md uses short names (`delegation`, `filesystem`, `ask_user`) which don't match class names — this is a pre-existing naming mismatch unrelated to this task.

**Orchestrator system prompt:** Add kanban pipeline instructions covering:

- How to use `kanban_pick` to claim tasks
- Task status lifecycle (todo → in-progress → review → done)
- Dependency tracking with `kanban_list --unblocked`
- Failure handling: `kanban_edit ID --block "reason"`

### 3.6 Error Handling

Follow GitLocalToolset: non-zero exit codes return `"error: {stderr}"` strings — never raise exceptions. The LLM can understand and react to error messages.

### 3.7 Constructor Design

```python
class KanbanToolset(FunctionToolset):
    def __init__(
        self,
        kanban_dir: Path,
        kanban_bin: Path | None = None,  # auto-detect from kanban_dir/../kanban-md.exe
        hooks: HookRegistry | None = None,
    ) -> None: ...
```

Binary path auto-detection: look for `kanban-md.exe` (Windows) or `kanban-md` beside the kanban dir, or fall back to PATH lookup.

## 4. Recommendation (.90 confidence)

**Implement `KanbanToolset(FunctionToolset)` as an async subprocess wrapper around kanban-md CLI** following the `GitLocalToolset` pattern exactly. Seven tools (list, show, create, move, edit, pick, context). Use `--dir` for multi-board support. Wire into `bootstrap.py build_toolsets()`. Update orchestrator system prompt with kanban workflow knowledge.

**Risks and mitigations:**

- **Binary not found at runtime** → Constructor validates path; tools return error string if missing.
- **Tool name resolver mismatch** → Pre-existing issue; use `KanbanToolset` class name in agent .md files for now.

## 5. Follow-up Tasks

1. **KanbanToolset implementation** — 7 tools, async subprocess, error handling, `--dir` support
2. **Bootstrap wiring** — Register in `build_toolsets()`, add to orchestrator agent definition tools list
3. **Orchestrator prompt update** — Add kanban pipeline workflow to system prompt
4. **Unit tests** — Mock subprocess (same pattern as test_git_local.py), test all 7 tools + error paths
