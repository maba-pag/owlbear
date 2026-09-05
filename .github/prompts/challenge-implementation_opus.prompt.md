---
name: "challenge-implementation_opus"
description: "Use Claude Opus 5 to review an implementation against its plan, intent, and material behavioral risks"
argument-hint: "Describe the implementation or provide its plan, commit, diff, or review scope"
agent: "agent"
---

Challenge an existing implementation with a fresh Claude Opus 5 subagent. Determine whether the
reviewed implementation fulfills the accepted plan and user intent, and whether it introduces other
concrete material defects in the implemented workflow or its directly connected boundaries. Treat
the subagent as an independent evidence source, not the final authority: the calling model owns
scope, contextual judgment, dispositions, and the final recommendation.

This is a read-only review. Proposed repairs are findings, not permission to edit files, commit,
publish, release, finalize, or perform lifecycle transitions. This prompt does not replace a
Delivery `build-reviewer`, exact-head finalization review, security audit, or other required gate.
These instructions guide behavior; they are not a deterministic write guard.
These instructions guide behavior; they are not a deterministic write guard.

## Implementation Frame

Before dispatch, establish the narrowest review frame supported by evidence:

- **Status quo and problem:** relevant behavior before the implementation and the evidenced failure,
  cost, risk, or unmet need that motivated the change.
- **Intent and expected outcome:** what should observably change, for whom, and why.
- **Acceptance contract:** explicit requirements, accepted plan decisions, invariants, and exclusions.
  Distinguish approved commitments from tentative suggestions. Explain how the plan should achieve
  the intended result.
- **Reviewed state:** repository and worktree, exact candidate and baseline commits when applicable.
  For a working-tree review, identify HEAD plus staged, unstaged, and relevant untracked changes;
  do not equate HEAD with the uncommitted implementation or claim immutable proof. Record subsequent
  changes as review limits.
- **Changed surfaces:** production code, contracts, tests, configuration, documentation, persistence,
  and directly connected callers or consumers affected by the implementation.
- **Expected versus actual behavior:** what evidence says the implementation should do and what it
  demonstrably does.

Do not invent a plan, immutable identity, or acceptance criterion that was not supplied or found.
If no formal plan exists, review against explicit user intent and the available contract, stating
that limit. Ask only for missing context that materially prevents responsible review; otherwise
proceed with a clearly bounded scope.

Start from the nearest concrete anchor and inspect the controlling source, not only wiring or the
diff. Follow connected callers, contracts, and data flow only as needed for the intended workflow or
a material risk. Check history when it can resolve a relevant decision or reversal. Verify supplied
claims rather than adopting earlier summaries or test counts. Do not audit the whole repository or
reopen architecture selection by default.

## Review Contract

### Conformance And Implementation Soundness

Review both dimensions independently:

1. **Conformance:** does the implementation satisfy the accepted plan, intent, and observable
   outcome? Literal plan adherence is insufficient when the intended behavior remains unmet.
2. **Implementation soundness:** does the changed code behave coherently through its relevant
   control flow, data flow, public boundaries, and directly connected workflow? Inspect concrete
   error, security, persistence, integration, compatibility, and operational risks only where the
   implementation makes them relevant.

A deviation from the plan is not automatically a defect. Judge whether it preserves intent and is
better supported by the actual system while respecting explicit constraints. Likewise, do not treat
unrelated repository cleanup, preferred architecture, speculative hardening, or theoretical edge
cases as implementation defects.
Distinguish candidate-introduced defects from pre-existing conditions, but do not dismiss an existing
condition that prevents the agreed outcome merely because it predates the diff.

For each material requirement or intent, build a compact mapping:

| Requirement or intent | Source control point and implementation evidence | Behavioral evidence and limits | Proof status | Match, gap, or blocked |
| --- | --- | --- | --- | --- |

Use file and symbol or line references tied to the reviewed state. Trace the primary workflow to
its intended result; the existence of named functions or tests is not enough.

### Evidence Sufficiency

A passing test or suite proves only the assertions, inputs, execution path, fixtures, and environment
it exercises. It does not by itself prove intent, completeness, integration, security, usability, or
operational correctness. Inspect the relevant source control point and use the cheapest behavioral,
assembled-boundary, runtime, or manual evidence that matches each material claim.

For each material claim, consider a plausible way tests could pass while the implementation remains
wrong, or state `none` for a genuinely narrow tested contract. Mocks do not prove an unexercised
assembled workflow. Name the cheapest check that could falsify the concern.

Use proof status `baseline-only`, `adequate`, or `inadequate`: passing checks whose sufficiency has
not been established; evidence supporting the bounded claim; or a material evidence gap, respectively.
Distinguish checks actually executed on the reviewed state from supplied or stale results. Report
relevant commands, outcomes, and limits. A test may be adequate for its exact narrow contract.

Do not automatically demand full suites, E2E, browser, manual checks, or new durable tests. Caller
and subagent may run only available focused checks that respect read-only constraints. Do not install
dependencies, update locks, auto-fix, or mutate application or external state to obtain proof.
If a needed check cannot run safely, name the missing evidence; do not claim it passed. Narrow an
overstated claim when appropriate, but never erase an agreed requirement to make the implementation
appear complete. An `implementation-sound` verdict requires adequate evidence for material claims.

### Necessity And Proportionality

For each material finding and proposed fix, require:

- the narrow claim and concrete evidence or locator;
- the affected requirement, workflow, or connected boundary;
- the concrete consequence and plausible trigger if unchanged;
- why current tests or evidence do or do not cover it;
- the cheapest falsifying check;
- the smallest effective fix;
- complexity, behavior, or failure modes introduced by that fix; and
- confidence and proof status.

Judge the finding and its proposed fix separately. Reject unsupported, non-material, duplicative, or
disproportionate concerns and repairs. If neither leaving the issue unchanged nor applying the fix
has a concrete material consequence, reject it.

The only finding and proposed-fix dispositions are `fix-now`, `reject`, and `block`:

- `fix-now`: a necessary, proportionate repair belongs in the current proposed repair sequence.
  This label does not authorize editing.
- `reject`: explain why the concern or response is unsupported, immaterial, duplicative, unrelated
  to the intended outcome, or disproportionate. Cite existing coverage when relying on it.
- `block`: name the exact missing evidence item or stakeholder decision preventing judgment and
  the minimum action needed to obtain it. Uncertainty alone is not a demonstrated defect.

Rejecting an oversized fix must not dismiss a valid finding: retain the finding and propose the
smallest effective repair. If existing behavior already satisfies the requirement, record a match
and reject redundant repair work; do not label the requirement itself rejected.
Do not use `defer`, `separate task`, `later`, `follow-up`, `out of scope`, or equivalent parking labels.
The caller must normalize invalid labels before reporting the result.

## Dispatch Requirements

Use `runSubagent` for a new review on every invocation, with these exact choices:

- Omit `agentName`. Do not use `Explore`, `planner-challenger`, `build-reviewer`, or another named or
  prepared role. The fresh, un-specialized subagent still inherits active workspace instructions;
  never describe it as context-free.
- Set `model` to exactly `Claude Opus 5 (copilot)`.
- Set `description` to a short phrase such as `Challenge implementation`.
- Require read-only work: no edits, branches, commits, destructive commands, external mutations,
  publication, finalization, or lifecycle transitions. Apply the same constraints to the caller.
- Supply the verified frame, user request, accepted plan or its absence, candidate and baseline
  identity, relevant paths, available proof, uncertainties, and the decision to challenge.
- Include the full Implementation Frame, Review Contract, Required Challenger Memo, and verdict
  definitions below in the dispatch. Do not assume the subagent can see this prompt or the caller's
  full context; do not reuse a prior memo in place of fresh inspection.
- Instruct it to verify the frame and independently inspect source and connected behavior,
  distinguishing verified facts, assumptions, defects, evidence gaps, and recommendations.
- If the tool or exact model is unavailable, report the capability problem. Do not silently
  substitute a model or present a caller-only review as the requested independent challenge.

## Required Challenger Memo

Ask for these sections in this order:

1. Reviewed state and corrected frame: candidate, baseline, scope, intent, and evidence limits.
2. Material findings, severity-ordered and evidence-backed, with separate finding and fix dispositions
  when they differ. Detail the five highest-impact findings; summarize each additional material
  finding in one line with evidence, consequence, and disposition. The limit is on detail, not
  disclosure. Omit speculative filler; briefly explain rejections that affect the decision.
3. Plan-to-implementation mapping, including justified deviations, unmet intent, and proof limits.
4. Smallest repair sequence containing only necessary, proportionate repairs, with focused
  verification for each, or `no repair`. Name exact blockers and their minimum resolving actions,
  or `none`.
5. Advisory verdict using the definitions below, explaining what the evidence supports and leaves
  unproven. This is input to caller reconciliation, not the final decision.

## Caller Reconciliation

Do not forward the challenger memo uncritically. Verify each high-impact, scope-expanding, or
verdict-determining claim with a focused read-only check. Reconcile it against the user's intent,
accepted plan, actual reviewed state, and directly connected workflow. The challenger's confidence,
finding, proposed fix, and overall verdict are evidence, not authority.
Address any material requirement the reviewer missed.

For every material finding and proposed fix, assign exactly one of `fix-now`, `reject`, or `block`
with a concise reason. Assess issue validity separately from repair value and cost. Accept only
concrete defects with material impact and only proportionate repairs. Reject unsupported doubt,
alternate implementation taste, unrelated cleanup, and overcompensation without reflexively
defending the implementation. Normalize every invalid parking label.

Do not reject a demonstrated defect solely because its suggested fix is too broad. Reconcile evidence
gaps with proportionate proof, a narrower claim that preserves requirements, or an exact blocker.
Never convert lack of proof into an invented defect or unsupported approval. If the candidate changed
during review, identify what was and was not reviewed; do not transfer the verdict without checking
the changed state.

Then issue one scoped caller verdict:

- `implementation-sound`: material intent and constraints are met with adequate evidence, and no
  accepted material defect or blocker remains. This is not a claim of defect-free software, release
  approval, or Delivery completion.
- `repair-required`: material defects are established and necessary, proportionate repairs can be
  specified. Report remaining evidence limits and blockers; uncertainty elsewhere does not erase
  known defects.
- `blocked`: missing evidence or a stakeholder decision prevents a responsible verdict. Report any
  already-established defects alongside the exact blocker rather than concealing them.

Keep the final report compact: lead with material findings and reconciled dispositions, or state
that none were found; then give the verdict, exact scope, plan/intent conformance, smallest proposed
repair sequence, proof limits, and blockers. Confirm whether the fresh unnamed Claude Opus 5 review
actually ran. Do not reproduce the entire memo.

Stop after the review and repair proposal. Do not edit, commit, publish, finalize, or perform lifecycle
transitions unless the user separately authorizes implementation after the challenge is complete.
