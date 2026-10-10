# Delivery Next: End-to-End Journey and Failure Modes

> **Owning task:** none — design input D1/D2 for milestone M3 of the
> [liveness-first rebuild](delivery-liveness-first-rebuild.md#37-roadmap-milestones-documents-and-products)
> **Date:** 2026-10-10
> **Question:** What does one Change look like end to end for a developer using OwlBear on their own
> GitHub project, and which failure modes must the design handle — ordinary ones first — so that
> problems found in real use need fixes, not rework?
> **Status:** Draft, revised after independent round-2 and round-3 challenges (user experience, failure
> modes, consumer fit, overall route and cross-document coherence; 2026-10-10). Everything here is
> `autonomous` until the user approves the M3 design; the user directions it follows are TD-2 and TD-3
> in the [rebuild research](delivery-liveness-first-rebuild.md#38-decisions-reserved-for-the-user).

## 1. Context and Question

Delivery has never run a Change on a consumer project as intended. It saw one short consumer use
about six months ago, in a form not comparable to today, and has since been used only on OwlBear
itself, in parts (user, 2026-10-10). Its designs caught obscure integrity failures and missed
ordinary ones: product hooks in engine commits, missing dependencies in new worktrees, limits the
author was never told, a moved target, a closed session.

The user's direction: the plan must be watertight on end-to-end user experience and on failure
modes, so that real use leads to fixes rather than another rework. Proof comes from walking the
design and from real use, not from test volume.

## 2. Sources Studied

| ID | Source | Relevant fact | Limits |
| --- | --- | --- | --- |
| C01 | [Consumer README](../../README-consumer.md) | Today's promise: `/ideate`, `/design`, `/continue-change`; Cockpit; human merge; requires Python 3.14, uv, GitHub CLI, a GitHub `origin`, VS Code with Copilot; macOS or Linux | Describes the current product, never exercised on a consumer project since its redesigns |
| C02 | [Setup guide](../../setup/setup-guide.md) | Setup, verification and troubleshooting steps for a consumer project | Same |
| C03 | [Redesign programme §1.1](change-continuation-delivery-redesign.md#11-requirements-from-the-user) U1–U8 | Recorded user requirements: every action reachable from a control or a complete prompt; the user never runs tests, edits worktree files, repairs JSON or operates Git custody; agents prepare checks; resume from persisted evidence; every failure has a handler and a bounded path; repeated evidence needs an invalidated claim; approval is not certification; three model tiers | Requirements text |
| C04 | [Rebuild research §3.3](delivery-liveness-first-rebuild.md#33-the-2026-10-09-session-as-a-microcosm) | Six failures in one session, all ordinary | One day |
| C05 | [Agent harnesses](https://code.visualstudio.com/docs/agents/run/agent-harnesses), [Agent Host](https://code.visualstudio.com/docs/agents/concepts/agent-host) | Copilot-harness sessions survive window close; per-session worktrees do not carry installed dependencies | Product documentation; behavior unprobed (R8) |
| C06 | Open Changes the user keeps running on the old engine (TD-2) | Further failure modes will surface there and become catalogue rows | Ongoing |

## 3. Analysis

### 3.1 Who uses it, on what

One developer with VS Code, a Copilot seat (possibly enterprise-managed) and their own GitHub
repository, often on a corporate laptop with a proxy and single sign-on. The repository can use any
language and toolchain, and may have CI or none, branch protection with required checks or reviews,
pre-commit hooks, signed commits, a merge queue, a non-`main` default branch, a monorepo layout,
private package registries or a GitHub Enterprise host.

Delivery must not assume OwlBear's own toolchain (uv, pytest, npm). Unknown repository properties
are detected at setup and confirmed once by the user as a **project profile**, never assumed. Today's
setup recognizes only `github.com` remotes and defaults non-interactive targets to `main`; Builder
and Planner skills prescribe `uv lock`, and the seeded test resolver falls back to pytest. None of
that carries over.

Teammates who do not use OwlBear share the repository. Setup is user-local by default; anything
written into tracked files requires the user's consent, and Delivery state lives outside the checkout
(DR11, DR14).

### 3.2 The journey

| Stage | The user does | The user sees | The system does |
| --- | --- | --- | --- |
| J0 Set up (once per project) | Runs setup; confirms the detected project profile | Host and repository, base and push repositories, default and target branch, install and check commands per package, CI and required checks, protections, signing, hooks, merge method; what is supported, human-assisted or unsupported; where the status view is | Detects the profile; checks GitHub CLI, Copilot and git identity; registers tool servers |
| J1 Start or return | Opens VS Code; says what they want or picks a waiting Change | Changes waiting for them first, with what happened since; nothing else, or one concrete fix for a broken prerequisite | Readiness check: authentication, servers, state, OwlBear version |
| J2 Shape | Answers questions one at a time; approves the brief | Brief: outcome, acceptance criteria, scope and non-goals, person-only checks, a split proposal if it is too big | Designer works from repository evidence; independent reviewer challenges the brief |
| J3 Plan | Nothing (can look) | Ordered task list with the checks each task must pass | Planner; independent challenge; overlap check against other open Changes |
| J4 Build | Nothing | "Building task 2 of 5: …" | Per task: prepare the workspace, implement, run project checks, commit, independent review, fix loop |
| J5 Stay current | Nothing | "Updating with `main`" | Integrates the moved target; conflicts are resolved as a task with checks and review |
| J6 Publish | Nothing | Pull-request link, "waiting for CI" | Pushes, opens or updates the PR, follows CI, fixes failures and review comments as tasks |
| J7 Person-only checks | Performs each declared check and answers pass or fail | Exact steps and what to look for | Prepares the environment; keeps the answer valid until its inputs change |
| J8 Merge | Reviews the PR and approves merging that exact source head, or merges in GitHub | "Ready to merge": diff summary, proof, required checks | Merges when green with the profile's merge method; follows a merge queue. A changed source head voids the approval and shows a short delta for renewed consent |
| J9 Done | Nothing | Summary and merged PR | Removes branch and workspace after a preservation check; records history |

**Touchpoint budget.** Per project: run setup and confirm the profile. Per Change: approve the brief,
answer genuine questions (each one plain question), perform the person-only checks declared in the
brief, review the PR and approve the merge. Announced prerequisite actions are allowed exceptions
(U3): sign in again, approve a permission, unlock a signer, set a credential outside chat — each with
the exact action and the condition under which work resumes. Anything else the user must do —
re-run a command after answering, choose an internal operation, repair state, notice an unannounced
tool-approval prompt — is a design defect.

**Surfaces.** Conversation and questions happen in chat. One status view lists every Change with its
stage, situation and next actor; whether that is Cockpit or the platform's Agents window plus the
pull request is open (Q9 in the rebuild research). The status shows observed activity and when it
was observed, and says "not running" when no executor is active, so "Building 2/5" never implies work
that is not happening. Answering a question resumes the work without re-issuing a command; if R8
shows the runtime cannot do that, the fallback is one generic "continue" action, disclosed at J0,
never a choice between recovery prompts.

### 3.3 One exit contract for every step

Every step — design, plan, task, integrate, publish, check, merge — ends in exactly one exit:

| Exit | Meaning | The user sees |
| --- | --- | --- |
| done | The step's postcondition is verified in its owning store: git or GitHub for code, PRs and merges; Delivery state for approvals and answers | Progress |
| retry | Transient, or fixable by the agent; bounded count with the reason recorded | "Retrying: checks failed (2 of 3)" |
| ask | Needs information or a decision only the user has; one question whose every option leads to a defined step | The question, in chat and in the status view |
| back | The step showed an earlier stage was wrong: task infeasible → plan; scope wrong → brief | "Re-planning: the API the task relies on does not exist" |
| stop | Cannot continue safely, or retries are exhausted; work preserved; one action that resumes | The reason and that one action |

A step that is waiting on an external condition — CI, a reviewer, a merge queue, the user's
person-only check — is **pending**, not exited. Pending records the condition, who acts, and who
observes it next and when; it consumes no retry budget. A wait that cannot progress (a required check
that never starts) becomes `ask` or `stop`.

Rules:

- Every retry budget ends in `ask` or `stop`, never in a silent loop. Budgets carry across `retry` and
  `back` for the same cause until its premise changes. Answering a request clears it only once its
  effect is observed.
- A `stop` names one action, who performs it, and the condition under which work resumes. The action
  works even when Delivery's own tool server is down. "Diagnose" and raw error output are not actions.
- No exit discards work. Preservation inventories staged, unstaged, untracked and conflicted files and
  local commits missing from the published head; it saves them privately, outside publishable
  branches, and leaves the workspace untouched when capture cannot be verified. Secrets are never
  republished.
- A worker or command is replaced only after its termination is confirmed. If liveness is unknown,
  the exit is `stop`, naming the session and how to end it. Heartbeat expiry starts that check; it
  never authorizes replacement.
- On re-entry a step first checks the world — does the commit, push, PR or merge already exist? —
  then acts. It replays only on confirmed absence; a failed observation is not absence.
- State records intent, decisions, answers and the current step. It does not mirror facts git or
  GitHub already hold.
- The status line is derived only from stage, step, exit or pending condition and observed activity,
  for example "Build 2/5 · waiting for you: which environment variable holds the test API key?".

**Fixability.** A fix is local when it keeps four contracts intact: the approved interaction
(touchpoints and exits), ownership (who owns state, sessions, workspaces, PRs and merges),
preservation and replay, and evidence validity. It may add detections, rows and wording. A failure
that requires changing one of those contracts sends that area back to M3, whatever exit it maps to.

### 3.4 Failure catalogue

Likelihood is a judgment, since no consumer usage exists: **C** common (expect in most Changes or
most projects), **O** occasional, **R** rare. Rows are ordered by likelihood within each stage.

**Setup and session**

| ID | Failure | L | Detection | Exit and handling |
| --- | --- | --- | --- | --- |
| S1 | GitHub CLI missing, signed out, token expired or not SSO-authorized for the organization | C | Readiness check calls the repository API | ask: the exact command to run; resume afterwards |
| S2 | Tool servers fail to start (dependency install, proxy, wrong Python) | C | Server health at session start | stop: the user runs setup's repair, which works without Delivery running; resumes on the next start |
| S3 | Project install or check commands unknown or wrong, or run in the wrong package directory | C | Profile confirmation; first task check fails for environment reasons | ask once at setup; later back to the profile with the failing output |
| S4 | Copilot signed out, no seat, or agents, MCP or models disabled by enterprise policy | O | Readiness check or runtime error | stop: what is blocked and what an administrator must allow |
| S5 | Corporate proxy or TLS interception breaks installs | O | Install error pattern | stop: proxy settings to check |
| S6 | OwlBear updated while Changes are open and the state format changed | O | State records its format version | Migrate automatically; if impossible, stop with "finish on the old version or migrate" |
| S7 | Wrong folder opened, or a project without setup | O | No project profile at the workspace root | ask: run setup here, or open the configured project |
| S8 | Network offline | O | git, GitHub or model calls fail | retry with backoff; then stop "offline", resuming on the next start |
| S9 | Copilot rate limit or exhausted quota | O | Runtime error | retry for rate limits; stop for quota, never marking the task failed |

**Shape and plan**

| ID | Failure | L | Detection | Exit and handling |
| --- | --- | --- | --- | --- |
| D1 | Idea too large for one Change | C | Designer sizing rule | ask: accept the proposed split |
| D2 | Ambiguous or conflicting requirement | C | Designer | ask, one question at a time |
| D3 | Acceptance criterion cannot be checked | C | Reviewer | Designer rewrites it as checkable or as a person-only check, visible in the brief |
| D4 | Task too large to finish in one agent session | C | Planner size rule; build exhaustion | back to plan to split the task |
| D5 | Brief or plan cites wrong repository facts | O | Reviewer verifies cited evidence | retry with the reviewer's findings |
| D6 | User changes their mind after approval | O | User says so in chat or the status view | Acknowledge at once and launch no new work; let a running step reach a safe point or stop it. If a merge was submitted, observe its outcome first: merged → the Change completes and the new intent starts a new brief; not merged, or no merge submitted → back to J2 showing kept and dropped work, and ask for re-approval. Say plainly what can no longer be undone |
| D7 | Plan overlaps another open Change | O | Overlap check on files and areas | ask: order them or proceed; conflicts are handled in J5 |
| D8 | Plan needs something only the user has (credential, product choice) | O | Planner flags it | ask |
| D9 | Planner and reviewer keep disagreeing | O | Round count (for example two) | ask with both positions summarized |
| D10 | The same cause returns after re-planning or an answered request | O | Carried episode budget; the prerequisite is observed again | ask with a genuine scope decision, or stop with work preserved |

**Build, per task**

| ID | Failure | L | Detection | Exit and handling |
| --- | --- | --- | --- | --- |
| B1 | Project checks fail after implementation | C | Check exit code | retry: the builder fixes (bounded); then ask: revise the requirement, or pause with work preserved |
| B2 | New workspace lacks installed dependencies | C | Workspace preparation step before every task | Run the profile's install command for the task's package; failure is handled as S3 |
| B3 | Pre-commit hook rewrites files or rejects the commit | C | Commit result | retry: stage the hook's fixes and re-run the affected checks, or fix the finding; hooks are project policy and are never bypassed |
| B4 | Agent ends early, claims success without changes, or runs out of context or turns | C | Engine checks diff, check results and the task's checklist | retry in a fresh session with the task and current diff (bounded); then back to plan to split |
| B5 | Agent's result or tool arguments are invalid or over a limit | C | The tool returns a field-specific error to the authoring agent (TD-1 T3/T4) | retry by the same agent in the same session |
| B6 | Command hangs: watch mode, interactive prompt, server start | C | Step timeout | Terminate and confirm termination, then retry with non-interactive flags; if termination cannot be confirmed, stop naming the process |
| B7 | Agent waits on a tool-approval prompt nobody sees | C | Permission request reported by the runtime (R8); heartbeat silence alone cannot identify it | Prevented by scoped pre-approved permissions for unattended steps; otherwise the status says "waiting for you to allow a command in session X" |
| B8 | Flaky check | O | Failure does not reproduce on one rerun | retry once; record the flake; repeated flakes → ask (fix or skip with record) |
| B9 | Task infeasible as planned | O | Builder reports a wrong assumption | back to plan with the reason |
| B10 | Task needs a secret, environment variable or external service | O | Builder reports what is missing | ask: where to set it; secrets are never pasted into chat |
| B11 | Agent edits outside the task's scope or outside its workspace | O | Diff against plan scope; main checkout dirty check | Scope: reviewer finding and retry. Outside the workspace: stop listing the files; the user keeps or reverts them, both preserved |
| B12 | Reviewer keeps rejecting | O | Round count | ask with the disagreement summarized |
| B13 | User edits files in the Change workspace while it runs | O | Unexpected diff at a step boundary | Include the edits and tell the reviewer; if they clash with the agent's edits, ask |
| B14 | Model unavailable or timing out | O | Runtime error | retry with backoff, falling back to another allowed model tier; then stop |
| B15 | A secret is committed | O | GitHub push protection rejects the push, or a local scan | back to build: remove it and rewrite unpublished commits; if it was published, ask the user to rotate it |
| B16 | Disk full or similar resource exhaustion | R | Command errors | stop with the reason |
| B17 | Project checks already fail before the task's edits | O | Profile checks on the starting revision | retry for environment causes; otherwise ask: fix first as a separate task, or pause. "Proceed with the failure recorded" is offered only when the Change's acceptance can be shown independently and the failure blocks no task check or required remote gate; that unchanged failure is then not treated as a new task failure |
| B18 | Commit identity or signer unavailable or locked (GPG, keychain, hardware key) | O | Commit or signing error | ask: the exact unlock or setup action outside chat; signing is never disabled |
| B19 | Workspace or Change branch missing on resume | O | Workspace and ref observation | Recreate from the branch and preserved work; stop if preservation cannot be confirmed |
| B20 | LFS objects or submodules not present in a new workspace | O | Profile flags them; pointer files or empty submodules after preparation | Hydrate during preparation; failure is handled as S3 |

**Integrate with the moving target**

| ID | Failure | L | Detection | Exit and handling |
| --- | --- | --- | --- | --- |
| I1 | Target moved; merge is clean and checks pass | C | Target head changed | done; re-review only if the merge changed reviewed inputs (P5) |
| I2 | Textual conflict | O | Merge result | Task: builder resolves, checks run, reviewer reviews the resolution |
| I3 | Semantic conflict: clean merge, failing checks | O | Checks | As B1 |
| I4 | Someone else pushed to the Change branch | O | Push rejected as non-fast-forward | Integrate those commits as I2 or I3 |
| I5 | Target rewritten, renamed or deleted | R | Ref check | ask: integrate onto the new target, or choose another |
| I6 | A task needs a target commit the Change does not contain yet | O | Builder names the missing commit or API | Integrate during Build, then resume the task |

**Publish and CI**

| ID | Failure | L | Detection | Exit and handling |
| --- | --- | --- | --- | --- |
| P1 | CI fails | C | Check runs and commit statuses on the current head | Task: builder fixes from the CI logs (bounded); then ask |
| P2 | CI is slow | C | Checks pending | pending: "waiting for CI", observed time shown; no user action |
| P3 | Review comments from people or Copilot code review | O (C where review is enabled) | PR review events | Task: address the feedback (bounded); disagreement → ask |
| P4 | Project intentionally has no CI | O | Profile, confirmed at J0 | Local checks are the declared gate, stated in the brief and the PR |
| P5 | Push rejected by authentication or branch rules | O | Push result | Authentication → S1; branch rule → ask, and record it in the profile |
| P6 | PR already exists, was closed, or the remote branch was deleted | O | Query before creating | Reuse an open PR; closed → ask: reopen or abandon |
| P7 | Required human reviewers or code owners | O | Effective branch rules | pending: "waiting for review by …"; that touchpoint happens in GitHub |
| P8 | CI flaky | O | Rerun passes | Rerun once automatically |
| P9 | GitHub API outage or rate limit | O | API errors | retry with backoff; then stop |
| P10 | Expected or required CI missing, not triggered, cancelled, or awaiting workflow approval | O | Checks and statuses on the current head against the CI declared in the profile and the effective rules | pending with bounded observation; then agent repair (for example a workflow trigger) or ask naming the owner's exact action; the gate is never downgraded |

**Person-only checks and merge**

| ID | Failure | L | Detection | Exit and handling |
| --- | --- | --- | --- | --- |
| H1 | User unavailable for days | C | — | pending without timeout; the status names the waiting check |
| H2 | User reports a check failed | O | Answer | back to build with the user's description as task input |
| H3 | Later change affects a passed check | O | A recorded input of the check changed (P5) | ask again, stating what changed; otherwise keep the answer |
| M1 | User merged in GitHub directly | C | PR state | done: cleanup after preservation (M5) |
| M2 | Merge blocked after approval: new target commits, a required check, a conflict | O | Merge result | back to integrate; any change to the source head voids the approval, so ask again with a short delta |
| M3 | Merge queue | O | Queue state | pending; removal from the queue routes its cause (CI → P1, conflict → I2), otherwise stop with the reason |
| M4 | PR closed without merging | O | PR state | ask: abandon or reopen |
| M5 | Cleanup finds uncommitted files, or local commits missing from the merged head | O | Workspace status; compare local commits with the merged head | Preserve privately and report; never delete unpreserved work |

**Cross-cutting**

| ID | Failure | L | Detection | Exit and handling |
| --- | --- | --- | --- | --- |
| X1 | Chat closed, VS Code quit, laptop asleep or rebooted mid-step | C | A step in progress without a live executor | Status says "not running"; re-enter the step by observation when an executor resumes. The user only reopens VS Code, or nothing if the runtime continues in the background |
| X2 | User asks unrelated things in the Change's chat | C | — | Allowed: loop state lives outside the chat |
| X3 | Weeks pass between sessions | C | — | Resume from state plus git and GitHub; a moved target is I1 |
| X4 | A tool server restarts during a write | O | Lost acknowledgement | Read state and effects on reconnect; replay only on confirmed absence; if observation fails, stop until it works |
| X5 | Two chats or windows continue the same Change | O | Per-Change lock | The second sees "already running in …"; takeover only after the first writer's termination is confirmed, otherwise stop naming the other session |
| X6 | User wants to pause, abandon or split a Change | O | Status-view action or chat | Handled as D6 for in-flight work; pause is a stop with resume; abandon closes the PR and keeps the branch; split is back to J2 |
| X7 | Copilot or VS Code update changes agent format, tool approval or model names | O | Readiness check or step error | stop with version information |
| X8 | Agent skips a step or edits state directly | O | Order is enforced in code; agents change state only through their one result tool | Prevented by design (P2) |

**Rare, with generic handling only.** No dedicated machinery: a corrupted or half-written state file
(atomic writes keep the previous version; stop with "restore previous"), a corrupted git repository,
clock skew, hostile repository or web content beyond the platform's own protections. Each ends in
`stop` with work preserved.

### 3.5 Design requirements

| ID | Requirement | Rows |
| --- | --- | --- |
| DR1 | **Project profile** at setup, each entry marked known, unknown or unsupported with its evidence: host and repository root; push and PR-base repositories (forks); default and target branch; per-package install and check commands with directory, runtime and covered scope; credential references; LFS and submodules; CI and required checks; effective branch rules and rulesets (reviews, code owners, linear history, signing); merge methods and queue; hooks. Re-read the effective rules before publishing and merging; re-detect on request | S3, B2, B3, B18, B20, P4, P5, P7, P10, M3 |
| DR2 | **Readiness check** at every start and before publishing; a failure yields one concrete fix | S1, S2, S4, S6, X7 |
| DR3 | **Project-facing work runs inside tasks** with the fix loop: installs, checks, commits with hooks, conflict resolution, CI fixes, review feedback. The engine's own operations never depend on project tooling; its git and GitHub calls map every failure to an exit | B1–B3, I2, I6, P1, P3 |
| DR4 | **One exit contract** (§3.3): five exits, pending situations, bounded retries with recorded reasons; no other step outcome | All |
| DR5 | **Re-entry by observation**: every step checks git and GitHub for its effect before acting and replays only on confirmed absence | X1, X4, P6, M1 |
| DR6 | **Work preservation** by inventory, privately and outside publishable branches; the workspace stays untouched when capture cannot be verified | B11, B19, M5, X1 |
| DR7 | **Durable questions** answerable from chat or the status view; answering resumes work | All `ask` exits |
| DR8 | **One status line** per Change, derived in one place, naming the next actor, observed activity and when it was observed | All |
| DR9 | **Unattended permissions**: unattended steps run with scoped pre-approved permissions, or visibly wait | B7 |
| DR10 | **One writer per Change**: a lock; replacement only after the previous writer's termination is confirmed | B6, X5 |
| DR11 | **State outside the checkout and product branches**, versioned, with a migration path | S6 |
| DR12 | **Small agent tools** per TD-1; the engine enforces step order | B5, X8 |
| DR13 | **Budgets per Change**, carried across `retry` and `back` for the same cause: retries, review rounds, re-plans; model spend policy disclosed before unattended work | S9, D9, D10, B12 |
| DR14 | **Footprint and support statement**: setup is user-local by default and writes tracked files only with consent; J0 states what is supported, human-assisted, unknown or unsupported, and never offers to bypass signing, reviews, push protection or workflow approvals | J0 |
| DR15 | **Merge consent is bound to the reviewed source head**; required remote gates are never downgraded to local checks | M2, P10 |

### 3.6 Proof without test volume

- **Design proof (M3).** Each journey stage and catalogue row is walked through against the
  specification: situation → detection → exit or pending → what the user sees → next step. A row
  without a concrete detection and exit fails the design. Rows are also walked as connected traces,
  because single rows hide loops and ownership gaps:
  - a session disconnects while its worker keeps writing, then a second window continues;
  - the user merges an older PR head while newer local commits exist;
  - a required workflow never triggers for this PR;
  - the same missing prerequisite survives a re-plan and an answered request;
  - the user changes intent during an active task, and again after a merge was submitted;
  - the merge is approved on head A, integration produces head B, then merge is attempted.
- **Practice proof (M4).** One end-to-end run on a sandbox consumer repository with a non-OwlBear
  toolchain in a nested package, CI with a required check, and branch protection. The cheap common
  failures are triggered by hand once: failing check, hook rejection, moved target with a conflict,
  closed chat mid-task, expired GitHub CLI login, CI failure, review comment, PR merged in GitHub.
  Each continues after its prerequisite is restored until the next successful step. One interruption
  leaves unfinished work and an unconfirmed push or PR, and must end without lost work or duplicate
  effects. User touchpoints are counted against the budget.
- **Real use (M5).** The first real consumer project. Problems found there become catalogue rows
  mapped to existing exits.
- **Automated tests (P8).** Only for engine logic whose failure would be silent: exit transitions,
  re-entry by observation, the lock, state migration, exported tool-schema structure (T4). No
  assertions on agent prose wording; agent definitions get structural checks only. The test budget
  is set in the charter.

### 3.7 What changes for the user compared with today

| Today | Next version |
| --- | --- |
| Re-run `/continue-change` after every stop | Answering a question resumes the work |
| Separate recovery prompts: repair, attention, target conflict | Exits inside the loop; at most one generic action per stop |
| Custody, claims, bases and attempts on the card | Stage, situation and next actor |
| Engine-owned merge runs product hooks and fails opaquely | Integration is a task with checks and the fix loop |
| Limits unknown to the authoring agent | Field-specific errors returned to the author |
| Assumes OwlBear's own toolchain | Project profile confirmed at setup |

## 4. Recommendation, Confidence, and Limits

**Recommendation:** use §3.2–3.6 as the first draft of D1 and D2 in M3. The charter (R4) adopts the
touchpoint budget, the exit contract and DR1–DR15 as binding; the remaining M3 documents (status
model, architecture, cutover) are written against this catalogue.

**Confidence:** medium-high that the common rows cover the ordinary failures of agent-driven work on a
GitHub repository; they combine the 2026-10-09 incidents, recurring incident classes from the old
engine's history (N11–N13), the consumer setup documentation, GitHub's documented branch-rule and CI
behavior, and two independent challenge rounds. Low on the likelihood labels, which are judgments to
be corrected by real use.

**Limits:** rows B7, X1 and DR7 depend on runtime capabilities that R8 must establish; worker
termination (DR10) depends on what the chosen runtime can confirm. No consumer project was observed.
The catalogue has not yet been reviewed by the user.
