# Target Delivery Information Flow — Step 14: Integrate And Complete

> **Owning task:** none — target delivery information-flow walkthrough
> **Date:** 2026-08-03
> **Question:** How should completed Delivery enter the configured target and leave the active board
> without a second cleanup change, stale research competition, or loss of reusable knowledge?

## 1. Status Quo And Evidence

`ChangeWorkspaceManager.integrate()` already serializes integration, verifies supplied commits are
ancestors of the exact change head, merges without rewriting them, and compare-and-swaps the configured
target ref. A conflict returns an integration finding. No production MCP or Cockpit boundary currently
joins runtime readiness, exact completed results, Git integration, and terminal board state.

Active target loading enumerates `.owlbear/target/changes/<change_id>/`. Moving one complete directory
outside that root removes it from active loading without status filtering. Runtime authority and state
are already structurally attributable to a change, but Design and research are not yet stored under a
change package. Research currently occupies one flat shared namespace and may be reused across changes,
so filename or prose-link inference cannot safely decide what to archive.

## 2. Phase Audit

| Dimension | Decision |
|---|---|
| Actor | Runtime establishes readiness; workspace manager performs Git integration; a thin Orchestrator invokes the operation. No clean-path agent or reviewer. |
| Authority | Current board status, completed implementation/result bindings, required Assembly completion, exact change head, configured target, and change package manifest. |
| Inputs | Change identity through the normal caller; runtime derives commits, heads, package, and readiness. |
| Tools | One purpose-built integration operation composing runtime, Git workspace, and package publication; transport-free managers remain reusable. |
| Outputs | Integrated commit plus completed-history package, or a typed Integration finding. |
| Handoff | Success disappears into completed history; failure creates change-scoped Integration attention. |

## 3. Decision D1 — Change-Owned Physical Package

From session creation onward, store all change-owned material under one active package root keyed by
`change_id`:

- current `intent.md`, `design.md`, and generated Delivery Contract;
- change-specific research and source-context references;
- accepted task chains and mutable board/runtime state;
- implementation and Assembly result bindings;
- admission, revision, request, and minimal recovery records that still have a pipeline consumer.

Do not copy shared project sources, knowledge, memory, repository code, or reusable institutional
findings into every package. Research starts change-owned. The operator may promote a finding from
active or completed history when another change can consume it independently. Promotion creates an
explicit shared artifact/reference and is never a completion gate; archival never guesses ownership
from filenames, prose links, task numbers, or search matches.

This physical boundary makes active rehydration, search, scheduling, completion, restoration, and
retention operate on one identity instead of reconstructing a change from global directories.
Confidence: high.

## 4. Decision D2 — Integration Commits Completion And Archive Together

Enter `integration` in the derived change lifecycle after every required outcome is `completed` and
optional Assembly is complete, every promoted Assembly verified head is an ancestor of the exact
change head, and either that head or the admitted contract digest differs from the latest completed
package. Outcomes remain claimable items; the whole change is not complete until current product and
package authority enter the target.

The deterministic operation takes the serialized integration lock plus the existing per-change
package/runtime lock, then revalidates readiness and refuses revision-pending state. While those locks
are held, require the exact change head to equal the recorded reviewed/completed branch boundary and
current target identity to equal the admitted receipt. Mismatch fails with typed attention naming any
unreviewed commit range; target-head movement under the same identity is normal.

A deterministic integration operation validates current readiness, derives the exact completed
commits and branch head, and creates one target commit that contains both:

1. the reviewed product-code integration without rewriting completed commits; and
2. an immutable snapshot of the complete active change package in completed history.

When only package authority changed, retain the current target product tree and replace only this
change's completed package path; do not manufacture a product merge or require a code-head movement.

Construct that commit from explicit Git objects, not either checkout's index or working tree. Reject
change-side modification of the target's completed-history subtree; only Integration may create or
replace this change's stable package path while every sibling path remains byte-identical. Reuse the
stable-source inventory and hashing mechanism to reject package mutation during capture, derive the
product merge tree, insert the verified snapshot, and validate the resulting tree before `commit-tree`
and CAS. Never stage sibling active packages or require their working trees to be clean.

When the target advanced beyond the change branch's reviewed baseline, prove the candidate integrated
tree in the clean warm change worktree while Integration locks remain held. Apply the repository changed-path
test-domain mapping to the union of target-side and change-side product paths, excluding the
completed-history metadata path; unmapped or unbounded product impact runs its conservative fallback
scope. Any failure blocks publication with typed Integration
attention. Add no per-change proof selector, clean-path reviewer, or retained passing report.

Compare-and-swap the configured target only after the resulting tree and package destination are
valid. This avoids a later unreviewed cleanup commit. Successful publication gives the change terminal
disposition `completed`; completed history is storage and retrieval, not another Kanban status.
Active board, dependency, frontier, and default search operations exclude the completed-history root
by construction. Step 1 Designer identity search alone may query bounded completed semantic index
fields to detect prior or duplicate work; it never loads completed package bodies. Cockpit may
provide a separate read-only history view.

After CAS, replayably remove the untracked package using committed identity and source digest.
`integrate_ready_change(change_id)` recognizes the already-published package identity, finishes matching
residue and warm-worktree cleanup, and returns the same completion identity without another commit.
Do not delete completed bytes, branches, or refs; destructive retention remains operator policy.
Confidence: moderately high pending representative Git transaction and cleanup-replay proof.

Active loaders first check the completed-history identity on the target. A residual active directory
for a completed change is cleanup residue unless an explicit operator reopen marker exists; residue is
excluded from inventory and exposed only as cleanup attention. Reopening remains a documented manual
recovery from the retained package, branch, and history ref until repeated use justifies a normal tool.

## 5. Initial Tool Disposition

- **Keep** `ChangeWorkspaceManager` and its serialized compare-and-swap integration mechanics.
- **Add** one purpose-built `integrate_ready_change(change_id)` operation that derives readiness,
  exact results, heads, and package paths rather than accepting caller-assembled commit lists.
- **Remove** manual reviewed-commit collection and integration interpretation from Orchestration.
- **Add** read-only completed-history lookup outside normal active-board tools.
- **Do not add** a clean-path integration agent, reviewer, archive agent, per-task archive calls, or
  post-integration cleanup workflow.

## 6. Decision D3 — Change-Scoped Integration Attention

The change is not claimable, so integration failure does not use a worker `block`. The deterministic
operation publishes one change-scoped finding consumed by Cockpit, `integrate_ready_change`, and the
repair prompt: failure kind, unchanged change and target heads, conflict or proof diagnostics, target,
and exact retry condition. It may reference an Action Request for external resolution.

Abort temporary merge state and do not alter completed outcomes or infer new work. The user resolves
the condition and explicitly retries integration, invokes bounded merge repair, or moves backward
through invariant-checked administration when Specification, Planning, or Implementation must change.
Every retry rereads current heads and supersedes stale diagnostics. Confidence: high.

## 7. Decision D4 — User-Invoked Bounded Integration Repair

Do not send ordinary merge conflicts through the full Planning and Implementation pipeline. Keep the
change in `integration` with attention and let the user invoke an integration-repair prompt. It
launches a capable repair agent in the existing change worktree with the exact change and target
heads, conflicting paths, completed result boundaries, and integration retry condition. Nothing
dispatches this lane automatically.

The repair agent may resolve only the current merge conflict and create one additive
integration-repair commit. It may not rewrite completed commits, broaden scope, redesign behavior, or
silently alter task results. It uses one fresh Build Reviewer internally against the exact repair
commit. Review feedback remains invisible inside the repair cycle; ordinary observations are handled
critically, and the repair agent alone decides whether to revise or abandon the attempt.

One clean reviewed repair commit supersedes the finding, updates the change head and completed branch
boundary, and makes deterministic integration retry ready. Persist only that commit binding and
cleared attention, not prompt conversation, review output, commands, or proof transcripts. When safe conflict resolution requires changed
Product Promise, architecture, task authority, or substantial implementation beyond reconciliation,
the helper stops and asks the user to make an explicit administrative move to `design`, `planning`,
or `implementation` through Cockpit/API.

Start with one prompt composing existing workspace and Build Reviewer capabilities. Add a permanent
agent or skill only if repeated use reveals stable reusable complexity. Confidence: moderately high.

## 8. Decision D5 — Minimal Completion Record And Conservative Cleanup

Successful integration durably exposes only the identities later retrieval and recovery consume:
change ID, admitted contract digest, exact reviewed change head, integration target, integrated
commit, and completed package identity and path. The package contains Specification, task chains, runtime and
result bindings, requests, revisions, and change-owned research; do not duplicate them into a
completion summary or receipt narrative.

Do not embed the integrated commit hash in package or index bytes included in that same commit.
Integration returns the hash directly; later lookup derives it as the commit that introduced the
latest version of the exact completed package path and verifies the package digest.

Maintain one bounded completed-history index for recognition and lookup as a rebuildable cache derived
from completed package roots and Git history, not transaction authority. Normal active tools never
load package bodies. One stable package path represents the latest completion; Git history preserves
prior versions. Lookup derives the latest commit that changed that exact path and verifies its digest.
Manual reopen verifies identity, copies the package, writes the explicit reopen marker, and rebuilds
coordination from the retained branch and current target before any backward transition.

After successful target publication and active-package cleanup, automatically remove only the warm worktree.
Retain the change branch, dedicated package-history ref, integration-repair and rejected-attempt
refs, completed package, and integrated target commit. Git object sharing keeps that recovery history comparatively cheap. Branch
or ref pruning, package deletion, and retention compaction require an explicit operator action and
must not occur during normal completion. Confidence: high.

## 9. Step Completion

Step 14 is decided. Runtime derives integration readiness; one purpose-built operation integrates the
exact change head and archives its physical package in the same target commit, then removes the warm
worktree and returns minimal completion identity. Merge or candidate-proof failure creates
change-scoped Integration attention; bounded merge repair may create one internally reviewed commit
before explicit retry. Active board and search ignore completed history, while exact lookup and
documented manual reopen remain available. No clean-path integration, archive, completion-review, or cleanup agent is added.
