# Delivery Next: Charter

> **Owning task:** none — M2 of the [liveness-first rebuild](delivery-liveness-first-rebuild.md)
> **Date:** 2026-10-10
> **Question:** What is the next Delivery for, who owns what, what may the user be asked to do,
> how does every step end, and how small must it stay?
> **Status:** Draft for the user's approval. Only TD-1 to TD-8 in the rebuild research are the
> user's decisions; everything else here is `autonomous` until he approves this charter.

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
| H01 | [Rebuild research](delivery-liveness-first-rebuild.md) | Root causes RC1–RC6, principles P1–P9, roadmap, decisions TD-1–TD-8, provenance rule |
| H02 | [Journey and failure modes](delivery-next-journey-and-failure-modes.md) | Journey J0–J9, touchpoint budget, exit contract, catalogue, DR1–DR15 |
| H03 | [Ownership map](delivery-next-ownership-map.md) | Who owns each current responsibility; what Delivery-next keeps |
| H04 | [Route comparison](delivery-next-route-comparison.md) | Thin core on the Copilot runtime; reuse by copying |
| H05 | [Platform probe](delivery-next-platform-probe.md) | SDK loop, loop-owned questions, default-deny permissions, termination, cost |
| H06 | [Tool-surface audit §4](delivery-tool-surface-audit.md#4-recommendation-confidence-and-limits) | Tool rules T1–T8 (TD-1) |

## 3. Charter

### 3.1 Purpose

Help the owner of a GitHub repository shape and approve a change, then deliver the intended,
verified and independently reviewed result as a merged pull request, spending the owner's
attention only on decisions, person-only checks and merge consent.

### 3.2 Operating context

- One developer per installation, on their own GitHub repository, in any language or toolchain;
  teammates may not use OwlBear.
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
| **Delivery-next** | Brief and plan; the step loop with its exits, pending conditions and budgets; durable questions and answers; validity of reviews and person-only checks; merge consent bound to one head; one writer per Change; one status line; the project profile |

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
genuine questions, perform the person-only checks declared in the brief, review the PR and approve
merging its exact head (or merge in GitHub). Announced prerequisite actions — sign in again,
approve a permission, unlock a signer, set a credential outside chat — are allowed, each with its
exact action and resume condition. Anything else asked of the user is a defect. Setup is user-local;
it writes tracked files only with the user's consent (DR14).

### 3.6 How every step ends

Every step ends in exactly one exit — done, retry, ask, back, stop — or is pending on a named
external condition, with the rules of the journey research §3.3: bounded retries carried across
`retry` and `back`; a stop names one action, its actor and its resume condition; no exit discards
work; replacement of a worker only after confirmed termination; replay only on confirmed absence;
merge consent void when the head changes; required remote gates never downgraded. The design
requirements DR1–DR15 of the journey research are binding.

### 3.7 Interaction surface and runner activation

- **Conversation** — shaping a brief, discussing a question — happens in VS Code chat through
  OwlBear skills.
- **Status and answers** live in one local status view (Cockpit), which lists every Change with
  stage, situation, next actor and observed activity, and accepts answers, person-only check
  results and merge consent. Chat can answer ordinary questions through the same operation. Recovery
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
- Models are chosen per step type in the project profile, with a spend estimate shown before
  unattended work.
- Platform preview features (agent merge, Agents-window PR form, dynamic workflows) are optional
  conveniences and never required for the journey.

### 3.9 Budgets

Proposed values for TD-1's T7 and the other budgets; tests enforce them from M4 on.

| Budget | Limit |
| --- | --- |
| Agent-facing Delivery tools | 6 in total, at most 3 per role; a tool with one fixed result schema per session counts once |
| Step kinds | 10 |
| Exit kinds | 5, plus pending |
| Error kinds shown to users or agents | 15 |
| Delivery-next source, including copied and adapted modules | 10,500 lines (6,000 new plus the 4,500 reused today) |
| Delivery skill and agent prose | 800 lines |
| Automated test code | No more than the source it tests (P8) |
| Retries per cause | 3, carried across `retry` and `back` |
| Review rounds per task | 2 before asking the user |

### 3.10 Proof policy

Proof is a design walkthrough of every journey stage, catalogue row and connected trace (M3), one
demonstration on a sandbox consumer repository with the common failures triggered by hand (M4), and
real consumer use (M5). Automated tests cover only engine logic whose failure would be silent: exit
transitions, re-entry by observation, the lock, state migration and exported tool schemas. No
assertions on agent prose wording; agent definitions get structural checks only (TD-3).

### 3.11 Non-goals

Teams or several users per installation; a hosted service; forges other than GitHub; Windows;
parallel tasks inside one Change; bypassing signing, reviews, push protection or workflow approvals;
running OwlBear's own rebuild through Delivery ("Never use Delivery to implement Delivery").

### 3.12 Earlier rules this charter replaces

All are agent decisions under the provenance rule of the rebuild research §3.8.

| Earlier rule | Replaced by | Reason |
| --- | --- | --- |
| "Bounded recovery now; explicit containment otherwise" | §3.6 exits and confirmed termination | Containment ended in read-only diagnosis (RC1) |
| Native VS Code Orchestrator, no Copilot CLI or other runtime | §3.4 SDK loop | The loop moves from model prose into code (RC2); the SDK is the runtime VS Code's Copilot harness already uses, so no foreign tool is added |
| Requirements U1–U8 | §3.5 touchpoints and §3.6 exits | Same intent, testable form |
| Exact-commit evidence validity | Validity by recorded inputs (P5) | Re-asking on every commit (RC3) |
| Delivery state in product branches, pinned controller releases | State outside the checkout, ordinary tags | Self-conflicts and upgrade friction (RC3) |

## 4. Recommendation, Confidence, and Limits

**Recommendation:** approve this charter as the frame for M3, including the interaction
arrangement of §3.7 and the budgets of §3.9.

**Confidence:** high for purpose, ownership, touchpoints, exits and proof policy — they follow from
three challenge rounds and M1. Medium for §3.7: it fits the probe's evidence and keeps T6, but no
part of it has run. Medium for the budget values: they are first limits, set below today's size by
an order of magnitude, and should be adjusted only by the user.

**Limits:** the probe ran on a free personal Copilot account with the Auto model and an
unprotected private repository. Model choice, cost on the employer seat, and merges under branch
protection remain unproven until those probes are repeated (rebuild research §3.9). Delivery state
lives in the clone's git directory ([architecture](delivery-next-architecture.md)): deleting the clone
deletes the state of its unfinished Changes, while their branches and PRs remain on GitHub.
