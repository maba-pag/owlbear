# Pull Requests, CI and the Merge Queue: Build Design (TD-226, TD-238, TD-278)

> **Owning decisions:** TD-226 (merge-queue support now), TD-238 as amended by TD-278 (OwlBear's `main`
> through PRs with required CI), TD-251 (CI switches on with the PR route), TD-279 (live proof repository)
> **Date:** 2026-10-17 (revision 4 after Sol's challenges: 55% with twelve findings, 73% with three open and
> four new, 80% with two open and one new; all taken)
> **Question:** How does Delivery merge through a GitHub merge queue, and how does OwlBear's own `main`
> move to pull requests with required CI?

## 1. Context

TD-226 replaces TD-22's "detect a queue and leave the merge to the owner" with real support. TD-238 wanted a
merge queue on OwlBear's `main`; GitHub offers queues only to organization repositories, so TD-278 puts
OwlBear on required CI with "up to date before merging" and proves the queue on `porsche-code/brief-layover`
(TD-279). TD-251 keeps every workflow disabled until this route switches CI on.

## 2. Sources Studied

| Source | Fact used |
| --- | --- |
| `github/gh.py` `read_rules`, `request_merge` | Rules come from `rules/branches/{b}` plus classic protection; `queue_required` is detected; the pull-request rule's allowed methods are not read; merge is `PUT pulls/{n}/merge` with `sha` |
| `github/merge_offer.py` `decide` | One ordered block list; `Block.QUEUE` hands the merge to the owner |
| `workflow_steps/merge.py` `gate`, `run`, `submit` | Gate at the exact head (review, person checks, local head, conversation, head contains target, CI, rules, review, visual, consent), the same gate again under the per-target merge lock, then the guarded merge and a readback |
| `workflow_steps/publish.py` `reviewed`, `change_contracts/evidence.py` | Review and visual acceptance are bound to the PR head and its tree |
| `workflow_steps/follow.py` `fix_ci`, `missing` | CI failures become a fix task with the log tail, counted by failing checks (progress, not commits) |
| `change_flow/loop.py` (pause), `change_flow/round_flow.py` `restartable` | Pause stops scheduling at once; restart is refused while a merge holds consent |
| `settings/profile.py` `_jobs`, `METHOD` | The workflow parser leaves reusable calls and matrices unresolved; the profile prefers squash when allowed |
| `design_packs/pack_git.py` `push` | Pack activation pushes its commit to the checkout's upstream branch and undoes it on refusal |
| GitHub GraphQL schema (introspected 2026-10-17) | `enqueuePullRequest(pullRequestId, expectedHeadOid, jump)`; `dequeuePullRequest(id)`; `PullRequest.mergeQueueEntry {state position headCommit baseCommit enqueuedAt}`, `isInMergeQueue`; states QUEUED, AWAITING_CHECKS, MERGEABLE, UNMERGEABLE, LOCKED; `AddedToMergeQueueEvent` and `RemovedFromMergeQueueEvent {id reason createdAt beforeCommit actor}` in the PR timeline; `MergeQueueConfiguration {mergeMethod checkResponseTimeout …}` |
| [Managing a merge queue](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue) | Required checks must run on `merge_group`, else the queue waits until its timeout; removal reasons: failed group checks, timeout, a user's removal, a protection failure; temporary branches start with `gh-readonly-queue/{base}` |
| [About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches) | Required checks pass when `successful`, `skipped` or `neutral` |
| `.github/workflows/*.yml` | Six pull-request suites (Python, Python browser, Cockpit, Static checks, Tooling, Agent ecosystem), each with its own `paths:` filter and draft guard, all disabled (TD-204) |
| `gh api repos/maba-pag/owlbear/rulesets/14785160` | `deletion`, `non_fast_forward`; bypass: repository role 5 (admin), mode `always` |
| Live probes (TD-278, TD-279) | Personal repositories refuse a merge-queue rule; `porsche-code/brief-layover` accepts one |

## 3. Delivery: Merging Through a Queue (TD-226)

### 3.1 Reading the queue

- `Rules` gains `queue_method` and `queue_timeout` (the `merge_queue` rule's parameters) and
  `allowed_methods` (the `pull_request` rule's `allowed_merge_methods`). The profile's merge methods become
  the repository's methods intersected with the rule's; with a queue the queue's method merges and the
  profile's method does not gate.
- The provider reads, in one GraphQL query per pass: the PR (state, merged, head), its `mergeQueueEntry`
  (state, position, head), and its latest `AddedToMergeQueueEvent` and `RemovedFromMergeQueueEvent` (id,
  time, reason, actor). It writes with `enqueue(pr, expected_head)` and `dequeue(pr)`.

### 3.2 Delivery's own records

They hold what Delivery did and handled, never GitHub's state (DR5):

- `Change.queue: QueueClaim | None`: the head Delivery enqueued, the attempt's time, whether the send's
  result is settled, and the merge-group runs seen while it was queued (id, head sha, branch). Written
  before the enqueue is sent; cleared when the PR merges, when a dequeue is read back, or when a removal
  after it is handled.
- `Change.queue_seen`: the id of the last removal event Delivery handled, kept apart from the claim and
  advanced in the same store write as the action that handles it, so one removal is handled and charged once.

Both are additive with defaults (`None`, `""`): existing format-4 records load unchanged and need no
migration; a round-trip test covers them.

### 3.3 The gate with a queue

The gate is unchanged: the head must contain the target, so review and visual evidence stay bound to what
the queue tests first (Sol's finding 4); integrations follow TD-235. The queue adds the re-test with PRs
queued ahead. Every pass while the PR is queued runs the gate again (conversation, person checks, evidence,
rules, head); a failed gate dequeues (§3.6) before it routes anywhere.

### 3.4 Each pass of the merge step with a queue

1. Merged: done (the merge commit from the PR), cleanup and pull-back as today; the claim is cleared.
2. A removal event newer than the claim's time and other than `queue_seen`: handled by §3.5.
3. An entry at the PR head: the gate runs (§3.3); passing, it stays pending ("PR #n in the merge queue:
   position p, state s") and records any new merge-group run for this PR and head in the claim. An entry
   without a claim (a person enqueued it) is adopted: a settled claim with the entry's head and time, then
   the gate as above, then follow or dequeue. An entry at
   another head, or reads that disagree (an added event after the claim but no entry and no merge): pending,
   read again next pass; nothing is sent.
4. No entry, no unhandled removal and no claim: the gate runs; under the target's merge lock everything is
   read again and gated again, the claim is written unsettled, then `enqueue(pr, head)` is sent with
   `expectedHeadOid`. A definite answer settles it: success, or a GitHub error that names why it was not
   enqueued (the claim is cleared and the error handled like a refused merge). A claim, settled or not, ends
   only by the merge, a handled removal after it, a dequeue read back, or the owner's answer; while one is
   outstanding nothing is sent again.
5. A claim whose evidence is missing (an unknown send's result, or a successful send followed by reads with
   no entry, no event after it and no merge) stays pending; after three such passes the owner is asked
   whether to enqueue again or pause.

Consent (the profile's "ask before merging") is asked for the exact head before the claim, as before. A host
restart cannot revoke a merge GitHub already accepted; the next pass reconciles it.

### 3.5 Removal from the queue

| Reason (exact strings fixed by the live proof, §5) | Action |
| --- | --- |
| Group checks failed | A fix task carrying the failing job's log from the merge group this removal ended: the recorded run whose commit is the event's `beforeCommit` when the live proof shows that it names the group, else the only failed group run for this PR and head that completed between the claim's time and the removal; when that is ambiguous or absent, the task says the diagnostics are unavailable and carries the reason text. Counted like `fix_ci` (§3.7) |
| Timed out waiting for checks | Ask the owner once: the queue waited for checks that never reported, usually a workflow without `merge_group:`; continue (enqueue again) or pause |
| Conflict | Integrate the target (builder task), then the usual CI and TD-235 round, then the next pass enqueues |
| Protection failure | Ask the owner, naming the unmet rule when GitHub gives it |
| Removed by a person, or not classified | Ask the owner: enqueue again, or pause; never re-enqueue against a person's removal on its own |

### 3.6 Leaving the queue

Pause, restart (TD-237), rebuild and plan again (TD-245), and any answer that sends the Change back from the
merge step must not leave a queued PR behind. Both callers of `Store.fold` (the host's `_one` and the step
runner) already read the PR before folding; one provider-aware pre-fold step, under the Change lock, runs
for such an item while the Change is at the merge step: it reads the PR's queue membership (with or without
a claim), dequeues an entry and reads back. No entry and no claim: the item folds. An outstanding claim
without evidence: the item waits until §3.4 settles it. Merged: the item waits and the merge step takes the
merged path. A failed dequeue: the item waits, the reason is logged and shown, and the next pass tries
again. A waiting item is neither acknowledged nor deleted by `Store.fold`. A confirmed dequeue clears the
claim, and the merge step's queue wait no longer counts as "a merge is under way" for `restartable`, so a
restart can retire the consent as TD-237 does. Abandoning closes the PR, which removes it.

### 3.7 Budgets

Group-check fixes share `fix_ci`'s accounting (failing checks, progress-based, across commits). Each
handled removal is charged once, in the write that advances `queue_seen`; polling and adopting a person's
entry charge nothing.

## 4. OwlBear: Pull Requests With Required CI (TD-238, TD-278, TD-251)

### 4.1 One required check

A workflow that never starts never reports, so path filters on required workflows would block PRs that do
not touch their paths. So:

- A new workflow `ci.yml` on `pull_request` (types opened, reopened, synchronize, ready_for_review; no path
  filter) has a `scope` job running a small script that lists the touched suites by the path lists the
  workflows hold today (moved into the script as their one source), one job per suite calling the existing
  workflow through `workflow_call` with `if:` on the scope, and a final job named **CI** (`if: always()`)
  that passes only when `scope` succeeded and every selected suite succeeded.
- The six suites lose their `pull_request` trigger and draft guard and gain `workflow_call`;
  `workflow_dispatch` stays. Each caller job grants the permissions its suite declares today. CI runs on
  drafts too, so a skipped draft run can never stand in for a ready PR's run. No `merge_group` trigger yet:
  OwlBear has no queue (TD-278).

### 4.2 Before the rules

1. Merge methods: the repository allows merge commits only (TD-229); Delivery's rule reading (§3.1) also
   intersects methods for every project.
2. Pack activation pushes to the checkout's upstream (`pack_git.push`); on a branch that requires PRs the
   push is refused and undone, so the old pack stays active. Its refusal message says that `main` needs a
   PR; activation through a PR is a follow-up.
3. The workspace instructions say maintenance reaches `main` through a PR.

### 4.3 The switch

1. The six workflows are enabled again (`gh workflow enable`); a PR runs its head's workflow files, so the
   §4.1 PR runs only `ci.yml`. TD-204's pre-commit hooks stay manual.
2. The §4.1 PR shows CI running only the touched suites and **CI** green; a docs-only PR shows every suite
   skipped and **CI** green. Both merge (merge commits).
3. The `main` ruleset gains `pull_request` (no approvals, no code-owner or last-push approval, merge commits
   only) and `required_status_checks` (`CI`, strict), keeps `deletion` and `non_fast_forward`, and loses the
   admin bypass, so the rules bind the owner and the assistant alike (TD-238: a broken Delivery is
   repaired through a PR; an admin can still edit the ruleset). The complete ruleset is read back.
4. From then on every OwlBear change goes through a branch and PR; the assistant merges once **CI** passes
   on an up-to-date branch (TD-229, TD-238); the runtime moves only to Sol-accepted merged commits (TD-247).

## 5. Proof

- Unit tests with the provider fake: every rule of §3.4 including adoption, disagreeing reads, a definite
  enqueue refusal, an unknown result settled by each kind of evidence or by the owner, and a successful send
  followed by empty reads that must not send again, every row of §3.5,
  a removal handled once across a restart, §3.6 for each leaving action through both fold callers (an entry
  without a claim, an already-merged PR, a failed dequeue), §3.7, the format-4 round trip, and the
  intersected merge methods.
- Live, on `porsche-code/brief-layover` (TD-279), a script (no Delivery host) drives the provider: a ruleset
  with a merge queue and one required check, a workflow on `pull_request` and `merge_group`, then (a) a PR
  enqueued and merged, (b) a PR whose group check fails and is removed (recording the reason text and the
  group run's branch and lookup), (c) a dequeue (recording its event), (d) a timeout with a workflow lacking
  `merge_group`, (e) the removal event's `beforeCommit` compared with the group run's commit. §3.5's
  strings and lookup are fixed from what it records.
- OwlBear: §4.3 step 2.

## 6. Open

- Pack activation through a PR (§4.2).
- Moving OwlBear into an organization, then switching its `main` to the queue (TD-278).
