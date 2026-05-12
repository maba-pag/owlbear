---
description: "Review curated memory entries with a guided approve/edit/reject workflow"
tools:
  - ob-memory/list_memories
  - ob-memory/read_memory
  - ob-memory/approve_memory
  - ob-memory/curate_memory
  - ob-memory/delete_memory
---

# Memory Review

Run a guided review session for MCP memory entries. This prompt is self-contained and does not require prior context.

## 1. Goal

Review entries in the `curated` state one by one and decide whether to approve, request changes, or reject.

## 2. Session Setup

1. Call `ob-memory/list_memories` with `states: ["curated"]`.
2. Present a compact queue summary with:
   - total count
   - entry ID
   - title
   - category
   - state
3. Ask the user if they want to proceed through the queue in order.

If no entries are returned, report that the review queue is empty and stop.

## 3. Review Loop (list -> read -> decide)

For each entry in the queue:

1. Read full content:
   - Call `ob-memory/read_memory` with the entry ID.
2. Present the entry:
   - ID and title
   - state and category
   - content
3. Ask the user to choose one action:
   - `Approve` -> call `ob-memory/approve_memory`
   - `Request changes` -> call `ob-memory/curate_memory`
   - `Reject` -> call `ob-memory/delete_memory`
   - `Skip` -> leave unchanged and continue

### 3.1 Action Details

When the user selects an action:

- `Approve`
  - Call `ob-memory/approve_memory` with `entry_id`.
  - Show the resulting state.

- `Request changes`
  - Collect a specific edit from the user (for example title/content/category changes).
  - Call `ob-memory/curate_memory` with `entry_id` and only the fields the user wants changed.
  - Show a concise before/after summary.

- `Reject`
  - Confirm deletion intent.
  - Call `ob-memory/delete_memory` with `entry_id`.
  - Confirm that the entry was removed.

- `Skip`
  - Make no mutation and continue to the next entry.

After each action, move to the next entry unless the user asks to stop.

## 4. End of Session (Batch Commit)

At the end of the review (or when the user stops), summarize:

- reviewed count
- approved count
- changed count
- rejected count
- skipped count

Then instruct the user to commit reviewed memory mutations with the state-aware helper:

```bash
uv --project ../owlbear run python -m owlbear_mcp_memory.git review
```

If this workspace uses a different OwlBear relative path, substitute the `--project`
path from the `ob-memory` entry in `.vscode/mcp.json`. Do not broad-add
`.owlbear/memory`; pending entries must remain uncommitted until curation.

## 5. Operating Rules

- Process one entry at a time.
- Never mutate an entry without explicit user confirmation.
- If a tool call fails, show the error and ask whether to retry, skip, or stop.
- Keep responses concise and decision-focused throughout the loop.
