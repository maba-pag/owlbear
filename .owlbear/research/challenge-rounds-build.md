# Challenge Rounds: Build Design (TD-208..217)

> **Owning task:** TD-213 — TD-208 for the builder's task and final reviews, one shared round module
> **Date:** 2026-10-17
> **Question:** How does the engine implement the owner's challenge-round rule for the builder's reviews?
> **Status 2026-10-20:** steps 1 to 8 built. TD-330 replaced TD-218 and is built: every loop's last round, ended
> early or at the maximum, gets one rejections-only check outside the round count (§3.4).

## 1. Context and Question

The owner corrected the built TD-189 rule (round-2 repeats, round 3+ to the owner) with TD-208..217 in
[the decision record](delivery-liveness-first-rebuild.md). This document is the build design Sol
challenged three times (75% → corrections, 90% for the retry list, 90% for the markers). It covers the
builder's task reviews and the Change's final review in detail; TD-220 and TD-221 add the planner, the pack
updater and the shaper's brief challenge to the same build (§3.9). More rounds for the design judge stay out.

## 2. Sources Studied

| Source | Fact used |
| --- | --- |
| `owlbear-dev-next` `budgets.py` `_round`, `round_key`, `review_round` | Rounds are keyed by task scope and reset on progress; the REVIEW gate after 2 rounds is replaced |
| `disputes.py`, `steps/review.py`, `steps/reconsider.py` | Keys are positions in one repair task; disputes and DISPUTED mode are held per task |
| `moves.py` `open_task`, `resolved`; `loop.py` `_done` | Repairs run before later tasks; a multi-part repair resolves only when all parts are done |
| `evidence.review_valid`, `steps/publish.py` `reviewed` | Publishing and merging require a passing final review bound to the head |
| `config.py` `Agent`, `Layer`, `resolve`; `config_routes._save` | Settings resolve per field (project, global, default); a save validates one layer only |
| `prompts.py` `_fixes`, `_brief`, `disputes.review_lines` | Accepted findings reach later reviewers through repair details and answered questions |
| `web/changes.html` `questionForm`, `tick`, `consequence` | Checkboxes, confirmation popups and native disclosures exist; no task-selection answer exists |

## 3. Design

### 3.1 Records

- `round_records.py`: `RoundFinding` (id `F<n>`, text, raised round, tasks it names, state, worker's reason,
  challenger's judgement, owner's decision and note, the repair that reported it fixed) and `RoundLoop`
  (subject, attempt, completed rounds, owner-granted extra rounds, the pinned policy, the findings, the
  verdict-time decision `last`, the ended reason, the unreviewed repair task ids, history of earlier
  attempts). `Change.loops: dict[str, RoundLoop]`.
- Subject: the root plan task (`origin == "plan"`) for task reviews, `final` for the final review. Visual and
  pre-push repairs are not review subjects. Repairs, renames, progress, failures and owner answers never
  reset or advance a round; only a complete, valid challenger verdict counts one.

### 3.2 Settings (TD-209, TD-211)

- Every role's `Agent` gains `max_rounds`, `max_findings`, `last_round_at`, `ask_owner_at` (`None` inherits;
  defaults 3/10/4/7). The final review resolves its own values (project, then global), else the builder's.
- Validation on the resolved values before saving: `max_rounds ≥ 1`, `1 ≤ max_findings ≤ 20`,
  `0 ≤ last_round_at < ask_owner_at ≤ max_findings`. Zero stays distinct from inheritance.
- The policy is pinned when a loop starts and passed through the session config to result validation.
- The config page shows a "Challenge rounds" group for the builder and the final review only.

### 3.3 One round

- Round 1: the reviewer judges the work and returns at most `max_findings` new findings (more are refused:
  "return the most important first"). Every final-review finding names its plan task(s) (TD-216).
- Round k ≥ 2: the prompt lists only round k−1's rejected findings (ID, finding, the worker's reason) under
  "Rejections to judge"; the reviewer answers each `upheld` (the rejection is not acceptable) or not, with a
  reason, and looks for new findings within the cap. Accepted findings never reach it: repair details,
  answered questions and settled-finding lists are filtered for challenged reviews; CI and PR constraints stay.
- The engine assigns IDs before packing a repair; repair lines carry them (`- F3: place: problem - fix: fix`)
  and `keyed` parses them, so parts keep IDs. The builder rejects by ID.
- A rejection judged not acceptable goes to the owner before the repair (TD-193 as built: Fix it with a
  note, Ask the reviewer to reconsider, Drop it with a note). A reconsideration runs only when the owner picks
  it and never counts as a round (TD-219). DISPUTED mode, the held verdict and the
  reconsideration bind to subject, attempt, round and head instead of a task.

### 3.4 After a verdict

- No new findings and nothing to fix: the review passes as today.
- Otherwise one repair batch (all its parts) carries the new findings and the owner's Fix findings. At
  verdict time the loop records `last = new ≤ last_round_at or round ≥ max_rounds + extra`.
- When every part of the batch is built: not `last` → the next round reviews it. `last` and the round reached
  `max_rounds + extra` with `new ≥ ask_owner_at` → the owner is asked (3.6). Otherwise the batch is done
  unreviewed: its tasks are listed as unreviewed repairs, its rejections stand unjudged, the subject resolves.
- Final review: its repair batch is reviewed by the next final-review round, not by a task review.
- Rejections-only check (TD-330, replacing TD-218): when a loop's last round, ended early by its count or at the
  maximum, leaves rejections no round judged, one short session judges only those on the repaired head, without
  new findings; a rejection it does not accept goes to the owner. It counts outside the rounds: the round number,
  that round's finding count and the head its new work is diffed from stay. When the last allowed round found
  `ask owner at` or more, the owner chooses after the check and its disputes. A check that reports a wrong premise
  instead judges nothing: its rejections stand, marked unjudged, and the premise is repaired like a finding.
  Repairs after one round share its label (`r<round>`), listed once as unreviewed.
- Completion without a pass: an engine-issued completion record binds the policy, the last verdict, the
  complete repair batch, the criteria and the resulting head. `publish.reviewed` and merge accept it for
  identical content under the same criteria only (TD-237); later changes invalidate it like a review.

### 3.5 Re-entry and restart (TD-215, TD-235)

- New work after the final loop ended adds one round to the same loop (beyond `max_rounds` if needed). The
  reviewer gets the diff since the loop's last reviewed head, judges it with what it affects or calls and
  obvious low-hanging issues, without a deep review of unrelated code, and judges the rejections the former
  last round left unjudged. Normal end rules apply. The added work (a CI, PR-comment or check fix, a target
  merge, a visual or pre-push repair) gets no review of its own; work added during a task's loop is
  reviewed by that task's next round.
- Repeated CI ↔ final-review cycles keep no-progress accounting across the chain, so they reach the owner.
- "Restart review loop" (Change page): only for a live, unmerged Change at or after its final review with no
  running step or merge; checked again under the lock; starts a new attempt at round 0, keeps the history,
  retires superseded questions and invalidates merge consent.

### 3.6 The owner's question at the last round

- Task subject: "Another round" (one extra round, then this check again) or "Reject the work and retry it"
  (TD-210: a fresh builder rebuilds the task from its plan entry).
- Final subject (TD-217): the plan's tasks with checkboxes, ticked = rebuild, red-marker tasks pre-ticked;
  the button reads "Rebuild N tasks", or "Accept as done" with none ticked (the review completes, the
  findings stay recorded as accepted by the owner). "Another round" and "Plan again from the brief" (with
  the choice: existing code or a clean state) stay beside it.
- Markers per task, task review and final review separately: one per round with findings, the loop's last
  round bold, coloured by its most urgent finding with a word and count — red open (fix agreed, not
  implemented; rejection the challenger did not accept), yellow unverified (fix reported, not re-reviewed;
  rejection never judged), grey settled (verified; rejection accepted; dropped; withdrawn). PDS semantic
  variants (`error`, `warning`, `secondary`) with icons; no hover-only content. A "Finding details" toggle
  gives per round e.g. "Round 3 (latest): 1 fix reported, not re-reviewed; 1 rejection not reviewed",
  then each finding with its reasons.
- As built (TD-252): a marker reads `R<round> · <count> <kind>`, the count being that round's findings of its most
  urgent kind; a fix counts as verified once a full round ran after its repair reported it (a rejections-only check
  is no full round). Markers show beside each plan task in the Plan section and beside the retry question's
  task list, task review and final review apart; only each loop's current attempt is shown. The "Finding details"
  toggle names each line's loop, since task and final rounds and their IDs are counted apart. A "Review rounds"
  section shows the final review's own markers, the repairs no round reviewed and the rejections that stand (not
  judged, or accepted by the reviewer). The settings page's "Challenge rounds" group has the builder's task reviews
  and the final review, each value with its source (the final review's may come from the builder's).
- Dependency warning: a rebuilt task that a kept task shares changed files with shows "may depend on" beside
  the kept task, above the button and in the confirmation popup; never blocking. After the rebuild the kept
  tasks' checks run again; a failure comes back as a finding.
- The answer carries the task ids, bound to the question, plan version, attempt and head shown; a stale or
  unknown selection is refused (409/422).
- As built (TD-245): five options, Rebuild the ticked tasks, Accept as done, Another round and Plan again from the
  brief on the existing code or from a clean state; the answer binds to the question, the loop attempt and the head
  (the plan version is always 1 today; a re-plan or a restart retires the question). A task starts ticked when a
  final-loop finding naming it, or a finding of its own loop, is open, escalated or decided by the owner to fix. Its
  files are those its reviews covered, its repairs' included. Markers and the details toggle stay in step 5.

### 3.7 Retry mechanics (TD-210, TD-214)

- The rejected head is archived first (`owlbear/archive/<slug>/<subject>/a<attempt>-<head>`, TD-233).
- Forward undo on the same branch and PR, never force: the commits each selected task (and its repairs)
  produced, recorded per attempt, are reverted in reverse commit order on a scratch branch; target merges are
  kept; mixed or ambiguous commits, or a revert conflict, stop with a question. The scratch result is promoted
  only if the Change head still matches. Progress is recorded so a restart resumes.
- Then fresh builder sessions rebuild the selected tasks in plan order (new task-loop attempts), then the
  final loop continues. A retry invalidates the final-review completion, merge consent, CI results and
  affected checks; answered PR requests whose fixes were undone are reconciled, not blindly re-posted.
- As built (TD-245): every build session records its own span `start..end` on its task (the end is the session's
  reported head, else the worktree's when it ends, else the held head when its usage stayed unread), so a task's
  commits are what its sessions made and never what came between them (an owner's commit while it was paused,
  another task's build). A span whose end is unknown stays open, and an open span stops any undo of that task.
  A rebuild undoes the ticked tasks, their task-loop repairs and each final repair whose fixed findings name only
  ticked tasks of the current plan (a finding of no task counts as kept work; history before a re-plan never counts);
  a final repair of both, or a task with an unrecorded span, stops with the owner's question. Undone tasks keep no
  span, so nothing is reverted twice. The head an undo starts from is recorded before anything is promoted: the undo
  is built on it and promoted only by a fast-forward, a restart finds it on the branch instead of repeating it, and a
  branch that moved without it stops it. The last rebuilt task then runs its own and every other plan task's checks,
  each from its task's own package (`cd <package> && <check>`, placed by the planned scope, which no rebuild widens;
  a report from one package never counts for another): its builder must pass them, so a failure is fixed in that
  build and reviewed by its rounds, and CI
  stays the second net (TD-246). The final loop ends `retried` and reopens with one round once the rebuilds are
  done (TD-235). CI results and person checks are bound to heads and content, so they need no separate invalidation;
  fixes of PR requests are kept work and never undone (a revert that conflicts with them stops). A clean plan is one
  commit setting the tree to the target's at the merge base. Planning again starts a new final-loop attempt, the old
  one `replanned` with the old plan's loops in its history; the planner gets the owner's reason and the last round's
  findings. The host and the fold check the whole selection and its binding.

### 3.8 Removed

TD-189's `Dispute.direct`, `repeat_of`, `disputes.earlier/repeats/REPEAT`, `Session.repeats`, `Task.found_in`;
the REVIEW round gate and `StepResult.authorised`; `_progress` resets for review loops. The PLAN gate went with step 6
(§3.10); `Question.repair` stays for reviews outside a loop. Removed fields get an explicit store migration.

### 3.9 The other challenged roles (TD-220, TD-221)

Each adopts the shared round module with its own TD-209 values; each gets its own design challenge before its
step is built.

- Planner (TD-190): plan-challenge findings become stored findings with IDs instead of one quoted text; the
  planner may reject them with reasons in its result; the 2-round PLAN gate goes. Retry means planning again
  from the brief (TD-210).
- Pack updater (TD-194's flow): its rounds, rejections and judgements use the module; an escalated rejection
  needs a place for the owner's question outside a Change (the pack page). Its TD-194 rework stays separate.
- Shaper (TD-221): the brief challenge runs in the shaping chat before the approve button; the shaper revises
  on findings it accepts and may reject others with reasons; the owner approves the challenged draft seeing
  its standing rejections; the challenge after approval (`brief_due`, `_brief_challenge`) goes away.

### 3.10 The planner's rounds (step 6), as built (TD-253)

- Loop: subject `plan`, with the planner's TD-209 values, started by the first plan challenge. The plan's acceptance
  (building starts) ends the attempt, and so does any other move off planning; a later plan starts a new attempt with
  the same values, the old one in its history. An accepted plan moves the replaced plan's task loops into that
  history, so a new plan's `t1` never inherits the old `t1`'s rounds. The final loop's Plan again keeps the plan loop.
- Round: each complete challenger verdict counts one; a failed session counts none. A challenger's wrong premise is
  its round's finding. Round 1 judges the plan with at most `max findings` new findings. Later rounds list the
  planner's rejections under "Rejections to judge" (ID, finding, the planner's reason), judged in `rechecked`, and may
  raise new findings; findings the planner revised for never reach them, and the owner's decisions about plan
  findings are left out of the challenger's brief.
- Revision: the planner gets its previous plan and the findings to answer by ID (the latest verdict's and those the
  owner kept, marked as the owner's with the note) and may reject any but the owner's in `PlanResult.rejected`
  (listed keys only, once each; no commit). Its plan is stored with the revision's marks (fixed as `r<round>`,
  rejected with the reason) and the step's mode `challenge` before its challenge starts: a failed or interrupted
  challenge challenges the same plan again, never plans again. Nothing in the planner's message comes from the
  outcome's text any more; the outcome keeps its typed `challenged` flag (TD-188) for the repair chance (TD-123).
- After a revision, as in the task loop: not the last round → challenged again; the last by count before
  `max rounds + extra` with rejections → a rejections-only challenge (`rejections` mode, no new findings, TD-218); the
  last at the limit with `ask owner at` or more new findings → the owner: "Another round" (one more challenge of the
  revision, no planner session) or "Plan again from the brief" (a new attempt; the planner is told the owner rejected
  the plan and that round's findings, without the old plan). Otherwise the revision is accepted unreviewed: the loop
  ends `count` or `max` and lists it (`r<round>`) as no round reviewed it.
- Escalation: a rejection the challenger upholds goes to the owner before the revision, one question per finding,
  TD-193's options: "Revise the plan for it" or "Drop it" (optional note), or "Ask the challenger to reconsider" (note
  required; a fresh challenger withdraws it, clarifies it for the planner as the owner's, or returns it unsure, asked
  again with the first two options only). Then the planner revises for the verdict's new findings and the owner's (no
  round is counted), or, with none, the plan is accepted (mode `settled`, no session). Plan questions settle only
  while open; an upheld rejection whose question a stop replaced is asked again before any planning; questions of an
  attempt that ended are retired.
- Removed: the 2-round PLAN gate (a plan retry is ungated) and the quoted findings text. An old gate question still
  open works by its own options. `Question.repair` stays for reviews outside a loop.
- Page and settings: the "Review rounds" section shows the plan challenge's markers and details (Planner and
  Challenger named), its unreviewed revision and standing rejections; the "Challenge rounds" group has a planner row.
- Code: `plan_rounds.py` (records, lines, marks, verdicts, questions, answers) and `steps/plan_round.py` (the
  challenge, the rejections-only check and the reconsideration, moved out of `runner.py`).

### 3.11 The shaper's brief challenge (step 8), as built (TD-254, TD-255)

- Loop: subject `brief` on the Change, with the shaper's TD-209 values, pinned at the first request; it stays with the
  Change through planning. Each verdict records the version it judged.
- Request: the chat tool `challenge_brief(change, version, rejected)`; the shaper calls it once the draft is ready
  (TD-249) and for each later round, naming the saved version and its rejections of findings it did not take (the
  owner's are never rejected; listed keys only). The host checks it under the Change's lock (a shaping Change, the
  current version, not challenged already, no challenge running, no owner decision pending) and records it; the open
  findings the shaper did not reject count as revised for in that version (`v<version>`). Asking again for a judged
  version needs every finding rejected, else a revision first. The tool reads the Change until the verdict is
  recorded (ten minutes at most) and returns the findings by ID; `show_status` shows the same under the brief's
  `challenge`.
- Host: the SHAPE step runs the challenger for a requested version; nothing runs after approval any more
  (`brief_due`, `_brief_challenge`, `loop.brief_challenge` removed). Round 1 judges the brief; later rounds judge the
  shaper's rejections and look for new findings within the cap; a challenger's wrong premise or a tool no runtime
  provides is its round's finding. A failed session counts none and runs again. Saves are refused while a
  challenge runs or the owner decides.
- After a request, as in the other loops: not the last round → a challenge; a last round with rejections → a
  rejections-only check (TD-330); then the last allowed round with `ask owner at` or more new findings → the owner on
  the Changes page: "Another round" or "Shape the brief again" (a new attempt; the shaper is told why); otherwise no
  session: the requested version is the loop's outcome, unreviewed (`count`/`max`). A verdict with nothing left to
  address, or the owner's decisions leaving none, makes the judged version the outcome (`clean`). An upheld
  rejection asks the owner first, with TD-193's options; a reconsideration runs in the SHAPE step; an upheld
  rejection whose question a stop replaced is asked again.
- Approval: the approve button (with the reason when it is off) and the approve route require `Brief.challenged ==
  version`, `challenged` now meaning the version its loop ended on; the fold ignores any other approval. A version
  the shaper revised after the last round counts as challenged, but the approve dialog makes the owner tick that he
  accepts that unreviewed revision, and the route refuses it without the tick (TD-255). A later save needs one added round on
  the changes (TD-215, TD-235). The approval view shows the brief challenge's markers and details; after approval
  the "Review rounds" section does.
- A Change the old flow approved before its challenge gets it on its next step and plans once its loop ends there;
  an old question "Plan from this brief as it is" still works by its options.
- Shaper: its agent grants `challenge_brief`; the skill's steps 8-9 say to ask for the challenge, judge each
  finding, revise with the owner where the choice is his, reject with evidence, ask again, and send the owner to
  approve naming the standing rejections and an unreviewed last revision. Settings: the "Challenge rounds" group
  has the shaper's row.
- Code: `brief_rounds.py`, `steps/brief_round.py`, `brief_routes.py` (the request and the approval route);
  `mcp_server.py` gets the tool.

### 3.12 The pack updater's rounds (step 7), as built (TD-256, TD-270)

- Loop: subject `pack`, one attempt per run, with the updater's TD-209 values pinned when the run starts; findings keep
  their IDs for the whole run. The run's context (candidate pins, manifest and notice, evidence, the package files'
  start digests, the checkout, the updater repository's start files, session ids, the next action), its loop and the
  owner's open questions are kept in the job's state file; the candidate's skills and the updater's repository live
  under the store. A run waiting for the owner survives a host restart; a running one still reads failed.
- Round: the challenger judges the whole candidate with at most `max findings` new findings (the session's cap); a
  later round lists the updater's open rejections under "Rejections to judge" and the findings the owner dropped,
  with his reasons (TD-193: raised again only as new findings); fixed findings never reach it. A wrong premise is its
  round's finding. A failed or unconfirmed session ends the run, as before.
- The updater: its first repair resumes the producer, later repairs a fresh updater told the earlier work (TD-123);
  it gets the findings to answer by ID, the owner's marked with his notes, and may reject only the others, checked at
  its result tool. It writes only in its own folder and runs no shell (`Policy.confined`); after each session every
  allowed skill is copied into the candidate, so a skill restored to its start replaces an earlier edit. The replay
  reruns whenever the pack identity changed.
- After a repair, as in the other loops: not the last round → the next round; a last round with rejections → a
  rejections-only check (TD-330), which never reviews the fixes beside them; otherwise the run stops before
  activating and asks the owner on the Settings page: "Activate the unreviewed repair" or "Discard the update"
  (TD-256), with "Another round" first when the last allowed round found `ask owner at` or more (TD-208). A full round
  with nothing left to address and no unreviewed repair activates and pushes as before.
- Disputes: each upheld rejection is one question on the Settings page with TD-193's options (fix with a note,
  reconsider with a required note by a fresh challenger, drop with a note); the run goes on once all are answered.
  "Discard the update" is offered whenever the run waits; a new run is refused while one runs or waits.
- Activation publishes only the candidate the last full round passed or the one the owner was asked about (pack
  identity), and only while the package's manifest, notice and skills are as they were at the start; the commit
  message names the rounds, what was not changed for, and an owner's activation without a pass.
- TD-270: the manifest is written by `json.dumps` in the old key order (its layout changes once, at the first
  update). Upstream's skill text is read at the pinned commit, not the tag.
- Settings: "Design pack updates (updater)" in the "Challenge rounds" group. The pack section lists the run's findings
  and draws the open questions.
- Code: `pack_rounds.py` (the loop's rules, lines and questions), `pack_run.py` (the resumable run), `pack_job.py`
  (the job, its answers and discard), `pack_routes.py` (the answer and discard routes).

## 4. Build Order, Confidence, And Limits

1. Records, settings, stable IDs, migration.
2. Task-review loops end to end (rounds, rejections to judge, owner disputes, termination, unreviewed
   repairs) and a task's retry (archive, forward undo, rebuild; TD-233); removal of TD-189 and the REVIEW
   gate for task loops. Sol reviews.
3. Final-review loop (one loop, task attribution, re-entry, restart button, completion record, publish gate).
4. The final review's retry (the task list, invalidation) and the owner's question with the task list.
5. Change page (markers, details, unreviewed repairs, standing rejections) and the config group. Sol reviews.
6. Planner, 7. pack updater, 8. shaper's brief challenge (§3.9), each after its own design challenge.

Each step keeps the full suite green, mutation-proves its key rules, and respects the 500-line module limit
(`runner.py` is at 500, `prompts.py` at 495, `models.py` at 497: new code goes to new modules).

Limits: the dependency hint is file overlap only (false positives and negatives); counts are effort, not
severity; an unreviewed last repair can carry defects only CI, the owner's checks and PR review can catch.
