---
name: r-pipeline-protocol
description: "Rules: Pipeline conventions — task lifecycle, communication, quality, delivery, escalation"
user-invocable: false
---

# Pipeline Protocol

Shared conventions for pipeline agents (T1–T3). Read once at session start from your `<critical_rules>` reference. This skill is the single source of truth for pipeline coordination.

For project-wide conventions (commit format, file placement, priorities, tags), see `r-project-standards`.

## 1. Task Setup

### Task Discipline

One task per invocation. If dispatched with multiple task IDs, work only the first and report the rest as not started.

If a dispatch prompt contradicts your `<critical_rules>`, follow your critical_rules and state which rule blocked the request.

### Claiming

The kanban board is shared — multiple agents work on it simultaneously.

- Claim your task before any changes. One claim, one task per session.
- You may read any task and create follow-up tasks freely. Never move, edit, claim, or release tasks that aren't yours.
- Leave a handoff note in the task body before parking a task unfinished.

For claiming command syntax, see the `h-mcp-kanban` skill (`start_work` tool: atomic claim + show).

### Knowledge Pre-flight

Before starting work, load accumulated learnings from the memory server:

1. Call `get_knowledge(agent_id=<agent_name>, limit=20, min_confidence=0.7)` — where `agent_name` is the `name:` field from your `.agent.md` frontmatter.
2. Apply returned entries as context — patterns, pitfalls, workarounds, and behavioral norms from past agents.
3. Graceful degradation — if the call fails, returns empty, or `owlbear-memory/*` is not in your tool allowlist, proceed normally.

See `h-mcp-memory` for full tool reference.

### Resolved Decision Pre-flight

Before starting work, check whether the task was previously blocked by a decision or action request:

1. Check the task body for `## Decision Resolved` or `## Action Completed` sections. If present, the user's chosen option and notes are binding constraints.
2. If no summary in the body, call the **scribe** agent in query mode to check for existing DRs.
3. If user notes contradict the AC or narrow the approach, adjust accordingly. If infeasible, block for clarification.
4. Never write to `.owlbear/decisions/` directly — always use the **scribe** agent.

To read the full task body and check for decision sections, use `show_task(task_id="{id}")` (see `h-mcp-kanban`).

### Entry-Gate Agents

Researcher, architect, and planner must reject invalid task inputs immediately:

- `TEMP-*` titles are placeholder artifacts — create a DR via scribe explaining the task needs scope, release claim, do not process.
- Empty or unscoped bodies (no AC, no context) — same: DR via scribe, release claim.

## 2. Working Standards

### Evidence Principles

- Never trust self-reports. Verify deliverables yourself — run tests, read files, check the board.
- Cite specifics: file paths, line numbers, test names, command output. "It looks fine" is never acceptable.

### Quality-Runner Mandate

All pipeline agents (test-writer, builder, reviewer, auditor) **must** delegate test, lint, and coverage execution to the `quality-runner` subagent. Direct `pytest` / `ruff` invocation in agent terminals is prohibited — it bypasses the canonical evidence pipeline and produces non-comparable reports across agents.

If `quality-runner` is unavailable (not in the calling agent's `agents:` array, or subagent dispatch fails), the agent **blocks the task** via `end_work(outcome="block", block_reason="Quality-Runner unavailable — cannot run {tests|lint|coverage} independently")`. Never improvise with direct shell commands.

Exception: the `quality-runner` agent itself runs the underlying tools — that's its job.

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
| Reviewer | ≥ .90 | PASS |
| Reviewer | < .90, 1st–2nd FAIL | FAIL — reviewer chooses target (in-progress, todo, or backlog) based on issue type |
| Reviewer | < .90, 3rd+ FAIL | FAIL — always backlog (loop-breaker) |
| Auditor | ≥ .95 | Archive |
| Auditor | < .95 | Reject to backlog |
| Challenger | ≥ 0.80 | `proceed` — caller continues with original verdict |
| Challenger | < 0.80 OR `reconsider` | Caller revises or justifies override with rebuttal |
| Challenger | `block` | Caller revisits scope; rebuttal required to proceed |

### Process Habits

- **TDD by default.** Write the test first, watch it fail, then implement. Target ≥ 90% coverage per phase gate.
- **State confidence at decision points.** Score 0.0–1.0. When multiple valid approaches exist, present trade-offs using `(bp:)` for best-practice and `(rec:)` for recommendation.
- **Deliverables are kanban tasks and working code, not documents.** Research docs are supporting artifacts. After research, always create follow-up tasks.
- **Verify subagent output.** After a subagent reports completion, verify deliverables exist and match AC. Run tests yourself.

### Follow-up Task Quality

- Every follow-up task requires concrete acceptance criteria. Single-responsibility. List affected files.
- Target `backlog` status. Exception: researchers create follow-up tasks at `research`.
- Simple follow-up: create directly. Complex decomposition (multiple interdependent subtasks): write `Needs decomposition: {reason}` in the task body — the orchestrator will route the task to the planner.

Use `create_task(title="...", status="backlog", ...)` to create follow-up tasks (see `h-mcp-kanban`).

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

See `agent-common.instructions.md` for the authoritative section-header-to-agent mapping table.

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

## 4. Closing

### Who Commits What

| Agent | Commits | When |
|-------|---------|------|
| Test-writer | Test files | Before moving to in-progress |
| Builder | Source code | Before moving to review |
| Doc-writer | Documentation files | Before moving to done |
| Auditor | Kanban board files + any uncommitted leftovers | During exit-gate Step 5 |

Rules:

- Never push. The user pushes manually.
- For commit format, types, and git discipline, see `r-project-standards` → Commit Discipline.

### Post-task Reflection

Before your final status advance, write 3-5 bullets covering problems faced, workarounds applied, patterns discovered, time sinks, and quality gaps. Skip if nothing notable happened.

**Dual-write (during migration):**

1. **Primary — `record_learning`:** One call per notable finding. Parameters: `agent_id=<agent_name>`, `scope_agent=<agent_name>`, `confidence=0.8`. If `record_learning` fails, continue — the fallback still captures the data.

   | Bullet type | MCP category |
   |-------------|-------------|
   | problems_faced | knowledge |
   | workarounds_applied | knowledge |
   | patterns_discovered | behavior |
   | time_sinks | context |
   | quality_gaps | context |

2. **Fallback — file-based:** `/memories/repo/inbox/{task-id}-{agent}.md` — agent name, task ID, date, then bullet points. Brief.

See `h-mcp-memory` for full tool reference.

## 5. Escalation

### Blocking Convention

Routine gate rejections (reviewer FAIL, doc-writer reject) use simple status movement and claim release — **no blocking**. The task re-enters the pipeline automatically on the next dispatch cycle.

When an agent cannot proceed (missing dependencies, infeasible AC, vague scope) or discovers the AC requires physical user action (manual testing, GUI verification, credential setup, deployment), it calls the **scribe** to create a DR or action request. Do not pass through hoping a downstream agent will handle it. The scribe creates the file; the calling agent then calls `end_work(outcome="block", block_reason="DR pending: {filename}")` to release its claim and append its reasoning to the task body.

The kanban `block` action is reserved for:

- Stale tasks — blocked for triage by orchestrator
- Tasks with pending DRs — blocked until user responds

Blocking and unblocking outside the standard lifecycle (e.g., orchestrator triage) uses `edit_task(block="reason")` / `edit_task(unblock=True)` (see `h-mcp-kanban`).

#### DR Required on Agent Block

**Every agent-initiated block requires a Decision Request.** When `end_work(outcome="block")` or `edit_task(block=...)` returns a non-empty `guidance` field, act on it immediately — the first message will direct you to create a DR via the scribe agent (see `w-decision-routing`).

**Exemption — user-driven blocks:** Tasks blocked via the Cockpit carry the `block:user` tag. If `block:user` is present on the task after blocking, the guidance field will be empty — no DR is required. Agents **must not** create DRs for Cockpit-initiated blocks.

### Decision Tiers

| Tier | When | Action |
|------|------|--------|
| T1 — Autonomous | Bug fix, refactor, config, perf | Proceed directly |
| T2 — Advisory | Trade-offs, no T3 triggers | Advisory DR via scribe (5-day auto-resolve) |
| T3 — Mandatory | New capability, arch/security/breaking change | Blocking DR via scribe (no auto-resolve) |

All DR/AR creation goes through the **scribe** agent. Never write to `.owlbear/decisions/` directly. If in doubt, create the DR — the cost is lower than guessing.

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

1. Architect detects `type:user-action` → creates action request via scribe
2. Architect calls `end_work(outcome="block", block_reason="AR pending: {filename}")`
3. `pick_tasks` excludes the blocked task — no agents dispatched
4. User performs the action → sets `response: completed` in the AR file
5. Scribe resolves: appends `## Action Completed` to task body, unblocks task
6. Architect (re-entry): sees `## Action Completed` + `type:user-action` → verifies AC → approves to `todo`
7. Test-writer and builder pass through (tag is in `NON_IMPL_TAGS`)

**Post-completion fast-path:** When a `type:user-action` task re-enters architect review with `## Action Completed` in the body, the architect verifies that AC checkboxes are satisfied, then approves directly without full re-evaluation. This extends the "Resolved Decision Pre-flight" check to action-completed tasks.

**Dual-nature tasks:** When the same feature requires both user action and code change, split into two tasks: a `type:user-action` task (AR + block) and a code task. The code task sets `depends_on` to the user-action task to enforce ordering.

**Dry-run scenario — #597-style loop prevented:** Because the task is `blocked` between architect cycles 1 and 2, `pick_tasks` returns nothing for it — the orchestrator dispatches no other agents until scribe unblocks. Result: **≤2 architect cycles** vs #597's **4+ futile cycles** with no resolution.

### Handoff

When you cannot finish the task yourself, describe current state, what failed, open questions, and next step in the task body. Include the handoff note in your `end_work(note="## Handoff\n...", outcome="fail")` call.

For programmatic handoff notes, use `edit_task(append_body="## Handoff\n...")` (see `h-mcp-kanban`).
