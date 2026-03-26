# Architecture Review: #905

**Verdict:** Split

## AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Add `bearclaw board` CLI command | Sound CLI-only feature, but this backlog card is no longer the executable implementation contract because research already split it into a RED task (#909) and a GREEN task (#910). | Keep the split; do not implement directly from #905. |
| Render a Rich table grouped by status with columns ID, title, assignee, age (days in status), tags | Good user-visible contract and consistent with existing Rich table output, but the implementation seam is the real `kanban-md` JSON contract: task rows from `list --json`, status order from `kanban/config.yml`, and age from move-log `timestamp` plus `detail` parsing rather than task `updated`. | Preserve in the split tasks as the binding behavior. |
| Target ~120 LOC in `src/bearclaw/` | Non-verifiable sizing guidance, not acceptance criteria. | Treat as non-binding implementation guidance only. |
| No new deps (Rich is already transitive) | Precise and verifiable; matches existing BearClaw command patterns. | Keep as a constraint on the GREEN task. |
| Scheduling note: either schedule #909/#910 or consolidate back into #905 | Consolidating back into #905 would collapse the explicit RED/GREEN separation and weaken TDD enforcement. The split is the correct architectural shape. | Retain #909 as RED and #910 as GREEN. |

## Architecture Notes

- The feature is single-domain CLI work, so it does not need a domain split beyond the existing TDD pair.
- Existing BearClaw patterns support this design:
  - `src/bearclaw/cli.py` promotes top-level commands via unnamed Typer apps (`chat`, `daemon`), which is the right wiring pattern for a top-level `board` command.
  - `src/bearclaw/commands/project.py` and `src/bearclaw/commands/decisions.py` already render direct Rich tables from command-local helpers.
  - `src/bearclaw/commands/chat.py` already uses `subprocess.run(...)` as a local CLI seam for external command data.
  - `src/owlbear/core/retrospective_hook.py` shows the live `kanban` move-log detail format (`from -> to`), which is the right prior art for computing days in current status.
  - `kanban/config.yml` is the configured source of status ordering.
- The split tasks are architecturally preferable to a single implementation card because they preserve the explicit RED -> GREEN flow required by the repo.
- One follow-up gap remains outside this task: #910 currently has no explicit dependency on #909. I am not modifying sibling tasks from this invocation, so that dependency needs to be added when #910 is architect-reviewed.

## Changes Made

- Claimed #905 as `architect-905`.
- Appended an architecture-review pointer to the task body and resolved the scheduling note in favor of keeping the RED/GREEN split.
- Left #905 in backlog as the research umbrella; implementation should proceed on #909 then #910 after separate architect review.

## Dependencies

- Verified: `docs/research/bearclaw-board-command.md` supplies the concrete research basis.
- Verified: #909 exists as the paired RED task and #910 exists as the paired GREEN task.
- Verified code patterns: `src/bearclaw/cli.py`, `src/bearclaw/commands/project.py`, `src/bearclaw/commands/decisions.py`, `src/bearclaw/commands/chat.py`, `src/owlbear/core/retrospective_hook.py`, `kanban/config.yml`.
- Outstanding for later task review: add explicit `depends_on: #909` to #910 before approving it.