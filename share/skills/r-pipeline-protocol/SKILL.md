---
name: r-pipeline-protocol
description: "Rules: Pipeline conventions — task lifecycle, communication, quality, delivery, escalation"
user-invocable: false
---

# Pipeline Protocol

Shared conventions for the OwlBear execution board:

```text
shape -> build -> verify -> collect -> archived
```

`archived` is off-board closure. Raw ideas and external intake are not pipeline statuses by default.

## Companion Skills

Load these via `read_file` when the referenced capability is needed:

| Skill | Load when |
|-------|-----------|
| `h-mcp-kanban` | Using kanban tools — claiming, editing, moving, blocking tasks |
| `h-ac-quality` | Drafting or judging acceptance criteria |
| `h-decision-requests` | Creating DR/AR records |
| `r-workspace-governance` | Required reading for pipeline agents; committing changes or creating OwlBear-managed artifacts |

## 1. Lifecycle

| Status | Agent | Purpose | Success route | Reject route |
|--------|-------|---------|---------------|--------------|
| `shape` | shaper via `/shape` | Turn intent into buildable scope, AC, and dependency shape | `build` for build-ready leaves; `collect` for aggregate parents/EPICs | stays `shape` |
| `build` | builder | Implement shaped work and choose proportional proof | `verify` | `shape` |
| `verify` | verifier | Verify task intent and evidence; patch small local defects | `collect` | `build` or `shape` |
| `collect` | collector | Verify parent/EPIC aggregate intent and archive readiness | `archived` | `shape` |

### Role Boundaries

- **Shaper** is user-facing and prompt-driven. It decides what should be built and what evidence would be meaningful. Shaper-created tasks use explicit routing: build-ready leaves in `build`, aggregate parents/EPICs in `collect`; `shape` is for manual intake and rejected work.
- **Builder** changes product files, runs focused proof, and calls builder-challenger before every DONE. Durable tests are optional and must earn their maintenance cost.
- **Verifier** validates the result, may patch small local issues, and calls verifier-challenger before every PASS.
- **Collector** has two modes: mechanically archive verified leaf tasks, and review aggregate parents/EPICs for parent intent fulfillment. Ordinary subtasks should not receive a second detailed implementation review in `collect`.

## 2. Task Setup

### Invocation Scope

Builder, verifier, and collector handle one task per invocation. If dispatched with multiple task
IDs, work only the first and report the rest as not started.

Shaper handles one shaping subject per invocation. A subject may be one OpenSpec change or an
explicit connected set of existing tasks whose combined repair or reshape cannot be made coherent
one task at a time. Before the first write to a connected set, identify the complete task IDs and
claim every existing task in deterministic ID order. If any claim fails, release the claims acquired
in this invocation and stop without mutation. Do not add tasks to the mutation set after approval or
after writes begin.

If a dispatch prompt contradicts your agent `<critical_rules>`, follow the critical rule and state which rule blocked the request.

### Claiming

- Claim every existing task before mutating it. Newly created tasks are owned by the creating
  workflow and do not require a separate claim.
- Builder, verifier, and collector never move, edit, claim, or release tasks other than their one
  assigned task. Shaper may mutate only the explicit connected set claimed in the current invocation.
- After loading required skills, make `start_work` the first read of the assigned task. It returns
  the full authoritative task body; do not precede it with `show_task` or a direct read of the
  task's Markdown file.
- Inspect other tasks without claiming them: use `list_tasks` for summaries and `show_task` for
  full context or `show_task(section=...)` for one body section. Never use `start_work` merely to
  inspect a dependency, parent, sibling, or referenced task.
- Treat `.owlbear/kanban/tasks/*.md` and archive task Markdown as storage representations. Read
  them directly only when the task is specifically about storage, serialization, corruption, or
  filesystem behavior; normal task context comes through the MCP task tools.
- If `start_work` fails, stop. Do not fall through to unclaimed work.

For tool syntax, load `h-mcp-kanban`.

### Resolved Decisions

After claiming, check the task body for `## Decision Request` summaries. Approved responses are binding constraints. Unresolved DR/AR files keep tasks blocked before dispatch.

Never write decision files directly. Use `create_request`.

### Memory

If `recall_memory` is available in your tool allowlist, call it after claiming with your agent name. Apply relevant reviewed entries. If unavailable or empty, continue normally.

If you used recalled memory, assess it before `end_work` per `h-mcp-memory`.

### Task Metadata

Use `medium` priority by default. Use `high` for a current blocker or work with strong dependency
fan-out; use `low` for non-urgent cleanup or later ideas.

Tags are free-form but use these conventions when they improve routing or grouping:

| Category | Examples | Purpose |
|----------|----------|---------|
| Phase | `phase-1` through `phase-12` | Group work by delivery phase |
| Category | `config`, `tooling`, `docs`, `test`, `cli`, `agent` | Identify the area touched |
| Type | `type:build`, `type:test`, `type:docs`, `type:user-action` | Identify the kind of work |
| Scope | `scope:copilot`, `scope:core`, `scope:cli` | Identify the codebase part |
| Rigor | `rigor:lean`, `rigor:standard`, `rigor:thorough` | Record the quality-versus-speed profile |

`type:user-action` means physical user action is required before the pipeline can continue. Shaper
creates an Action Request, blocks the task, and records the resolved decision on re-entry.

## 3. Working Standards

### Minimum Change Contract

Before the first edit, define a change envelope: the expected files or symbols, the behavior that
must change, and the cheapest proof that can falsify the implementation. Preserve unaffected code
verbatim and prefer a targeted edit inside an existing owner over file replacement, reorganization,
or a new abstraction.

- Every added file, helper, abstraction, fallback, compatibility branch, edge case, and durable test
  must be required by shaped scope or an observed defect. Anticipated future value is not enough.
- Do not add cleanup, hardening, documentation, compatibility, or refactors adjacent to the task.
  Route independently valuable follow-up work separately instead of implementing it now.
- The default durable-test delta is zero. Validation does not imply committing a test, and AC lines
  do not map one-to-one to tests. One focused proof may cover several AC when it exercises their
  shared public boundary.
- Reuse existing tests and validators before creating proof artifacts. Add a durable test only when
  it names a plausible meaningful regression, existing durable coverage does not protect that risk,
  and the Rent Test passes.
- A task or AC that prescribes a durable test does not waive admission. If the requested test fails
  the Rent Test, reject to shape so proof guidance can be corrected; do not commit the test.
- If the diff expands materially beyond the change envelope, stop and reassess. Reduce your own
  excess work or return to shape; do not normalize expansion by writing more tests around it.

### Evidence

- Evidence must fit the risk and blast radius of the change.
- Tests are evidence, not product spec. Update or remove stale tests when they contradict current product direction.
- No intrinsic coverage target exists. Coverage is useful only when it proves a real risk boundary.
- Cite specifics: files, commands, outputs, task AC, and observed behavior.
- Evidence is valid only for the boundary actually exercised. Mocks and injected dependencies may
  replace lower layers, but they must not replace the command, endpoint, workflow, generated
  operation visibility, assembled context, or user journey whose behavior is being claimed.
- When a task names a canonical source or contract authority, builder and verifier compare the
  implementation and fixtures with that authority. A contradiction invalidates completion even when
  task-local tests pass.

### Rent Test For Durable Tests

Create or keep a durable test only when it protects a concrete behavioral risk not already covered
by the maintained suite and at least one is true:

- The behavior is easy to regress and hard to notice manually.
- The code path is shared, security-sensitive, or data-loss-prone.
- The test is cheaper to maintain than repeated manual verification.
- The task explicitly requires a long-lived regression guard.

Do not create tests solely because code changed, an AC exists, a coverage report has a gap, or proof
feels more complete with another case. Delete or update stale task-scoped tests when they preserve
old workflow assumptions rather than product behavior.

### Continuous Change Module Map

When Shape Notes provide a Change Module Map, carry it through build and verify:

- Shaper verifies named owners, responsibilities, interfaces, and precedents against source before
  approval.
- Builder starts from the mapped modules, keeps implementation inside them when source supports the
  plan, and records justified deviations in Builder Notes.
- Verifier compares changed modules and interface impact with the map and investigates concrete
  deviations or adjacent invariants.
- Return to shape when source contradicts ownership, architecture, interfaces, or task scope. Do not
  silently expand the map.
- Current source remains stronger authority than the shaped map.

Collector and challengers do not perform open-ended orientation by default. They check closure or
the proposed decision against the map and direct evidence within their role boundary.

### Proof Checks And Challengers

The agent proposing a route owns the evidence for that route. Do not hand evidence ownership to an unnamed utility role.

- Builder runs the focused command that best proves the change, then calls builder-challenger before DONE.
- Builder-challenger checks the Minimum Change Contract and any new durable tests before running
  focused lint, typecheck, import smoke, or named tests. It may run deterministic auto-fix commands
  such as `ruff check --fix` or established package-local lint-fix commands. It returns
  `decision: pass|fail`, reports any concrete DONE defect, and notes every auto-fixed file; it never
  performs manual edits.
- Verifier runs any additional checks needed for verification, then calls verifier-challenger before PASS. Verifier-challenger returns `decision: pass|fail` after checking task intent to code, proof sufficiency, scope drift, and unresolved AC.
- Collector runs aggregate checks directly only when parent/EPIC closure needs them.

For aggregate normal-path proof, record the tested commit SHA and the command or artifact proving
the aggregate AC at that SHA or a later descendant. A SHA without tied proof is not closure evidence.

Challenger decisions are advisory to the caller, not pipeline verdicts. `decision: pass` means the caller may continue with the proposed route. `decision: fail` means the caller must not continue with that route until the named problem is resolved or routed by the owning agent.

Only use the challenger agents named in the caller's agent file. If no challenger is named, run the required proof directly or route the task to the owning status.

## 4. Communication

### Channel A

Builder, verifier, collector, and other orchestrator-dispatched pipeline agents return at most two
lines:

```text
{VERDICT} #{id} -> {target_status} | {one-line evidence}
```

The orchestrator does not route from Channel A. It re-plans from board state.

Shaper is user-facing and is not dispatched by orchestrator. It returns the human summary required
by `w-spec-shaping` or `w-task-repair`; it does not expose a machine verdict as the user interface.
Board movement and `## Shape Notes` remain the durable routing and history record.

### Channel B

Append the full agent section through the `note` parameter of `end_work`; the note is timestamped automatically.

| Agent | Verdict tokens | Body section |
|-------|---------------|--------------|
| shaper | internal route recorded in task state | `## Shape Notes` |
| builder | DONE / REJECT / BLOCK | `## Builder Notes` |
| verifier | PASS / REJECT / RESHAPE | `## Verify Notes` |
| collector | ARCHIVED / REJECT | `## Collect Notes` |
| memory-curator | DONE | `## Curation` |

If a single section exceeds about 1500 tokens, write details to `.owlbear/scratch/{task-id}-{agent}.md` and reference it from the body.

### Required Follow-up

Any `REJECT`, `RESHAPE`, or `BLOCK` verdict must include:

```markdown
### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | {role} | {imperative action} | {paths or n/a} | {finding reference} |
```

Target roles must match the route: `shape` -> shaper via `/shape`, `build` -> builder.

## 5. Closing

### Before `end_work`

- Record changed files and evidence in your Channel B note.
- Run the focused validation that can falsify your current claim when one exists.
- Check only your own domain for uncommitted deliverables.
- Inventory explicit task-owned paths for the final scoped commit. Include durable files changed by
  this agent and the task's current storage path; never use a broad directory pathspec.

### After `end_work`

- Read the returned task state and guidance, then immediately commit per `r-workspace-governance`.
- Include the final task record in every pipeline commit. If `end_work` archived the task, include
  both its former task path and final archive path so the move is committed.
- Preserve unrelated tracked, staged, and untracked changes. A dirty worktree is expected and is not
  a reason to omit the commit.
- Treat the scoped commit as part of closure: do not return a success verdict or allow another board
  mutation until it succeeds.
- On an unrecoverable commit error, follow `r-workspace-governance`'s `COMMIT_FAILED` containment:
  block an on-board advanced task before returning so orchestrator cannot redispatch it. Archived
  tasks are already off-board. Never translate commit failure into `DONE`, `PASS`, or `ARCHIVED`.

Use path-scoped git checks. Never stage unrelated files.

### Who Commits What

| Agent | Commits |
|-------|---------|
| shaper | Final Kanban task record plus task-body/config docs it intentionally changed |
| builder | Final Kanban task record, product files, and durable proof artifacts it created |
| verifier | Final Kanban task record and small local patches it applied |
| collector | Final Kanban/archive task record for leaf, parent, or EPIC closure |

Never push.

## 6. Escalation

Use the cheapest route that preserves correctness:

| Cause | Action | Route |
|-------|--------|-------|
| Vague or wrong scope | Explain gap in Required Follow-up | `shape` |
| Implementation defect | Explain concrete fix needed | `build` |
| Missing prerequisite or dependency shape | Reject with Required Follow-up for shaper to split/resequence | `shape` |
| User decision/action needed | `create_request`, then block with the returned reason | current status blocked |
| Tool unavailable | Release/fail with `TOOL_UNAVAILABLE` and stop | no improvised workaround |

Block only when the board must not redispatch the task automatically. Routine rejections should move to `shape` or `build`.

### Decision Tiers

| Tier | When | Action |
|------|------|--------|
| T1 — Autonomous | Local implementation, cleanup, proof choice | Proceed directly |
| T2 — Advisory | Preference or trade-off where either path is acceptable | Advisory DR via `create_request` |
| T3 — Mandatory | New capability, architecture/security/breaking change, user action | Blocking DR/AR via `create_request` |

If in doubt, create the DR. Guessing is more expensive than a small decision record.
