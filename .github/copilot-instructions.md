# OwlBear — Copilot Workspace Instructions

## Project purpose

OwlBear is an on-demand, laptop-resident AI development system built around Copilot CLI. It receives user intent, extracts intent, plans work, executes it through agent workflows, and delivers results through shared workspace artifacts (code, kanban board, sessions). VS Code remains the user's IDE for interactive work; OwlBear and VS Code share the filesystem as the integration point.

## Principles

### Core values

- **Quality over speed, always.** The output must be excellent — but quality means concise, actionable, and immediately usable. Not voluminous. **This applies equally to foundations.** Never rush scaffolding, configuration, or bootstrap work. A polished foundation makes everything built on top of it better. Treat P1 tasks with the same care as P2 tasks.
- **Research before implementation, always.** Nothing we build is new or unique. Before implementing anything, find how others have solved it. Every task must go through the research phase — there are no exceptions. Even when you think you know the answer, you don't. Look it up, validate your assumptions, and learn from prior art.
- **KISS** — Keep it simple, stupid. Don't over-engineer.
- **YAGNI** — You aren't gonna need it. Don't build for hypothetical future requirements.
- **DRY** — Don't repeat yourself. Single source of truth for every piece of knowledge.
- **No legacy code, no backwards compatibility.** It is okay to break things in order to improve them.

### Coding discipline (adapted from Karpathy's principles)

- **Think before coding.** Before writing any code, articulate the approach: what will change, what the expected behavior is, and what could go wrong. Plan the change, then execute it. Never jump straight into editing.
- **Simplicity first.** Write the simplest code that solves the problem. Avoid abstractions until the third repetition. Flat is better than nested. If a function exceeds ~50 lines, split it.
- **Surgical changes.** Make the smallest diff that achieves the goal. Resist the urge to refactor unrelated code in the same change. One logical change per commit.
- **Goal-driven execution.** Every action should trace back to a concrete task on the kanban board. If you can't name the task you're working on, stop and check the board first.

### Process habits

- **TDD by default.** Write the test first, watch it fail, then implement. Target ≥ 90 % coverage per phase gate.
- **State confidence at decision points.** When deriving a decision from source material, state confidence as a score (0.0–1.0). When multiple valid approaches exist, present them with trade-offs using `(bp:)` for best-practice options and `(rec:)` for your recommendation, per the decision-requests skill convention. Never assume — surface the choice.
- **Agent-specific verdict thresholds** (reviewer ≥ .90, auditor ≥ .95) are defined in `agent-common.instructions.md` and remain the authority for pipeline gate decisions.
- **Deliverables are kanban tasks and working code, not documents.** Research documents are _supporting artifacts_ — they have value, but writing a doc is never the end goal. After completing a research or analysis task, always create the follow-up kanban tasks that the research recommends. A research task is not done until its findings are actionable items on the board. Link the kanban task body to the research doc (e.g., `See docs/research/{slug}.md for details`).
- **Verify subagent output, never trust self-reports.** After a subagent reports completion, verify the deliverables exist and match the acceptance criteria. Run tests yourself. Check that promised kanban tasks were actually created.

## Command Surface Selection

| Surface      | Choose this when                                                                                                                                | OwlBear example                     |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------- |
| `.prompt.md` | You are defining a user-facing one-shot command that should run only when explicitly invoked.                                                   | `prompts/orchestrate.prompt.md`     |
| `SKILL.md`   | You are defining reusable domain knowledge that should auto-load by relevance, or you need co-located resources (scripts, templates, examples). | `skills/research-workflow/SKILL.md` |
| `.agent.md`  | You are defining a long-lived role/persona with persistent behavior such as tool restrictions, model preferences, or handoff boundaries.        | `agents/reviewer.agent.md`          |

Default rule: user-facing one-shot commands use `.prompt.md` unless they need auto-loading or co-located resources.

Pipeline-only skills (owned by orchestrator pipeline agents — researcher, architect, test-writer, builder, reviewer, writer, auditor) must add `user-invocable: false` to their SKILL.md frontmatter so they are hidden from the `/` slash-command menu but remain auto-loadable by agents. See `docs/research/user-invocable-skills.md` for the full 11/10 categorization.

## Formatting rules for writing files

- **No backtick wrappers around `.agent.md` or `.instructions.md` content.** When the `read_file` tool returns agent/instruction files, it wraps them in ` ```chatagent ` or ` ```instructions ` fencing. These fences are **added by the tool, not part of the file**. Never write them back when creating or editing these files. The file must start directly with `---` (YAML frontmatter).
- **Empty lines around enumerations.** Always add a blank line before and after bullet lists (`-`) and numbered lists (`1.`). This is especially important before closing XML tags (e.g., `</self_critique>`, `</boundaries>`). Without the blank line, linters interpret the next line as a continuation of the list and add unwanted indentation.

## Tech stack

| Component    | Technology                                  | Notes                                                                                                                                                                                         |
| ------------ | ------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Language     | Python 3.12+                                | `uv` package manager, never bare `pip`                                                                                                                                                        |
| Runtime      | On-demand Copilot CLI sessions              | No background process; work is executed when invoked through CLI commands and agent workflows.                                                                                                |
| Agents       | VS Code / Copilot custom agents             | Agents are defined via `.agent.md` files and can delegate to nested subagents.                                                                                                                |
| LLM provider | GitHub Copilot (flat-rate)                  | Copilot is the primary model/runtime for orchestration and implementation tasks.                                                                                                              |
| Orchestrator | ACP over NDJSON                             | Orchestrator launches `copilot --acp --stdio` and exchanges NDJSON messages over stdin/stdout.                                                                                                |
| MCP servers  | 5 servers (4 custom stdio + 1 GitHub remote) | Core: `mcp-kanban`, `mcp-knowledge`, `mcp-project`, `mcp-memory` (stdio) + `github` remote (`api.githubcopilot.com/mcp/`) — all scaffolded by `setup.py`.                                    |
| Knowledge    | Graph + vector knowledge package            | Knowledge services live under `packages/knowledge/` and are exposed through MCP.                                                                                                              |
| Projects     | `owlbear-project.json` + MCP project server | Project metadata and operations are handled through project files and the project MCP server.                                                                                                 |
| Safety       | Git safety net + audit log                  | Use git review/revert as operational safety; keep an audit log for retrospective self-improvement.                                                                                            |
| Distribution | Clone = install                             | Run `scripts/setup.py` from a new project dir to wire `.vscode/settings.json`, `.vscode/mcp.json`, `kanban/`, `owlbear-project.json`, and `.github/copilot-instructions.md` to the shared `../owlbear/` installation. |
| Diagrams     | Kroki HTTP API                              | Kroki supports mermaid, plantuml, graphviz, d2, c4plantuml, and excalidraw outputs.                                                                                                           |
| Task board   | kanban-md (via MCP abstraction)             | `kanban-md` remains the board engine with MCP as the long-term integration boundary.                                                                                                          |

## MCP Server Conventions

All four custom MCP servers (`mcp-kanban`, `mcp-knowledge`, `mcp-project`, `mcp-memory`) follow these conventions:

- **Error prefix:** Tool execution errors return a string starting with `error: ` (e.g., `f"error: {stderr.strip()}"`). Empty-result messages (e.g., "No sources found.") are informational — no prefix.
- **Tool annotations:** Every tool declares `readOnlyHint`, `idempotentHint`, and `destructiveHint` in its `ToolAnnotations`. See `mcp-kanban` for the reference implementation.
- **Return types:** Use `dict` or `list[dict]` for queryable data (lists, metadata). Use `str` for content bodies, messages, and errors.
- **Lifespan pattern:** Server startup uses an `AppContext` dataclass and an `asynccontextmanager` lifespan function passed to `FastMCP`.
- **Tool exclusion:** Each server reads a `*_TOOLS_EXCLUDE` env var (`KANBAN_TOOLS_EXCLUDE`, `KNOWLEDGE_TOOLS_EXCLUDE`, `PROJECT_TOOLS_EXCLUDE`) at startup. Comma-separated tool names are removed via `server.remove_tool()`; unknown names are silently ignored. Default (unset) = all tools registered.
- **Module exports:** Every `server.py` defines `__all__` listing its public symbols.

GitHub-hosted Copilot Memory is explicitly disabled in workspace settings to preserve OwlBear's local-first operating model and reduce cloud memory retention risk for project context. This guardrail is intentional because Copilot Memory defaults changed to ON for Pro and Pro+ in March 2026.

## Memory governance

**Built-in memory tool** (`/memories/`) stores agent-centric learning only. This prevents duplication with the general KB and project KB layers.

**User memory** (`/memories/`) — store:

- Tool usage patterns and CLI flag recipes (e.g., "use bare `--cov` for scoped pytest")
- Agent behavior observations (what worked, what failed, effective workflows)
- Process pitfalls to avoid (e.g., "PS 5.1 here-strings split in ArgumentList")

**User memory** — do NOT store:

- Architecture decisions (use `docs/decisions/`)
- Research findings (use `docs/research/`)
- Domain knowledge or project conventions (use project KB via MCP)
- Code snippets or implementation details
- Task-specific context (use session memory — auto-cleared)

**Repo memory** (`/memories/repo/`) follows the built-in `repoMemoryInstructions` constraints. Agents write lessons-learned to `/memories/repo/inbox/` per `agent-common.instructions.md`.

**Management:** Run `Chat: Show Memory Files` to view stored memories. Delete stale entries with the `memory delete` command. GitHub-hosted Copilot Memory stays disabled — see the paragraph above.

## kanban-md usage

The project uses [kanban-md](https://github.com/antopolskiy/kanban-md) (v0.33.0) for file-based task management. The binary lives at `kanban/kanban-md.exe` (gitignored); run `kanban/setup.ps1` to download it.

For CLI commands, workflows, and cheatsheets, see the `kanban-md` skill. The sections below cover only **OwlBear-specific** conventions that override or extend the defaults.

### Board structure

- **Config:** `kanban/config.yml` — statuses: ideation → backlog → todo → in-progress → review → docs → done
- **Priorities:** `someday` < `nice-to-have` < `important` (default) < `needed` < `critical`
- **Tasks:** `kanban/tasks/*.md` — YAML frontmatter (id, title, status, priority, tags, depends_on) + body with acceptance criteria

### Priority scheme

| Priority       | Meaning                                          | When to use                             |
| -------------- | ------------------------------------------------ | --------------------------------------- |
| `someday`      | Future vision, no commitment                     | Ideas we might never build              |
| `nice-to-have` | Useful improvement, no urgency                   | Build when everything important is done |
| `important`    | Clear value, scheduled for a phase **(default)** | Most feature work lands here            |
| `needed`       | Core capability, do soon                         | Required for the next milestone         |
| `critical`     | Can't function without it                        | Current blocker — do immediately        |

### Task lifecycle

Full pipeline with agent ownership:

```
ideation → (researcher) → backlog → (architect) → todo → (test-writer RED) → in-progress → (builder GREEN) → review → (reviewer) → docs → (writer) → done → (auditor) → archived
```

Each agent's `.agent.md` defines its gate ownership, exit criteria, and rejection paths.
Pipeline-only agents (planner, researcher, architect, test-writer, builder, reviewer, writer, auditor) use `disable-model-invocation: true` in their frontmatter to prevent unintended invocation by arbitrary callers; the orchestrator's explicit `agents` array overrides this flag.
See `agent-common.instructions.md` → **Task coordination** for claiming and handoff workflow.

Research gate (ideation → backlog): see researcher agent for the full checklist.

**Blocked tasks:** Use `kanban-md edit ID --block "reason"` on any task in any status. Filter with `kanban-md list --blocked`. Do not use a separate status for blocked state.

**Blocking convention:** Routine gate rejections (reviewer FAIL, writer reject, auditor reject-to-review) use simple status movement without `--block` — the task auto-redispatches. Reserve `--block` for fundamental rejections (auditor → backlog), architect gates, handoff, and decision requests. See `agent-common.instructions.md` → **Blocking convention**.

### Dependency tracking

Use `depends_on` in task frontmatter + kanban-md flags (`--blocked`, `--not-blocked`) to track blocked tasks. Do **not** use status columns to encode dependency state.

### Tag taxonomy

Tags are free-form (no config file — just `--tags` on create/edit). Use these conventions:

| Category     | Tags                                                        | Purpose                                     |
| ------------ | ----------------------------------------------------------- | ------------------------------------------- |
| Phase        | `phase-1` … `phase-12`                                      | Group tasks by project phase                |
| Category     | `config`, `tooling`, `docs`, `test`, `cli`, `auth`, `agent` | What area the task touches                  |
| Specialty    | `hooks`, `model`, `rename`, `research`                      | Specific concern                            |
| Type prefix  | `type:build`, `type:test`, `type:docs`, `type:deploy`       | Task nature (what kind of work)             |
| Block prefix | `blocked:user-decision`, `blocked:external`                 | Why a task is blocked                       |
| Scope prefix | `scope:copilot`, `scope:core`, `scope:cli`                  | Which part of the codebase                  |
| Rigor prefix | `rigor:lean`, `rigor:standard`, `rigor:thorough`            | Quality-vs-speed profile for task execution |

Filter examples: `kanban-md list --tag research`, `kanban-md list --tag phase-3,auth`.

### Research tasks

Tag research tasks with `research`. Follow the research-docs instruction (`docs/research/*.md`). The research lifecycle is: complete checklist → write doc → **execute kanban-md create commands** to create follow-up tasks at `ideation` → move to `backlog`. If a finding requires a user decision, create a decision request in `docs/decisions/pending/` instead (see the `decision-requests` skill at `skills/decision-requests/SKILL.md`).
It is encouraged to clone repos that are the subject of research into `docs/scratch/research/` (gitignored) for analysis, over fetching single files or relying on web access. This keeps all research artifacts in one place and avoids polluting the project root. The cloned repos should be deleted when the research is complete.

## Directory structure

| Directory                 | Purpose                                                |
| ------------------------- | ------------------------------------------------------ | --- | ---------- | ------------------------------------------------------------------------- | --- | ----- | ---------------------------------- |
| `packages/orchestrator/`  | ACP client, dispatch planning, wave-based dispatch loop (wave assembly + ACP dispatch), `owlbear` CLI entry point (`dispatch`, `run`, `status` commands), audit analysis (pattern detectors) |
| `packages/knowledge/`     | Knowledge engine (graph + vector)                      |
| `packages/mcp-kanban/`    | MCP server wrapping kanban operations                  |
| `packages/mcp-knowledge/` | MCP server exposing knowledge operations               |
| `packages/mcp-project/`   | MCP server for project metadata and lifecycle          |
| `packages/mcp-memory/`    | MCP server for persistent agent memory (SQLite-backed) |
| `packages/voice/`         | Voice addon (speech recognition + TTS)                 |
| `agents/`                 | Agent definitions (`.agent.md`)                        |
| `skills/`                 | Agent skills (`SKILL.md`, agentskills.io style)        |
| `instructions/`           | Shared instruction files (`*.instructions.md`)         |
| `docs/`                   | Research, decisions, sources, and supporting docs      |
| `kanban/`                 | kanban board data and tooling                          |     | `scripts/` | Project tooling scripts (`setup.py`, `validate_skills.py`, `validate_agents.py`, `skills_ref/`) |     | `v1/` | Archived v1 codebase for reference |

### Package dependency rules

Cross-namespace imports are enforced by `tests/test_package_boundary.py`. The `ALLOWED_IMPORTS` constant in that file maps each package namespace to its permitted owlbear-namespace imports. When adding a new package, update `ALLOWED_IMPORTS` — the manifest guard will fail otherwise. Full dependency rules and the TYPE_CHECKING import policy are documented in the test module docstring.

## File placement rules

Keep the project root clean. Every file created during a task must go to the right location:

| File type                | Location                  | Naming                                | Tracked?        |
| ------------------------ | ------------------------- | ------------------------------------- | --------------- |
| Temp/debug output        | `docs/scratch/`           | `{task-id}-{desc}.{ext}`              | No (gitignored) |
| Research documents       | `docs/research/`          | `{slug}.md` with task ref in content  | Yes             |
| Cloned external repos    | `docs/scratch/research/`  | `{repo-name}/`                        | No (gitignored) |
| Benchmark / eval scripts | `tests/benchmarks/`       | descriptive `.py` name                | Yes             |
| Source code              | `packages/*/src/`         | follow package-local module structure | Yes             |
| Tests                    | `tests/`                  | `test_{module}.py`                    | Yes             |
| Agents                   | `agents/`                 | `{role}.agent.md`                     | Yes             |
| Skills                   | `skills/`                 | `{skill}/SKILL.md`                    | Yes             |
| Instructions             | `instructions/`           | `{name}.instructions.md`              | Yes             |
| Decision requests        | `docs/decisions/pending/` | `{task-id}-{slug}.md`                 | Yes             |

Before marking a task `done`, delete all `docs/scratch/{task-id}-*` files created for that task. See `docs/scratch/.instructions.md` for details.

## Attribution

All code and patterns taken from external sources must be logged in `docs/sources/overview.md`.

| Column     | Description                                               |
| ---------- | --------------------------------------------------------- |
| Source     | Project or article name                                   |
| URL        | Link to the repo, article, or doc                         |
| What       | What was taken (pattern, code snippet, architecture idea) |
| Where Used | Where it appears in OwlBear (file path or module)         |
| Date       | When it was adopted                                       |

Update `docs/sources/overview.md` whenever adopting external patterns. This ensures proper credit and traceability.
