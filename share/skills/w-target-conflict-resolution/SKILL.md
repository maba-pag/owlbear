---
name: w-target-conflict-resolution
description: "Workflow: Resolve one exact target merge conflict in managed Delivery custody"
user-invocable: false
---

# Target Conflict Resolution

Resolve one exact integration-target merge through the managed Change worktree. Delivery owns the
merge identity, preserved conflict state, final merge commit, and lifecycle authority; the agent
owns only the semantic file edits and focused proof needed to make the merge resolvable.

## Step 0 - Bind Current Authority

Require one native `change_id`. Read `list_work_items`, `show_work_item_view` with
`{"change_id": "<change-id>", "item_key": "publication"}`, and `show_finalization_context` before
mutation. Bind the current Change, branch, managed worktree, reviewed head, integration target,
pull-request identity, and any target-sync conflict identity from the detailed publication view.
Read `.owlbear/delivery/config.json` to identify the configured remote and target branch, then read
that target's remote-tracking commit with Git. Do not infer a target head from the GitHub PR page or
from an old prompt result.

A current open pull request with no Delivery target-sync conflict is still eligible for this
workflow: use the exact configured target head and a stable operation ID to call
`sync_change_with_target`. If Delivery returns a preserved conflict, re-read
`show_work_item_view` for `publication` and bind `publication.attention.disposition_id` plus
`publication.target_sync_conflict.target_head`, `operation_id`, and conflict paths. If a conflict
is already present, never start a second synchronization attempt.

Use only the one managed Change worktree returned by Delivery. Verify its branch, exact head,
`MERGE_HEAD` when a conflict is retained, and staged, unstaged, and untracked state with read-only
Git before editing. A missing, stale, ambiguous, or dirty state outside the preserved merge is an
authority gap; do not repair it with raw Git cleanup.

## Step 1 - Resolve In Managed Custody

Inspect only the preserved conflict paths and their base, ours, and theirs content. Classify each
path against the current Change authority and the configured target:

- combine mechanical, non-overlapping changes when both sides remain valid;
- choose the current authoritative version for generated or superseded content;
- preserve both additions only when the source contracts require both definitions; and
- stop with `authority-gap` when two versions express incompatible product, architecture, security,
  or Delivery authority that the current evidence cannot choose.

When a material choice is user-owned, ask exactly one bounded question and leave the merge
preserved. Do not invent a choice from the conflict-marker order. Do not edit the primary checkout,
GitHub PR contents, target branch, or Delivery state files.

After editing, require every original conflict path to be resolved, stage only those paths in the
managed worktree, and run the focused maintained checks for the affected packages. Include a
whitespace/conflict-marker check and a clean-worktree check after staging. Do not create the merge
commit yourself.

Call `resolve_target_sync_conflict` with the exact retained disposition ID, target head, and
operation ID. Delivery then requires a clean resolved worktree and a merge commit whose parents are
the preserved Change head and requested target head. Treat its returned receipt as the only
successful merge-resolution result.

## Step 2 - Handoff

After Delivery returns a resolution receipt, re-read the Change state and managed worktree. The
resolved merge invalidates the old finalization authority or requires fresh review. Return the next
user-visible command exactly as:

```text
/finalize-change <change-id>
```

Do not publish the checkpoint, mark the pull request ready, resolve GitHub review threads, or merge
the pull request in this workflow.

## Output Template

On successful Delivery resolution:

```yaml
kind: resolved
action: resolve_target_sync_conflict
change_id: <change-id>
target_head: <exact target head>
merged_head: <exact returned merge head>
next_command: /finalize-change <change-id>
```

When the current evidence cannot safely choose or prove a resolution:

```yaml
kind: blocked
action: resolve_target_sync_conflict
change_id: <change-id>
reason: <bounded authority gap or user decision>
conflict_paths: [<relative paths>]
next_command: none
```

When target synchronization completes without conflicts:

```yaml
kind: synced
action: sync_change_with_target
change_id: <change-id>
target_head: <exact target head>
merged_head: <exact returned merge head>
next_command: /finalize-change <change-id>
```

## Known Pitfalls

- An open conflicted PR is provider evidence; it is not itself a Delivery merge commit.
- `resolve_target_sync_conflict` validates and commits staged resolutions; it does not decide file content.
- A merge commit must be created by Delivery after the worktree is clean and all unmerged paths are gone.
- Rebase, force-push, manual runtime edits, target-branch edits, and primary-checkout merges destroy the exact custody boundary.
- A clean automatic merge still moves the Change head and requires fresh finalization before publication.
