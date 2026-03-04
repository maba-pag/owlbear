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
- **Deliverables are kanban tasks and working code, not documents.** Research documents are _supporting artifacts_ — they have value, but writing a doc is never the end goal. After completing a research or analysis task, always create the follow-up kanban tasks that the research recommends. A research task is not done until its findings are actionable items on the board. Link the kanban task body to the research doc (e.g., `See docs/{task-id}-research.md for details`).
- **Verify subagent output, never trust self-reports.** After a subagent reports completion, verify the deliverables exist and match the acceptance criteria. Run tests yourself. Check that promised kanban tasks were actually created.

## Formatting rules for writing files

- **No backtick wrappers around `.agent.md` or `.instructions.md` content.** When the `read_file` tool returns agent/instruction files, it wraps them in ` ```chatagent ` or ` ```instructions ` fencing. These fences are **added by the tool, not part of the file**. Never write them back when creating or editing these files. The file must start directly with `---` (YAML frontmatter).
- **Empty lines around enumerations.** Always add a blank line before and after bullet lists (`-`) and numbered lists (`1.`). This is especially important before closing XML tags (e.g., `</self_critique>`, `</boundaries>`). Without the blank line, linters interpret the next line as a continuation of the list and add unwanted indentation.

## Tech stack

| Component       | Technology                                 | Notes                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| --------------- | ------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Language        | Python 3.12+                               | `uv` package manager, never bare `pip`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| Runtime         | Standalone daemon                          | Background process started via BearClaw CLI                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| Agents          | PydanticAI                                 | Structured output, dependency injection                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| LLM provider    | GitHub Copilot OAuth                       | Device-flow auth, `api.individual.githubcopilot.com`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| Retry           | tenacity                                   | Exponential backoff, jitter, max 5 attempts                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| CLI             | Typer (BearClaw)                           | Entry point for daemon, auth, and user commands                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| HTTP            | httpx + truststore                         | Async HTTP client with system certificate trust                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| Config          | pydantic-settings                          | Env vars + TOML config file, validated at startup                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| Knowledge       | SQLite (graph) + Qdrant (vectors) + BGE-M3 | Knowledge graph with hybrid vector search; schema v7 (knowledge_sources table; chunk_id on entities; bookmarks table with URL+scope dedup); idle-timeout model unloading; `GraphAugmentedRetriever` adds graph-neighbor expansion to vector results (token-budgeted); KnowledgeToolset exposes `query_knowledge`, `ingest_document`, `list_knowledge_sources` to agents; `KnowledgeSourceToolset` exposes `add_source`, `list_sources`, `refresh_source` to agents; `KnowledgeQueryService` provides per-turn context injection (`knowledge_context_tokens` config, default 2000; delegates to `GraphAugmentedRetriever` when `knowledge_graph_expansion` config is enabled); `RefreshOrchestrator` dispatches source refreshes by type (url_list, crawl, file_glob) with per-item error collection; `bearclaw knowledge-source add/list/show/refresh/remove` CLI; queries scoped to active project when set; `InterDocGraphBuilder` infers cross-document edges via embedding similarity + LLM (opt-in via `inter_doc_graph_building` config); `BookmarkStore` CRUD for evaluated URLs with relevance scoring; `SourceEvaluator` PydanticAI agent scores content relevance (0–1) with tags/summary/worth_ingesting structured output; `BookmarkPipeline` orchestrates URL→extract→evaluate→ingest→bookmark with dedup and configurable ingest threshold; `BookmarkToolset` exposes `bookmark_source`, `list_bookmarks` to agents |
| Web search      | ddgs + trafilatura                         | DuckDuckGo search via `ddgs`; page extraction via httpx + trafilatura; `WebSearchToolset` exposes `web_search`, `web_read` to agents; optional `search` extra                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| Browser         | Playwright                                 | Launch or attach via CDP (`localhost` only); see `bearclaw browser` CLI; `ScreenshotService` captures/saves/delivers screenshots; `screenshot_mode` setting (`auto`/`manual`/`on_error`, default `on_error`); `CLIChannel.send_file()` delivers files to terminal; `VisualFeedbackToolset` exposes `share_screenshot`, `share_terminal_output` to agents; `ScreenshotOnErrorHook` auto-captures browser screenshot on `ON_ERROR` event (respects `screenshot_mode`)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| Messaging       | Slack (slack_sdk)                          | Socket Mode WebSocket + AsyncWebClient; see `bearclaw slack` CLI; `slack_templates.py` Block Kit builders (proposal, status, interactive proposal, approval, progress) + text fallbacks; interactive handler routes `block_actions` to message queue or registered `register_action` callbacks by `action_id`; thread registry auto-threads messages by `context_key`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| Safety          | Approval gates                             | `ApprovalPolicy` rules in config gate destructive tools (git push, PRs, deploy); `ApprovalGateToolset` wraps toolsets in bootstrap (sends Block Kit approval buttons on Slack, plain text on CLI); per-session pre-grants; `ErrorJournal` append-only JSONL log in `.owlbear/error_journal.jsonl` with 10K-entry rotation + `query` for agent learning; `EscalationHook` wires ON_ERROR to user prompt (retry/skip/abort) when retries exhausted                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| Projects        | JSON file store                            | Multi-project support; `bearclaw project create/list/switch/archive/new`; per-project session dirs; `ProjectStore` CRUD; `ProjectToolset` exposes `switch_project`, `list_projects`, `workspace_create_project` to agents; bootstrap reads `active_project` file to derive workspace; `ProjectWorkspace` scaffolds new projects (`project_root` config field, default `~/projects`); 4 templates: bare, python-uv, python-pip, node; orchestrates dir creation → git init → kanban-md init → store registration; workspace switching updates CWD, `ContextManager.update_root`, and toolset `_workspace_root`/`_root` references                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| Voice (planned) | Whisper STT + pyttsx3 TTS                  | Local-first voice I/O                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| Task board      | kanban-md                                  | Go CLI binary in `kanban/`, file-based kanban; `KanbanToolset` exposes `kanban_list`, `kanban_show`, `kanban_create`, `kanban_move`, `kanban_edit`, `kanban_pick`, `kanban_context` to agents                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |

## kanban-md usage

The project uses [kanban-md](https://github.com/antopolskiy/kanban-md) (v0.33.0) for file-based task management. The binary lives at `kanban/kanban-md.exe` (gitignored); run `kanban/setup.ps1` to download it.

For CLI commands, workflows, and cheatsheets, see the `kanban-md` and `kanban-based-development` skills. The sections below cover only **OwlBear-specific** conventions that override or extend the defaults.

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

### No worktrees

The `kanban-based-development` skill describes a git-worktree workflow. **We do not use worktrees.** VS Code Copilot operates in a single workspace. Make code changes in place on the main branch.

### Task lifecycle — statuses, roles, and quality gates

The pipeline has 7 statuses. Each status has a gate owner — the role that processes tasks in that status and advances them forward. Research is not a status — it is the work that happens inside `ideation` before a task can graduate to `backlog`.

| Status        | Meaning                                              | Gate owner | Exit criteria (to move forward)                               |
| ------------- | ---------------------------------------------------- | ---------- | ------------------------------------------------------------- |
| `ideation`    | Raw idea captured, not yet researched                | Researcher | Research checklist completed (see below)                      |
| `backlog`     | Researched, refined AC, approach documented          | Architect  | AC refined, architectural review done, may split/merge/expand |
| `todo`        | Architect-approved, unblocked, ready for dev         | Builder    | —                                                             |
| `in-progress` | Actively being implemented (TDD)                     | Builder    | Tests pass, ruff clean, AC met                                |
| `review`      | Code + tests complete, needs verification            | Reviewer   | Tests pass independently, ruff clean, every AC line evidenced |
| `docs`        | Docs gate — verify/update all relevant documentation | Writer     | Docs-gate checklist passed (see below)                        |
| `done`        | Verified complete, ready for archival                | Closer     | AC verified with evidence, confidence ≥ .80, archived         |

### Agent roles and movement authority

#### Forward (normal pipeline flow)

| Role       | Moves                    | Responsibility                                                                                 |
| ---------- | ------------------------ | ---------------------------------------------------------------------------------------------- |
| Planner    | → `ideation`             | Entry gate: every task created with AC, priority, tags, dependencies, atomicity.               |
| Researcher | `ideation` → `backlog`   | Completes the research checklist. Documents findings in task body or linked doc.               |
| Architect  | `backlog` → `todo`       | Reviews research, refines/splits/merges AC, ensures architectural soundness, approves for dev. |
| Builder    | `todo` → `in-progress`   | Claims task, starts TDD implementation.                                                        |
| Builder    | `in-progress` → `review` | Implementation and tests complete, lint clean.                                                 |
| Reviewer   | `review` → `docs`        | Verifies implementation: runs tests, ruff, checks every AC line with evidence.                 |
| Writer     | `docs` → `done`          | Runs docs-gate checklist, updates docs as needed, cleans scratch files.                        |
| Closer     | `done` → archived        | Verifies AC with evidence, scores confidence, archives confirmed tasks, commits + pushes.      |

#### Backward (quality rejection paths)

Any gate owner can reject a task backward when quality doesn't meet the bar. The rejecting agent adds a block reason explaining the gap and what must be fixed.

| Role      | Moves                  | Trigger                                            |
| --------- | ---------------------- | -------------------------------------------------- |
| Architect | `backlog` → `ideation` | Research insufficient — needs more investigation   |
| Reviewer  | `review` → `backlog`   | AC is fundamentally flawed — needs re-architecture |
| Reviewer  | `review` → `todo`      | Implementation wrong — builder retries             |
| Writer    | `docs` → `review`      | Found untested behavior during docs review         |
| Closer    | `done` → `review`      | Verification failed — evidence doesn't match AC    |
| Closer    | `done` → `backlog`     | Fundamental quality issue — needs re-design        |

### Research checklist (gate: ideation → backlog)

Before a task can leave `ideation`, the researcher must complete this checklist. The first 5 items are **mandatory**; items 6–7 are **recommended**.

1. **Theoretical validity** — Is this a sound concept? Does the abstraction make sense? Is it the right approach?
2. **Prior art** — Find 2+ GitHub repos, articles, or docs showing how others solved this problem.
3. **Technical feasibility** — Will it work in our stack (Python 3.12, PydanticAI, etc.)? Any blockers or dependencies?
4. **Architecture fit** — How does it integrate with existing OwlBear components? What interfaces does it touch?
5. **Implementation approach** — What patterns, idioms, and data structures should we adopt from prior art?
6. **Testing strategy** _(recommended)_ — How will we test this? Unit, integration, mocks? Coverage approach?
7. **Findings documented** _(recommended)_ — Brief notes in task body, or linked `docs/{slug}.md` for complex research.

For trivial tasks (rename, typo, config tweak): items 1–3 get a one-liner `N/A — trivial change, rationale: X` and the task moves through quickly. **The gate still exists** — it just doesn't create busywork.

**Docs gate rule:** Before moving any task from `docs` → `done`, the writer verifies:

1. If the task changed behavior or API: is copilot-instructions.md updated?
2. If the task added/changed a module: are docstrings complete?
3. If the task used external inspiration: is docs/sources.md updated?
4. If the task changed CLI commands: is README.md updated?
5. If the research phase produced a doc: is it archived or linked from the task?
6. If none of the above apply, explicitly note "no docs impact" and move through.

**Blocked tasks:** Use `kanban-md edit ID --block "reason"` on any task in any status. Filter with `kanban-md list --blocked`. Do not use a separate status for blocked state.

### Dependency tracking

Use `depends_on` in task frontmatter + kanban-md flags (`--blocked`, `--not-blocked`) to track blocked tasks. Do **not** use status columns to encode dependency state.

### Tag taxonomy

Tags are free-form (no config file — just `--tags` on create/edit). Use these conventions:

| Category     | Tags                                                        | Purpose                         |
| ------------ | ----------------------------------------------------------- | ------------------------------- |
| Phase        | `phase-1` … `phase-12`                                      | Group tasks by project phase    |
| Category     | `config`, `tooling`, `docs`, `test`, `cli`, `auth`, `agent` | What area the task touches      |
| Specialty    | `hooks`, `model`, `rename`, `research`                      | Specific concern                |
| Type prefix  | `type:build`, `type:test`, `type:docs`, `type:deploy`       | Task nature (what kind of work) |
| Block prefix | `blocked:user-decision`, `blocked:external`                 | Why a task is blocked           |
| Scope prefix | `scope:copilot`, `scope:core`, `scope:cli`                  | Which part of the codebase      |

Filter examples: `kanban-md list --tag research`, `kanban-md list --tag phase-3,auth`.

### Research tasks

Tag research tasks with `research`. Follow the research-docs instruction (`docs/*.md`). The research lifecycle is: complete checklist → write doc → create follow-up kanban tasks → move to `backlog`.
It is encouraged to clone repos that are the subject of research into `docs/research/` (gitignored) for analysis, over fetching single files or relying on web access. This keeps all research artifacts in one place and avoids polluting the project root. The cloned repos should be deleted when the research is complete.

## Directory structure

| Directory           | Purpose                                            |
| ------------------- | -------------------------------------------------- |
| `src/owlbear/`      | Main Python package                                |
| `src/bearclaw/`     | CLI python                                         |
| `tests/`            | pytest test suite (unit + integration)             |
| `tests/benchmarks/` | Performance benchmark scripts                      |
| `docs/`             | Research and analysis documents                    |
| `docs/research/`    | Cloned third-party repos for analysis (gitignored) |
| `docs/scratch/`     | Ephemeral working files (gitignored)               |
| `kanban/`           | kanban-md board, binary, and setup script          |
| `.github/`          | Copilot instructions, agent/skill/prompt files     |

## File placement rules

Keep the project root clean. Every file created during a task must go to the right location:

| File type             | Location            | Naming                               | Tracked?        |
| --------------------- | ------------------- | ------------------------------------ | --------------- |
| Temp/debug output     | `docs/scratch/`     | `{task-id}-{desc}.{ext}`             | No (gitignored) |
| Research documents    | `docs/`             | `{slug}.md` with task ref in content | Yes             |
| Cloned external repos | `docs/research/`    | `{repo-name}/`                       | No (gitignored) |
| Benchmark scripts     | `tests/benchmarks/` | descriptive `.py` name               | Yes             |
| Source code           | `src/`              | follow existing package structure    | Yes             |
| Tests                 | `tests/`            | `test_{module}.py`                   | Yes             |

Before marking a task `done`, delete all `docs/scratch/{task-id}-*` files created for that task. See `docs/scratch/.instructions.md` for details.

## Confidence scores

When presenting proposals via askQuestions, prefix each option label with a confidence score on a scale of `.0`–`1.0` (no leading zero). Example: `.85 Accept — matches precedent X`. Mark the recommendation separately — it may differ from the highest-confidence option.

### Workflow steps

```
1. Pick next task:  kanban-md pick --status todo --move in-progress
2. Read AC:         kanban-md show <id>
3. Think: plan the change, write AC as test assertions
4. Write failing test(s)
5. Implement minimal code to pass
6. Refactor if needed (keep diff small)
7. Verify:          uv run pytest + uv run ruff check
8. Review:          kanban-md move <id> review (tests pass, ruff clean, AC met)
9. Docs gate:       kanban-md move <id> docs (check docs-gate checklist above)
10. Complete:       kanban-md move <id> done
11. Close:          closer verifies AC, archives, commits, pushes
12. Phase gate:     coverage >= 90%, all tests green, ruff clean
```

### Agent inventory

| Agent          | Role                                                           | User-invokable | Pattern                                       |
| -------------- | -------------------------------------------------------------- | -------------- | --------------------------------------------- |
| orchestrator   | Classify intent, route to specialists, track progress          | Yes            | Triage + wave dispatch + pipeline enforcement |
| kanban-planner | Entry gate + feature decomposition into kanban tasks           | Yes            | Quality-enforced task creation, TDD pairing   |
| researcher     | Investigate topics, produce structured findings + kanban tasks | Yes            | Read-only, comparison tables, source-backed   |
| architect      | Review researched tasks, refine AC, approve for development    | Yes            | Gate: backlog → todo, never writes code       |
| builder        | Implement kanban tasks with TDD                                | No             | Full edit, TDD mandatory, uses tdd-workflow   |
| reviewer       | Read-only quality verification of completed work               | No             | Never edits, evidence-based, uses code-review |
| writer         | Verify and update documentation before marking done            | No             | Gate: docs → done, uses docs-gate             |
| closer         | Verify done tasks, archive confirmed, commit + push            | No             | Gate: done → archived, uses task-verification |

### Skill inventory

| Skill                    | Description                                                                                                                                                                         |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| kanban-md                | CLI reference for kanban-md — commands, flags, decision tree                                                                                                                        |
| kanban-based-development | Autonomous parallel-safe dev workflow — claims, worktrees, handoff                                                                                                                  |
| project-definition       | LLM-guided project scoping and definition workflow. Turns a vague idea into a structured ProjectDefinition through clarification, research, and iterative refinement with the user. |
| tdd-workflow             | TDD implementation workflow: read AC → write failing tests → implement → verify → advance. Used by builder agent.                                                                   |
| code-review              | Evidence-based code review workflow: run tests → lint → read code → verify AC → verdict. Used by reviewer agent.                                                                    |
| docs-gate                | Documentation gate checklist: verify and update docs before marking done. Used by writer agent.                                                                                     |
| task-verification        | Exit gate verification: verify AC with evidence → score confidence → archive or reject → commit. Used by closer agent.                                                              |

### Instruction file inventory

| File                                                 | Scoped to           | Content                                                      |
| ---------------------------------------------------- | ------------------- | ------------------------------------------------------------ |
| `.github/copilot-instructions.md`                    | Workspace           | This file — project conventions and principles               |
| `mcp.instructions.md`                                | User profile        | askQuestions conventions, tool notes, general workflow       |
| `.github/instructions/python.instructions.md`        | `**/*.py`           | Python conventions — ruff, pytest, uv, Pydantic, tenacity    |
| `.github/instructions/research-docs.instructions.md` | `docs/*.md`         | Guardrails ensuring research docs produce kanban tasks       |
| `.github/instructions/terminal.instructions.md`      | `**`                | Terminal discipline — first-call concise flags, long output  |
| `.github/instructions/agent-common.instructions.md`  | `.github/agents/**` | Shared agent rules — task discipline, evidence, tool hygiene |
| `docs/scratch/.instructions.md`                      | `docs/scratch/**`   | Naming and lifecycle rules for ephemeral scratch files       |

### Prompt file inventory

| File                                    | Agent          | Description                                                   |
| --------------------------------------- | -------------- | ------------------------------------------------------------- |
| `.github/prompts/orchestrate.prompt.md` | orchestrator   | Start orchestration with a scope filter                       |
| `.github/prompts/plan.prompt.md`        | kanban-planner | Decompose a plan into atomic, dependency-aware kanban tasks   |
| `.github/prompts/research.prompt.md`    | researcher     | Start a research investigation on a topic                     |
| `.github/prompts/architect.prompt.md`   | architect      | Review backlog tasks, refine AC, approve for development      |
| `.github/prompts/build.prompt.md`       | builder        | Implement a kanban task or feature using TDD                  |
| `.github/prompts/review.prompt.md`      | reviewer       | Review and verify task output with evidence                   |
| `.github/prompts/writer.prompt.md`      | writer         | Verify and update docs for completed tasks                    |
| `.github/prompts/closer.prompt.md`      | closer         | Verify and archive done tasks, commit + push in packages      |
| `.github/prompts/commit.prompt.md`      | _(any)_        | Group changes into logical commits with conventional messages |

## Attribution

All code and patterns taken from external sources must be logged in `docs/sources.md`.

| Column     | Description                                               |
| ---------- | --------------------------------------------------------- |
| Source     | Project or article name                                   |
| URL        | Link to the repo, article, or doc                         |
| What       | What was taken (pattern, code snippet, architecture idea) |
| Where Used | Where it appears in OwlBear (file path or module)         |
| Date       | When it was adopted                                       |

Update `docs/sources.md` whenever adopting external patterns. This ensures proper credit and traceability.
