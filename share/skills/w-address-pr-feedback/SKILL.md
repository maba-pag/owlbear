---
name: w-address-pr-feedback
description: "Workflow: Evaluate and address external pull-request feedback in managed Delivery custody"
user-invocable: false
---

# Address Pull-Request Feedback

Evaluate external pull-request review threads critically and repair only the findings that are
true for the current Delivery Change. The review is external evidence, not Delivery authority:
reviewer comments may be correct, incorrect, stale, duplicated, or outside the Change boundary.
The workflow owns repair work only. It does not add external review to Delivery's internal review
receipts or replace the finalization review.

## Step 0 - Bind The Change And Pull Request

Require one native Delivery `change_id` from the prompt. Use the Delivery MCP surface for Change
authority and the `gh` CLI for GitHub review data. Do not use a GitHub MCP server for this workflow.

1. Call `list_work_items` and require the requested Change publication item to be present.
2. Call `show_finalization_context` and retain the exact branch, managed worktree, finalized head,
   reviewed head, and publication phase. Continue only for a finalized PR. If the PR is still in
   an earlier draft checkpoint, report `authority-gap: change-not-finalized` without replying,
   resetting, or editing; external review repair is not supported before finalization.
3. Require `gh auth status` to succeed. Read `github_repository` from the tracked Delivery
   configuration and find the open pull request for the exact managed branch:

   ```text
   gh pr list --repo <repository> --head <managed-branch> --state open \
     --json number,url,state,isDraft,headRefName,headRefOid,baseRefName
   ```

   Require exactly one open pull request, the expected repository, managed branch, target branch,
   and current head identity. A closed or merged pull request, missing PR, multiple matches, or
   head mismatch is a bounded stop; do not repair it through another branch or PR.
4. Read unresolved inline review threads with `gh api graphql --paginate --slurp`. Use a query that
   includes `reviewThreads(first: 100, after: $endCursor)`, each thread's `id`, `isResolved`,
   `isOutdated`, location, and its comments' `id`, `url`, `body`, author, and creation time. Save
   large raw responses only under `.owlbear/scratch/` and remove temporary files before closure.

   A minimal paginated query is:

   ```text
   review_query='query($owner:String!, $name:String!, $number:Int!, $endCursor:String) { repository(owner:$owner, name:$name) { pullRequest(number:$number) { reviewThreads(first:100, after:$endCursor) { nodes { id isResolved isOutdated path line startLine comments(first:100) { nodes { id url body createdAt author { login } } } } pageInfo { hasNextPage endCursor } } } } }'
   gh api graphql --paginate --slurp -f query="$review_query" -f owner="$owner" -f name="$repo_name" -F number="$pr_number"
   ```

   Keep only unresolved threads for normal work. Outdated threads still require a deliberate
   classification, but do not automatically receive a code repair. `gh api graphql` is read-only
   for this query; it does not alter the PR.

Treat one unresolved review thread as one review comment unit. Multiple messages in one thread are
one unit. General issue comments without a resolvable review thread are context only and are not
silently marked resolved.

Do not call `gh pr checkout`, `gh pr merge`, `gh pr ready --undo`, or a raw `git push`. The managed
Change worktree and Delivery operations own source custody, draft state, finalization, and branch
publication.

## Step 1 - Critically Triage Every Thread

Before changing code, inspect the current managed Change worktree, the exact Change context, the
reviewed diff, relevant requirements, and focused tests. For each unresolved non-outdated thread,
write a bounded internal record containing:

- thread identity and reviewer claim;
- the reviewer's problem statement and assumptions;
- the evidence that the problem is true or false for this Change;
- the affected code path, acceptance behavior, and task or Change boundary;
- one classification: `fix`, `no-change`, `duplicate`, `stale`, `needs-user-decision`, or
  `authority-gap`;
- the proof needed to support the classification.

A reviewer sees only a partial code context. Do not accept a comment merely because it is specific,
confident, or from a trusted reviewer. Do not reject it merely because it conflicts with the current
implementation. Reproduce or reason through the concrete behavior.

Use these routes:

| Classification | Route |
| --- | --- |
| `fix` | Implement one bounded repair commit for this thread. |
| `no-change` | Record the evidence and defer the reply and resolution until the repaired head is published. |
| `duplicate` | Record the existing fix or thread reference; do not create an empty second commit, and defer the reply and resolution until publication. |
| `stale` | Record the current evidence and defer any reply and resolution until publication if the thread remains actionable. |
| `needs-user-decision` | Ask exactly one user question, leave the thread unresolved, and stop. |
| `authority-gap` | Stop without editing; identify the missing Design, Planning, Delivery, or provider authority. |

If there are no unresolved actionable threads, report `no-actionable-feedback` and do not reset the
PR or create commits. Never turn a style preference or unsupported concern into implementation
work without a concrete behavior or authority boundary.

## Step 2 - Prepare The Provider And Delivery State

When at least one `fix` classification is ready to implement, call the Delivery MCP operation
`prepare_review_repair` before the first edit. It verifies the exact open, unmerged PR, returns a
ready PR to draft through the configured provider, invalidates the old finalization and ready
authority, and publishes the repair-ready state. It is replay-safe when the PR is already draft or
the repair preparation already completed.

Do not manually change the PR draft flag. Do not use `resolve_change_disposition` as a substitute.
If preparation reports a closed PR, merged PR, head mismatch, missing publication, or provider
failure, stop and report the exact authority gap. A merged PR requires a fresh Change or an
explicitly designed merged-history recovery; this workflow never rewrites accepted history.

After preparation, re-read `show_finalization_context` and direct Git state in the returned managed
worktree. Require the managed branch, current head, reviewed boundary, and clean status to be
consistent before editing. The finalization ID must be absent while repair is in progress. If a
finalization reappears before a repair commit, stop with `authority-gap: review-repair-was-reversed`.
Never enter or modify the user's primary checkout.

## Step 3 - Repair One Thread At A Time

Process `fix` threads in a stable order. For each thread:

1. Re-read the thread and current code immediately before editing. Keep the repair inside the
   current Change boundary. If the comment reveals a new product requirement, architectural choice,
   or missing earlier authority, stop with `authority-gap` instead of expanding the repair.
2. Implement the smallest complete fix in the managed Change worktree.
3. Run focused proof for the affected behavior. A failed proof is not a reason to resolve the
   thread; repair or stop with the failure evidence.
4. Create exactly one commit for this thread using explicit owned paths and the scoped mechanics in
   `r-workspace-governance`. Do not amend, squash, rebase, or combine this commit with another
   actionable thread. Use a message that identifies the bounded review repair, for example:

   ```text
   fix: address PR feedback <short-slug> (<change-id>, address-pr-feedback)
   ```

5. Record the full commit SHA and proof result in the thread record before moving to the next
   thread.

One commit per thread means one commit per independent review conversation that warrants a code
change. If two threads are demonstrably duplicates of the same defect, keep one repair commit,
classify the second as `duplicate`, and reference the first commit in its reply rather than making
an empty or duplicate commit.

A clean commit does not by itself authorize publication or acceptance. The repaired branch remains
unpublished until the normal finalization and checkpoint publication steps.

## Step 4 - Hand Off To Finalization

After all eligible repairs:

1. Re-read the PR threads and current Delivery context. Require every repaired thread to have a
   recorded commit. Do not resolve repaired threads yet.
2. Re-read `show_finalization_context`. A repaired Change should be in
   `finalization-invalidated` or `ready-for-finalization` with the managed worktree at the new
   exact head and clean.
3. Do not construct finalization evidence inside this workflow. Give the user the exact next
   command and stop:

   ```text
   /finalize-change <change-id>
   ```

The first invocation stops here. It must not reply to or resolve a thread before the repaired head
is finalized and published.

## Step 5 - Publish Then Reply And Resolve Threads

Resume `/address-pr-feedback <change-id>` after `/finalize-change` succeeds. On that resumed
invocation:

1. Re-bind the exact open, unmerged pull request and re-read the unresolved review threads.
2. Call Delivery `reconcile_change_checkpoint` to publish the new Change head and update the
   existing PR. Verify the repaired commit is the current PR head before changing any thread.
3. Use `gh api graphql` mutations, never a GitHub MCP server, to reply to each eligible thread.
   For a repaired thread, include the full commit SHA and URL when available, the accepted problem
   and fix, and the focused proof that passed. For `no-change`, `duplicate`, or `stale`, include
   the recorded evidence and decision. Keep the reply on the original thread.

   Pass the reply as a GraphQL variable so review text is not interpolated into the query:

   ```text
   reply_query='mutation($threadId:ID!, $body:String!) { addPullRequestReviewThreadReply(input: {pullRequestReviewThreadId: $threadId, body: $body}) { comment { id url } } }'
   gh api graphql -f query="$reply_query" -f threadId="$thread_id" -f body="$reply_body"
   ```

4. Only after the reply succeeds, resolve that same thread and verify the returned thread has
   `isResolved: true`:

   ```text
   resolve_query='mutation($threadId:ID!) { resolveReviewThread(input: {threadId: $threadId}) { thread { id isResolved } } }'
   gh api graphql -f query="$resolve_query" -f threadId="$thread_id"
   ```

   If either mutation fails, leave the thread unresolved, retain the repair commit, report the exact
   GitHub error, and do not claim the conversation was closed. Do not post a new top-level PR
   comment when a thread reply is available.

5. Leave the PR draft and do not merge it. The user owns the ready-state decision and GitHub merge;
   Delivery records the user-owned merge later through `observe_acceptance`.

The workflow may finish immediately when no code repair was needed. A repair run stops for
finalization and is resumed only after the user invokes this prompt again. It must not mark the PR
ready, merge the PR, or claim completion.

## Output Template

Return a concise report in this shape:

```yaml
kind: addressed-pr-feedback | no-actionable-feedback | blocked
change_id: <native Change ID>
pull_request: <repository>#<number>
pr_state_before: draft | ready | unknown
prepared_for_repair: true | false
threads:
  - thread_id: <GitHub thread node ID>
    classification: fix | no-change | duplicate | stale | needs-user-decision | authority-gap
    commit: <full SHA or null>
    response_posted: true | false
    resolved: true | false
    proof: <bounded proof or reason>
next_command: /finalize-change <change-id> | /address-pr-feedback <change-id> | none
remaining_blocker: <non-empty reason or none>
```

Do not claim a repair, publication, or conversation resolution without the corresponding commit,
GitHub response, and observed state evidence.

## Known Pitfalls

- A review comment is evidence to evaluate, not an automatic work order.
- A PR commit SHA is not a merge commit and does not prove acceptance.
- Returning a PR to draft is a Delivery state transition, not a reason to reset a branch or checkout
  the PR in the user's repository.
- `prepare_review_repair` invalidates old finalization authority; it does not finalize or publish the
  repaired head.
- Never amend a reviewed commit, combine independent comment fixes, force-update a branch, hand-edit
  Delivery state, or resolve a thread before its reply is posted.
- External review remains outside the product's internal review receipts; only the resulting repair
  commits enter the normal finalization workflow.
