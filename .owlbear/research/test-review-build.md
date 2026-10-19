# Test review build (C-26: TD-3, TD-112, TD-311, TD-339, TD-370..373, TD-390)

Revision 3, 2026-10-19: Sol's second challenge (REVISE, 95%) taken: the fixed brief and plan written out, a TESTS
step kind instead of a REVIEW mode, the ordinary retry budget for shares, a curation result with nothing applied,
and its end without a PR.

Revision 2: Sol's challenge of revision 1 (REVISE, 95%) taken: one Change instead of a Change per
reviewer, a pinned commit, a curator role route with an unchanged-suite end, rewrite-lower report-only, discovery
at the pinned commit, cost shown before the start. The owner decided the admission (TD-390). Sol placed the button
in the existing "Review Tests" row of each project's Maintenance page (TD-370).

Status: built (#499, 2026-10-19). Order and gaps of the remaining work: [the plan](owlbear-plan.md).

## 1. Decisions in force

From [the decision record](delivery-liveness-first-rebuild.md), topic C-26:

- Only the owner starts a test review, for each registered project from its own Maintenance page [TD-370, TD-371].
- Reviewers split the test files and only report; the curator checks their retire and merge verdicts against the
  code, applies what holds in a reviewed Change the owner can still stop, then measures again [TD-311, TD-339, TD-372].
- A test review's brief and one-task plan are fixed; the owner's Start in its dialog approves both, so no brief
  challenge or planner runs [TD-390].
- Reviewers run in parallel as Delivery steps of their own, each with its role's values, credits and retry; the
  curator step then checks their verdicts [TD-373].
- Reviewers default to Sol, medium effort, default context; the curator to Opus 5.5, high effort, long context; both
  are roles in Settings [TD-339].
- Keep, rewrite lower, merge or retire; doubt keeps. A removal names the behaviour, a plausible bug and the test that
  still catches it; security guards, incident regressions and public contracts stay [TD-112, TD-339].
- The reviewers' speed-up rewrites are not done in this pass [TD-312].

## 2. Shape: one Change, a review step of parallel shares, then the curator

One Change carries the whole review, so Changes page, spend, pause, abandon, PR and merge stay as they are.

- **Record:** `Change.tests: TestReview | None`: the pinned commit, the shares (paths, verdicts, each session's end),
  and the curator's report (applied and refused verdicts, the measurements, or nothing applied). Change format bump.
- **Start:** the owner's Start creates the Change in one write, as approval, an ended brief challenge and plan
  acceptance would leave it (TD-390): brief version 1 approved, `approved_version == version == challenged == 1`,
  its approved snapshot and `approved_at`, the plan accepted with t1 covering every criterion; the worktree made at
  the target's HEAD, whose commit is pinned; its step is TESTS.
- **The fixed brief:** title "Review the tests"; outcome "Tests that protect no behaviour beyond another test are
  retired or merged; every other test stays"; scope the chosen folders' test files; criteria: AC-1 "Every retired or
  merged test names the behaviour it protected, a plausible bug and the remaining test that still catches it"; AC-2
  "Security guards, incident regressions and public-contract tests stay"; AC-3 "A test in doubt stays"; AC-4 "The
  suite is measured before and after with the same command and scope, and no test that passed before fails".
- **The fixed plan:** t1 "Curate the tests", its scope the brief's, its detail the rules; no checks of its own: the
  curator's before and after measurement is its evidence, CI the PR's gate.
- **The TESTS step:** a step kind of its own before BUILD (never a REVIEW, so no review or final-loop bookkeeping
  applies). One runner runs every unfinished share's `test-reviewer` session, read-only, in the Change's read-only
  copy of its worktree at the pinned commit, together in waves of its session grant (TD-336: the step asks for the
  project's limit). A submitted review ends its share. If shares remain unfinished, the step's result is the
  ordinary failure of the first unfinished one (its cause kind: environment waits, defects retry, both under the
  Change's ordinary budget, never re-planned); the next runner reruns only unfinished shares. A share's report of a
  wrong premise or a missing tool is that share's retry, never a way back to PLAN or a re-plan option. When the budget
  is spent the owner is asked, with an extra option "Go on without the unfinished shares", which records them "not
  reviewed". An unread usage gates as any judge's (TD-54); a session not confirmed gone stops the Change and no
  further wave starts; a worktree HEAD other than the pinned commit stops it. With every share ended it goes to
  BUILD t1.
- **The curator:** the curation task t1 runs the `test-curator` role; a repair, CI fix or pull-request reply after
  it is an ordinary build, so its report stays t1's (Sol's build review). It checks each retire and merge
  verdict against the code, applies what holds, keeps what does not, measures the suite before and after with
  identical commands and scope, restores a removal that breaks collection, a fixture or a maintained reference, and
  reports. With changes, ordinary build validation holds (commits on the task base, a clean worktree); then the task
  review against AC-1..AC-4, the final review, PR with the decision table and both measurements, CI, merge and
  cleanup. With nothing applied, its result is accepted only on a HEAD still at the pinned commit (no earlier
  curation commit) and a clean worktree, and the Change goes to CLEANUP without PUBLISH or MERGE: shown "Done · no
  test changed", archived as "unchanged". A repair that applies nothing after a changing build goes on to review.

## 3. Reviewers and curator

- **Shares:** the tracked files at the pinned commit (`git ls-tree`) matching test names (`test_*.py`, `*_test.py`,
  `conftest.py`, `*.test.*` and `*.spec.*` for js/ts, files under `tests/`, `__tests__/`, `e2e/`) in the folders the
  owner chose; whole files, first-fit by folder then size into shares of about 5,000 lines, deterministic; a larger
  file is a share of its own. Line counts are a heuristic, not a context guarantee.
- **A reviewer's message:** its share, the other shares' paths (a test that still catches a bug may be elsewhere),
  the rules and the decision questions (what it protects, which bug fails it, where else it is caught, a cheaper
  test). It submits `submit_test_review`: per test the action, the behaviour, and for retire or merge the plausible
  bug and the still-catching test with its assertion; rewrite-lower is recorded as a note for later (TD-312).
- **The curator's message:** every retire and merge verdict with its share, the rules, the pinned commit. Its own
  agent file, not `w-test-curation` (an interactive workflow for the lead outside Delivery's worktrees). It submits
  `submit_test_curation`: applied and refused verdicts with reasons, the before and after measurement (command,
  scope, commit, tests collected, time, failures, pre-existing failures named).

## 4. Start, page and settings

- **Button:** "Review tests" in the "Review Tests" row of the project's Maintenance page. Its dialog lists the
  folders with test files at the target's HEAD with their lines, all chosen; it shows the shares that follow, the
  reviewer and curator roles' model, effort and context, and the project's sessions-at-once limit; "Each share is an
  agent session, then the curator's and the reviews': this uses AI credits". Refused while a test review of this
  project is open; the row links to it.
- **Route:** `POST /maintenance/test-review {folders}`; `GET /maintenance/test-review` lists the folders for the
  dialog.
- **Roles:** `test-reviewer` (gpt-6.1-sol, medium, default context) and `test-curator` (claude-opus-5.5, high, long
  context), their minutes the reviewer's and the builder's defaults; in Settings' role tables; a config format bump.
- **Changes page:** the TESTS step shows "reviewing tests · 3 of 5 shares done"; the card's credits are the Change's.

## 5. Proof

- Shares: whole files, folders, the owner's choice, determinism, an empty choice refused.
- Start: one Change with the approved fixed brief and plan (`brief_ready` holds), the pinned commit, step TESTS; a
  second start refused while one is open.
- TESTS step: shares in waves of the grant; a submitted review ends its share; a failed session reruns only
  unfinished shares under the ordinary budget, never re-planned; the owner's "go on" records "not reviewed"; an
  unconfirmed end stops; a moved HEAD stops; usage per share label.
- A verdict to retire or merge without bug and still-catching test is refused by the tool's schema.
- Curator: the curation task uses its role and a repair does not; its message holds every retire and merge verdict;
  nothing applied at the pinned commit goes to CLEANUP and shows and archives "unchanged", while a repair applying
  nothing after a changing build goes on to review; its report is recorded and the PR text holds the table and
  measurements, within GitHub's size limit.
- A share's wrong premise or missing tool retries it and never enters PLAN.
- Roles in Settings; the Maintenance dialog, its cost lines and its refusal (page test).

## 6. Accepted limits

- Delivery has no test command of its own for a project: the curator measures with the project's.
- A reviewer reads code and tests; it does not run them.
- In the VS Code window runtime the shares run one at a time.

## 7. Build steps

| Step | Content |
| --- | --- |
| A | Roles `test-reviewer` and `test-curator`: settings, migration, agent files, tools and their schemas |
| B | `TestReview` record and start: shares, routes, the fixed brief and plan, the Maintenance dialog |
| C | The TESTS step: shares in waves, per-share results, its failures under the ordinary budget, the status line |
| D | The curator: role route, message, report, the unchanged end, PR text |

## 8. Where a new step kind goes (Sol's checklist)

`models.py` (StepKind, Change format, Role); `status.py` (`QUIET`, `_WORK`, share progress, the unchanged end);
`progress.py` (`STAGES`, `_STAGE`); `loop.py` (`EXITS`, TESTS DONE to BUILD t1, the unchanged BUILD DONE to CLEANUP);
`runner.py` (its own dispatch, read-only); `session_slots.py` (`wanted` returns `ALL`, never `NO_AGENT`); `roles.py`
(defaults, `MINUTES`, `SESSIONS`, the curator for BUILD); `sdk_adapter.py` (`ROLES`); `step_input.py` (both messages
and submit schemas); `session_result.py` (payloads, the cause, no route to PLAN); `budgets.py` (no `_alternative`,
the "go on" option); `changes.html` (share display).
