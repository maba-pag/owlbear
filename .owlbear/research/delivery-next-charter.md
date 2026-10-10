# Delivery Next: Charter

> **Owning task:** none — M2 of the [liveness-first rebuild](delivery-liveness-first-rebuild.md)
> **Date:** 2026-10-10
> **Question:** What is the next Delivery for, who owns what, what may the user be asked to do,
> how does every step end, and how small must it stay?
> **Status:** Draft for the user's approval, revised after decisions TD-10 to TD-22. Only TD-1 to
> TD-22 in the rebuild research are the user's decisions; everything else here is `autonomous` until
> he approves this charter.

## 1. Context and Question

The rebuild research recommends a re-founding with the weight on design. M1 is done: the
[ownership map](delivery-next-ownership-map.md), the [route comparison](delivery-next-route-comparison.md)
and a live [platform probe](delivery-next-platform-probe.md). This charter turns them, the
[journey and failure catalogue](delivery-next-journey-and-failure-modes.md) and the decided
[tool rules](delivery-tool-surface-audit.md#4-recommendation-confidence-and-limits) into the binding
frame for the M3 design. Later design cannot override it without the user deciding again.

## 2. Sources Studied

| ID | Source | Used for |
| --- | --- | --- |
| H01 | [Rebuild research](delivery-liveness-first-rebuild.md) | Root causes RC1–RC6, principles P1–P9, roadmap, decisions TD-1–TD-22, provenance rule |
| H02 | [Journey and failure modes](delivery-next-journey-and-failure-modes.md) | Journey J0–J9, touchpoint budget, exit contract, catalogue, DR1–DR16 |
| H03 | [Ownership map](delivery-next-ownership-map.md) | Who owns each current responsibility; what Delivery-next keeps |
| H04 | [Route comparison](delivery-next-route-comparison.md) | Thin core on the Copilot runtime; reuse by copying |
| H05 | [Platform probe](delivery-next-platform-probe.md) | SDK loop, loop-owned questions, default-deny permissions, termination, cost |
| H06 | [Tool-surface audit §4](delivery-tool-surface-audit.md#4-recommendation-confidence-and-limits) | Tool rules T1–T8 (TD-1) |

## 3. Charter

### 3.1 Purpose

Help the owner of a GitHub repository shape and approve a change, then deliver the intended,
verified and independently reviewed result as a merged pull request, spending the owner's
attention only on the brief, genuine questions and person-only checks.

### 3.2 Operating context

- OwlBear is for the owner's personal use on his laptop (TD-9). A colleague might at most read the
  repository and build their own variant; no shared installation, distribution or support for
  others is planned.
- Delivery-next need not support OwlBear developing itself (TD-10); OwlBear keeps being developed
  directly in chat.
- The Changes it delivers land in the owner's GitHub repositories, in any language or toolchain;
  colleagues who share such a repository may not use OwlBear.
- VS Code with GitHub Copilot (TD-4); local Copilot CLI and SDK use is allowed (TD-5).
- macOS or Linux laptop that sleeps, closes and restarts; often a corporate proxy and single
  sign-on.
- Agents are trusted but fallible. Repository and web content is data, not instruction authority.
- What a failure costs: the owner's attention, lost unfinished work, duplicated pushes, PRs or
  merges, and bypassed repository policy. The design must make the last three impossible and the
  first rare.

### 3.3 Who owns what

| Owner | Owns |
| --- | --- |
| git | Branches, worktrees, commits, history |
| GitHub | Pull requests, reviews, checks and statuses, rules and rulesets, merge, merge queue, push protection |
| CI | The project's remote checks |
| Copilot platform | Agent sessions, model execution, tool-permission enforcement, transcripts, skills and instructions loading |
| **Delivery-next** | Brief and plan; the step loop with its exits, pending conditions and retry policy; durable questions and answers; validity of reviews and person-only checks; the merge gate bound to one head and the pull-back; one writer per Change; one status line; the project profile |

Delivery-next reads code facts from git and GitHub when it needs them and never stores copies.
Anything that touches product code — installs, checks, commits with hooks, conflict resolution, CI
fixes, review feedback — runs inside an agent task with the fix loop, never as an engine operation
(DR3). Custody, receipts, fences, recovery routes, a remote state branch and custom refs are dropped.

### 3.4 Route

A new thin core beside the old engine, in its own package, built on the Copilot runtime: a small
Python loop drives agent sessions through the Copilot SDK and uses git and GitHub through copied,
adapted modules (route comparison §3.4). The old engine stays frozen except for fixes the open
Changes need (TD-2) and is deleted at cutover (M6).

### 3.5 Touchpoints

Per project: run setup and confirm the project profile. Per Change: approve the brief, answer
genuine questions and perform the person-only checks the brief declares. There is no merge-consent
touchpoint: Delivery merges automatically when the merge gate passes (TD-15, §3.6). Reviews that
GitHub requires from people still apply; until they arrive the Change is pending "waiting for review
by …". A profile setting "ask before merge" (default off) restores a consent question for owners
who want it. Overlap between Changes is recorded and shown as "overlaps with X", never asked; docs,
lockfiles and generated files are ignored. Integration asks only on a behavioural collision — a
Builder-resolved conflict, or an integration ending in a question, that touches the scope of another
open Change or one merged in the last 14 days — with the options keep this behaviour, adopt the
other's, or pause (TD-12; this test is `autonomous`). Announced prerequisite actions — sign in again, approve a permission,
unlock a signer, set a credential outside chat — are allowed, each with its exact action and resume
condition. Anything else asked of the user is a defect. Setup is user-local (TD-11): it writes
`.vscode/tasks.json` and `.mcp.json` only with consent and only while they are untracked, and adds
both to the clone's `.git/info/exclude`, so nothing is committed. `.git/info/exclude` covers only
untracked files: if either file is already tracked, setup does not write it and shows the manual
alternative — start the host by command, or add the chat server in the user-level MCP
configuration. Skills and agents are installed user-level (`~/.copilot/skills/`), never in the
project (interpretation of TD-11, `autonomous`).

### 3.6 How every step ends

Every step ends in exactly one exit — done, retry, ask, back, stop — or is pending on a named
external condition, with the rules of the journey research §3.3: bounded retries carried across
`retry` and `back`; a stop names one action, its actor and its resume condition; no exit discards
work; replacement of a worker only after confirmed termination; replay only on confirmed absence;
required remote gates never downgraded. The design requirements DR1–DR16 of the journey research
are binding.

**Retry policy** (`autonomous`). Failures are classified by normalised signature (numbers, SHAs and
temporary paths removed). Environment faults — network and capacity — are pending with growing
pauses from 1 minute, capped at 30, and never consume budget; quota waits only for its reset; an
expired sign-in asks the owner to run the exact login command, then continue. The card shows the pending age and
attempts, goes quiet after 1 hour, and asks after 24 hours of the same signature. The same Delivery
defect signature — tooling, state or an invalid result — three times is asked with the error, never
waited on. Otherwise only identical failures without progress count, three at most per signature.
Progress means a strict improvement with no new failure — fewer failing checks, more satisfied
criteria, a resolved finding — not merely a new commit or changed error text; it resets the count.
On exhaustion of a check, review, scope, commit-policy or conflict cause the loop tries one re-plan,
then asks one question. A stronger model is not yet an alternative (D4 O11).

**Merge gate** (TD-15). Delivery merges when the exact head (SHA guard) has a valid final review;
every check observed at that head passed, with declared and required checks started; for UI
changes a passed agent visual check (TD-14); valid person-only checks; every PR conversation item
handled; and the target integrated. A failing check that was not declared becomes a fix task. The
declared CI is bound to a digest of the head's workflow files; unknown check names are asked once
per digest, unreadable workflows wait, and unknown CI never counts as none. Conversation items are
issue comments, review bodies and review threads; an item is Delivery's only by a recorded reply or
its own marked comment. Each other item version is answered by a reply, resolved after a fix, or
recorded on the card as "no action needed: <reason>"; an edited or reopened item is a new version
(interpretation of TD-15, `autonomous`). The host merges one Change per target branch at a time:
it evaluates the gate, takes the target's merge lock, re-reads the PR and evaluates the gate again
in the order of D3 §3.2. It merges with the profile's method and reads the result back. After the
merge it watches the target checks; a failure drafts one fix Change for the owner's approval.
Review comments become bounded Builder fix tasks; after a fix Delivery replies on the thread and
resolves it; on disagreement it asks the owner with both positions (TD-16).

### 3.7 Interaction surface and runner activation

- **Conversation** — shaping a brief, discussing a question — happens in VS Code chat through
  OwlBear skills.
- **Status and answers** live in one local status view (Cockpit), which lists every Change as a
  card with stage, situation, next actor, a deterministic "now" line (step plus last tool event),
  step time, a quiet warning when a step is unusually silent, credits per Change and step,
  visual-check screenshots and pull-back status, and accepts answers and person-only check results.
  Chat can answer ordinary questions through the same operation. Recovery
  decisions stay Cockpit actions, as tool rule T6 decided; moving them to chat would need the
  user's re-decision.
- **A local Delivery host** (the process that serves the status view) owns runners. Until cutover
  (M6) the host is its own small app serving the Changes page, so the pinned old Cockpit stays
  untouched for the open Changes; at M6 the page and its routes move into Cockpit. Recovery
  decisions are actions in that page in both phases (T6). A runner is a
  bounded process: it drives one step through the SDK, records the exit, and ends. The host starts
  the next runner after `done`, `retry` or `back` once the previous worker's termination is
  confirmed, re-observes pending conditions, and keeps answers that arrive during active work for
  the next step. It also starts a runner when the user starts or approves a Change, and when an
  answer or check result arrives. After a restart or wake it observes first, then resumes steps
  that are neither waiting on the user nor paused or stopped.
- **New Change button** (TD-13). The Changes page calls the host, which runs
  `code chat -r -m agent "<start prompt for the delivery skill>"` in the project folder; if `code` is
  missing, the page shows the exact command.
- **Pull-back** (TD-15). After a merge the host fetches. It fast-forwards the local target branch
  when it is not checked out, or when it is checked out in a clean, not-diverged working copy, with
  `git merge --ff-only --no-autostash --no-overwrite-ignore` in each worktree from
  `git worktree list`, never `git pull`.
  Otherwise it never stashes, resets or merges; the card shows "local <target> is behind: <reason>"
  with a one-click pull action once that becomes possible. Unsaved editor buffers are invisible to
  git; VS Code shows its "file changed on disk" dialog.
- **The host starts** when VS Code opens the project, through a folder-open task. Setup asks for
  and verifies the automatic-task permission and workspace trust this needs. Where automatic start
  is unavailable, one disclosed start action exists, and the status view or chat says nothing
  advances until it runs.

This arrangement is proposed, not probed: M3 must walk it against rows X1, X5 and DR7, and M4 must
demonstrate answer → runner → resume with the original runner gone.

### 3.8 Agents and platform use

- Agents author content, never identities (T2). Workers return one typed result per step; the
  loop, not the agent, records exits and advances.
- Each step type has a default-deny permission policy with an explicit allow list; denials appear in
  the status line. Allow-all is never used.
- Models and reasoning effort are chosen per role in the project profile, to be proven by the
  `maba-pag` probe (TD-17). Credits are shown per Change and step, never used to stop or ask (TD-21).
- Platform preview features (agent merge, Agents-window PR form, dynamic workflows) are optional
  conveniences and never required for the journey.

### 3.9 Size and style rules

TD-19 removes the total source line budget and line ceilings on agent instructions. Tests enforce
the countable rules from M4 on.

| Rule | Limit |
| --- | --- |
| Agent-facing Delivery tools (T7, TD-1) | 6 in total, at most 3 per role; a tool with one fixed result schema per session counts once |
| Step kinds | 10 |
| Exit kinds | 5, plus pending |
| Error kinds shown to users or agents | 15 |
| Agent instructions | No line ceiling; specialist terms instead of fillers and explanations, complete sentences where needed, no "caveman" style (TD-19) |
| Modules | Follow use cases: one step kind, one adapter, the API, the host. A module over about 400 lines of logic — not counting blank lines, comments, docstrings, imports, type-only declarations and interface definitions — is split by use case |
| Decisions | One owner per decision; a rule never lives in two modules |
| Function complexity | ruff complexity limits per function |
| Automated test code | No more than the source it tests (TD-3, P8) |
| Identical failures without progress | 3, carried across `retry` and `back` (§3.6) |
| Review rounds per task | 2 before asking the user |

### 3.10 Proof policy

Proof is a design walkthrough of every journey stage, catalogue row and connected trace (M3), one
demonstration on a sandbox consumer repository with the common failures triggered by hand (M4), and
real consumer use (M5). Automated tests cover only engine logic whose failure would be silent: exit
transitions, re-entry by observation, the lock, state migration and exported tool schemas. No
assertions on agent prose wording; agent definitions get structural checks only (TD-3).

UI changes always get a visual check (TD-14): the host launches the preview from the brief's render
recipe (start command, URL or entry, up to six UI states to capture), takes screenshots at desktop
and phone sizes, and a reviewer judges them against the criteria. A Change is UI when the brief's
`ui` flag says so or its diff touches UI files or folders; "Not a UI change" holds only for the UI
paths it was given for. The screenshots are kept with the Change and shown on its card; a
failure becomes a Builder fix task. The owner looks only when the brief declares a person-only check.
Shaping establishes the recipe before approval; if the project has none, it offers to add one as part
of the Change, declare a person-only visual check in the brief, or change scope. Visual testing is
never skipped (interpretation of TD-14, `autonomous`).

### 3.11 Non-goals

Teams or several users per installation; packaging or supporting OwlBear for anyone else; a hosted
service; forges other than GitHub; Windows;
parallel tasks inside one Change; bypassing signing, reviews, push protection or workflow approvals;
supporting OwlBear's own development (TD-10); merge queues (TD-22); stopping or asking because of
cost (TD-21).

### 3.12 Earlier rules this charter replaces

All but the last are agent decisions under the provenance rule of the rebuild research §3.8; the
last is replaced by the user's decision TD-15.

| Earlier rule | Replaced by | Reason |
| --- | --- | --- |
| "Bounded recovery now; explicit containment otherwise" | §3.6 exits and confirmed termination | Containment ended in read-only diagnosis (RC1) |
| Native VS Code Orchestrator, no Copilot CLI or other runtime | §3.4 SDK loop | The loop moves from model prose into code (RC2); the SDK is the runtime VS Code's Copilot harness already uses, so no foreign tool is added |
| Requirements U1–U8 | §3.5 touchpoints and §3.6 exits | Same intent, testable form |
| Exact-commit evidence validity | Validity by recorded inputs (P5) | Re-asking on every commit (RC3) |
| Delivery state in product branches, pinned controller releases | State outside the checkout, ordinary tags | Self-conflicts and upgrade friction (RC3) |
| Merge consent touchpoint | Automatic merge gate (TD-15), §3.5–§3.6 | The user decided automatic merge with pull-back |

## 4. Recommendation, Confidence, and Limits

**Recommendation:** approve this charter as the frame for M3, including the merge gate and retry
policy of §3.6, the interaction arrangement of §3.7 and the size and style rules of §3.9.

**Confidence:** high for purpose, ownership, touchpoints, exits and proof policy — they follow from
three challenge rounds, M1 and decisions TD-10 to TD-22. Medium for §3.7: the prototype ran a
Changes page and host in the sandbox, but the New Change button, pull-back and the card's "now"
line have not run. Medium for the merge gate: a merge under a ruleset with the SHA guard was proven
in a sandbox, automatic merge with thread resolution and pull-back was not. Medium for the module
size of about 400 lines of logic: a first value that only the user should change.

**Limits:** the probe ran on a free personal Copilot account with the Auto model. Models, reasoning
effort and cost on `maba-pag`'s business seat remain unproven until the `maba-pag` probe (TD-17). Delivery state
lives in the clone's git directory ([architecture](delivery-next-architecture.md)): deleting the clone
deletes the state of its unfinished Changes, while their branches and PRs remain on GitHub.
