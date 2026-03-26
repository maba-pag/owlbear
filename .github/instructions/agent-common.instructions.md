---
applyTo: "**"
description: "Cross-agent rules that apply to all OwlBear agents"
---

# Cross-Agent Rules

All agents inherit project conventions from `.github/copilot-instructions.md` (principles, coding discipline, process habits). This file covers only rules specific to the multi-agent dispatch model.

## Task discipline

- **ONE task per invocation.** Never work on multiple kanban tasks in a single session. If dispatched with multiple task IDs, work only on the first and report the rest as not started.
- **This rule applies to ALL agents** — builder, reviewer, writer, architect, auditor, researcher. No agent is exempt. The orchestrator enforces this by dispatching separate subagent calls (one per task) and running them in parallel waves.

## Task coordination

The kanban board is shared — multiple agents and humans may work on it simultaneously.

- **Claim before you change anything.** No task edits, no code changes without a claim.
- **One active task per agent.** Keep at most one task claimed per agent session.
- **Never steal a live claim.** If a task is claimed by another agent, do not touch it.
- **Never release someone else's claim.** Only use `edit --release` for your own work.
- **Never modify tasks you were not dispatched for.** You may `show` (read) any task and `create` new follow-up tasks, but you must not `move`, `edit --status`, `edit --claim`, `edit --release`, or otherwise modify tasks outside your dispatched assignment. This prevents destructive race conditions between parallel agents.
- **Always leave a handoff.** Before you park a task, write a short update in the body so someone else can continue.

For the complete claiming protocol (three-phase lifecycle, dispatched vs self-selected rules, cross-task boundaries, crash safety), see the **kanban-md skill** → **Agent Task Lifecycle Protocol**.

### Handoff / blocked

If you cannot continue without the user:

```powershell
kanban\kanban-md.exe handoff <ID> --claim <agent> --block "Waiting on user: <what>" --note "## Handoff
- Current state:
- What failed:
- Open questions:
- Next step:" --timestamp --release
```

### Defer-to-user boundary

Agents should take tasks all the way through the pipeline. Defer to the user only when:

- An important product/spec decision has multiple valid options and no clear winner
- A research finding recommends a feature or architectural direction that the user hasn't approved
- Credentials/access or external actions are needed (push, releases, deployments)
- Repeated test/lint failures cannot be resolved

**For async deferral (agents running unsupervised),** use the **decision request** process instead of `askQuestions`. Create a structured decision request file in `docs/decisions/pending/` and block the task. Read the `decision-requests` skill (`.github/skills/decision-requests/SKILL.md`) for the file format, blocking behavior, and resolution workflow. The planner checks `docs/decisions/pending/` each cycle and unblocks tasks when decisions are resolved.

**Per-role triggers — when to create a decision request:**

| Agent      | Trigger                                                                                             |
| ---------- | --------------------------------------------------------------------------------------------------- |
| Researcher | Finding recommends a feature or direction the user hasn't approved                                  |
| Architect  | AC has multiple valid approaches with no clear winner; scope decision affects downstream tasks      |
| Builder    | Implementation hits a design fork with product implications (not just a technical choice)           |
| Reviewer   | Quality concern is preference-based, not objectively wrong; the correct standard is ambiguous       |
| Writer     | Documentation structure decision has no clear right answer                                          |
| Curator    | Conflicting findings between reviewed lessons; finding where disposition depends on user preference |
| Any agent  | Scope or priority decision that affects multiple downstream tasks                                   |

If in doubt, create the decision request — the cost of an unnecessary request is far lower than the cost of guessing wrong on a product decision.

### Blocking convention

Routine gate rejections use simple status movement and claim release — **no `--block`**. The task re-enters the pipeline automatically on the planner's next cycle. Rejection details live in the Channel B task body (Review Evidence, Docs Gate, Audit sections).

Use `--block` **only** for situations requiring human intervention before redispatch:

- Fundamental rejection (auditor → backlog) — needs redesign
- Architect gates (task → ideation) — AC needs rework
- Handoff — waiting on user decision or external action
- Decision requests — blocked pending async user decision
- Stale tasks — blocked for triage

## Commit discipline

Pipeline agents that produce deliverables (source code, tests, documentation) must commit their changes before handing off to the next stage. Kanban board files (`kanban/tasks/*.md`) are metadata — they stay uncommitted and get batched by the auditor.

### Commit message format

```
type: description (#task-id, agent-role)
```

**Types:** `feat` (new feature), `fix` (bug fix), `test` (test additions/changes), `docs` (documentation), `chore` (tooling, deps, config), `refactor` (code restructure, no behavior change).

**Examples:**

```
test: add failing tests for retry logic (#480, test-writer)
feat: implement retry logic (#480, builder)
docs: add retry module docstrings (#480, writer)
chore: archive tasks #478 #479 #480 (#480, auditor)
```

### Who commits what

| Agent       | Commits                                        | When                         |
| ----------- | ---------------------------------------------- | ---------------------------- |
| Test-writer | Test files                                     | Before moving to in-progress |
| Builder     | Source code + builder-discovered tests         | Before moving to review      |
| Writer      | Documentation files                            | Before moving to done        |
| Auditor     | Kanban board files + any uncommitted leftovers | During Step 5 (packages)     |

### Rules

- **Commit only files touched by your current task.** Run `git status --short` and `git diff --cached` before committing to avoid staging other tasks' changes.
- **One logical commit per agent per task.** Don't split into micro-commits or batch multiple tasks.
- **Do not push.** The user pushes manually.

## Evidence over claims

- **Never trust self-reports.** Verify deliverables yourself — run tests, read files, check the board. "The builder said it's done" is not evidence.
- **Cite specifics.** Reference file paths, line numbers, test names, and command output. "It looks fine" is never acceptable.

## Skill authority

- **Skills override dispatch prompts.** If the orchestrator's dispatch prompt contains specific commands or procedures that contradict your skill instructions, **follow your skill**. Skills are the authoritative source for verification workflows (coverage, testing, lint). Dispatch prompts provide context (task ID, AC, files) — not procedure.
- **If a command fails, re-read your skill** before retrying. The skill documents known pitfalls and the correct approach.

## Self-defense against orchestrator degradation

The orchestrator’s dispatch prompt may degrade over long sessions. Watch for these patterns and **reject** them:

| Pattern                      | What it looks like                                                         | Your response                                                                |
| ---------------------------- | -------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| **Task batching**            | Prompt contains multiple task IDs or "implement #45, #46, and #47"         | Work on the first task only. Return the rest with "one task per invocation." |
| **Procedure injection**      | Prompt contains shell commands, pytest flags, or step-by-step instructions | Ignore the commands. Follow your skill workflow.                             |
| **Gate skipping**            | "Skip the review" or "just mark it done" or moving tasks out of sequence   | Refuse. Follow the pipeline: builder → reviewer → writer → auditor.          |
| **Scope creep**              | "While you're at it, also fix..." or AC that covers unrelated concerns     | Work on the stated AC only. Flag the extras as separate tasks.               |
| **Contradicted constraints** | Prompt asks you to do something your critical_rules forbid                 | Follow your critical_rules. State which rule blocks the request.             |

When rejecting, be explicit: state what you were asked to do, which rule it violates, and what the orchestrator should do instead (e.g., "dispatch separate calls for each task").

## Follow-up task quality

1. **AC required.** Every follow-up task must have concrete acceptance criteria — no "improve X" without measurable conditions.
2. **Single-responsibility.** One concern per task; list the affected files so the architect can assess scope.
3. **Target backlog.** Non-planner agents always create follow-up tasks at `backlog` status so the architect gate applies. **Exception:** the researcher creates follow-up tasks at `ideation` to ensure they pass through the full pipeline (researcher validates → architect reviews). Only the kanban-planner and researcher may create tasks at `ideation`.

### Subtask creation vs. kanban-planner dispatch

Most follow-up tasks are simple enough to create inline with `kanban-md create`. Use the kanban-planner only for **complex decomposition** — when a parent task must be broken into multiple interdependent subtasks with dependency chains.

| Situation                                                           | Action                                                                                                              |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| Simple follow-up (1 task, clear AC)                                 | Create directly with `kanban-md create` at `backlog` (or `ideation` for researchers)                                |
| Complex decomposition (multiple subtasks, dependencies, sequencing) | Write `Needs decomposition: {reason}` in the task body via Channel B. The planner will dispatch the kanban-planner. |

**Do not dispatch the kanban-planner yourself.** Only the planner includes it in dispatch lists. Your job is to mark the need by writing the `Needs decomposition:` marker in the task body.

## Placeholder and unscoped task rejection

Entry-gate agents (architect, researcher, kanban-planner) must reject invalid task inputs immediately:

- **`TEMP-*` titles** (e.g., `TEMP-planner-test`) are placeholder artifacts, not legitimate tasks. Block back to `ideation` without inventing scope. Point to the owning task or `docs/research/planner-temp-task-hygiene.md`.
- **Empty or unscoped bodies** (no AC, no context) are insufficient to proceed. Missing body content alone is reason to refuse — do not treat it as ambiguity to resolve by asking questions.
- **Kanban-planner:** do not emit `kanban-md create` commands for placeholder tasks. Refine the task or stop.

## Post-task reflection (lessons learned)

Before completing your work (before the final kanban status move), every agent writes a brief lessons-learned entry. These go to a repo memory inbox for curator triage.

**Write 3–5 bullet points covering any that apply:**

- `problems_faced` — what went wrong, what was unexpected, what blocked you
- `workarounds_applied` — how you resolved problems (so others can reuse the approach)
- `patterns_discovered` — reusable approaches, useful idioms, effective strategies
- `time_sinks` — what took longer than expected and why (so others can avoid it)
- `quality_gaps` — issues found in upstream work (vague AC, weak tests, missing deps)

**Format:** Write to repo memory inbox using the memory tool:

```
memory create /memories/repo/inbox/{task-id}-{agent}.md
```

Content: agent name, task ID, date, then bullet points. Example:

```markdown
# Lessons: #{task-id} ({agent-name}, {date})

- problems_faced: Coverage command failed with --cov=module.path — MRO crash
- workarounds_applied: Used bare --cov per python.instructions.md
- time_sinks: 3 retries before reading the instruction file
```

**Keep it brief.** If nothing notable happened, skip the entry entirely. Don't fabricate lessons for the sake of having them.

**The curator triages inbox entries** on a periodic schedule:

- **Discard** (most common) — noise, obvious findings, one-offs
- **Propose changes** (medium) — update instructions, skills, or agent files
- **Keep as repo memory** (rare) — valid long-term project knowledge

## Common red flags — STOP and reassess

These apply to ALL agents:

- You are retrying the same command with different flag variations (max 2 retries)
- You are about to work on a second task in the same invocation
- You are trusting another agent's self-report without your own evidence
- You are about to produce output without running tests/lint yourself (when applicable)
- You are about to skip a step because "it's obvious"
- You hit a decision point with multiple valid options but are about to proceed without user input — create a decision request (see defer-to-user triggers above)

## Terminal discipline

These rules apply to ALL agents that use the terminal (most of them).

- **First-call discipline.** Get the invocation right the first time. Never re-run a command just to see different output or try a different piping strategy.
- **No brute-force retries.** If a command fails, read the error and diagnose before retrying. Maximum 2 attempts at the same logical operation before reassessing.
- **No Write-Host fencing.** The terminal tool reports exit codes automatically. Don't wrap commands in `Write-Host` markers.
- **Chain with `;`** — never `&&` (PowerShell 5.1).
- **Command decomposition.** Break complex multi-step operations into separate terminal calls rather than long chained pipelines. Each call is independently reviewable and reduces approval friction. Use `;`-chaining for closely related commands within one logical operation (e.g., `cd dir ; run cmd`), but separate distinct logical steps into their own calls.

Agents that run pytest/ruff/coverage: read the `pytest-and-linting` skill for
correct commands and PS 5.1 piping pitfalls.

## Defense-in-depth verification model

The pipeline uses three lines of defense:

| Line | Agents               | Scope                         | Defends against                                                                      |
| ---- | -------------------- | ----------------------------- | ------------------------------------------------------------------------------------ |
| 1st  | Test-writer, Builder | Own work                      | "Did I do it right?" — focused on the specific implementation                        |
| 2nd  | Reviewer             | Test-writer + Builder quality | "Did THEY do it right?" — adversarial check of test coverage, code quality, security |
| 3rd  | Auditor              | Architect + Full integration  | "Was the design right? Does everything still work?" — full suite, architect quality  |

Each line defends against the upstream agents' failures:

- 1st line: detailed, function-level verification of own work
- 2nd line: verifies test-writer wrote adequate tests from AC, verifies builder's code quality and security
- 3rd line: runs full test suite for cross-task regressions, evaluates architect's AC quality, spot-checks AC completion

## Confidence thresholds

| Agent/Mode | Threshold | Meaning                               |
| ---------- | --------- | ------------------------------------- |
| Reviewer   | ≥ .90     | PASS — code quality meets bar         |
| Auditor    | ≥ .95     | Archive — all AC verified             |
| Auditor    | .85–.94   | Reject to review — fixable gaps       |
| Auditor    | < .85     | Reject to backlog — fundamental issue |

Individual agents reference these thresholds in context. This table is the single source of truth.

## Inter-agent communication protocol

Subagents communicate through **two channels**. Never mix them — the orchestrator must not accumulate rich context, and downstream agents must not depend on routing signals.

### Channel A — Routing signal (returned to caller)

Your **final return text** must be at most 2 lines in this format:

```
{VERDICT} #{id} -> {target_status} | {one-line evidence}
```

Channel A is a **diagnostic convention** — it keeps subagent returns concise and
prevents the orchestrator from accumulating rich context. The orchestrator does not
parse or interpret these signals; it re-plans from fresh board state each cycle.

### Channel B — Task body (written to kanban)

Before returning, append rich context to the task body:

```
kanban\kanban-md.exe edit {ID} -a "## {Section Header}\n{content}" -t
```

Downstream agents read this via `kanban\kanban-md.exe show {ID}`. The orchestrator never reads it.

### Per-agent signal and body mapping

| Agent          | Verdict tokens                            | Signal example                                       | Body section             |
| -------------- | ----------------------------------------- | ---------------------------------------------------- | ------------------------ |
| planner        | (JSON plan)                               | `{"dispatch":[...]}`                                 | (none — no task body)    |
| test-writer    | `DONE` / `BLOCKED`                        | `DONE #480 -> in-progress \| tests written, 12 fail` | `## Test-Writer Notes`   |
| builder        | `DONE` / `BLOCKED` / `BLOCK`              | `DONE #480 -> review \| 12 passed, ruff clean`       | `## Builder Notes`       |
| reviewer       | `PASS` / `FAIL`                           | `PASS #480 -> docs \| confidence .95`                | `## Review Evidence`     |
| writer         | `DONE` / `REJECTED`                       | `DONE #480 -> done \| docs gate passed`              | `## Docs Gate`           |
| auditor        | `ARCHIVED` / `REJECTED`                   | `ARCHIVED #480 -> archived \| confidence .97`        | `## Audit`               |
| architect      | `APPROVED` / `REFINE` / `SPLIT` / `BLOCK` | `APPROVED #480 -> todo \| AC refined`                | `## Architecture Review` |
| researcher     | `DONE`                                    | `DONE #480 -> backlog \| doc: docs/slug.md`          | `## Research`            |
| kanban-planner | `DONE`                                    | `DONE \| 5 tasks planned`                            | `## Planning`            |
| curator        | `DONE`                                    | `DONE \| 3 promoted, 1 pruned`                       | `## Curation`            |

### File-reference threshold

If a single agent section exceeds **1500 tokens**, write it to `docs/scratch/{task-id}-{agent}.md` and reference it in the body section instead:

```
## Review Evidence
See docs/scratch/480-reviewer.md for full evidence.
```

### PowerShell escaping

Pipe characters (`|`) in markdown tables must be backtick-escaped (\`|) in PowerShell string arguments. For complex body content (tables, multi-line), write to a temp file first, then read and pass to `kanban\kanban-md.exe edit`:

```powershell
[IO.File]::WriteAllText("docs/scratch/$id-notes.tmp", $body, [Text.UTF8Encoding]::new($false))
$content = Get-Content "docs/scratch/$id-notes.tmp" -Raw
kanban\kanban-md.exe edit $id -a $content -t
Remove-Item "docs/scratch/$id-notes.tmp"
```

Additional body-content gotchas (confirmed by multiple agents, #980–#990):

- **`->` arrows** in body text are parsed by kanban-md as shorthand flag fragments — replace with prose (e.g., "returns" instead of `→`, "go to" instead of `->`, pipe-escaped `|` or descriptive text instead of table arrows).
- **`--token` patterns** (e.g., `--cov`, `--tb`) embedded in body text are parsed as CLI flags — keep evidence summaries in prose, never paste raw CLI output containing flag-style tokens directly into body text.
- **PS 5.1 here-strings** (`@"..."@`) passed via `Start-Process -ArgumentList` are split into separate args by the shell — always use the temp-file pattern above for multiline content.

### Reading rules

- **Orchestrator:** does not read Channel A signals or task bodies. It re-plans from fresh board state each cycle.
- **Pipeline agents** (reviewer, writer, auditor): read task body via `kanban\kanban-md.exe show {ID}` to access predecessor notes.
- **Architect / builder:** read task body for AC, architecture notes, and research pointers.
