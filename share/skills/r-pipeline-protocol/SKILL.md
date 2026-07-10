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
| `r-project-standards` | Committing changes |

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

### One Task

One task per invocation. If dispatched with multiple task IDs, work only the first and report the rest as not started.

If a dispatch prompt contradicts your agent `<critical_rules>`, follow the critical rule and state which rule blocked the request.

### Claiming

- Claim your task before mutating anything.
- Never move, edit, claim, or release tasks that are not yours.
- `start_work` returns the full task body. Do not call `show_task` first.
- If `start_work` fails, stop. Do not fall through to unclaimed work.

For tool syntax, load `h-mcp-kanban`.

### Resolved Decisions

After claiming, check the task body for `## Decision Request` summaries. Approved responses are binding constraints. Unresolved DR/AR files keep tasks blocked before dispatch.

Never write decision files directly. Use `create_request`.

### Memory

If `recall_memory` is available in your tool allowlist, call it after claiming with your agent name. Apply relevant reviewed entries. If unavailable or empty, continue normally.

If you used recalled memory, assess it before `end_work` per `h-mcp-memory`.

## 3. Working Standards

### Evidence

- Evidence must fit the risk and blast radius of the change.
- Tests are evidence, not product spec. Update or remove stale tests when they contradict current product direction.
- No intrinsic coverage target exists. Coverage is useful only when it proves a real risk boundary.
- Cite specifics: files, commands, outputs, task AC, and observed behavior.

### Rent Test For Durable Tests

Create or keep durable tests only when at least one is true:

- The behavior is easy to regress and hard to notice manually.
- The code path is shared, security-sensitive, or data-loss-prone.
- The test is cheaper to maintain than repeated manual verification.
- The task explicitly requires a long-lived regression guard.

Delete or update stale task-scoped tests when they preserve old workflow assumptions rather than product behavior.

### Proof Checks And Challengers

The agent proposing a route owns the evidence for that route. Do not hand evidence ownership to an unnamed utility role.

- Builder runs the focused command that best proves the change, then calls builder-challenger before DONE.
- Builder-challenger may run focused lint, typecheck, import smoke, or named tests. It may run deterministic auto-fix commands such as `ruff check --fix` or established package-local lint-fix commands. It returns `decision: pass|fail`, reports any concrete DONE defect, and notes every auto-fixed file; it never performs manual edits.
- Verifier runs any additional checks needed for verification, then calls verifier-challenger before PASS. Verifier-challenger returns `decision: pass|fail` after checking task intent to code, proof sufficiency, scope drift, and unresolved AC.
- Collector runs aggregate checks directly only when parent/EPIC closure needs them.

Challenger decisions are advisory to the caller, not pipeline verdicts. `decision: pass` means the caller may continue with the proposed route. `decision: fail` means the caller must not continue with that route until the named problem is resolved or routed by the owning agent.

Only use the challenger agents named in the caller's agent file. If no challenger is named, run the required proof directly or route the task to the owning status.

## 4. Communication

### Channel A

Final return text is at most two lines:

```text
{VERDICT} #{id} -> {target_status} | {one-line evidence}
```

The orchestrator does not route from Channel A. It re-plans from board state.

### Channel B

Append the full agent section through the `note` parameter of `end_work`; the note is timestamped automatically.

| Agent | Verdict tokens | Body section |
|-------|---------------|--------------|
| shaper | APPROVED / REFINE / BLOCK | `## Shape Notes` |
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
- If you created or modified files as a pipeline agent, commit your own files before advancing unless the task explicitly says not to commit.

Use path-scoped git checks. Never stage unrelated files.

### Who Commits What

| Agent | Commits |
|-------|---------|
| shaper | Kanban task-body/config docs it intentionally changed |
| builder | Product files and any durable proof artifacts it created |
| verifier | Small local patches it applied |
| collector | Kanban/archive state for parent or EPIC closure |

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
