# Delivery N13 — Engine-Owned Target Prerequisites

> **Package:** N13, added after programme completion (2026-10-09), from the Cockpit incident on
> `macos-managed-browser-authentication` (TASK-005).
> **Planned on:** `dev` at `e8db645c4`; N13-B merged as `2d7b33a76` (#427). Live Delivery is pinned;
> live state was read only through Delivery's read tools.
> **Deviation (user-directed, 2026-10-09):** no Delivery for this work; direct implementation in two
> worktrees (engine, Cockpit), with an implementation gate after each phase.
> **Plan gates:** chat plan v1 Sol `revision-required` (custody transaction, incident adoption,
> companions and activation, one requirement representation); v2 Sol `plan-sound`, no findings.
> Reviews work in the execution plan's [operating context](delivery-redesign-execution-plan.md#19-operating-context).

## 1. Contract

### 1.1 Result

A Builder that needs a target-branch commit its Change does not contain stopped with a human action
request ("run Delivery target synchronization"). No control could satisfy it: Delivery offered sync
only before finalization, sync refused while the Builder handoff held uncommitted work, and a
free-text answer cleared the block without checking anything, so the Builder relaunched and blocked
again.

After N13 the Builder returns a **target-sync block**: no request and one `target-commit:<commit>`
locator.
Delivery preserves the handoff under refs, resets the worktree to its reviewed head, offers the sync
as engine work (continuation prompt or Cockpit **Merge target into Change**), clears the block once
the reviewed head contains the commit, and starts a fresh claim for the same task whose
`return_context` names the preserved refs. A conflict follows the existing target-conflict route.

### 1.2 Requirements

- R1 A Builder target-sync block carries exactly one `target-commit:<40-hex>` locator and no request;
  a request beside that locator is refused. Using a locator keeps every persisted schema unchanged.
- R2 Settlement records the block with no request and keeps a same-task handoff.
- R3 Readiness offers `sync-target` (engine-executable) for that block before finalization, bound to
  the reviewed head and the observed target head; a commit the target lacks is
  `target-commit-missing` for the user.
- R4 Before a sync, Delivery preserves the handoff's head, index and worktree under the Design-return
  refs, resets to the reviewed head and releases the handoff in one transaction; drifted uncommitted
  content is captured as found.
- R5 After a sync whose merged head contains the commit, Delivery resolves the block with the
  receipt and commit locators; the next continuation does the same after a crash in between.
- R6 The fresh claim for the task sees the preserved refs in `return_context`.
- R7 Cockpit shows the block's prerequisite and offers the merge on the Outcome.

### 1.3 Invariants

- Uncommitted Builder work is never discarded: capture precedes reset (N04 §1.7 order).
- A requested Pause keeps the handoff; a paused or terminal Change refuses the release.
- The release is one runtime transaction (frontier and coordination); the loader accepts a captured,
  unreleased handoff like a Design return.
- Persisted schemas are unchanged (the prerequisite is a validated locator), so the record-schema
  fingerprints hold and no format change is needed.

### 1.4 Existing owners reused

`release_design_return` capture and reset; `sync_change_with_target`; target-conflict capture and
resolution; `runtime.unblock`-style resolution; the engine `sync-target` continuation action.

### 1.5 Exclusions

- A Planner-authored task prerequisite (dropped from plan v2 as a lead decision: a target-sync block
  is refunded, so the cost is one short Builder invocation, and no new plan schema or readiness path
  is needed).
- Automatic re-application of preserved work; the Builder reconciles it.
- Converting the incident's existing action request; it is answered once and the Builder re-blocks
  with the typed form.

### 1.6 User decisions

- U1 (2026-10-09): wait for the fix; preserve the incident's five uncommitted files.
- U2 (2026-10-09): the preservation mechanism is the lead's choice (R4).
- U3 (2026-10-09): implement directly in worktrees, not through Delivery.

## 2. Phases

| Phase | Scope | Proof |
| --- | --- | --- |
| N13-B | Cockpit detail UX: open request first, anchored link, answered history, hints, short commits | Merged #427 |
| N13-A | R1–R7, Builder and Planner skills | Code `a88f2fb91` + repair `42ee7852e`. N13 tests 13 passed (incl. default-loader restart at capture and release boundaries); changed-scope `uv run test --changed` 3533 passed, 4 failures fixed or isolated-pass flakes; `npm test` 397 passed; build ok; LC load form on `42ee7852e`: 10 live Changes available, copy records unchanged, inspector healthy. Sol round 1 `repair-required` (P2 current-target selector, fixed); delta `implementation-sound` |

## 3. Activation (live, after merge)

1. `/upgrade-delivery` to the merge commit after an LC rehearsal on a live copy.
2. Answer the incident's open request once ("superseded by the typed target-sync route").
3. Continue the Change: the Builder re-blocks with a `target-commit:` locator; Delivery preserves the
   five files, merges `dev` (expected conflicts go to `/resolve-target-conflict`) and restarts
   TASK-005 with the preserved refs.

## 4. Verification gaps

- G1 Real-Git mid-build conflict: covered by the existing conflict owners and a patched capture test;
  the incident's activation exercises it live.
- G2 Engine-run (continuation) sync is proven through acquisition and release; the fixture has no
  branch publisher, so the engine action itself runs only in live activation.
