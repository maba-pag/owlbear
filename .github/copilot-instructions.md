# OwlBear — Copilot Workspace Instructions

## Project purpose

OwlBear is an always-on, laptop-resident AI development system. It receives user intent (via CLI, Teams, or voice), extracts intent, plans work, executes it autonomously, and delivers results — with human approval gates for destructive or publishing actions. It owns the full build pipeline (ideation → spec → code → test → review → deliver) and operates as a standalone daemon process. VS Code remains the user's IDE for interactive work; OwlBear and VS Code share the filesystem (code, kanban board, sessions) as the integration point.

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

| Component           | Technology                  | Notes                                                                   |
| ------------------- | --------------------------- | ----------------------------------------------------------------------- |
| Language            | Python 3.12+                | `uv` package manager, never bare `pip`                                  |
| Runtime             | Standalone daemon           | Background process started via BearClaw CLI                             |
| Agents              | PydanticAI                  | Structured output, dependency injection                                 |
| LLM provider        | GitHub Copilot OAuth        | Device-flow auth, `api.individual.githubcopilot.com`                    |
| Retry               | tenacity                    | Exponential backoff, jitter, max 5 attempts                             |
| CLI                 | Typer (BearClaw)            | Entry point for daemon, auth, and user commands                         |
| HTTP                | httpx + truststore          | Async HTTP client with system certificate trust                         |
| Config              | pydantic-settings           | Env vars + TOML config file, validated at startup                       |
| Knowledge (planned) | Knowledge graph + vector DB | Structured memory with embeddings; DB tech TBD                          |
| Browser             | Playwright                  | Launch or attach via CDP (`localhost` only); see `bearclaw browser` CLI |
| Voice (planned)     | Whisper STT + pyttsx3 TTS   | Local-first voice I/O                                                   |
| Task board          | kanban-md                   | Go CLI binary in `kanban/`, file-based kanban                           |

## kanban-md usage

The project uses [kanban-md](https://github.com/antopolskiy/kanban-md) (v0.33.0) for file-based task management. The binary lives at `kanban/kanban-md.exe` (gitignored); run `kanban/setup.ps1` to download it.

For CLI commands, workflows, and cheatsheets, see the `kanban-md` and `kanban-based-development` skills. The sections below cover only **OwlBear-specific** conventions that override or extend the defaults.

### Board structure

- **Config:** `kanban/config.yml` — statuses: ideation → backlog → todo → in-progress → review → docs → done
- **Tasks:** `kanban/tasks/*.md` — YAML frontmatter (id, title, status, priority, tags, depends_on) + body with acceptance criteria

### No worktrees

The `kanban-based-development` skill describes a git-worktree workflow. **We do not use worktrees.** VS Code Copilot operates in a single workspace. Make code changes in place on the main branch.

### Task lifecycle — statuses, roles, and quality gates

The pipeline has 7 statuses. Each transition is owned by a specific role and guarded by explicit exit criteria. Research is not a status — it is the work that happens inside `ideation` before a task can graduate to `backlog`.

| Status        | Meaning                                              | Owner      | Exit criteria (to move forward)                                |
| ------------- | ---------------------------------------------------- | ---------- | -------------------------------------------------------------- |
| `ideation`    | Raw idea captured, not yet researched                | Anyone     | —                                                              |
| `backlog`     | Researched, refined AC, approach documented          | Researcher | Research checklist completed (see below)                       |
| `todo`        | Architect-approved, unblocked, ready for dev         | Architect  | AC refined, architectural review done, may split/merge/expand  |
| `in-progress` | Actively being implemented (TDD)                     | Dev        | —                                                              |
| `review`      | Code + tests complete, needs verification            | Dev        | Tests pass, ruff clean, AC met                                 |
| `docs`        | Docs gate — verify/update all relevant documentation | Reviewer   | Verified against architect's instructions, may demo to user    |
| `done`        | Verified complete                                    | Writer     | README, copilot-instructions, docstrings, sources.md as needed |

### Agent roles and movement authority

| Role       | Moves                    | Responsibility                                                                                 |
| ---------- | ------------------------ | ---------------------------------------------------------------------------------------------- |
| Anyone     | → `ideation`             | Capture ideas. Minimal description is fine.                                                    |
| Researcher | `ideation` → `backlog`   | Completes the research checklist. Documents findings in task body or linked doc.               |
| Architect  | `backlog` → `todo`       | Reviews research, refines/splits/merges AC, ensures architectural soundness, approves for dev. |
| Dev        | `todo` → `in-progress`   | Claims task, starts TDD implementation.                                                        |
| Dev        | `in-progress` → `review` | Implementation and tests complete, lint clean.                                                 |
| Reviewer   | `review` → `docs`        | Verifies implementation against architect's instructions, may re-test, may demo to user.       |
| Writer     | `docs` → `done`          | Adds/updates documentation, archives research materials, verifies docs-gate checklist.         |

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
| Phase        | `phase-1`, `phase-2`, `phase-3`, `phase-4`                  | Group tasks by project phase    |
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
11. Phase gate:     coverage >= 90%, all tests green, ruff clean
```

### Agent inventory

| Agent          | Role                                                             | Pattern                                        |
| -------------- | ---------------------------------------------------------------- | ---------------------------------------------- |
| kanban-planner | Use when a plan or feature needs decomposition into kanban tasks | User-invokable, TDD-first decomposition        |
| orchestrator   | Use when tasks need to be executed from the kanban board         | User-invokable, wave-based parallel execution  |
| researcher     | Investigate topics, produce structured findings + kanban tasks   | Read-only, comparison tables, source-backed    |
| architect      | Review researched tasks, refine AC, approve for development      | Gate: backlog → todo, never writes code        |
| builder        | Implement kanban tasks with TDD                                  | Full edit access, TDD mandatory, surgical diff |
| reviewer       | Read-only quality verification of completed work                 | Never edits, evidence-based PASS/FAIL verdict  |
| writer         | Verify and update documentation before marking done              | Gate: docs → done, edits docs only             |

### Skill inventory

| Skill                    | Description                                                        |
| ------------------------ | ------------------------------------------------------------------ |
| kanban-md                | CLI reference for kanban-md — commands, flags, decision tree       |
| kanban-based-development | Autonomous parallel-safe dev workflow — claims, worktrees, handoff |

### Instruction file inventory

| File                                                 | Scoped to         | Content                                                   |
| ---------------------------------------------------- | ----------------- | --------------------------------------------------------- |
| `.github/copilot-instructions.md`                    | Workspace         | This file — project conventions and principles            |
| `mcp.instructions.md`                                | User profile      | askQuestions conventions, tool notes, general workflow    |
| `.github/instructions/python.instructions.md`        | `**/*.py`         | Python conventions — ruff, pytest, uv, Pydantic, tenacity |
| `.github/instructions/research-docs.instructions.md` | `docs/*.md`       | Guardrails ensuring research docs produce kanban tasks    |
| `docs/scratch/.instructions.md`                      | `docs/scratch/**` | Naming and lifecycle rules for ephemeral scratch files    |

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
