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

The prompt accepts an optional `mode=start` or `mode=resume`; mode is an assertion, not a phase
selector. When omitted, Step 0 derives `start-reentry`, `start`, or `resume` from current Delivery
and PR evidence. `start-reentry` is a `start` run while Delivery is already in `review-repair`; it
replays preparation and reuses compatible mapped commits. First-entry `start` owns triage,
preparation, and repair commits. `resume` handles replies and resolution after fresh finalization.
Never run preparation in `resume` or in a first-entry `start` that needs no repair.

## Step 0 - Derive The Phase Before Mutation

Gather read-only Delivery and PR identity in Step 1 before any mutation. For finalized phases,
gather the trailer-map and comment evidence needed to derive the route. When the publication phase
is `review-repair`, derive `start-reentry` from that authority alone and defer comment and trailer
reads until `prepare_review_repair` succeeds in Step 2. Do not let the optional prompt input select
the phase.

| Current authoritative state | Derived phase |
| --- | --- |
| Publication phase is `review-repair` | `start-reentry` |
| A current finalization exists, has no review-repair invalidation, and its `finalized_head` equals the Change head; at least one unresolved bound-PR thread mapped by a trailer reachable from that head is awaiting | `resume` |
| The same valid finalization conditions hold, but no unresolved mapped thread is awaiting | `start` |
| Every other state | `authority-gap: change-not-finalized` |

An unresolved bound-PR thread is `awaiting` when it is mapped by a `Review-Thread` trailer
reachable from the exact finalized head and has no viewer-authored marker reply for its newest
mapped commit, or has a settled marker reply for it. A mapped thread is `reopened` when every
viewer-authored marker reply for its newest mapped commit is unsettled; reopened threads do not
select `resume` by themselves. If another awaiting mapped thread selects `resume`, reopened threads
are re-evaluated in its Resume Order; when no awaiting thread selects `resume`, they are triaged in
`start`.

If `mode` is omitted, use the derived phase (`start-reentry` accepts `start`). If it is supplied,
accept only `start` or `resume` and require it to match the derived phase. Refuse any other value or
mismatch before mutation, identify the derived phase, and report the mode-free command
`/address-pr-feedback <change-id>` so the user can rerun against current state.

For either derived finalized phase (`start` or `resume`), after the mode assertion and before
triaging, replying, or resolving any thread, call Delivery `reconcile_change_checkpoint`. Continue
only when it reports publication and the bound PR head exactly equals `finalized_head`. If
reconciliation does not publish or the PR head differs, stop with the exact Delivery/provider
error, leave threads untouched, and report `/address-pr-feedback <change-id>`. `start-reentry` is
not finalized and follows its preparation gate in Step 2 instead.

## Step 1 - Bind The Change And Pull Request

Require one native Delivery `change_id` from the prompt. Use the Delivery MCP surface for Change
authority and the `gh` CLI for GitHub review data. This step is read-only; do not prepare, reconcile,
post, resolve, edit, or otherwise mutate while deriving the phase. Do not use a GitHub MCP server.

1. Call `list_work_items` and require the requested Change publication item to be present.
2. Call `show_finalization_context` and retain the exact Change head, managed branch and worktree,
   reviewed head, `finalized_head`, finalization ID, publication phase, and any active
   review-repair invalidation. Do not infer a current finalization from a prior invocation.
3. Require `gh auth status` to succeed. Read `github_repository` from the tracked Delivery
   configuration and find the open pull request for the exact managed branch:

   ```text
   gh pr list --repo <repository> --head <managed-branch> --state open \
     --json number,url,state,isDraft,headRefName,headRefOid,baseRefName
   ```

   Require exactly one open pull request, the expected repository, managed branch, target branch,
   and retain its observed head. A closed or merged pull request, missing PR, multiple matches, or
   repository/branch/target mismatch is a bounded stop; do not repair it through another branch or
   PR. For finalized phases, do not reject a stale PR head before Step 0's
   `reconcile_change_checkpoint`; require exact equality with `finalized_head` only afterward.
   In `review-repair`, `prepare_review_repair` validates the expected head before thread inspection.
For a finalized phase, continue with the comment and trailer reads below to derive `resume` or
first-entry `start`. For `review-repair`, stop after binding the exact PR here; defer viewer,
comment, and trailer reads until `prepare_review_repair` succeeds in Step 2.
4. Read the authenticated viewer login with `gh api user --jq .login`. Read review threads with
   `gh api graphql --paginate --slurp`. Include `reviewThreads(first: 100, after: $endCursor)`, each
   thread's `id`, `isResolved`, `isOutdated`, location, and the comments' `id`, `url`, `body`,
   `author.login`, and `createdAt`. Read every page of each thread's comments; when a thread's
   `comments` page has `hasNextPage`, fetch subsequent pages by its `endCursor` before deriving
   marker state or triaging it. Save large raw responses only under `.owlbear/scratch/` and remove
   temporary files before closure.

   The initial thread-page query is:

   ```text
   review_query='query($owner:String!, $name:String!, $number:Int!, $endCursor:String) { repository(owner:$owner, name:$name) { pullRequest(number:$number) { reviewThreads(first:100, after:$endCursor) { nodes { id isResolved isOutdated path line startLine comments(first:100) { nodes { id url body createdAt author { login } } pageInfo { hasNextPage endCursor } } } pageInfo { hasNextPage endCursor } } } } }'
   gh api graphql --paginate --slurp -f query="$review_query" -f owner="$owner" -f name="$repo_name" -F number="$pr_number"
   ```

   Keep only unresolved threads bound to this exact PR. Outdated threads still require a deliberate
   classification, but do not automatically receive a code repair. Read the trailer map using the
   single command in Step 6 at `finalized_head` for a finalized phase. In `start-reentry`, Step 2
   reads it from the managed worktree's `HEAD` only after preparation and custody checks succeed.
   Keep only trailer IDs matching review-thread IDs from this bound pull request. `git log` lists
   newest commits first; when a thread appears in multiple commits, use its first (newest) full SHA.
   These GitHub and Git reads do not alter the PR.

Treat one unresolved review thread as one review comment unit. Multiple messages in one thread are
one unit. General issue comments without a resolvable review thread are context only and are not
silently marked resolved.

Do not call `gh pr checkout`, `gh pr merge`, `gh pr ready --undo`, or a raw `git push`. The managed
Change worktree and Delivery operations own source custody, draft state, finalization, and branch
publication.

## Step 2 - Critically Triage Every Thread

Run this step only for a derived `start` or `start-reentry` phase.

### Start Re-entry

For `start-reentry`, call Delivery `prepare_review_repair` first, before worktree inspection,
trailer mapping, or thread triage. It must replay against the same bound PR and expected head. Stop
on any refusal or identity mismatch; do not inspect threads for repair, edit, reply, or resolve.
After it succeeds, re-read `show_finalization_context` and direct Git state. Require the exact
managed branch and worktree, no current finalization, a clean worktree, and `HEAD` descending from
the recorded reviewed head. Read the trailer map at this worktree `HEAD` with the Step 6 command
after these custody checks and before triage. Then read every page of each bound thread's comments
with `author.login` and `createdAt`; only then classify threads.

For each unresolved bound-PR thread, keep an existing mapped, non-reopened thread classified as
`fix` with its recorded commit and create no new commit for it. Re-triage every reopened thread and
every thread without a mapped commit under the rules below. This preserves compatible interrupted
repair work without repairing an already-mapped thread again.

### First-Entry Start

For first-entry `start`, the finalized publication fence in Step 0 has already reconciled the
checkpoint and verified the PR head. Triage only after that fence succeeds.

Before changing code, inspect the current managed Change worktree, the exact Change context, the
Before changing code, inspect the current managed Change worktree, the exact Change context, the
reviewed diff, relevant requirements, and focused tests. For each unresolved non-outdated thread
that is not retained by the re-entry rule, write a bounded internal record containing:

- thread identity and reviewer claim;
- the reviewer's problem statement and assumptions;
- the evidence that the problem is true or false for this Change;
- the affected code path, acceptance behavior, and task or Change boundary;
- one classification: `fix`, `no-change`, `duplicate`, `stale`, `needs-user-decision`, or
  `authority-gap`;
- the proof needed to support the classification.

A reviewer sees only a partial code context. Do not accept a comment merely because it is specific,
confident, or from a trusted reviewer. Do not reject it merely because it conflicts with the current
implementation. Reproduce or reason through the concrete behavior, and judge its trigger against the
Change's operating context in `intent.md`: a concern that needs an actor or input that context
excludes is `no-change`.

Use these routes:

| Classification | Route |
| --- | --- |
| `fix` | Implement one bounded repair commit for this thread. |
| `no-change` | Record the evidence; use the no-fix start path after the finalized head is verified. |
| `duplicate` | Record the existing fix or thread reference; include this thread's trailer on the shared repair commit when known before commit creation. |
| `stale` | Record the current evidence and reply only after the publication fence. |
| `needs-user-decision` | Ask exactly one user question, leave the thread unresolved, and stop. |
| `authority-gap` | Stop without editing; identify the missing Design, Planning, Delivery, or provider authority. |

If there are no unresolved threads to triage, report `no-actionable-feedback` and do not prepare,
reset the PR, or create commits. If triage finds no new repair commit is needed, use the no-fix
first-entry path in Step 6; do not call `prepare_review_repair`. Never turn a style preference or
unsupported concern into implementation work without a concrete behavior or authority boundary.

## Step 3 - Prepare The Provider And Delivery State

Run this step only for first-entry `start` when at least one accepted `fix` needs a new repair
commit. `start-reentry` already replayed preparation before triage in Step 2. Neither `resume` nor a
no-fix first-entry `start` calls `prepare_review_repair`.

When at least one `fix` classification is ready to implement, call the Delivery MCP operation
`prepare_review_repair` before the first edit. It verifies the exact open, unmerged PR, returns a
ready PR to draft through the configured provider, invalidates the old finalization and ready
authority, and publishes the repair-ready state. It is replay-safe when the PR is already draft or
the repair preparation already completed.

Do not manually change the PR draft flag. Do not use the high-level `answer` facade as a substitute
for the provider-owned draft transition.
If preparation reports a closed PR, merged PR, head mismatch, missing publication, or provider
failure, stop and report the exact authority gap. A merged PR requires a fresh Change or an
explicitly designed merged-history recovery; this workflow never rewrites accepted history.

After preparation, re-read `show_finalization_context` and direct Git state in the returned managed
worktree. Require the managed branch, current head, reviewed boundary, and clean status to be
consistent before editing. The finalization ID must be absent while repair is in progress. If a
finalization reappears before a repair commit, stop with `authority-gap: review-repair-was-reversed`.
Never enter or modify the user's primary checkout.

If preparation completed but no accepted thread produced a commit, leave the Change in its prepared
repair state or abandon it. Do not restore finalization or ready authority. A repair commit must be
handled through fresh `/finalize-change <change-id>` and checkpoint publication before any ready-state
decision.

## Step 4 - Repair One Thread At A Time

Run this step only in `start` mode.

Process `fix` threads in a stable order. For each thread:

1. Re-read the thread and current code immediately before editing. Keep the repair inside the
   current Change boundary. If the comment reveals a new product requirement, architectural choice,
   or missing earlier authority, stop with `authority-gap` instead of expanding the repair.
2. Implement the smallest complete fix in the managed Change worktree.
3. Run focused proof for the affected behavior. A failed proof is not a reason to resolve the
   thread; repair or stop with the failure evidence.
4. Create exactly one commit for this thread using explicit owned paths and the scoped mechanics in
   `r-workspace-governance`. Do not amend, squash, rebase, or combine this commit with another
   actionable thread. The message passed to `commit-owned` must end with one `Review-Thread:
   <thread node ID>` trailer line per thread addressed by this commit. Use a message that identifies
   the bounded repair, for example:

   ```text
   fix: address PR feedback <short-slug> (<change-id>, address-pr-feedback)

   Review-Thread: <thread node ID>
   ```

5. Record the full commit SHA and proof result in the thread record before moving to the next
   thread.

One commit per thread means one commit per independent review conversation that warrants a code
change. If two threads are demonstrably duplicates of the same defect, keep one repair commit,
include one trailer for each thread on that same repair commit, classify the second as `duplicate`,
and reference the first commit in its reply rather than making an empty or duplicate commit.

A clean commit does not by itself authorize publication or acceptance. The repaired branch remains
unpublished until the normal finalization and checkpoint publication steps.

## Step 5 - Hand Off To Finalization

Run this step only in `start` mode.

After all eligible repairs, including a `start-reentry` that retained mapped commits:

1. Re-read the PR threads and current Delivery context. Require every repaired thread to have a
   recorded commit. Do not resolve repaired threads yet.
2. Re-read `show_finalization_context`. A repaired Change should be in
   `finalization-invalidated`, `review-repair`, or `ready-for-finalization` with the managed
   worktree at the new exact head and clean.
3. Do not construct finalization evidence inside this workflow. Give the user the exact next
   command and stop:

   ```text
   /finalize-change <change-id>
   ```

The first invocation stops here. It must not reply to or resolve a thread before the repaired head
This repair path stops here. It must not reply to or resolve a thread before the repaired head is
finalized and published. A `start-reentry` with retained mapped commits also hands off here even if
this invocation created no new commit. Report `/finalize-change <change-id>`.

## Step 6 - Publish Then Reply And Resolve Threads

Use this step only for `resume`, or for a first-entry `start` whose triage created no repair commit.
Never use it after a repair or during `start-reentry`. The only trailer read-back command for this
workflow is:

```text
git -C <worktree> log --format='%H%x09%(trailers:key=Review-Thread,valueonly,separator=%x2C)' <head>
```

It reads all reachable commits without a target-branch range and emits full commit SHAs plus their
comma-separated `Review-Thread` values. Keep only trailer IDs matching review-thread IDs from this
bound pull request. `git log` lists newest commits first; when a thread appears in multiple commits,
use its first (newest) full SHA. Step 0 uses this same read-back to derive the phase; `start-reentry`
uses the managed worktree's `HEAD`, while finalized phases use the exact `finalized_head`.

### Resume Order

1. Require a current finalization with no review-repair invalidation and `finalized_head` equal to
   the Change head. Call Delivery `reconcile_change_checkpoint` before thread triage or mutation.
   Require publication to succeed and the bound PR head to equal the finalized head; otherwise
   stop with the exact error and `/address-pr-feedback <change-id>`.
2. Read the trailer map at that exact finalized head.
3. Re-evaluate every unresolved bound-PR thread that is unmapped or reopened using Step 2's
   classification criteria. Do not prepare review repair or edit during `resume`. Any thread judged
   `fix` stays unresolved and unreplied; report `next_command: /address-pr-feedback <change-id>`.
   Retain the classification and evidence for every non-fix thread for the reply step.
4. Run the shared reply and resolve procedure for all awaiting mapped threads and all re-evaluated
   non-fix threads. A re-evaluated thread uses its current key: newest mapped repair commit when
   mapped, or the verified PR head with `commit=none` when unmapped. Resolve only after its settled
   current-key viewer marker is observed.

### No-Fix First-Entry Start

After triage, when no new repair commit was created, retain the current finalization. Step 0 has
already reconciled the checkpoint and verified that the PR head equals `finalized_head`. Do not call
`prepare_review_repair`; use the shared procedure for triaged `no-change`, `duplicate`, or `stale`
threads and report `next_command: none` when all eligible replies and resolutions are complete. If
triage creates any repair commit, or the derived phase was `start-reentry`, hand off to
`/finalize-change <change-id>` without replying or resolving.

### Shared Reply And Resolve Procedure

Use `gh api graphql` mutations, never a GitHub MCP server. Keep replies on the original thread and
pass the body as a GraphQL variable. Include the accepted problem, decision, focused proof, and full
repair commit SHA and URL when available. Append this exact hidden marker to every reply body:

`<!-- owlbear-pr-feedback thread=<thread-id> head=<head-sha> commit=<repair-sha-or-none> -->`

For a mapped thread the current key is its newest mapped repair commit; for an unmapped thread the
current key is the verified PR head with `commit=none`. The marker's `thread` must be the bound
thread ID. Obtain the viewer login with `gh api user --jq .login`. A viewer-authored marker reply is
settled only when no comment by another author follows it in `createdAt` order. An unsettled marker
never counts as posted.

Before every post, after any uncertain response, and before resolving, read all pages of that
thread's comments with `author.login` and `createdAt`. Accept only a settled viewer-authored marker
for the thread's current key. If one is already settled, never post another reply; record
`already-posted`. Otherwise post once with a GraphQL variable:

```text
reply_query='mutation($threadId:ID!, $body:String!) { addPullRequestReviewThreadReply(input: {pullRequestReviewThreadId: $threadId, body: $body}) { comment { id url } } }'
gh api graphql -f query="$reply_query" -f threadId="$thread_id" -f body="$reply_body"
```

If the response is uncertain, immediately reread all comment pages. If a settled current-key marker
is visible, treat the reply as posted and continue to the resolve preflight. Without one, leave the
thread unresolved, report the exact provider error as `reply-uncertain` (`reply_state: uncertain`),
and do not retry or resolve in this run. On an explicit reply failure, leave it unresolved, report the exact
provider error with `reply_state: failed`, and do not resolve.

Resolve only after a fresh all-page comment read shows a settled viewer-authored marker reply for
the current key. Resolve that same thread and require the result to show `isResolved: true`:

```text
resolve_query='mutation($threadId:ID!) { resolveReviewThread(input: {threadId: $threadId}) { thread { id isResolved } } }'
gh api graphql -f query="$resolve_query" -f threadId="$thread_id"
```

If the marker is absent or unsettled, or the resolve mutation fails or does not return
`isResolved: true`, leave the thread unresolved, retain its repair commit, report the exact provider
error when present, and do not claim closure. Reply always precedes resolve. Do not post a new
top-level PR comment when a thread reply is available. Leave the PR draft; never mark it ready or
merge it. The user owns the ready-state decision and GitHub merge; Delivery records the user-owned
merge later through `observe_acceptance`.

The workflow may finish immediately when no code repair was needed. A repair run stops for
finalization; the user invokes `/address-pr-feedback <change-id>` again after `/finalize-change`
succeeds. The next command never carries a `mode` argument.

## Output Template

Return a concise report in this shape:

```yaml
kind: "addressed-pr-feedback | no-actionable-feedback | blocked"
change_id: <native Change ID>
phase: "start-reentry | start | resume"
pull_request: <repository>#<number>
pr_state_before: "draft | ready | unknown"
prepared_for_repair: true | false
threads:
threads: [
   {
      thread_id: "<GitHub thread node ID>",
      classification: "fix | no-change | duplicate | stale | needs-user-decision | authority-gap",
      commit: "<full SHA or null>",
      mapped_commit_source: "trailer | new | none",
      reopened: "true | false",
      reply_state: "posted | already-posted | uncertain | failed | not-attempted",
      resolved: "true | false",
      proof: "<bounded proof or reason>"
   }
]
next_command: "/finalize-change <change-id> | /address-pr-feedback <change-id> | none"
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
   repaired head. Review repair is a one-way handoff and never restores stale finalization or ready
   authority.
- Never amend a reviewed commit, combine independent comment fixes, force-update a branch, hand-edit
  Delivery state, or resolve a thread before its reply is posted.
- External review remains outside the product's internal review receipts; only the resulting repair
  commits enter the normal finalization workflow.
