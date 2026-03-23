# OwlBear — Copilot Workspace Instructions

## Project purpose

OwlBear is an always-on, laptop-resident AI development system. It receives user intent (via CLI, Slack, or voice), extracts intent, plans work, executes it autonomously, and delivers results — with human approval gates for destructive or publishing actions. It owns the full build pipeline (ideation → spec → code → test → review → deliver) and operates as a standalone daemon process. VS Code remains the user's IDE for interactive work; OwlBear and VS Code share the filesystem (code, kanban board, sessions) as the integration point.

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

- **askQuestions liberally.** Use the askQuestions tool at every decision point. Never assume — when in doubt, ask. Include `(bp:)` for best practice and `(rec:)` for recommendation per mcp.instructions.md conventions.
- **manage_todo_list extensively.** Track progress, create checkpoints, add a reflection step at the end.
- **TDD by default.** Write the test first, watch it fail, then implement. Target ≥ 90 % coverage per phase gate.
- **Deliverables are kanban tasks and working code, not documents.** Research documents are _supporting artifacts_ — they have value, but writing a doc is never the end goal. After completing a research or analysis task, always create the follow-up kanban tasks that the research recommends. A research task is not done until its findings are actionable items on the board. Link the kanban task body to the research doc (e.g., `See docs/research/{slug}.md for details`).
- **Verify subagent output, never trust self-reports.** After a subagent reports completion, verify the deliverables exist and match the acceptance criteria. Run tests yourself. Check that promised kanban tasks were actually created.

## Formatting rules for writing files

- **No backtick wrappers around `.agent.md` or `.instructions.md` content.** When the `read_file` tool returns agent/instruction files, it wraps them in ` ```chatagent ` or ` ```instructions ` fencing. These fences are **added by the tool, not part of the file**. Never write them back when creating or editing these files. The file must start directly with `---` (YAML frontmatter).
- **Empty lines around enumerations.** Always add a blank line before and after bullet lists (`-`) and numbered lists (`1.`). This is especially important before closing XML tags (e.g., `</self_critique>`, `</boundaries>`). Without the blank line, linters interpret the next line as a continuation of the list and add unwanted indentation.

## Tech stack

| Component       | Technology                                 | Notes                                                                                                                                                                                                                                            |
| --------------- | ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Language        | Python 3.12+                               | `uv` package manager, never bare `pip`                                                                                                                                                                                                           |
| Runtime         | Standalone daemon                          | BearClaw CLI daemon; dual-coroutine (`channel_loop` + `poll_loop`) in `asyncio.TaskGroup`                                                                                                                                                        |
| Agents          | PydanticAI                                 | Structured output, dependency injection; opt-in `SummarizingCondenser` for long conversations; `BoardContextProvider` (`owlbear.core.board_context`) injects live kanban board state into agent turns with TTL caching (wired in #771); `DispatchContext` + `format_dispatch_context()` (`owlbear.core.delegation`) forward workspace/channel/task metadata as per-run `instructions=`/`metadata=` to child agents during delegation (wired in #958) |
| LLM provider    | GitHub Copilot OAuth                       | Device-flow auth, `api.individual.githubcopilot.com`                                                                                                                                                                                             |
| Retry           | tenacity                                   | Two-layer retry (tool + daemon); `CircuitBreaker` on Copilot HTTP transport                                                                                                                                                                      |
| CLI             | Typer (BearClaw)                           | Entry point for daemon, auth, and user commands                                                                                                                                                                                                  |
| HTTP            | httpx + truststore                         | Always `timeout=httpx.Timeout(T, connect=5)` on every `httpx.AsyncClient`                                                                                                                                                                        |
| Config          | pydantic-settings                          | Env vars (OWLBEAR\_ prefix), validated at startup; use `get_settings()` singleton from `owlbear.config` (never instantiate `OwlBearSettings()` directly); nested models use `__` delimiter (e.g., `OWLBEAR_BROWSER__HEADLESS=true`)              |
| Knowledge       | SQLite (graph) + Qdrant (vectors) + BGE-M3 | Hybrid search (graph + vector); queries scoped to active project when set; opt-in `ConsolidationService` for cross-document insight synthesis; all major pipeline entry points (`refresh_all`, `ingest_text`, `crawl_and_ingest`, `BookmarkPipeline.process`) accept `cancel: asyncio.Event \| None` for cooperative cancellation |
| Web search      | ddgs + trafilatura                         | DuckDuckGo search via `ddgs`; page extraction via `extract_content` (wraps trafilatura internally); leaf markdown helper `extract_markdown` in `owlbear.web_extract`; optional `search` extra                                                    |
| Browser         | Playwright                                 | CDP `localhost` only; isolated browser context (SEC-07); `screenshot_mode` config setting; a11y snapshot via CDP `getFullAXTree`                                                                                                                 |
| Messaging       | Slack (slack_sdk)                          | `ChannelPlugin` protocol; CLI + Slack implementations; Socket Mode WebSocket; sender allowlist filtering; per-user sliding-window rate limiting                                                                                                  |
| Safety          | Approval gates                             | Six layers: `RolePolicy` tool allow-list + `ApprovalPolicy` gates + `sandbox_path()` confinement + `CommandSafetyGuard` blocklist + `ContentInjectionGuard` content scanning + `wrap_untrusted_content()` web-content tagging. See `SECURITY.md` |
| Errors          | `OwlBearError` root exception              | All custom exceptions inherit from `OwlBearError` (`owlbear.core.exceptions`). Use MI for stdlib compatibility (e.g. `AskUserTimeoutError(OwlBearError, TimeoutError)`). See `docs/research/exception-hierarchy.md`                              |
| Projects        | JSON file store                            | Multi-project `ProjectStore` CRUD; 4 templates (bare, python-uv, python-pip, node)                                                                                                                                                               |
| Diagrams        | Kroki HTTP API                             | Kroki API; supports mermaid, plantuml, graphviz, d2, c4plantuml, excalidraw; output svg/png (excalidraw: svg only)                                                                                                                               |
| Voice (planned) | Whisper STT + pyttsx3 TTS                  | Local-first voice I/O                                                                                                                                                                                                                            |
| Task board      | kanban-md                                  | Go CLI binary in `kanban/`; `KanbanToolset` exposes board ops to agents                                                                                                                                                                          |

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

Tag research tasks with `research`. Follow the research-docs instruction (`docs/research/*.md`). The research lifecycle is: complete checklist → write doc → **execute kanban-md create commands** to create follow-up tasks at `ideation` → move to `backlog`. If a finding requires a user decision, create a decision request in `docs/decisions/pending/` instead (see the `decision-requests` skill at `.github/skills/decision-requests/SKILL.md`).
It is encouraged to clone repos that are the subject of research into `docs/scratch/research/` (gitignored) for analysis, over fetching single files or relying on web access. This keeps all research artifacts in one place and avoids polluting the project root. The cloned repos should be deleted when the research is complete.

## Directory structure

| Directory           | Purpose                                             |
| ------------------- | --------------------------------------------------- |
| `src/owlbear/`      | Main Python package                                 |
| `src/bearclaw/`     | CLI python                                          |
| `tests/`            | pytest test suite (unit + integration)              |
| `tests/benchmarks/` | Performance benchmarks and evaluation harnesses     |
| `docs/`             | Non-research documents (architecture, audits, etc.) |
| `docs/research/`    | Research and analysis documents                     |
| `docs/sources/`     | External attribution and sources                    |
| `docs/decisions/`   | Async decision requests (pending + resolved)        |
| `docs/scratch/`     | Ephemeral working files (gitignored)                |
| `kanban/`           | kanban-md board, binary, and setup script           |
| `.github/`          | Copilot instructions, agent/skill/prompt files      |

## File placement rules

Keep the project root clean. Every file created during a task must go to the right location:

| File type                | Location                  | Naming                               | Tracked?        |
| ------------------------ | ------------------------- | ------------------------------------ | --------------- |
| Temp/debug output        | `docs/scratch/`           | `{task-id}-{desc}.{ext}`             | No (gitignored) |
| Research documents       | `docs/research/`          | `{slug}.md` with task ref in content | Yes             |
| Cloned external repos    | `docs/scratch/research/`  | `{repo-name}/`                       | No (gitignored) |
| Benchmark / eval scripts | `tests/benchmarks/`       | descriptive `.py` name               | Yes             |
| Source code              | `src/`                    | follow existing package structure    | Yes             |
| Tests                    | `tests/`                  | `test_{module}.py`                   | Yes             |
| Decision requests        | `docs/decisions/pending/` | `{task-id}-{slug}.md`                | Yes             |

Before marking a task `done`, delete all `docs/scratch/{task-id}-*` files created for that task. See `docs/scratch/.instructions.md` for details.

## Confidence scores

When presenting proposals via askQuestions, prefix each option label with a confidence score on a scale of `.0`–`1.0` (no leading zero). Example: `.85 Accept — matches precedent X`. Mark the recommendation separately — it may differ from the highest-confidence option.

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
