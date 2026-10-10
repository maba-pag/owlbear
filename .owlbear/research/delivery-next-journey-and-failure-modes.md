# Delivery Next: End-to-End Journey and Failure Modes

> **Owning task:** none — design input D1/D2 for milestone M3 of the
> [liveness-first rebuild](delivery-liveness-first-rebuild.md#37-roadmap-milestones-documents-and-products)
> **Date:** 2026-10-10
> **Question:** What does one Change look like end to end for a developer using OwlBear on their own
> GitHub project, and which failure modes must the design handle — ordinary ones first — so that
> problems found in real use need fixes, not rework?
> **Status:** Draft, revised after independent round-2 and round-3 challenges (user experience, failure
> modes, consumer fit, overall route and cross-document coherence; 2026-10-10); aligned with the M3
> design (D3–D5), 2026-10-10; revised for decisions TD-10 to TD-22, 2026-10-10; aligned with the M4
> reshape (`adfb5a77c`), 2026-10-10. Everything else here
> is `autonomous` until the user approves the M3 design; the user decisions it follows are TD-2, TD-3
> and TD-10 to TD-22 in the [rebuild research](delivery-liveness-first-rebuild.md#38-decisions-reserved-for-the-user).

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
| C03 | [Redesign programme §1.1](change-continuation-delivery-redesign.md#11-requirements-from-the-user) U1–U8 | Earlier requirements: every action reachable from a control or a complete prompt; the user never runs tests, edits worktree files, repairs JSON or operates Git custody; agents prepare checks; resume from persisted evidence; every failure has a handler and a bounded path; repeated evidence needs an invalidated claim; approval is not certification; three model tiers | Agent-written, labelled "from the user"; input, not user decisions ([rebuild research §3.8](delivery-liveness-first-rebuild.md#38-decisions-reserved-for-the-user)) |
| C04 | [Rebuild research §3.3](delivery-liveness-first-rebuild.md#33-the-2026-10-09-session-as-a-microcosm) | Six failures in one session, all ordinary | One day |
| C05 | [Agent harnesses](https://code.visualstudio.com/docs/agents/run/agent-harnesses), [Agent Host](https://code.visualstudio.com/docs/agents/concepts/agent-host) | Copilot-harness sessions survive window close; per-session worktrees do not carry installed dependencies | Product documentation; SDK-side behavior probed (R8), Agent Host behavior unprobed |
| C06 | Open Changes the user keeps running on the old engine (TD-2) | Further failure modes will surface there and become catalogue rows | Ongoing |

## 3. Analysis

### 3.1 Who uses it, on what

One developer with VS Code, a Copilot seat (possibly enterprise-managed) and their own GitHub
repository, often on a corporate laptop with a proxy and single sign-on. The repository can use any
language and toolchain, and may have CI or none, branch protection with required checks or reviews,
pre-commit hooks, signed commits, a merge queue (unsupported, TD-22), a non-`main` default branch, a monorepo layout,
private package registries or a GitHub Enterprise host.

Delivery must not assume OwlBear's own toolchain (uv, pytest, npm). Unknown repository properties
are detected at setup and confirmed once by the user as a **project profile**, never assumed. Today's
setup recognizes only `github.com` remotes and defaults non-interactive targets to `main`; Builder
and Planner skills prescribe `uv lock`, and the seeded test resolver falls back to pytest. None of
that carries over.

Teammates who do not use OwlBear share the repository. Setup is user-local: it writes
`.vscode/tasks.json` and `.mcp.json` only with the user's consent and only while they are untracked,
and lists both in the clone's `.git/info/exclude`, so nothing is committed; a tracked file is left
alone and setup shows the manual alternative. Skills and agents are installed user-level. Delivery
state lives outside the checkout (DR11, DR14).

### 3.2 The journey

| Stage | The user does | The user sees | The system does |
| --- | --- | --- | --- |
| J0 Set up (once per project) | Runs setup; confirms the detected project profile; consents to the two local files | Host and repository, base and push repositories, default and target branch, install and check commands per package, CI and required checks, protections, signing, hooks, merge method, "ask before merge" (default off); what is supported, human-assisted or unsupported; where the status view is | Detects the profile; checks GitHub CLI, Copilot and git identity; writes `.vscode/tasks.json` and `.mcp.json` where untracked and adds both to `.git/info/exclude`; recommends "require branches to be up to date" and "require conversation resolution" where allowed |
| J1 Start or return | Opens VS Code; presses New Change on the Changes page, or picks a waiting Change | Changes waiting for them first, with what happened since; nothing else, or one concrete fix for a broken prerequisite | Readiness check: authentication, servers, state, OwlBear version; New Change runs `code chat` with the delivery skill's start prompt in the project folder |
| J2 Shape | Answers questions one at a time; approves the brief | Brief: outcome, acceptance criteria, scope and non-goals, person-only checks, for UI changes a render recipe, a split proposal if it is too big | Designer works from repository evidence; independent reviewer challenges the brief |
| J3 Plan | Nothing (can look) | Ordered task list with the checks each task must pass; "overlaps with X" where another open Change touches the same files | Planner; independent challenge; overlap check against other open Changes, shown, never asked |
| J4 Build | Nothing | "Build 2/5" with a "now" line (step plus last tool event), step time, a quiet warning and credits | Per task: prepare the workspace, implement, run project checks, commit, independent review, fix loop |
| J5 Stay current | Nothing | "Updating with `main`" | Integrates the moved target; conflicts are resolved as a task with checks and review |
| J6 Publish | Nothing | Pull-request link, "waiting for CI" | Pushes, opens or updates the PR, follows CI, fixes failures and review feedback as tasks; replies on and resolves each thread it fixed |
| J7 Visual and person-only checks | Performs each declared person-only check and answers pass or fail | Screenshots of the agent visual check on the card; for person-only checks, exact steps and what to look for | For UI changes the host launches the preview from the brief's render recipe, takes screenshots and a reviewer judges them against the criteria; failure → fix task. Prepares the environment for person-only checks; keeps each result valid until its inputs change |
| J8 Merge | Nothing; reviews in GitHub only where GitHub requires a human review | "Merging PR #14 at a1c3f02", or what the merge gate still waits for | Merges automatically when the merge gate passes, under the host's merge lock for the target, after a final re-read, with the profile's merge method and the head as SHA guard, then reads back. "Ask before merge" adds one consent question |
| J9 Pull back and done | Nothing, or presses Pull when the local target was behind | Summary and merged PR; "local main is behind: <reason>" with Pull when pull-back could not run | Pulls the merge back to the local target (pull-back); removes branch and workspace after a preservation check; records history |

**Touchpoint budget.** Per project: run setup, confirm the profile and consent to the two local
files. Per Change: approve the brief, answer genuine questions (each one plain question) and perform
the person-only checks declared in the brief. There is no merge consent: Delivery merges when the
merge gate passes. Human reviews that GitHub requires still happen in GitHub. The profile setting
"ask before merge" (default off) restores one consent question. Announced prerequisite actions are allowed exceptions
(as in earlier requirement U3): sign in again, approve a permission, unlock a signer, set a credential outside chat — each with
the exact action and the condition under which work resumes. Anything else the user must do —
re-run a command after answering, choose an internal operation, repair state, notice an unannounced
tool-approval prompt — is a design defect.

**Surfaces.** Conversation happens in chat: shaping the brief and answering ordinary questions. A
local Delivery host serves a Changes page — its own small app until M6, then inside Cockpit — that
lists every Change with its stage, situation and next actor, starts new Changes (New Change button),
and accepts answers and person-only check results. Each Change card shows a "now" line (step plus
last tool event), step time, a quiet warning when no activity is seen, credits per Change and step,
visual-check screenshots, overlaps and decision origins (`decided` for brief approvals, answers and
owner choices; `autonomous` for agent choices). Recovery decisions are actions only in that page (T6). The status shows
observed activity and when it was observed, and says "not running" when no runner is active, so
"Building 2/5" never implies work that is not happening. The host starts when VS Code opens the
project, through a folder-open task whose permission setup verifies; where that is unavailable, one
Start Delivery action is disclosed at J0, and the status says nothing advances until it runs.
Answering a question resumes the work without re-issuing a command: the host starts the next runner
([charter §3.7](delivery-next-charter.md#37-interaction-surface-and-runner-activation)).

**Merge gate.** Delivery merges only the exact head (SHA guard) that has: a valid final review; every
check observed at that head passed, with declared and required checks started; for UI changes a
passed agent visual check; valid person-only checks; every PR conversation item handled; the target
integrated. A failing check that was not declared becomes a fix task. The declared CI is bound to a
digest of the head's workflow files; unknown check names are asked once per digest, unreadable
workflows wait, and unknown CI never counts as none. Conversation items are issue comments, review
bodies and review threads; an item is Delivery's only by a recorded reply or its own marked comment.
Each other item version is answered by a reply, resolved after a fix, or recorded on the card as "no
action needed: <reason>", for example a bot preview link or a coverage report (interpretation of
TD-15, `autonomous`). The host evaluates the gate, takes one merge lock per target branch, re-reads
the PR and evaluates the gate again ([D3 §3.2](delivery-next-status-and-exits.md)); a target that
is not an ancestor of the PR head sends the Change back to integrate (`autonomous`). It merges with
the profile's method and reads the result back. Setup recommends GitHub's "require branches to be up
to date" and "require conversation resolution" where allowed, and the profile records whether they
are on. Without them, a change between the re-read and the merge is a documented residual risk for
personal use (TD-9): after the merge Delivery watches the target checks, and a failure drafts one
fix Change for the owner's approval.

**Pull-back.** After the merge Delivery fetches and inspects every worktree from `git worktree list`.
If the local target branch is not checked out, or is checked out in a clean working copy (no
untracked files in paths the update touches) that has not diverged, it fast-forwards it with
`git merge --ff-only --no-autostash --no-overwrite-ignore`, never `git pull` with the user's
configuration. Otherwise it never stashes, resets or merges: the card shows "local <target> is
behind: <reason>" with a one-click Pull once pulling becomes possible. Submodules are not updated; if
the update changes a gitlink, the notice says "submodules changed". Hooks and LFS filters run as
with the user's own `git merge`. Unsaved editor buffers are invisible to git; VS Code shows its own
"file changed on disk" dialog.

### 3.3 One exit contract for every step

Every step — design, plan, task, integrate, publish, check, merge — ends in exactly one exit:

| Exit | Meaning | The user sees |
| --- | --- | --- |
| done | The step's postcondition is verified in its owning store: git or GitHub for code, PRs and merges; Delivery state for approvals and answers | Progress |
| retry | Fixable by the agent; identical failures without progress are counted, with the reason recorded | "Retrying: checks failed (2 of 3)" |
| ask | Needs information or a decision only the user has; one question whose every option leads to a defined step | The question, in chat and in the status view |
| back | The step showed an earlier stage was wrong: task infeasible → plan; scope wrong → brief | "Re-planning: the API the task relies on does not exist" |
| stop | Cannot continue safely, or retries are exhausted; work preserved; one action that resumes | The reason and that one action |

A step that is waiting on an external condition — CI, a reviewer, the user's person-only check, an
environment failure — is **pending**, not exited. Pending records the condition, who acts, and who
observes it next and when; it consumes no retry budget. A wait that cannot progress (a required check
that never starts) becomes `ask` or `stop`.

Rules:

- Retry policy (`autonomous`, adopted from the fork): failures are classified by normalised
  signature. Environment faults — network and capacity — are pending with growing pauses (1 to 30
  min) and never consume budget; quota waits only for its reset; an expired sign-in asks the owner to
  run the exact login command, then continue. The card shows the pending age and attempts, goes quiet after 1 hour,
  and asks after 24 hours of the same signature. The same Delivery defect signature — tooling, state
  or an invalid result — three times is asked with the error. Only identical failures without
  progress count (3 per signature). Progress means a strict improvement with no new failure — fewer
  failing checks, more satisfied criteria, a resolved finding — not merely a new commit or changed
  error text; it resets the count. On exhaustion of a check, review, scope, commit-policy or
  conflict cause the step tries one re-plan, then asks one question; never a silent loop. A stronger
  model is not yet an alternative (D4 O11). Counts carry across `retry` and `back` for the same cause until its
  premise changes. Answering a request clears it only once its effect is observed.
- No cost question (TD-21): credits are shown per Change and step, never used to stop or ask.
- A `stop` names one action, who performs it, and the condition under which work resumes. The action
  works even when Delivery's own tool server is down. "Diagnose" and raw error output are not actions.
- No exit discards work. Preservation inventories staged, unstaged, untracked and conflicted files and
  local commits missing from the published head; it saves them privately, outside publishable
  branches, and leaves the workspace untouched when capture cannot be verified. Secrets are never
  republished.
- A worker or command is replaced only after its termination is confirmed. If liveness is unknown,
  the exit is `stop`, naming the session and how to end it. Heartbeat expiry starts that check; it
  never authorizes replacement.
- A step ends at the worker's result event, never at runtime idleness.
- Answers that arrive during active work are kept; the host applies them before the next step.
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
| S1 | GitHub CLI missing, signed out, token expired or not SSO-authorized for the organization | C | Readiness check calls the repository API | pending with growing pauses, showing the exact command as an announced prerequisite action; resumes when readiness passes |
| S2 | Tool servers fail to start (dependency install, proxy, wrong Python) | C | Server health at session start | stop: the user runs setup's repair, which works without Delivery running; resumes on the next start |
| S3 | Project install or check commands unknown or wrong, or run in the wrong package directory | C | Profile confirmation; first task check fails for environment reasons | ask once at setup; later ask with the failing output, whose "correct the command" option writes a new profile version, which resets that cause's retry budget |
| S4 | Copilot signed out, no seat, or agents, MCP or models disabled by enterprise policy | O | Readiness check or runtime error | stop: what is blocked and what an administrator must allow |
| S5 | Corporate proxy or TLS interception breaks installs | O | Install error pattern | stop: proxy settings to check |
| S6 | OwlBear updated while Changes are open and the state format changed | O | State records its format version | Migrate automatically; if impossible, stop with "finish on the old version or migrate" |
| S7 | Wrong folder opened, or a project without setup | O | No project profile at the workspace root | ask: run setup here, or open the configured project |
| S8 | Network offline | O | git, GitHub or model calls fail | pending with growing pauses on the host's network check, resuming by itself when the network returns |
| S9 | Copilot rate limit or exhausted quota | O | Runtime error | pending with growing pauses; exhausted quota names its reset time; never marks the task failed |
| S10 | Python cannot reach GitHub through a TLS-intercepting corporate proxy, while `gh` and Node can (found in M4) | C on corporate laptops | Readiness check | Prevented: OwlBear's own HTTP calls use the system trust store |
| S11 | The Copilot SDK runtime download is blocked by the proxy (found in R8) | C on corporate laptops | Readiness check | Prevented: the SDK runs on the installed Copilot CLI |
| S12 | The `code` command-line launcher is missing, so New Change cannot open chat | O | The host's `code chat` call fails to start | The page shows the exact command to run in the project folder |

**Shape and plan**

| ID | Failure | L | Detection | Exit and handling |
| --- | --- | --- | --- | --- |
| D1 | Idea too large for one Change | C | Designer sizing rule | ask: accept the proposed split |
| D2 | Ambiguous or conflicting requirement | C | Designer | ask, one question at a time |
| D3 | Acceptance criterion cannot be checked | C | Reviewer | Designer rewrites it as checkable or as a person-only check, visible in the brief |
| D4 | Task too large to finish in one agent session | C | Planner size rule; build exhaustion | back to plan to split the task |
| D5 | Brief or plan cites wrong repository facts | O | Reviewer verifies cited evidence | retry with the reviewer's findings |
| D6 | User changes their mind after approval | O | User says so in chat or the status view | Acknowledge at once and launch no new work; let a running step reach a safe point or stop it. If a merge was submitted, observe its outcome first: merged → the Change completes and the new intent starts a new brief; not merged, or no merge submitted → back to J2 showing kept and dropped work, and ask for re-approval. Say plainly what can no longer be undone |
| D7 | Plan overlaps another open Change | O | Overlap check on files and areas; docs, lockfiles and generated files are ignored | Shown as "overlaps with X", never asked; integration handles conflicts (J5); ask only on a behavioural collision: a Builder-resolved conflict, or an integration ending in a question, that touches another open or recently merged Change's scope — keep this behaviour, adopt the other's, or pause (`autonomous`) |
| D8 | Plan needs something only the user has (credential, product choice) | O | Planner flags it | ask |
| D9 | Planner and reviewer keep disagreeing | O | Round count (for example two) | ask with both positions summarized |
| D10 | The same cause returns after re-planning or an answered request | O | Carried episode budget; the prerequisite is observed again | ask with a genuine scope decision, or stop with work preserved |

**Build, per task**

| ID | Failure | L | Detection | Exit and handling |
| --- | --- | --- | --- | --- |
| B1 | Project checks fail after implementation | C | Check exit code | retry: the builder fixes; three identical failures without progress → one different approach, then ask: revise the requirement, or pause with work preserved |
| B2 | New workspace lacks installed dependencies | C | Workspace preparation step before every task | Run the profile's install command for the task's package; failure is handled as S3 |
| B3 | Pre-commit hook rewrites files or rejects the commit | C | Commit result | retry: stage the hook's fixes and re-run the affected checks, or fix the finding; hooks are project policy and are never bypassed |
| B4 | Agent ends early, claims success without changes, or runs out of context or turns | C | Engine checks diff, check results and the task's checklist | retry in a fresh session with the task and current diff (bounded); then back to plan to split |
| B5 | Agent's result or tool arguments are invalid or over a limit | C | The tool returns a field-specific error to the authoring agent (TD-1 T3/T4) | retry by the same agent in the same session |
| B6 | Command hangs: watch mode, interactive prompt, server start | C | Step timeout | Terminate and confirm termination, then retry with non-interactive flags; if termination cannot be confirmed, stop naming the process |
| B7 | Unattended agent needs a command outside its step's allow list | C | The step's permission handler | Denied immediately, never left waiting ([probe](delivery-next-platform-probe.md#32-results) 5); the last denial is recorded and shown in the status; if it blocks the task, the Builder ends with ask |
| B8 | Flaky check | O | Failure does not reproduce on one rerun | retry once; record the flake; repeated flakes → ask (fix or skip with record) |
| B9 | Task infeasible as planned | O | Builder reports a wrong assumption | back to plan with the reason |
| B10 | Task needs a secret, environment variable or external service | O | Builder reports what is missing | ask: where to set it; secrets are never pasted into chat |
| B11 | Agent edits outside the task's scope or outside its workspace | O | Diff against plan scope; main checkout dirty check | Scope: reviewer finding and retry. Outside the workspace: stop listing the files; the user keeps or reverts them, both preserved |
| B12 | Reviewer keeps rejecting | O | Round count | ask with the disagreement summarized |
| B13 | User edits files in the Change workspace while it runs | O | Unexpected diff at a step boundary | Include the edits and tell the reviewer; if they clash with the agent's edits, ask |
| B14 | Model unavailable or timing out | O | Runtime error | pending with growing pauses; ask after 24 hours of the same signature; switching to another allowed model is not built (D4 O11) |
| B15 | A secret is committed | O | GitHub push protection rejects the push, or a local scan | back to build: remove it and rewrite unpublished commits; if it was published, ask the user to rotate it |
| B16 | Disk full or similar resource exhaustion | R | Command errors | stop with the reason |
| B17 | Project checks already fail before the task's edits | O | Profile checks on the starting revision | retry for environment causes; otherwise ask: fix first as a separate task, or pause. "Proceed with the failure recorded" is offered only when the Change's acceptance can be shown independently and the failure blocks no task check or required remote gate; that unchanged failure is then not treated as a new task failure |
| B18 | Commit identity or signer unavailable or locked (GPG, keychain, hardware key) | O | Commit or signing error | ask: the exact unlock or setup action outside chat; signing is never disabled |
| B19 | Workspace or Change branch missing on resume | O | Workspace and ref observation | Recreate from the branch and preserved work; stop if preservation cannot be confirmed |
| B20 | LFS objects or submodules not present in a new workspace | O | Profile flags them; pointer files or empty submodules after preparation | Hydrate during preparation; failure is handled as S3 |
| B21 | A review or fix task sees changes that are not the Change's own, because its diff base is a stale local target (found in M4) | O | Diff base is `origin/<target>` after a fetch | Design rule; a wrong-base deletion is then caught by review and repaired as a task |
| B22 | An agent asks again for something the owner already answered (found in M4) | C | — | Prevented: every agent prompt carries the owner's answers for the Change |
| B23 | The agent visual check fails | O | Reviewer verdict on the screenshots against the criteria | back to build with a fix task naming the screenshot and finding |
| B24 | The visual check cannot run at runtime: the render recipe fails or the browser is missing | O | Preview start from the recipe, readiness or browser start fails | ask with the concrete fix (for example the browser install command or the failing recipe step); the gate is never skipped. A missing recipe is caught in shaping, before approval |

**Integrate with the moving target**

| ID | Failure | L | Detection | Exit and handling |
| --- | --- | --- | --- | --- |
| I1 | Target moved; merge is clean and checks pass | C | Target head changed; integration runs before publish, before merge, and on I4, I6 and M2 | done; re-review only if the merge changed reviewed inputs (P5) |
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
| P3 | Review feedback from people, bots or Copilot code review | O (C where review is enabled) | Every PR conversation item not by Delivery: issue comments, review bodies, review threads | Per item version, by exact ID: a fix task (bounded), after which Delivery replies and resolves the thread; or a reply answering it; or "no action needed: <reason>" on the card. An edited or reopened item is a new version; a fix counts only while its commit is in the PR head. Disagreement → ask the owner with both positions |
| P4 | Project intentionally has no CI | O | Profile, confirmed at J0 | Local checks are the declared gate, stated in the brief and the PR |
| P5 | Push rejected by authentication or branch rules | O | Push result | Authentication → S1; branch rule → ask, and record it in the profile |
| P6 | PR already exists, was closed, or the remote branch was deleted | O | Query before creating | Reuse an open PR; closed → ask: reopen or abandon |
| P7 | Required human reviewers or code owners | O | Effective branch rules | pending: "waiting for review by …"; that touchpoint happens in GitHub |
| P8 | CI flaky | O | Rerun passes | Rerun once automatically |
| P9 | GitHub API outage or rate limit | O | API errors | pending with growing pauses on the host's network check, resuming by itself when GitHub answers |
| P10 | Expected or required CI missing, not triggered, cancelled, or awaiting workflow approval | O | Checks and statuses on the current head against the CI declared in the profile for the head's workflow digest and the effective rules | pending with bounded observation; then agent repair (for example a workflow trigger) or ask naming the owner's exact action; unknown check names are asked once per digest; unreadable workflows wait; the gate is never downgraded |
| P11 | A bot or informational comment needs no action, or a person asks a question in an issue comment | C | Conversation item without a fix to make | Bot preview links or coverage reports: recorded "no action needed: <reason>" and shown on the card, then they no longer block. Human questions are answered by a reply before the gate passes (interpretation of TD-15, `autonomous`) |
| P12 | Delivery's reply was posted but its acknowledgement was lost | O | Hidden marker `<!-- delivery:<change>:<item-id>:<fix-id> -->` found on the item | Never post twice: the engine finds the marker before posting and continues to resolve |
| P13 | A new reply arrives on a thread while its fix runs | O | Thread re-read before resolving shows a newer comment not by Delivery | No resolution; the new comment becomes a new feedback item |

**Person-only checks and merge**

| ID | Failure | L | Detection | Exit and handling |
| --- | --- | --- | --- | --- |
| H1 | User unavailable for days | C | — | pending without timeout; the status names the waiting check |
| H2 | User reports a check failed | O | Answer | back to build with the user's description as task input |
| H3 | Later change affects a passed check | O | A recorded input of the check changed (P5) | pending again on the check, naming what changed; otherwise keep the answer |
| M1 | User merged in GitHub directly | C | PR state | done: pull-back, then cleanup after preservation (M5) |
| M2 | Merge blocked after the gate passed: new target commits, a required check, a conflict | O | Merge result or SHA guard | back to integrate; the gate is re-evaluated for the new head |
| M3 | Rules require a merge queue | O | Profile | Out of scope (TD-22): J0 marks it unsupported; no queue submission or observation |
| M4 | PR closed without merging | O | PR state | ask: abandon or reopen |
| M5 | Cleanup finds uncommitted files, or local commits missing from the merged head | O | Workspace status; compare local commits with the merged head | Preserve privately and report; never delete unpreserved work |
| M7 | Pull-back cannot fast-forward: a checked-out local target is dirty, has untracked files in paths the update touches, or has diverged | C | `git worktree list`, working-copy status and ancestry after the fetch | Fast-forward only with `git merge --ff-only --no-autostash --no-overwrite-ignore`; never `git pull`, stash, reset or merge; card shows "local <target> is behind: <reason>" with Pull once possible; a changed gitlink adds "submodules changed". Unsaved editor buffers are invisible to git; VS Code shows its "file changed on disk" dialog |
| M8 | GitHub requires a human review before merging | O | Effective rules; review decision on the PR | pending: "waiting for review by …"; the review happens in GitHub |
| M9 | The target moves while the merge gate is evaluated | O | Re-read under the merge lock: the target is not an ancestor of the PR head | No merge; back to integrate; the gate is re-evaluated for the new head. Without "require branches to be up to date", a move after the re-read is the residual risk: the post-merge target-check watch drafts one fix Change for approval if checks fail on the target |
| M10 | A comment arrives while the merge gate is evaluated | O | Re-read under the merge lock finds an unhandled conversation item | No merge; the item becomes feedback (P3, P11). Without "require conversation resolution", a comment after the re-read is shown on the card after the merge |
| M11 | Cleanup finds Git LFS in use or submodules with local changes | O | Workspace inspection before retiring it | Not retired: card shows "workspace kept: <reason>" with its path |

**Cross-cutting**

| ID | Failure | L | Detection | Exit and handling |
| --- | --- | --- | --- | --- |
| X1 | Chat closed, VS Code quit, laptop asleep or rebooted mid-step | C | A step in progress without a live executor | When the host is down, the status shows "Delivery is not running" with the Start Delivery action. On start or wake the host observes, waits for live runners to finish or their termination to be confirmed, then resumes. The user only reopens VS Code, or uses Start Delivery where automatic start is unavailable |
| X2 | User asks unrelated things in the Change's chat | C | — | Allowed: loop state lives outside the chat |
| X3 | Weeks pass between sessions | C | — | Resume from state plus git and GitHub; a moved target is I1 |
| X4 | A tool server restarts during a write | O | Lost acknowledgement | Read state and effects on reconnect; replay only on confirmed absence; if observation fails, stop until it works |
| X5 | Two chats or windows continue the same Change | O | Per-Change lock | The second sees "already running in …"; takeover only after the first writer's termination is confirmed, otherwise stop naming the other session |
| X6 | User wants to pause, abandon or split a Change | O | Status-view action or chat | Handled as D6 for in-flight work; pause is a stop with resume; abandon closes the PR and keeps the branch; split is back to J2 |
| X7 | Copilot or VS Code update changes agent format, tool approval or model names | O | Readiness check or step error | stop with version information |
| X8 | Agent skips a step or edits state directly | O | Order is enforced in code; agents change state only through their one result tool | Prevented by design (P2) |
| X9 | The termination scan counts unrelated system processes as leftovers (found in M4 on macOS) | C | Scan limited to the step's worktree and to processes started after the step began | Design rule; real leftovers still block the next writer |
| X10 | Consented local files show up as changes | C | Setup checks `git ls-files` | Prevented: setup writes `.vscode/tasks.json` and `.mcp.json` only while untracked and adds them to `.git/info/exclude`; a tracked file is not written and setup shows the manual alternative (start the host by command; add the chat server in the user-level MCP configuration) |

**Rare, with generic handling only.** No dedicated machinery: a corrupted or half-written state file
(atomic writes keep the previous version; stop with "restore previous"), a corrupted git repository,
clock skew, hostile repository or web content beyond the platform's own protections. Each ends in
`stop` with work preserved.

### 3.5 Design requirements

| ID | Requirement | Rows |
| --- | --- | --- |
| DR1 | **Project profile** at setup, each entry marked known, unknown or unsupported with its evidence: host and repository root; push and PR-base repositories (forks); default and target branch; per-package install and check commands with directory, runtime and covered scope; credential references; LFS and submodules; CI and required checks; effective branch rules and rulesets (reviews, code owners, linear history, signing); merge methods; hooks. Re-read the effective rules before publishing and merging; re-detect on request | S3, B2, B3, B18, B20, P4, P5, P7, P10, M3 |
| DR2 | **Readiness check** at every start and before publishing; a failure yields one concrete fix | S1, S2, S4, S6, X7 |
| DR3 | **Project-facing work runs inside tasks** with the fix loop: installs, checks, commits with hooks, conflict resolution, CI fixes, review feedback. The engine's own operations never depend on project tooling; its git and GitHub calls map every failure to an exit | B1–B3, I2, I6, P1, P3 |
| DR4 | **One exit contract** (§3.3): five exits, pending situations, bounded retries with recorded reasons; no other step outcome | All |
| DR5 | **Re-entry by observation**: every step checks git and GitHub for its effect before acting and replays only on confirmed absence | X1, X4, P6, M1 |
| DR6 | **Work preservation**: a bundle of the Change branch plus an archive of dirty, staged, untracked and conflicted files, kept privately outside publishable branches; the workspace stays untouched until both are verified; a workspace with Git LFS or submodules with local changes is never retired ("workspace kept: <reason>") | B11, B19, M5, M11, X1 |
| DR7 | **Durable questions** owned by the loop, not the runtime: a worker ends with `ask`; answers from chat or the Changes page land in the host's inbox, which the host reconciles before skipping a waiting Change, then resumes the work | All `ask` exits |
| DR8 | **One status line** per Change, derived in one place, naming the next actor, observed activity and when it was observed | All |
| DR9 | **Unattended permissions**: default deny with an explicit allow list per step kind; denials are recorded and visible in the status; allow-all is never used | B7 |
| DR10 | **One writer per Change**: a lock; replacement only after termination is confirmed by cancelling runtime tasks, verifying their PIDs and the runtime's exit, and a host scan of the worktree including the runner's former subtree | B6, X5 |
| DR11 | **State outside the checkout and product branches**, versioned, with a migration path | S6 |
| DR12 | **Small agent tools** per TD-1; the engine enforces step order | B5, X8 |
| DR13 | **Budgets per Change** under the retry policy (§3.3), carried across `retry` and `back` for the same cause: identical failures, review rounds, re-plans; environment failures never count; credits shown per Change and step, never a cost question | S8, S9, D9, D10, B12, B14 |
| DR14 | **Footprint and support statement**: setup is user-local; it writes `.vscode/tasks.json` and `.mcp.json` only with consent and only while untracked, and lists them in `.git/info/exclude`, so nothing is committed; skills and agents are installed user-level; J0 states what is supported, human-assisted, unknown or unsupported, and never offers to bypass signing, reviews, push protection or workflow approvals | J0, X10 |
| DR15 | **Merge gate** (§3.2): Delivery merges the exact head automatically once the gate passes, without a consent touchpoint unless the profile asks before merge; one merge lock per target; the gate evaluated before and again after taking the lock, with the PR re-read; a new head re-evaluates the gate; every check observed at the head gates; required remote gates are never downgraded to local checks | M2, M8, M9, M10, P3, P10, P11, P12, P13, B23 |
| DR16 | **Pull-back** (§3.2): after a merge, fast-forward the local target with `git merge --ff-only --no-autostash --no-overwrite-ignore` only when it is not checked out, or is checked out clean and not diverged, in every worktree; never `git pull`, stash, reset or merge; otherwise a "behind" notice with Pull | M1, M7 |

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
  - the merge gate passes on head A, integration produces head B, then merge is attempted;
  - the target moves while the merge gate is evaluated (M9);
  - a comment arrives while the merge gate is evaluated (M10).
- **Practice proof (M4).** One end-to-end run on a sandbox consumer repository with a non-OwlBear
  toolchain in a nested package, CI with a required check, and branch protection. The cheap common
  failures are triggered by hand once: failing check, hook rejection, moved target with a conflict,
  closed chat mid-task, expired GitHub CLI login, CI failure, review comment, PR merged in GitHub,
  pull-back onto a dirty checked-out target.
  Each continues after its prerequisite is restored until the next successful step. One interruption
  leaves unfinished work and an unconfirmed push or PR, and must end without lost work or duplicate
  effects. User touchpoints are counted against the budget.
- **Visual check (M4).** A UI change in the sandbox gets the agent visual check: the host launches
  the preview from the brief's render recipe, takes screenshots and a reviewer judges them against
  the criteria. One deliberately broken layout must fail it and return a fix task; the screenshots
  appear on the Change card. Captures need `uv run playwright install chromium` once.
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
| The user merges every PR | Automatic merge when the merge gate passes, then pull-back to the local clone |
| Limits unknown to the authoring agent | Field-specific errors returned to the author |
| Assumes OwlBear's own toolchain | Project profile confirmed at setup |

## 4. Recommendation, Confidence, and Limits

**Recommendation:** use §3.2–3.6 as the first draft of D1 and D2 in M3. The charter (R4) adopts the
touchpoint budget, the exit contract and DR1–DR16 as binding; the remaining M3 documents (status
model, architecture, cutover) are written against this catalogue.

**Confidence:** medium-high that the common rows cover the ordinary failures of agent-driven work on a
GitHub repository; they combine the 2026-10-09 incidents, recurring incident classes from the old
engine's history (N11–N13), the consumer setup documentation, GitHub's documented branch-rule and CI
behavior, and two independent challenge rounds. Low on the likelihood labels, which are judgments to
be corrected by real use.

**Limits:** the [platform probe](delivery-next-platform-probe.md#4-recommendation-confidence-and-limits)
proved B7 and DR9 on its setup; X1, X4, X5, DR5 and DR10 are partly proven. DR7's answer surface and
runner activation are designed ([charter §3.7](delivery-next-charter.md#37-interaction-surface-and-runner-activation),
D3, D4) but not yet demonstrated. The `maba-pag` business seat (TD-17), a protection-gated automatic
merge, pull-back and the visual check are still unproven.
No consumer project was observed.
The catalogue has not yet been reviewed by the user.
