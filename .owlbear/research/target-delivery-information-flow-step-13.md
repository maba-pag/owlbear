# Target Delivery Information Flow — Step 13: Correct Or Re-Enter

> **Owning task:** none — target delivery information-flow walkthrough
> **Date:** 2026-08-03
> **Question:** How should a failed, disputed, blocked, or invalidated Delivery claim return to its
> earliest owner without a correction coordinator, summary handoff, or duplicate authority?

## 1. Status Quo And Evidence

Runtime already distinguishes local `repair`, fresh `restart`, two duplicate planning returns,
Design return, parked requests, one owner evidence response, arbitration, and interrupted-claim
recovery. Steps 10–12 separately define launch recovery, Plan and Build review outcomes, workspace
reconciliation, and exact successor contexts.

`task-plan` and `solution-plan` currently call the same `_republish_plan` transition. Current runtime
also lets reviewer dispositions directly change job state and stores a generic `returned` state plus
a return level. That mixes feedback, worker instruction, transition, and current Kanban status. Parked
requests preserve exact claim and commit identities, but `resolve_request(request_id, resolved_at)`
stores no answer, so later work cannot recover what was decided without conversation context.

## 2. Phase Audit

| Dimension | Decision |
|---|---|
| Actor | Working agent issues the final transition instruction; reviewer supplies internal feedback; runtime applies the mechanical transition; user resolves bounded questions and material consequences. |
| Authority | Live claim and finding are temporary correction evidence; accepted task graph, admitted Delivery Contract, and approved Specification remain their respective authorities. |
| Inputs | Current board item and status, exact claim, phase output, reviewer feedback, worker transition instruction, source boundary, and minimum successor context. |
| Tools | Phase-output publication, read-only review inside the work cycle, minimal transition operation, exact context projections, answer-bearing request resolution, claim recovery, and Design-session re-entry. |
| Outputs | `advance`, `retry`, `return`, or `block`; runtime updates status and exposes the next exact context. |
| Handoff | Runtime updates status and directly publishes or exposes successor context; Orchestration only reacquires claimable work and never interprets feedback. |

## 3. Decision D1 — Runtime-Owned Typed Routing Protocol

Step 13 is a cross-loop protocol, not a separately dispatched phase or agent. Claiming a board item
starts one work cycle in its current Kanban column. Independent review supplies feedback to the
working agent and has no direct board effect. The agent addresses feedback as needed, then issues one
final transition instruction:

- `advance` declares current-column work complete and asks runtime to move mechanically forward;
- `retry` ends the claim and leaves the item in the same column for another attempt;
- `return` names one earlier column permitted from the current column and supplies the reason and
  exact successor context;
- `block` ends the claim in place and supplies reason, unblock condition, expected evidence, and exact
  locators; include a request only when its bounded user answer or action is the resolution mechanism.

Runtime validates the separately produced phase output and maps the instruction through the fixed
transition table. `advance` may require successful independent review inside the agent contract, but
review itself never moves the item. The successor owner may broaden a defect to an earlier authority
but may not narrow away supplied facts.
The Orchestrator refreshes current board state and claims ready work without reading feedback or
choosing a destination. Design remains manually user-started.

Add no correction coordinator, correction agent, generic correction mutation, summary handoff,
return ledger, or user-facing technical routing decision. Confidence: high.

## 4. Initial Tool Disposition

- **Split** phase-output publication from the minimal worker transition operation. The transition
  references an already produced task chain, commit, or assembled result when validation needs it.
- **Keep** exact-claim recovery for interrupted active work.
- **Keep** role-specific Plan, Build, and Design context projections; add no generic correction view.
- **Replace** `task-plan` and `solution-plan` with `return(target="planning")`.
- **Replace** parked active claims with same-column `block`; answer-bearing resolution makes the item
  claimable again with preserved source context.
- **Remove** direct reviewer lifecycle mutation, correction interpretation from Orchestration, and any
  requirement to persist closed review prose solely for audit.

## 5. Decision D2 — Answer-Bearing Requests, Owner-Judged Routing

Keep Decision and Action Requests distinct. A Decision Request provides bounded evidence-backed
options that appear valid inside admitted authority. An Action Request names the external action or
controlled input, required evidence, and exact resume condition. Both explain why the active owner
cannot proceed autonomously.

Resolution is user/Cockpit controlled, not agent callable. It records an optional selected option and
optional response text, requiring at least one. Response text is either the complete free-text answer
or notes refining a selected option. Never force the user to choose a listed option or classify
whether their answer requires redesign.

Resolving a request makes the same blocked board item claimable again in its unchanged column with
the preserved source boundary. Its role-specific Plan or Build context includes the complete relevant
request and resolution directly; the next owner does not traverse request lists or conversation. The
assigned Planner or Builder judges the response against current authority and the stated resume
condition:

- proceed when the answer is sufficient and remains inside admitted meaning;
- create one narrower follow-up request when only bounded clarification or action evidence is absent;
- issue `return(target="design")` after required review when the answer changes, contradicts, or exposes
  insufficiency in protected meaning.

For a requestless block, the user may resolve its condition manually or through an out-of-band agent.
Cockpit then performs a same-column unblock with a resolution note and needed evidence locators.
Runtime does not judge that work; it clears attention and makes the unchanged item claimable.
The user may separately start Design at any time under revision quiescence rules. Persist the request
and resolution because the resumed claim consumes them; do not persist chat, generated summaries, or
an agent interpretation of the answer. Confidence: high.

## 6. Decision D3 — Result Is Not Status

A reviewer returns feedback to the working agent. The worker issues the transition instruction.
Runtime consumes that instruction and updates the board item's canonical pipeline status. Do not
store `returned` as the current status plus a separate return level.

- `advance` moves to the mechanically derived next column or `completed`;
- `retry` keeps the current column;
- `return` moves to its validated earlier column;
- `block` keeps the column and adds reason, unblock condition, evidence needs, and optional request.

Outcome items use `design`, `planning`, `implementation`, `assembly`, and `completed`. Dependencies
require prerequisite outcomes to be `completed`; they never read review, change lifecycle, or prior
instructions. Remove generic `TargetJobState.RETURNED`, `ReturnLevel`, and transition-shaped status.

The change is not a claimable outcome. Its derived lifecycle is `design`, `active-delivery`,
`integration`, or `completed`, with mixed outcome stages exposed separately. Runtime enters
`integration` after all outcomes complete; Step 14 alone completes the change after target integration.

## 7. Decision D4 — Constrained MCP Results, Invariant-Checked Administration

For agent-driven MCP completion of an outcome, use this fixed transition table:

| Current status | `advance` | Allowed `return` targets |
|---|---|---|
| `planning` | `implementation` | `design` |
| `implementation` | remain until required implementation work succeeds, then `assembly` when required or `completed` | `planning`, `design` |
| `assembly` | `completed` | `planning`, `design` |
| `completed` | terminal | none through worker completion |

From every active status, `retry` and `block` remain in the current column. Runtime derives the
forward destination and validates an explicit return target. No worker claims `design`; revised
admission or invariant-checked administration alone produces `design` to `planning`. An MCP worker
cannot invent a status, skip forward, or reopen completed work.

Authorized administrative interfaces may move an item backward and deterministically invalidate
later authority plus the completed dependent closure of any invalidated result, preserving only
evidence deterministically proven unaffected. A forward move is allowed only when normal destination
invariants hold; it cannot synthesize completion or skip required work. Record the reason and expose
the move as operator-directed. Cockpit may clear a same-column block when its condition is satisfied. Confidence: high.

## 8. Decision D5 — Advisory Feedback, Worker-Owned Transition

Review one complete candidate inside the active work cycle. Ordinary reviewer observations are
advisory. The worker must inspect and disposition every material observation, but should critically
reject speculative scope, taste, or overcorrection rather than implementing feedback mechanically.
Useful corrections remain inside the same work cycle. Materially changed candidates receive a fresh
review before `advance`; minor corrections need only the cheapest affected recheck.

Reviewer may identify an attempt as fundamentally mis-anchored or unsafe, but issues no command.
The worker decides whether to repair, `retry`, `return`, or `block` and preserves diagnostics when its
chosen transition needs them. Deterministic runtime validation may reject invalid output or stale
references but never interprets review prose.

Feedback and worker disposition remain invisible outside the cycle. Remove review persistence,
owner-response, arbitration, and reviewer lifecycle authority. Persist only the worker transition
and output or successor context consumed by the pipeline.
Confidence: high.

## 9. Decision D6 — Read-Only Assembly, Explicit Integration Work

The independent Assembly verifier is the sole working agent for the `assembly` column. It inspects
the exact assembled result and issues `advance`, `retry`, `return`, or `block` without another
reviewer. A second reviewer would only review the review.

Assembly never edits code or invokes a Builder subagent. When pieces require implementation to fit
together, Planner creates an explicit integration task, normally as the final dependent
`implementation` task before Assembly. That task receives the normal Builder and independent review
cycle. Planning must consider whether interfaces, generated artifacts, wiring, migrations, or
cross-result composition require such an integration task; it must not add one by convention when
the independently implemented results already compose.

Assembly returns to `planning` when verification requires redone implementation, missing integration
work, or changed task authority; Planner republishes the graph and claimable jobs. It returns to
`design` when admitted meaning is insufficient. Confidence: high.

## 10. Decision D7 — Separate Output From Transition
Use one minimal transition operation with `advance`, `retry`, `return`, and `block`. It does not carry
the work product except Assembly's read-only verified binding. Planning publishes the task chain and
Implementation creates the exact commit/result before transition. Assembly's `advance` carries its
verified head and result identities because no separate durable output exists.

Non-Git output publication is idempotent and claim-scoped. It creates a candidate identity and digest,
not accepted authority; `advance` atomically promotes the exact candidate with status movement.
Recovery may replay that transition or expose an unpromoted candidate as retry context, never as
dependency or completion evidence.

`retry` carries only context that materially helps a fresh attempt. `return` carries its earlier
target plus the concrete problem and exact locators that owner consumes; Design return also carries
affected commitment and outcome IDs. `block` carries the reason
and optional Decision or Action Request identity. Do not include internal review feedback, reviewer
identity, model, transcript, command output, timestamps, or a generic evidence list. Confidence:
high.

## 11. Step Completion

Step 13 is decided. Correction is a mechanical board transition owned by the worker's minimal
instruction: `advance`, `retry`, `return`, or `block`. Review remains invisible inside the active
work cycle with no reviewer lifecycle command. Phase output
is written separately, requests carry exact user answers, MCP transitions follow the fixed table,
and administrative recovery preserves destination invariants. Step 14 receives completed
implementation and Assembly bindings plus current board status; it does not receive review history.
