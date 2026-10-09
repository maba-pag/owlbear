# PR Feedback Replay-Safe Resume

> Status: candidate Design authority; admission gates pending (D3 added 2026-10-07; challenger rounds 3-4 repaired)

## Problem

Issue #225 (Delivery D11, audit baseline `5ba3d49ae`, 2026-09-05) reports that `/address-pr-feedback` has no durable handoff between `start` and `resume`. The Delivery redesign planned the fix as N05-D (`.owlbear/research/delivery-n05-plan.md` §3.7, D13, rows Y1-Y4) but did not build it (lead decision 2026-10-05: size M, medium-high risk; two persisted families with a format step, three MCP tools, engine-owned reply custody). #225 stays open (comment 2026-10-06).

Re-evaluation against current `dev` (2026-10-06, rechecked 2026-10-07):

### Already covered (observed)

- `prepare_review_repair` (`serve/delivery/src/owlbear_delivery/application_publication.py`) binds the exact repository, PR number, node ID, base branch, finalized head and open/unmerged state under the checkpoint lock; it is replay-safe (an existing `review-repair` invalidation replays, re-validating the PR at its expected head, and re-drafts only if needed) and refuses merged Changes.
- Repair commits live on the managed Change branch in the retained Change worktree; they survive chat loss and enter normal finalization and checkpoint publication.
- While review repair is open, target sync and external-head adoption or promotion are refused (`_require_no_review_repair`).
- Continuation surfaces the state: the `review-repair` publication phase renders a "Review feedback needs attention" card with `/address-pr-feedback <change-id>` (`work_items.py`), and the finalized PR summary names the same command (`application_support.py`).
- Feedback arriving after finalization is the supported entry. Feedback after merge is refused by the merged latch and needs a successor Change; feedback before finalization is an explicit `authority-gap: change-not-finalized`. Neither is a #225 gap.

### Still missing (observed)

- G1 Classification and thread-to-commit map are chat-only. `w-address-pr-feedback` Step 2 writes "a bounded internal record" (line 80) and Step 4 records the commit SHA "in the thread record" (line 158). A fresh `resume` cannot recover which commit repaired which thread.
- G2 Interrupted `start` cannot resume: Step 1 continues "only for a finalized PR" (line 33), but after `prepare_review_repair` the finalization is invalidated; and nothing lets a re-run recognize a thread already repaired on the branch.
- G3 Replies are not idempotent. Step 6 posts `addPullRequestReviewThreadReply` (line 210) without first reading the thread for a prior reply; the thread query paginates threads but not comments (line 58).
- G4 No-repair runs have no reply step (lines 101-102, 229).
- G5 No focused workflow tests exist for this skill.
- G6 The repair-to-finalize handoff is refused: the Change stays in publication phase `review-repair` until re-finalized (`work_items.py` `resolve_publication_phase`), and the engine finalizes a repaired head in that phase (`application_lifecycle.py` `_finalize_change_locked`, `application_readiness.py`), but `w-change-finalization` Step 0 admits a user-invoked attempt only in `ready-for-finalization` or `finalization-invalidated`.
- G7 Mode routing depends on the user (observed 2026-10-07): the prompt defaults to `start`, while the Cockpit review-repair card (`work_items.py`) and the finalized PR summary (`application_support.py`) name only `/address-pr-feedback <change-id>`. After re-finalization that default `start` sees mapped repaired threads and hands off to `/finalize-change` again instead of replying, so the journey loops unless the user remembers `mode=resume`.

## Product Promise

- A fresh `resume` (new chat, no prior output) recovers every repaired thread's repair commit from the managed Change branch at the finalized head, bound to the exact PR.
- An interrupted `start` can be re-run during review repair, re-validated against the same PR and expected head, and does not repair an already-repaired thread again unless someone commented after its reply.
- After repairs, `/finalize-change` accepts the repaired Change so the journey reaches `resume`.
- The single command `/address-pr-feedback <change-id>`, as named by Cockpit and the PR summary, selects the correct phase in every state of a feedback round, including an unpublished finalized checkpoint, later rounds, and reopened threads; the user never needs to remember a mode.
- The workflow treats a reply as posted only when a settled viewer marker reply for the thread's current repair or head is visible, never posts while one is, never retries automatically after an uncertain response, and resolves a thread only after observing such a reply.
- A thread judged to need a fix without a recorded repair commit fails closed: no reply, thread unresolved, bounded route `/address-pr-feedback <change-id>` again.
- Failed reply or resolve mutations leave the thread unresolved, keep repair evidence, and report the exact provider error.
- A `start` run with no new `fix` on a still-finalized, published Change replies and resolves at the unchanged finalized head.
- External comments remain evidence, never Design or Delivery authority.

## Normal Workflow

1. User runs `/address-pr-feedback <change-id>` on a finalized Change with an open PR.
2. The workflow derives the `start` phase, publishes any pending finalized checkpoint, and verifies the PR head. It reads the branch's thread-to-commit map, triages unresolved threads not already repaired (and reopened ones), prepares review repair when any new `fix` exists, commits one repair per `fix` thread with its thread trailer, and hands off to `/finalize-change`. With no new `fix`, it replies and resolves directly.
3. If interrupted, the user re-runs `/address-pr-feedback <change-id>`; in the `review-repair` phase it re-enters `start`, replays `prepare_review_repair` to re-validate the PR, and continues from the recorded map.
4. The user runs `/finalize-change <change-id>`; it proceeds in `review-repair` when the engine reports the Change ready.
5. The user runs `/address-pr-feedback <change-id>` again, possibly in a new chat. The workflow derives the `resume` phase from the fresh finalization and the repaired threads still awaiting their reply, publishes the checkpoint, verifies the PR head, reads the map at the finalized head, re-evaluates non-fix and reopened threads, and replies at most once per settled marker before resolving.
6. If someone comments after a reply, the same command later derives `start` and re-triages that thread.

## Operating Context (inferred from execution plan §1 and N05 D13/D14)

- Actors and trust: one trusted local user; OwlBear agents trusted but fallible; GitHub reviewers (humans and bots) untrusted for authority.
- Exposure: PR review-comment text (untrusted input) is read and quoted in agent reasoning; GitHub GraphQL via the user's `gh` credentials.
- Stakes: local and reversible. Worst cases: one duplicate visible PR reply, a thread resolved prematurely, a duplicate repair commit. No data loss, no secrets, no merge (user owns merge).
- Guarded: lost thread-to-commit map across chat loss; duplicate replies after uncertain responses or partial runs; double repair after interruption; acting on a stale PR or head; running the wrong phase from the default command; silently closing a thread someone answered. Not guarded: concurrent operators on the same Change; reviewer-forged markers beyond viewer-authorship matching; edited or deleted prior replies; a provider-delayed post becoming visible only after a later read; a reviewer unresolving a thread without commenting.

## Scope

- `share/skills/w-address-pr-feedback/SKILL.md` and `share/prompts/address-pr-feedback.prompt.md`.
- `share/skills/w-change-finalization/SKILL.md` Step 0 user-invoked phase gate only (user decision D2).
- Focused tests in `tests/test_agent_ecosystem_validation.py`, including an executable check of the documented trailer read-back command against a disposable Git repository.

## Accepted Exclusions

- No Delivery-owned handoff record, persisted state family, MCP tool, or engine-posted reply (user decision D1). Removed value: engine-level reply custody (release-gated launcher, Y1-Y4 settlement) and lock-serialized replies.
- Rationale for `no-change`, `duplicate` (without its own trailer), and `stale` is not persisted; `resume` re-evaluates those threads against current evidence (user decision D1, reaffirmed 2026-10-07 over a local ledger). Removed value: identical non-fix rationale across sessions and avoiding their re-triage.
- Absolute no-duplicate guarantee: GitHub offers no reply idempotency key, so a provider-delayed post can still produce one visible duplicate (factual limit shared by every option, including N05-D D13).
- Reopen without comment (pending user confirmation at approval): a thread the reviewer unresolves without a new comment keeps a settled reply and is resolved again by the next run (designer consequence of D3; reading unresolve history would add a second provider query surface).
- No engine change: Delivery readiness, finalization, ready, `prepare_review_repair` and `reconcile_change_checkpoint` semantics, the Cockpit card command, and the PR summary text are unchanged (D3 makes their existing command correct).
- No change to PR merge ownership or Design authority; no second repair agent; no GitHub MCP server.
- Feedback after merge (successor Change) and before finalization (existing authority gap) stay out of scope.

## Preserved Behavior

- One commit per independent `fix` thread; duplicates reference the first commit and create no second commit.
- `start` hands off to `/finalize-change` when it creates repair commits or runs in review repair; `resume` never calls `prepare_review_repair`.
- Reply before resolve; failures leave threads unresolved and retain repair commits.
- The workflow never marks the PR ready, merges, or uses `gh pr checkout`, raw `git push`, or a GitHub MCP server.
- All other `w-change-finalization` steps and its issued-launch path are unchanged.

## Decisions

- D1 (user-confirmed 2026-10-06, reaffirmed 2026-10-07): Option B — durable thread-to-commit map as `Review-Thread` commit trailers on the managed Change branch, and reply idempotence through a hidden marker matched only in viewer-authored thread comments. Rejected: A, Delivery-owned record and engine replies (prior N05-D); C, an additional local handoff file (reconsidered 2026-10-07 and rejected again: it duplicates facts already held by commits and comments, adds stale/malformed-ledger routes, and only saves re-triage of non-fix threads, which fails safe).
- D1 consequence (design): a no-fix `start` run on a still-finalized Change replies and resolves at the unchanged finalized head without `prepare_review_repair` (N05-D no-repair precedent; skill "may finish immediately" rule). Mixed runs keep non-fix replies for `resume`.
- D2 (user-confirmed 2026-10-06): Option A — include the `w-change-finalization` Step 0 fix: a user-invoked attempt also proceeds in `review-repair` when `ready_for_finalization` is true. Rejected: B, separate issue.
- D3 (user-confirmed 2026-10-07): derived phase routing — `mode` becomes optional; the workflow selects `start` or `resume` from `show_finalization_context`, the trailer map, and viewer marker replies of unresolved threads, and an explicit mode that conflicts with the derived phase is refused with the command `/address-pr-feedback <change-id>`. Rejected: keeping explicit mode with an engine card/summary cue (engine and golden-fixture changes; the user can still choose wrongly), and no routing change (G7 stays open).
- Challenger repairs (2026-10-06): map read from the head without a target-ref range; `start` re-entry in `review-repair` replays `prepare_review_repair` as its PR and head fence; reconcile before verifying the PR head in `resume`; paginated per-thread comment reads; no automatic retry after an uncertain reply; trailers via the `commit-owned` message.
- Challenger repairs (2026-10-07, round 3): the marker carries the thread's current repair commit; a marker reply is settled only when no other-author comment follows it; awaiting versus reopened mapped threads replace the head-keyed reopen rule; COM-005 handoff narrowed to runs that create repair commits or run in review repair.
- Challenger repairs (2026-10-07, round 4): every reply-observed check (skip, uncertain recovery, resolve precondition) requires a settled marker for the current key; the finalized publication fence (`reconcile_change_checkpoint`, then PR head equals finalized head) applies to `start` first entry as well as `resume`.

## Success

A run interrupted after one of two repair commits, re-run, finalized, and resumed in a fresh session, using only `/address-pr-feedback <change-id>` and `/finalize-change <change-id>`, yields exactly one repair commit per `fix` thread and one marked reply per thread, with repaired-thread replies citing the commit read from its trailer.

## Technically Done But Wrong

- Map kept only in chat or in an untracked scratch file.
- `start` re-entry proceeding without replaying `prepare_review_repair` against the same PR and expected head.
- Resume trusting a mapped commit not reachable from the finalized head, or verifying the PR head before reconciling the checkpoint.
- Dedupe matching markers in comments not authored by the viewer, or reading only the first page of comments.
- Retrying a reply automatically after an uncertain response.
- Replying directly from `start` while the Change is in review repair or has unpublished repair commits.
- Widening the finalization gate beyond `review-repair` with `ready_for_finalization`, or changing engine readiness.
- A documented trailer read-back command that the test does not actually execute.
- The default command on a freshly finalized Change with awaiting threads handing off to `/finalize-change` again instead of entering `resume`.
- An explicit `mode` overriding the derived phase.
- An older-round marker blocking `resume` for a newly repaired thread, or an unsettled marker counted as a posted reply anywhere (skip, uncertain recovery, or resolve).
- `start` first entry on a checkpoint-pending Change acting before `reconcile_change_checkpoint` and the PR head fence.

```yaml target-contract
kind: commitment
id: COM-001
class: dealbreaker
provenance: "issue #225 acceptance criteria"
statement: A fresh resume recovers each repaired thread's repair commit from the managed Change branch at the finalized head without prior chat output, bound to the exact open PR, and an interrupted start can be re-run during review repair, re-validated by replaying prepare_review_repair against the same PR and expected head, without repairing an already-mapped thread again unless another author's comment follows every viewer marker reply for its current repair.
```

```yaml target-contract
kind: commitment
id: COM-002
class: dealbreaker
provenance: "issue #225 acceptance criteria, bounded by the provider's lack of reply idempotency"
statement: The workflow reads all comments on a thread before every post and after any uncertain response and treats a reply as posted only when a settled viewer-authored marker reply for the thread's current repair commit or reply head is visible; it never posts while one is visible, never retries automatically after an uncertain response, resolves a thread only after observing such a reply, and on any mutation failure or unsettled evidence leaves the thread unresolved with the exact provider error and repair evidence intact.
```

```yaml target-contract
kind: commitment
id: COM-003
class: agreed-path
provenance: user decision D1 (2026-10-06, reaffirmed 2026-10-07)
statement: The durable map is one Review-Thread trailer per addressed thread in each repair commit message, and reply idempotence uses a hidden marker; the change edits only workflow skills, the PR-feedback prompt, and focused tests, and adds no Delivery state, MCP tool, engine change, local handoff file, or engine-posted reply. Non-fix threads are re-evaluated on resume.
```

```yaml target-contract
kind: commitment
id: COM-004
class: protected-request
provenance: "source-observed existing behavior and issue #225 scope"
statement: One commit per independent fix thread, the start-to-finalize handoff, no preparation in resume, reply-before-resolve, no PR ready or merge action, no GitHub MCP server, and external comments as evidence only remain unchanged.
```

```yaml target-contract
kind: commitment
id: COM-005
class: important-reviewed
provenance: designer consequence of D1 and existing skill rule; N05-D no-repair precedent
statement: A start run that creates no new repair commit on a Change that is still finalized, with no review-repair invalidation and the PR head at the finalized head after checkpoint reconciliation, replies to and resolves its triaged threads without calling prepare_review_repair; a start run that creates repair commits or runs in the review-repair phase hands off to finalization without replying.
```

```yaml target-contract
kind: commitment
id: COM-006
class: agreed-path
provenance: user decision D2 (2026-10-06)
statement: The user-invoked finalization workflow proceeds in the review-repair publication phase when the engine reports ready_for_finalization, so the PR-feedback repair handoff reaches finalization; engine readiness and every other finalization rule are unchanged.
```

```yaml target-contract
kind: commitment
id: COM-007
class: agreed-path
provenance: user decision D3 (2026-10-07); challenger round 3-4 repairs
statement: The workflow derives its phase from show_finalization_context, the trailer map, and viewer marker replies of unresolved threads so that the existing command /address-pr-feedback <change-id> is correct in every state of a feedback round, including an unpublished finalized checkpoint, later rounds, and reopened threads; on a finalized Change both phases reconcile the checkpoint and verify the PR head before any thread action; mode is optional, an explicit mode that conflicts with the derived phase is refused with that command and no mutation, and the Cockpit card, PR summary, and Delivery engine are unchanged.
```

```yaml target-contract
kind: outcome
id: OUT-001
title: Replay-safe PR feedback resume
promise: The user can interrupt and resume PR-feedback repair in a fresh session with one command, finalize the repaired Change, and close review threads without choosing a mode, losing repair mappings, repairing a thread twice, or receiving duplicate replies while a prior reply is visible.
dependencies: []
commitments: [COM-001, COM-002, COM-003, COM-004, COM-005, COM-006, COM-007]
acceptance:
  - "AC-001: Given the updated skill, Step 4 requires every repair commit message passed to commit-owned to end with one 'Review-Thread: <thread node ID>' trailer line per thread it addresses, a demonstrated duplicate adds its trailer to the same repair commit, and the skill documents one exact git log command that reads the trailer map from a given head without a target-branch range and keeps only thread IDs of the bound pull request."
  - "AC-002: Given a disposable Git repository whose commits were made with multi-paragraph messages carrying Review-Thread trailers (one commit with two trailers, one with one, one with none, one with an unrelated thread ID), running the read-back command extracted verbatim from the skill and filtering to the synthetic pull-request thread set returns exactly the expected thread-to-full-SHA map."
  - "AC-003: Given the updated skill, start in the review-repair phase first calls prepare_review_repair and stops on any refusal, then requires a clean managed worktree descending from the reviewed head, reads the trailer map from the worktree HEAD before triage, keeps each already-mapped unresolved thread that is not reopened classified fix with its recorded commit and creates no new commit for it, and triages reopened threads."
  - "AC-004: Given the updated skill, resume requires a current finalization with no review-repair invalidation and finalized head equal to the Change head, calls reconcile_change_checkpoint before requiring the PR head to equal the finalized head, reads the map at the finalized head, and leaves any thread it judges to need a fix without a mapped commit unresolved and unreplied with next command /address-pr-feedback <change-id>."
  - "AC-005: Given the updated skill, every reply body carries the hidden marker '<!-- owlbear-pr-feedback thread=<thread-id> head=<head-sha> commit=<repair-sha-or-none> -->'; a marker reply counts only when authored by the gh viewer and is settled only when no comment by another author follows it; before posting, after any uncertain response, and before resolving, the workflow reads all pages of the thread's comments with author and createdAt and accepts only a settled marker reply for the thread's current repair commit (mapped) or current head (unmapped); an unsettled marker never counts; after an uncertain response without such a reply it leaves the thread unresolved, does not resolve, and reports reply-uncertain without retrying in that run."
  - "AC-006: Given the updated skill, a thread is resolved only after a settled viewer-authored marker reply for its current key is observed and the resolve result shows isResolved true; any failed reply or resolve leaves the thread unresolved, reports the exact provider error, and retains the repair commit."
  - "AC-007: Given the updated skill, a start run that creates no new repair commit on a Change with a current finalization and no review-repair invalidation, after reconcile_change_checkpoint and with the PR head at the finalized head, replies to and resolves its triaged threads without calling prepare_review_repair and reports next command none; a start run that creates any repair commit or runs in the review-repair phase hands off to /finalize-change without replying."
  - "AC-008: Given the updated skill and prompt, the preserved rules remain stated: one commit per independent fix thread, finalize handoff after repairs, no prepare_review_repair in resume, reply before resolve, no ready or merge action, no GitHub MCP server, external comments as evidence only."
  - "AC-009: Given the change, the new and affected tests in tests/test_agent_ecosystem_validation.py pass and Ruff reports no findings for that file."
  - "AC-010: Given the updated skill, the output template reports the derived phase and per thread the mapped commit source (trailer, new, or none), whether it was reopened, and the reply state (posted, already-posted, uncertain, failed, or not-attempted)."
  - "AC-011: Given the updated w-change-finalization skill, Step 0 admits a user-invoked attempt when the phase is ready-for-finalization, finalization-invalidated, or review-repair and the context reports ready_for_finalization, and admits no other phase."
  - "AC-012: Given the updated skill, Step 0 derives the phase before any mutation: publication phase review-repair selects start re-entry; a current finalization with no review-repair invalidation and finalized head equal to the Change head selects resume when at least one unresolved bound-PR thread mapped by a trailer reachable from the finalized head is awaiting (no viewer marker reply for its newest mapped commit, or a settled one), and start otherwise; a mapped thread whose every viewer marker reply for its newest mapped commit is unsettled is reopened and is triaged in start; every other state reports authority-gap change-not-finalized; on a finalized Change both derived phases then call reconcile_change_checkpoint and require the PR head to equal the finalized head before any thread action, stopping with the exact error and /address-pr-feedback <change-id> when reconciliation does not publish or the head still differs."
  - "AC-013: Given the updated skill and prompt, mode is optional and documented as derived when omitted; an explicit start or resume that differs from the derived phase, or any other value, is refused before any mutation with the command /address-pr-feedback <change-id>; every next_command the skill reports for continuing the round is /address-pr-feedback <change-id> or /finalize-change <change-id> without a mode argument."
```
