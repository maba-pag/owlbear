# Delivery Action Readiness and Failure Visibility

> Status: P00 candidate; not approved or admitted.
> Programme: .owlbear/research/change-continuation-delivery-redesign.md; WP1 / P01-P04.
> Inspected baseline: 5f978744ad356456ff9d198893690b508b6aa1be on dev, 2026-09-12, plus the separately user-approved prerequisite working-tree changes.
> Preparation, model choices, test evidence, and release gates: .owlbear/research/delivery-action-readiness-p00.md.

## Problem and Product Promise

Delivery exposes lifecycle-derived actions whose executable preconditions are checked separately. A completed outcome can advertise Finalize Change while the managed checkout is dirty. Finalization can then return proof_failed without retaining the failure in Change state, so a fresh session repeats the same instruction. A malformed runtime can prevent get_change from returning information needed for diagnosis.

For a named Change, agents and Cockpit must receive one truthful readiness decision and a durable account of unsuccessful finalization. The user sees whether verification ran, what prevents progress, and which supported interaction exists, without being asked to run tests, inspect a worktree, edit state, or supply a digest. This is WP1, not the whole continuation/recovery system.

## Normal Workflow

1. An operator inspects a Change in Cockpit or an agent reads get_change.
2. The application captures admitted state, workspace readiness, retained finalization failure, and supported actions into a coherent response.
3. The same readiness decision shapes the card, detail, and finalization preflight. An unclean or unobservable checkout is not executable finalization.
4. A finalizer that cannot proceed records a bounded diagnostic report through an engine operation when a trusted report basis exists. It changes neither branch nor proof authority and performs no repair.
5. A fresh host reads that report and distinguishes checks not run, failed checks, and review findings. A report is observation, not a new lifecycle gate or permission to ignore existing gates.
6. Existing actions remain accessible when current preconditions permit them. A passing same-candidate finalization retires the matching active diagnostic pointer; the immutable report remains. A changed head or contract makes old reports historical.
7. A read-only inspection prompt explains current blockers and supported next interactions. It cannot apply repairs or ask the user to change worktree files.

## Scope and Preserved Remainder

One shared readiness decision; coherent list/detail/MCP/HTTP views; bounded persisted finalization failure reporting and reachable finalizer wiring; degraded read projections; read-only inspection; focused and assembled tests. The agent-config companion P02-W is a separate domain task inside the P02 primary session, not another packet launch.

No automatic repair, worktree restoration, new writer fencing, continuation controller, merge mutation, requirement revision, private-input form, evidence waiver, or live B1/D1 migration. P05 offline execution is separate. Selected Change/task acquisition and explicit host model binding are prerequisite work, not WP1 implementation. Preserve the programme's later outcomes without advertising unavailable prompts today.

Retain independent exact-head review, strict receipt/schema validation, user merge approval, engine-owned Git effects, claim custody, pending publication replay, and unrelated staging. A runtime parse failure must not be made permissive merely for display. New reports are host-local and intentionally excluded from portable authoritative snapshots in this Change.

## Decisions and Release Gates

The user requested P00, one primary session per packet, and three model tiers; subsequently the user approved bounded baseline/selected-launch prerequisite maintenance. Selected models are T3 GPT-6 Astra (copilot), T2 Claude Opus 5 (copilot), and T1 GPT-5.6 Luna (copilot). Host probes accepted explicit model arguments; they do not attest underlying model identity or prove Builder/reviewer nesting. Different model families must produce and independently review a candidate.

Prerequisite source was implemented and passed an expanded 622-test selection. Its exact release commit and live schema activation remain prerequisites, not inferred from working-tree tests. It permits fenced selected acquisition while preserving shared capacity and existing transaction recovery. Previously recorded root transactions may recover sibling filesystem state; it does not acquire new sibling claims or replay sibling remote publication.

No final approval of this WP1 contract has been given. The agent must obtain a reviewed immutable prerequisite baseline, verify the live selected acquisition schema, obtain exact WP1 package approval/admission, and use a native task plan before acquiring P01. Current B1/D1 are not paused or modified to force scheduling. The user performs no test, worktree, state-file, or Git repair operation.

## Success and Technically Done but Wrong

Success is consistent executability and understandable retained failure after restart. Wrong outcomes include an accurate tooltip beside an ineligible button, tests labelled failed when none ran, a report becoming a permanent block, a fake repair command, report writes changing proof/custody, or a broken Change disappearing from the portfolio.

```yaml target-contract
kind: commitment
id: COM-001
class: dealbreaker
provenance: user-requested actionable Delivery UX and observed D1 preflight failure
statement: Action eligibility and explanation come from one application-owned decision; unavailable or unobservable finalization cannot be advertised as executable.
```

```yaml target-contract
kind: commitment
id: COM-002
class: protected-request
provenance: user prohibits manual tests and worktree/state repair
statement: Unsuccessful finalization remains visible after restart with checks-run status, bounded structural diagnostics, and a read-only inspection interaction; the user is not instructed to edit worktrees or run tests.
```

```yaml target-contract
kind: commitment
id: COM-003
class: dealbreaker
provenance: existing exact-candidate review, custody, and receipt contracts
statement: Readiness inspection and failure reporting cannot mutate product files, release custody, alter acceptance, create successful proof, or authorize a stale candidate; diagnostic history alone cannot add a lifecycle gate.
```

```yaml target-contract
kind: commitment
id: COM-004
class: protected-request
provenance: existing quarantined runtime and state-reconciliation failure surfaces
statement: An unreadable Change remains inspectable through a degraded read projection without relaxing canonical validation or claiming unavailable state is healthy.
```

```yaml target-contract
kind: commitment
id: COM-005
class: agreed-path
provenance: programme wave plan, domain boundaries, and user-approved launch prerequisite
statement: WP1 depends on release and activation of the selected-launch prerequisite; P01, P02 including its separate P02-W domain task, P03, and P04 then run serially in one Change worktree with independent exact-commit review and no new acquisition of unrelated Changes.
```
