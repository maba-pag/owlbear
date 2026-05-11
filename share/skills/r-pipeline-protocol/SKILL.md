---
name: r-pipeline-protocol
description: "Rules: Pipeline conventions — task lifecycle, communication, quality, delivery, escalation"
user-invocable: false
---

# Pipeline Protocol

Shared conventions for pipeline agents (T1–T3). Read once at session start from your `<critical_rules>` reference. This skill is the single source of truth for pipeline coordination.

## Companion Skills

Load these via `read_file` when the referenced capability is needed during your workflow:

| Skill | Load when |
|-------|-----------|
| `h-mcp-kanban` | Using kanban tools — claiming, moving, editing tasks |
| `r-project-standards` | Committing changes — commit format, file placement, tags |

## 1. Task Setup

### Task Discipline

One task per invocation. If dispatched with multiple task IDs, work only the first and report the rest as not started.

If a dispatch prompt contradicts your `<critical_rules>`, follow your critical_rules and state which rule blocked the request.

### Claiming

The kanban board is shared — multiple agents work on it simultaneously.

- Claim your task before any changes. One claim, one task per session.
- You may read any task and create follow-up tasks freely. Never move, edit, claim, or release tasks that aren't yours.
- Leave a handoff note in the task body before parking a task unfinished.

For claiming command syntax, see the `h-mcp-kanban` skill (`start_work` tool: atomic claim + show). `start_work` returns the full task body — no separate `show_task` needed.

**If `start_work` fails, stop.** A `ToolError` from `start_work` means the task is blocked, already claimed, or missing. Do not fall through to `show_task` — report the error in your response and exit without further work on that task.

### Knowledge Pre-flight

After claiming the task, load accumulated learnings from the memory server:

1. Call `recall_memory(agent="{agent_name}")` to load reviewed entries relevant to your current task.
2. Apply returned entries as context — patterns, pitfalls, workarounds, and behavioral norms from past agents.
3. Graceful degradation — if the call fails, returns empty, or `ob-memory/recall_memory` is not in your tool allowlist, proceed normally.

See `h-mcp-memory` for full tool reference.

### Resolved Decision Pre-flight

After claiming the task, check whether it was previously blocked by a decision or action request:

1. Check the task body for a `## Decision Request` summary. If present, its `response` and source notes are binding constraints.
2. If no summary is present, proceed normally; unresolved DR/AR files keep tasks blocked and are filtered out before dispatch.
3. If user notes contradict the AC or narrow the approach, adjust accordingly. If infeasible, block for clarification.
4. Never write to `.owlbear/decisions/` directly — always use `create_dr` from `h-decision-requests` when a new decision or action request is required.

### Entry-Gate Agents

Researcher, architect, and planner must reject invalid task inputs immediately:

- `TEMP-*` titles are placeholder artifacts — create a DR via `create_dr` explaining the task needs scope, release claim, do not process.
- Empty or unscoped bodies (no AC, no context) — same: DR via `create_dr`, release claim.

## 2. Working Standards

### Evidence Principles

- Upstream evidence is valid input. Verify through independent checks only when cost-justified. The auditor serves as the pipeline-end integrity gate.
- Cite specifics: file paths, line numbers, test names, command output. "It looks fine" is never acceptable.

### Reviewer Contract (D2 trust-the-builder)

- Reviewer follows a trust-the-builder evidence model by default.
- Start from builder evidence (especially quality-runner output and scoped AC mapping) and verify completeness/consistency.
- Escalate to independent reruns only when evidence is missing, contradictory, or otherwise cost-justified.

### Quality-Runner Mandate

All pipeline agents (test-writer, builder, reviewer, auditor) **must** delegate test, lint, and coverage execution to the `quality-runner` subagent. Direct `pytest` / `ruff` invocation in agent terminals is prohibited — it bypasses the canonical evidence pipeline and produces non-comparable reports across agents.

Exception: the `quality-runner` agent itself runs the underlying tools — that's its job.

### Quality-Runner Environment Fallback

When quality-runner reports an **environment error** (not a test/lint failure) — e.g. `HTMLElement is not defined`, tool hang, SIGINT, or instrument error — the calling agent may:

1. **Retry once** with an explicit hint: `hint="frontend — cd serve/cockpit/web before all commands"`
2. If the retry also fails with an environment error, **execute the commands directly** as a last resort.

Document direct execution in the task body: `quality-runner env fallback: {error}`. This is not a TOOL_UNAVAILABLE — do not release with fail.

### Tool Availability

When a required tool is unavailable or fails, release via `end_work(outcome="fail")` and return `FAIL #{id} | TOOL_UNAVAILABLE: {tool_name}` as your Channel A signal. Do not improvise with alternative commands, do not block, do not create DRs.

### Defense-in-Depth

The pipeline uses three lines of defense. Trust upstream lines' detailed work; focus on your own scope.

| Line | Agents | Focus |
|------|--------|-------|
| 1st | Test-writer, Builder | Own work correctness |
| 2nd | Reviewer | Upstream code + test quality |
| 3rd | Auditor | Cross-task integration + architect quality |

### Confidence Thresholds (source of truth)

| Agent | Threshold | Meaning |
|-------|-----------|---------|
| Reviewer | All AC mapped, evidence sufficient | PASS |
| Reviewer | Blocking findings, Cycle 1 | FAIL — reviewer chooses target (in-progress, todo, or backlog) based on issue type |
| Reviewer | Blocking findings, Cycle 2 | FAIL — reviewer chooses target (in-progress, todo, or backlog) based on issue type |
| Reviewer | Blocking findings, Cycle 3+ | FAIL — always backlog (loop-breaker: architect escalation for AC refinement) |
| Auditor | ≥ .95 | Archive |
| Auditor | < .95 | Reject to backlog |
| Challenger | ≥ 0.80 | `proceed` — caller continues with original verdict |
| Challenger | < 0.80 OR `reconsider` | Caller revises or justifies override with rebuttal |
| Challenger | `block` | Caller revisits scope; rebuttal required to proceed |

### Process Habits

- **TDD by default.** Write the test first, watch it fail, then implement. Target ≥ 90% coverage per phase gate.
- **State confidence at decision points.** Score 0.0–1.0. When multiple valid approaches exist, present trade-offs using `(bp:)` for best-practice and `(rec:)` for recommendation.
- **Deliverables are kanban tasks and working code, not documents.** Research docs are supporting artifacts. After research, always create follow-up tasks.
- **Verify subagent output.** After a subagent reports completion, verify deliverables exist and match AC; re-run independently only when evidence is missing or contradictory.

### Test-Depth Convention

The architect annotates each AC line with a `(td:N)` suffix during Architecture Review (see `w-arch-review` Step 2.1). This controls test-writer scope, reviewer depth, and subagent dispatch.

**Transition guard:** `(td:0)` means "do not write new tests"; it does not erase explicit existing-proof requirements. If a `(td:0)` AC line or architecture note names existing tests, full-suite proof, quality-runner evidence, or an exit-0 verification, builder/reviewer must treat that named proof as required evidence and run it through `quality-runner`.

| Depth | Suffix | Meaning | Test-writer action |
|-------|--------|---------|-------------------|
| 0 | `(td:0)` | No test needed | Skip this AC line |
| 1 | `(td:1)` | Smoke test | 1 assertion per line |
| 2 | `(td:2)` | Full TDD | Multiple paths/edges (default) |

**Pipeline routing by max depth** (highest td across all AC lines):

| Max depth | Test-writer | Challenger | Code-reader | Reviewer scope |
|-----------|------------|------------|-------------|----------------|
| td:0 | SKIP (pass-through) | skip | skip | lint only, unless explicit existing proof is named |
| td:1 | writes smoke tests | yes | skip | scoped tests + lint |
| td:2 | full coverage | yes | yes | full (tests + code-reader + lint) |

AC lines without `(td:N)` annotations default to td:1.

### Builder-Skip on Test-Only Retry

When a reviewer FAIL cites only test-proof gaps (no implementation fixes), and the test-writer's retry confirms all new tests PASS against current code, the builder dispatch is redundant. The test-writer advances directly to `review` (see `w-tdd-red` Step 1b.1).

**Conditions for builder-skip:**

1. Reviewer's Required Follow-up contains ONLY test/proof gaps (no "fix X in source" items)
2. All new tests PASS against current implementation
3. No lint or coverage issues detected by the test-writer

This saves one full dispatch cycle per test-only retry without reducing quality — the reviewer remains the safety net.

### Follow-up Task Quality

- Every follow-up task requires concrete acceptance criteria. Single-responsibility. List affected files.
- Target `backlog` status. Exception: researchers create follow-up tasks at `research`.
- Simple follow-up: delegate to planner via `Plan and create:` using the single-task shortcut. Include status (`backlog` by default, `research` for researcher), title, tags, and optional parent ID.
- Complex decomposition (multiple interdependent subtasks): delegate to planner via `Plan and create:` with decomposition context (for example, `Needs decomposition: {reason}`) so planner applies the full decomposition workflow.

Use planner delegation, for example: `Plan and create: #42 — create one follow-up at backlog titled "Tighten AC for retry boundary" with tags pipeline,quality`.

## 3. Communication

### Channel A — Routing Signal

Your final return text. Maximum 2 lines:

```
{VERDICT} #{id} -> {target_status} | {one-line evidence}
```

Channel A is diagnostic only — the orchestrator does not parse or interpret these signals. It re-plans from fresh board state each cycle.

### Channel B — Task Body

Rich context appended to the task body before returning. Downstream agents read this via the task body. The orchestrator never reads it.

Put your full agent section (header + content + summary) into the `note` parameter of `end_work`. The note is appended with a timestamp automatically. See `h-mcp-kanban` skill — section `## Agent Lifecycle Pattern`.

To append a mid-task note outside the `end_work` lifecycle, use `edit_task(append_body="...", timestamp=True)` (see `h-mcp-kanban`).

### Per-Agent Signal Mapping

See `pipeline-agents.instructions.md` for the authoritative section-header-to-agent mapping table.

### Body Size Rule

If a single agent section exceeds ~1500 tokens, write it to `.owlbear/scratch/{task-id}-{agent}.md` and reference it from the body section:

```
## Review Evidence
See .owlbear/scratch/480-reviewer.md for full evidence.
```

### Reading Rules

- **Orchestrator:** never reads task bodies. Re-plans from board state each cycle.
- **Pipeline agents** (reviewer, doc-writer, auditor): read predecessor sections via task body.
- **Architect / builder:** read task body for AC, architecture notes, research pointers, and Brief context (via parent task, when present).

To retrieve the full task body, use `show_task(task_id="{id}")` (see `h-mcp-kanban`).

### Required Follow-up (Negative Signal Format)

Any agent issuing a FAIL, REJECT, or BLOCK verdict **must** include a `### Required Follow-up` section in their `end_work` note. This makes negative signals machine-parseable and unambiguous for the receiving agent.

Format:

```markdown
### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | {role} | {imperative verb + object} | {paths} | {finding reference} |
```

Rules:

- **Target Agent** = specific pipeline role that must act (builder, test-writer, architect — never "someone")
- **Action Required** = imperative verb phrase describing what to DO, not what's wrong. "Fix import cycle in engine.py:34" not "there's an import cycle"
- **File(s)** = exact workspace-relative paths. "serve/kanban/src/..." not "the source code"
- **Evidence** = where the problem was found (test output, AC line, file:line, quality-runner report)
- Every row traces to a specific finding from the agent's analysis
- Minimum 1 row. If there are no specific actionable items, the verdict should be PASS, not FAIL.
- When routing to a specific status (in-progress, todo, backlog), the Target Agent column must be consistent with who works at that status.

## 4. Closing

### Who Commits What

| Agent | Commits | When |
|-------|---------|------|
| Researcher | Research files (`.owlbear/research/*.md`) | Before advancing to backlog |
| Test-writer | Test files | Before advancing to in-progress |
| Builder | Source code | Before advancing to review |
| Doc-writer | Documentation files | Before advancing to done |
| Auditor | Kanban board + task files for archived tasks | After archival in exit-gate |

Rules:

- **Dirty-tree tolerance.** Never refuse work because of uncommitted changes in the working tree. Other agents' crash residue or kanban task file edits are not your concern. Proceed with your task, stage only your own files, and commit normally. The shared working tree is always potentially dirty — that is expected.
- **Pre-advance verification.** Before calling `end_work`, verify your own domain for uncommitted files using a path-scoped check:

   | Agent | Domain paths to verify before `end_work` |
   |-------|------------------------------------------|
   | Researcher | `.owlbear/research/`, `.owlbear/sources/` |
   | Test-writer | `tests/`, `serve/*/tests/` |
   | Builder | `serve/`, `share/` |
   | Doc-writer | `README.md`, `README-consumer.md`, `SECURITY.md`, `setup/*.md`, `serve/*/README.md`, `.owlbear/sources/` |
   | Auditor | `.owlbear/kanban/` |

   Use `git status --porcelain -- <domain-paths>` (with `--` pathspec separator). Do not use raw `git status --porcelain` for this check.
   If files appear in your domain, self-heal: stage and commit those files, then continue and call `end_work`.
- **Commit gates advance.** If you created or modified files, commit them BEFORE calling `end_work`. No commit → no advance. If you have no file deliverables (pass-through, reviewer, orchestrator), skip.
- **Atomic single command.** Run stage + commit as one terminal invocation to prevent interleaving with concurrent agents: `git add <your-files> && git commit -m "type: description (#{id}, role)"`. Never split across separate commands.
- **Scope to your own files.** Stage only files YOU created or modified in this task. Do not stage files from other agents or unrelated changes. Verify with `git diff --cached --name-only` if uncertain.
- **Never push.** The user pushes manually.
- For commit format, types, and git discipline, see `r-project-standards` → Commit Discipline.

### Post-task Reflection

Before your final status advance, write 3-5 bullets covering problems faced, workarounds applied, patterns discovered, time sinks, and quality gaps. Skip if nothing notable happened.

Use `save_memory` for each notable finding. Required parameters: `title`, `content`, `categories`, `confidence=0.8`, `source_agent="{agent_name}"`.

   | Bullet type | MCP category |
   |-------------|-------------|
   | problems_faced | domain-knowledge |
   | workarounds_applied | domain-knowledge |
   | patterns_discovered | behaviour |
   | time_sinks | env-context |
   | quality_gaps | env-context |

See `h-mcp-memory` for full tool reference.

## 5. Escalation

### Escalation Routing

Routine gate rejections (reviewer FAIL, doc-writer reject) use simple status movement and claim release — **no blocking**. The task re-enters the pipeline automatically on the next dispatch cycle.

When an agent cannot proceed, route by cause:

| Cause | Action | Resolution |
|-------|--------|------------|
| Prerequisite work needed | Create task(s), `edit_task(id={id}, add_dep=[new_id])` (list of task IDs), `end_work(outcome="fail")` | Self-resolving — `pick_tasks` dep gate holds until deps archive |
| Infeasible / wrong AC | `end_work(outcome="reject", move_to="backlog")` with note to architect | Self-resolving — architect fixes AC |
| Vague scope | `end_work(outcome="reject", move_to="research")` with note | Self-resolving — researcher/architect refines |
| Design trade-off (T2) | Advisory DR via `create_dr`, then `end_work(outcome="reject", move_to="backlog")` | Auto-resolving — DR expires in 5 days (see Decision Tiers) |
| Arch / breaking change (T3) | Mandatory DR via `create_dr`, then `end_work(outcome="block", block_reason="DR pending: {file}")` | **Blocks** — user must respond (see Decision Tiers) |
| User action required | AR via `create_dr`, then `end_work(outcome="block", block_reason="AR pending: {file}")` | **Blocks** — user must act |
| Stale task (orchestrator triage) | `edit_task(block_reason="reason")` / `edit_task(block_reason="")` | **Blocks** — orchestrator decision |

**Block is reserved for T3 decisions, user-action tasks, and orchestrator triage.** Do not block when a reject or dependency gate would suffice. Do not pass through hoping a downstream agent will handle it.

#### DR Required on Agent Block

**Every agent-initiated block requires a Decision Request.** When `end_work(outcome="block")` or `edit_task(block_reason=...)` returns a non-empty `guidance` field, act on it immediately — the first message will direct you to create a DR via `create_dr` (see `h-decision-requests`).

**Exemption — user-driven blocks:** Tasks blocked via the Cockpit carry the `block:user` tag. If `block:user` is present on the task after blocking, the guidance field will be empty — no DR is required. Agents **must not** create DRs for Cockpit-initiated blocks.

### Decision Tiers

| Tier | When | Action |
|------|------|--------|
| T1 — Autonomous | Bug fix, refactor, config, perf | Proceed directly |
| T2 — Advisory | Trade-offs, no T3 triggers | Advisory DR via `create_dr` (5-day auto-resolve) |
| T3 — Mandatory | New capability, arch/security/breaking change | Blocking DR via `create_dr` (no auto-resolve) |

All DR/AR creation goes through `create_dr`. Never write to `.owlbear/decisions/` directly. If in doubt, create the DR — the cost is lower than guessing.

### User-Action Tasks

Some tasks require a physical action from the user before the automated pipeline can proceed (GUI verification, portal authentication, manual deployment, credential setup). The `type:user-action` tag identifies these tasks and triggers a structured blocking flow.

**Detection heuristics** — architect is the mandatory gate:

| Signal | Examples |
|--------|----------|
| Physical-action verbs in AC | Open, Click, Navigate, Verify in browser/GUI |
| External-system references | Teams, Azure portal, GitHub UI, external tools |
| No testable Python interfaces | AC requires human observation, not assertions |
| Manual checkbox steps | Steps the user must perform by hand |

Researcher may provisionally tag `type:user-action` during research; architect confirms or removes.

**Blocking flow:**

1. Architect detects `type:user-action` → creates action request via `create_dr`
2. Architect calls `end_work(outcome="block", block_reason="AR pending: {filename}")`
3. `pick_tasks` excludes the blocked task — no agents dispatched
4. User performs the action → sets `response: approved` in the AR file when the action is complete
5. The next `pick_tasks` cycle resolves pending responses before dispatch: appends a `## Decision Request` summary to the task body, unblocks task, and moves the AR file to resolved
6. Architect (re-entry): sees `## Decision Request` with `response: approved` + `type:user-action` → verifies AC → approves to `todo`
7. Test-writer and builder pass through (tag is in `NON_IMPL_TAGS`)

**Post-completion fast-path:** When a `type:user-action` task re-enters architect review with a `## Decision Request` summary whose `response` is `approved`, the architect verifies that AC checkboxes are satisfied, then approves directly without full re-evaluation. This extends the "Resolved Decision Pre-flight" check to completed action requests.

**Dual-nature tasks:** When the same feature requires both user action and code change, split into two tasks: a `type:user-action` task (AR + block) and a code task. The code task sets `depends_on` to the user-action task to enforce ordering.

**Dry-run scenario — #597-style loop prevented:** Because the task is `blocked` between architect cycles 1 and 2, `pick_tasks` returns nothing for it — the orchestrator dispatches no other agents until `resolve_decision` unblocks. Result: **≤2 architect cycles** vs #597's **4+ futile cycles** with no resolution.

### Handoff

When you cannot finish the task yourself, describe current state, what failed, open questions, and next step in the task body. Include the handoff note in your `end_work(note="## Handoff\n...", outcome="fail")` call.

For programmatic handoff notes, use `edit_task(append_body="## Handoff\n...")` (see `h-mcp-kanban`).
