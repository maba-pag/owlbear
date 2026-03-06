---
name: kanban-based-development
description: Autonomous development workflow using kanban-md in a single workspace. Use when the user asks to work through tasks, do kanban-based development, or when multiple agents need to coordinate work on the same codebase. Optimized for explicit handoffs and a "defer to user" protocol when human intervention is required.
user-invocable: false
---

# Kanban-Based Development

Autonomous development using `kanban-md` to coordinate work on a shared board.
Claims prevent duplicate work; `review` is the waiting room (handoff, user action, decisions).

All work happens in the single workspace on the main branch — no worktrees.

## Multi-Agent Environment

**This board is shared.** Multiple agents and humans may be working on it simultaneously:

- Another agent may claim a task between the time you list it and try to pick it.
- Tasks you saw as available a moment ago may no longer be available.

The **claim** mechanic is the coordination primitive. **You MUST claim a task before starting any work on it, and you MUST only pick unclaimed tasks.**

## Non-Negotiables

- **Claim before you change anything.** No task edits, no code changes.
- **One active task per agent.** Keep at most one task in `in-progress` for your agent session.
- **Never steal a live claim.** If it's claimed, pick something else.
- **Never release someone else's claim.** Only use `edit --release` for your own work (or when the user explicitly asks).
- **Always leave a handoff.** Before you park a task, write a short update in the body so someone else can continue.

## Defer-to-User Boundary

By default, agents should take tasks all the way through the pipeline.
Defer to the user (leave the task in `review` with a handoff) only when you need:

- an important product/spec decision with multiple valid options and no clear winner
- credentials/access or external actions (push to remote, releases, deployments)
- repeated test/lint failures you can't resolve

## Default Loop

Use `--compact` for board/list/log output to keep output short.

### 1) Pick and claim (atomically)

```powershell
kanban\kanban-md.exe pick --claim <agent> --status todo --move in-progress
```

If `todo` is empty:

```powershell
kanban\kanban-md.exe pick --claim <agent> --status backlog --move in-progress
```

`pick` prints full task details (including body), so a separate `show` is not needed.

### 2) Implement, test, commit (in the workspace)

Make changes directly in the workspace on the main branch.

- Follow TDD: write failing tests first, then implement.
- Run checks:

```powershell
uv run pytest tests/ -m "not api" --tb=short -q
uv run ruff check src/ tests/
```

Commit when green:

```powershell
git add <files>
git commit -m "feat: <description>"
```

### Progress notes (recommended)

Leave timestamped notes during long tasks:

```powershell
kanban\kanban-md.exe edit <ID> --append-body "Implemented X, now running tests." --timestamp --claim <agent>
```

### 3) Advance through pipeline

After implementation:

```powershell
kanban\kanban-md.exe edit <ID> --release
kanban\kanban-md.exe move <ID> review
```

The orchestrator dispatches reviewer → writer → auditor through the remaining gates.

## Blocked / Needs User Input

If you cannot continue without the user:

```powershell
kanban\kanban-md.exe handoff <ID> --claim <agent> --block "Waiting on user: <what you need>" --note "## Handoff
- Current state:
- Open questions (A/B):
- Next step:" --timestamp --release
```

Then pick the next task. Do not idle.

## Resuming a parked task

```powershell
kanban\kanban-md.exe edit <ID> --claim <agent>
kanban\kanban-md.exe edit <ID> --unblock --claim <agent>
kanban\kanban-md.exe move <ID> in-progress --claim <agent>
```

## Status meanings

| Status | Meaning |
|---|---|
| `in-progress` | Actively being worked by an agent right now |
| `review` | Waiting: tests pass, code complete, needs verification |
| `docs` | Docs gate: verify/update documentation before closing |
| `done` | Verified complete, ready for archival |

## When there is nothing to pick

If `pick` returns "no unblocked, unclaimed tasks found":

- Check blocked work: `kanban\kanban-md.exe list --compact --blocked`
- Check waiting work: `kanban\kanban-md.exe list --compact --status review`
- If everything is waiting on the user, ask targeted questions and stop.
