# Decision Requests

This directory contains structured decision requests from agents that need user input before proceeding.

- `pending/` — Unresolved decisions awaiting user response
- `resolved/` — Decisions the user has acted on (moved here by the scribe)

## For users

Check `pending/` periodically (or when notified). Each file has a `response` field in the YAML header — change it to tell the system what you want.

### Quick reference

| `response` value | When to use | What happens |
|-----------------|-------------|--------------|
| `pending` | Default — haven't looked at it yet | Task stays blocked |
| `approved` | Accept the recommendation (or override `decision:` first) | Task unblocks, work proceeds |
| `needs-info` | You have questions — write them in `notes:` | Agent researches and comes back |
| `rejected` | None of the options work — explain in `notes:` | Task unblocks for re-scoping |
| `completed` | Action request only — you did the steps | Task unblocks |

### Accept the recommendation (most common)

The agent pre-fills `decision:` with its recommended option. To accept:

1. Open the file in `pending/`
2. Change `response: pending` → `response: approved`
3. Save.

### Override the recommendation

1. Change `decision:` to your preferred option (e.g., `decision: "B: Build custom"`)
2. Optionally fill in `notes:` with your reasoning
3. Change `response: pending` → `response: approved`
4. Save.

### Ask follow-up questions

1. Change `response: pending` → `response: needs-info`
2. Write your questions in `notes:`
3. **Leave `decision:` as-is**
4. Save.

The agent will research your questions and come back with a new or updated DR.

### Reject all options

1. Change `response: pending` → `response: rejected`
2. Write your reasoning in `notes:`
3. Save.

### Complete an action request

Action requests (`request_type: action`) ask you to **do something** rather than make a choice.

1. Read `## Context` and work through the `## Steps` checklist
2. Change `response: pending` → `response: completed`
3. Save.

### Use the CLI instead

```shell
bearclaw decisions list              # see all pending decisions
bearclaw decisions show TASK_ID      # read a specific decision
bearclaw decisions resolve TASK_ID   # interactive resolve (prompts for choice + notes)
```

### What happens after you save?

The scribe checks `pending/` each orchestration cycle. When it finds a `response` value other than `pending`, it processes it:

- **`approved`** / **`completed`** — unblocks the task, moves file to `resolved/`
- **`needs-info`** — keeps the task blocked, dispatches the agent to research your questions, resets to `pending`
- **`rejected`** — unblocks the task for re-scoping, moves file to `resolved/`

If no response is made within 5 days, T2 decisions auto-approve. T3 decisions never auto-approve.

## For agents

See `w-decision-routing` skill for the full format and workflow.
