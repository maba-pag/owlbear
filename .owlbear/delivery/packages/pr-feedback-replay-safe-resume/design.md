# PR Feedback Replay-Safe Resume - Design

> Status: candidate; D1 (Option B, reaffirmed 2026-10-07), D2 (Option A), and D3 (derived phase routing, 2026-10-07) resolved; challenger rounds 1-4 findings repaired; gates must rerun for this revision

## Current Ownership (observed)

- Workflow: `share/skills/w-address-pr-feedback/SKILL.md`; prompt `share/prompts/address-pr-feedback.prompt.md`.
- Engine: `prepare_review_repair` (`application_publication.py`) owns the draft transition and review-repair invalidation. On replay it re-validates the open, unmerged PR against the invalidation's `expected_head` (`_review_repair_authority`, `_observe_review_repair_pull_request`, `_replay_review_repair`) and re-drafts only if needed.
- `show_finalization_context` (`application_lifecycle.py`, model `DeliveryFinalizationContext`) returns branch, worktree path, `change_head`, `reviewed_change_head`, `publication_phase`, `ready_for_finalization`, `finalization_id`, `finalized_head`, `finalization_invalidation_id`. During review repair `finalized_head` is null.
- Phase: `resolve_publication_phase` (`work_items.py`) reports `review-repair` while the review-repair invalidation exists, i.e. until a fresh finalization clears it.
- Finalization: `finalize_change` (`application_lifecycle.py` `_finalize_change_locked`) requires `ready_for_finalization` and the exact `change_head`; readiness blocks with reason `review-repair` only while the head equals the invalidation's expected head (`application_readiness.py`). So the engine finalizes a repaired head in `review-repair` phase.
- Finalization workflow gate: `share/skills/w-change-finalization/SKILL.md` Step 0 admits a user-invoked attempt only in `ready-for-finalization` or `finalization-invalidated`, rejecting the `review-repair` phase that the PR-feedback handoff produces (pre-existing defect; D2).
- `/finalize-change` records finalization and queues a checkpoint; `reconcile_change_checkpoint` (`application_publication.py`) publishes it under the engine checkpoint lock, returns `reconciled: false` with the pending error while a retry is not yet eligible, and is the engine-owned publication path for a lagging PR head.
- Entry command: the Cockpit review-repair card (`work_items.py`) and the finalized PR summary (`application_support.py`) name `/address-pr-feedback <change-id>` without a mode; the prompt defaults omitted mode to `start` (G7; D3).
- Provider: GitHub through `gh api graphql` run by the agent.
- Commits: `r-workspace-governance` via `commit-owned` (`serve/tools/src/owlbear_tools/commit_owned.py`), which passes a complete multi-line `-m` message.
- History: normal publication does not rewrite commit messages. Out-of-band head recovery (`workspace_target_sync.py`) resets the managed branch to the reviewed head, removing later commits from the branch.

## Architecture

### Marker and settled reply

- Marker appended to every reply body: `<!-- owlbear-pr-feedback thread=<thread-id> head=<head-sha> commit=<repair-sha-or-none> -->`, where `head` is the head the reply is posted at and `commit` is the thread's current mapped repair commit (`none` for unmapped threads).
- A marker reply counts only when its comment author equals the `gh` viewer.
- A marker reply is **settled** when no comment by any other author (human or bot) follows it in the thread (`createdAt` order). A later comment unsettles it: someone responded, so the thread needs re-triage.
- Key: a mapped thread's current repair is its newest trailer commit `C` (key `commit=C`); an unmapped thread's key is `head=<current head>` with `commit=none`.
- Every reply-observed check in this workflow (skip before posting, recovery after an uncertain response, precondition for resolve) requires a **settled viewer marker reply for the thread's current key**. An unsettled marker never counts as a posted reply.

### Phase routing (D3)

Step 0 runs before any mutation and replaces the user-selected mode:

1. Bind the Change and open PR (existing Step 1 checks), read `show_finalization_context`, the viewer, the unresolved bound-PR threads with all comment pages, and the trailer map.
2. Classify each unresolved mapped thread with current repair `C`:
   - **awaiting**: no viewer marker reply with `commit=C`, or a settled one (reply or resolve still owed for `C`);
   - **reopened**: every viewer marker reply with `commit=C` is unsettled.
3. Derive the phase:

   | Delivery state | Map condition | Phase |
   | --- | --- | --- |
   | `publication_phase == review-repair` | any | `start` re-entry |
   | `finalization_id` present, no review-repair invalidation, `finalized_head == change_head` (map read at `finalized_head`) | at least one awaiting thread | `resume` |
   | same | otherwise | `start` first entry |
   | any other | any | stop: `authority-gap: change-not-finalized` |

4. A supplied `mode` must equal the derived phase; a mismatch or any other value is refused before any mutation, naming `/address-pr-feedback <change-id>`.
5. Finalized publication fence (both `resume` and `start` first entry): call `reconcile_change_checkpoint`, then require the PR head to equal `finalized_head`. A result with `reconciled: false` and an error, or a remaining head mismatch, stops without any reply, preparation, or edit, reports the exact error, and names `/address-pr-feedback <change-id>`.

Consequences:
- After `/finalize-change`, the default command enters `resume` (G7 closed): the repaired threads are unresolved and have no marker for their new commit.
- A checkpoint-pending finalized Change is published by step 5 before any thread action, whichever phase is derived.
- A thread repaired again in a later round has a newer `C`; its older-round marker carries the older commit and does not block `resume`.
- A reopened thread does not select `resume`; `start` re-triages it. A new fix adds a newer trailer commit; a non-fix classification posts a new reply whose settled marker then satisfies the key.
- A finalized Change with only reopened or unmapped unresolved threads enters `start`; COM-005 covers its no-fix reply path.
- `resume` with unmapped unresolved threads re-evaluates them (step 4 of `resume`); any judged `fix` stays unresolved with `/address-pr-feedback <change-id>`, which derives `start` once no awaiting thread remains.
- Cockpit card, PR summary, and engine stay unchanged; their existing command is now correct in every phase.

### Thread-to-commit map (D1)

- Each repair commit message ends with a trailer paragraph: one `Review-Thread: <thread node ID>` line per thread it addresses (primary plus demonstrated duplicates), passed in the `commit-owned -m` message.
- Read-back, documented once in the skill and executed by the test:
  `git -C <worktree> log --format='%H%x09%(trailers:key=Review-Thread,valueonly,separator=%x2C)' <head>`
  where `<head>` is the managed worktree `HEAD` in `start` re-entry and `finalized_head` on a finalized Change. No target-ref range; the agent keeps only thread IDs in the bound PR's thread list. A thread mapped to more than one commit uses the newest (`git log` order) as `C` and reports the others.
- Every mapped commit is an ancestor of `<head>` by construction. If out-of-band recovery removed a repair commit, its thread is unmapped and `resume` fails closed for it.

### `start` entry and re-entry

- First entry: derived when the Change is finalized (`finalization_id` present, no invalidation, `finalized_head == change_head`) and no awaiting thread exists; passes the finalized publication fence first.
- Re-entry: `publication_phase` is `review-repair`. Call `prepare_review_repair` first; its replay re-validates the same open, unmerged PR at the invalidation's expected head and re-drafts if needed. Any refusal stops with the exact authority gap. Then require a clean managed worktree whose `HEAD` descends from `reviewed_change_head`.
- Step 2 reads the map before triage; already-mapped unresolved threads that are not reopened keep `fix` with their commit and are not re-triaged or re-repaired. Reopened threads are triaged.
- Routing after triage:
  - Any new `fix`: `prepare_review_repair` (first entry) or already prepared (re-entry), one repair commit per thread, hand off to `/finalize-change`.
  - No new `fix` in the `review-repair` phase (mapped repairs pending finalization): hand off to `/finalize-change` (no reply).
  - No new `fix` on a still-finalized Change past the publication fence: run the reply procedure directly for the triaged threads (COM-005).

### Finalization gate (D2)

- `w-change-finalization` Step 0: a user-invoked attempt also proceeds in `review-repair` when the context reports `ready_for_finalization`. Engine readiness is unchanged and still blocks the unrepaired head. No other finalization step changes.

### `resume` order

1. Phase routing has already required `finalization_id` present, no review-repair invalidation, and `finalized_head == change_head`.
2. Finalized publication fence: `reconcile_change_checkpoint`; then require PR head equals `finalized_head`.
3. Read the map at `finalized_head`.
4. Re-evaluate unmapped and reopened unresolved threads; any judged `fix` stays unresolved, unreplied, `next_command: /address-pr-feedback <change-id>`.
5. Reply procedure for awaiting threads and re-evaluated non-fix threads.

### Reply procedure (shared by `resume` and no-fix `start`)

- Viewer: `gh api graphql -f query='{ viewer { login } }'`, once per run (also used by phase routing).
- Body passed as a GraphQL variable with the marker appended.
- Marker read: per-thread paginated query (`node(id:$threadId) { ... on PullRequestReviewThread { comments(first:100, after:$endCursor) { nodes { body createdAt author { login } } pageInfo { hasNextPage endCursor } } } }` with `--paginate --slurp`).
- Before posting: a settled viewer marker reply for the current key -> already posted; skip to resolve.
- Post: parsed response with `comment.id` -> posted. Anything else is uncertain: re-read; a settled viewer marker reply for the current key -> posted; otherwise leave the thread unresolved, do not resolve, report `reply-uncertain` with the exact provider output, no automatic retry in this run.
- Resolve only after a settled viewer marker reply for the current key is observed; verify `isResolved: true`; failure leaves the thread unresolved with the exact error.

### Prompt

- `${input:mode:...}` becomes optional with the description "omit to derive; start or resume only to assert"; the body points to Step 0 routing and no longer states that omitted mode means `start`.

### Output template

Add top-level `phase: start | resume` (derived). Per thread add `mapped_commit_source: trailer | new | none`, `reopened: true | false`, and `reply_state: posted | already-posted | uncertain | failed | not-attempted`. `next_command` values are `/finalize-change <change-id>`, `/address-pr-feedback <change-id>`, or `none`.

## Alternatives And Tradeoffs

- D1 A (rejected): engine-owned record with Y1-Y4 settlement; previously cut as not small.
- D1 C (rejected 2026-10-06 and again 2026-10-07): local handoff file. It is a second copy of facts the commits and comments already hold, must be validated against them anyway, adds malformed/stale/missing-ledger routes, and only saves re-triage of non-fix threads, whose disagreement fails safe (unresolved, no reply).
- D2 B (rejected): separate issue for the finalization gate; would leave this Change's main journey blocked.
- D3 explicit mode plus engine cue (rejected): card and summary changes with golden fixtures, and the user can still choose wrongly. D3 no change (rejected): leaves G7.
- Reopen detection alternatives: head-keyed marker (rejected, challenger round 3: cannot separate a failed resolve from a reopen at an unchanged head, and blocks resume after a new repair); GitHub unresolve history (no thread-level unresolve event is read today; adds a second query surface).
- Publication fence only in `resume` (rejected, challenger round 4): a checkpoint-pending Change without awaiting threads derives `start` and would meet a lagging PR head.
- B weaknesses: agent-executed custody; no protection against concurrent runs; a provider-delayed post can still duplicate once; edited or deleted replies defeat the marker; proof is text contracts plus one executable command check.
- D3 weaknesses: routing is agent-executed from text rules; a reviewer who unresolves a thread without commenting leaves a settled reply, so the next run resolves it again; a bot comment after a reply unsettles it and forces re-triage of that thread.

## Proof Approach

- Text-contract assertions in `tests/test_agent_ecosystem_validation.py` (existing normalized-text pattern) for AC-001, AC-003 to AC-008, AC-010 to AC-013.
- AC-002 executable: extract the fenced read-back command from the skill verbatim, substitute `<worktree>` and `<head>`, run it in a `tmp_path` repository with commits whose multi-paragraph messages carry two trailers, one trailer, none, and one unrelated thread ID; filter to a synthetic PR thread set; assert the exact map.
- Baseline: local Git 2.56.0 accepts the format and returns trailer values (read-only check on this repository).
- Inner loop: `uv run pytest tests/test_agent_ecosystem_validation.py -q -n0 -k "pr_feedback or finalization"`; then the file; `uv run ruff check tests/test_agent_ecosystem_validation.py`.
- No live GitHub mutation in tests.

## Known Limits

- No end-to-end or executable proof of reply dedupe, resolution, or phase routing against GitHub; routing counterexamples (reopen at unchanged head, re-repair in a later round, checkpoint pending, unsettled marker after an uncertain response) are covered by text contract only.
- One duplicate reply remains possible when GitHub applies an uncertain post after the marker-negative read; GitHub offers no idempotency key.
- Edited or deleted prior replies defeat the marker read (N05 G7), including reopen detection.
- A thread unresolved by a reviewer without a new comment is resolved again by the next run.
- Non-fix rationale may differ between `start` and `resume`.
- Out-of-band head recovery removes repair commits from the branch; affected threads fail closed.
