# Decision Requests

This directory contains structured decision requests from agents that need user input before proceeding.

- `pending/` — Unresolved decisions awaiting user response
- `resolved/` — Decisions the user has acted on (moved here by the planner)

## For users

Check `pending/` periodically (or when notified).

### Accept the recommendation (most common)

The agent pre-fills `decision:` with its recommended option. To accept it:

1. Open the file in `pending/`
2. Change `approved: false` → `approved: true` in the YAML header
3. Save. Done.

The planner automatically unblocks the task and moves the file to `resolved/`.

### Override the recommendation

1. Open the file in `pending/`
2. Change `decision:` to your preferred option (e.g., `decision: "B: Build custom"`)
3. Optionally fill in `notes:` with your reasoning or conditions
4. Change `approved: false` → `approved: true`
5. Save. Done.

### Use the CLI instead

```shell
bearclaw decisions list              # see all pending decisions
bearclaw decisions show TASK_ID      # read a specific decision
bearclaw decisions resolve TASK_ID   # interactive resolve (prompts for choice + notes)
```

### What happens after you save?

The planner checks `pending/` each cycle. When it finds `approved: true`, it unblocks
the corresponding kanban task and moves the file to `resolved/`. You never need to move
files yourself.

If no decision is made within 5 days, the planner auto-approves the agent's
recommendation to prevent permanent blockage.

## Action requests

Action requests ask you to **do something** rather than make a choice. A file in `pending/`
with `request_type: action` contains a checklist of steps.

### Mark as complete

1. Open the file in `pending/`
2. Read `## Context` to understand why the action is needed
3. Work through the `## Steps` checklist — check off each item as you complete it
4. Set `completed: false` → `completed: true` in the YAML header
5. Save. Done.

The planner detects `completed: true` on its next cycle and automatically unblocks the
task and moves the file to `resolved/`.

## For agents

See `skills/decision-requests/SKILL.md` for the full format and workflow.
