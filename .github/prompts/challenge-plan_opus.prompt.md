---
name: "challenge-plan_opus"
description: "Use Claude Opus 5 to challenge a technical plan and reconcile material risks with user intent"
argument-hint: "Describe or paste the plan, decision, or compatibility proposal to challenge"
agent: "agent"
---

Challenge the plan or proposal with a fresh Claude Opus 5 subagent before recommending
implementation. Treat the subagent as an independent evidence source, not a replacement planner:
the calling model owns the contextual judgment and final plan.

This is a read-only challenge and proposed plan revision, not implementation authority. It does not
replace Delivery's native planning review, security audit, or any required approval or lifecycle gate.
These instructions guide behavior; they are not a deterministic write guard.

## Decision Frame And Necessity Gate

Before dispatching the challenger, and again when reconciling its memo, establish the decision frame:

- **Status quo:** what exists and what currently happens, verified against the nearest relevant
 source or other concrete evidence.
- **Problem:** the specific failure, cost, risk, or unmet need that is actually evidenced. Do not
 turn a preference, theoretical possibility, or confusing symptom into a problem without proof.
- **Expected outcome:** what should be observably different, for whom, and in which workflow.
- **Intent and change contract:** what the user is trying to accomplish, why it matters now, what
 to do, why to do it, how the proposed route does it, and what result that route should produce.
- **Commitments and scope:** distinguish explicit requirements and constraints, approved decisions,
  and tentative suggestions. Identify the plan version or exact supplied text, relevant repository
  and worktree, and the source state supporting its premises. If uncommitted changes matter, identify
  HEAD plus staged, unstaged, and relevant untracked changes; do not claim immutable proof from HEAD.

Start from the nearest concrete anchor and inspect the controlling source, not just wiring. Follow
connected callers, contracts, and data flow only as needed to evaluate the primary workflow or a
material risk. Verify supplied claims instead of adopting earlier summaries. Ask only for context
that materially prevents responsible judgment; otherwise proceed with explicit evidence limits.
Do not invent a missing plan or requirement. If only an idea exists, identify the proposed route as
tentative rather than presenting it as an approved commitment.

Assess whether the route actually solves the problem, not only whether its steps are internally
coherent. Check material omissions, dependencies, ordering, hidden surfaces, and relevant prior
decisions or reversals. Consider existing mechanisms and no change before adding machinery; do not
redesign toward a preferred architecture or audit the whole repository by default.

For every finding and every proposed fix, independently decide whether it is necessary for that
outcome. Check its concrete impact if left alone, its fit with the user's intent, whether the
proposed response is the smallest effective change, and whether it creates more complexity or risk
than the problem warrants. Reject unsupported, non-material, duplicative, or disproportionate
concerns and fixes. A valid finding does not automatically make the reviewer's fix necessary.

For each material finding and proposed fix, run both counterfactuals: state the concrete material
failure if the concern remains unfixed, and state the complexity, behavior, or failure mode the fix
would introduce. If neither counterfactual identifies material impact, reject the concern or fix as
unnecessary.

The only valid dispositions are `fix-now`, `reject`, and `block`. `defer`, `separate task`, `later`,
`follow-up`, `out of scope`, and equivalent parking labels are not dispositions. Incorporate the
minimum necessary change into the current plan, or reject it with the reason. Use `block` only when
one exact missing evidence item or stakeholder decision makes a responsible decision impossible;
name that blocker explicitly. If the challenger uses an invalid parking label, normalize it to one
of the three valid dispositions before reporting it.

`fix-now` means a necessary change to the proposed plan, not permission to edit. A `block` must also
name the minimum action needed to obtain the missing evidence or decision. Rejecting an oversized
fix must not dismiss a valid finding: choose the smallest effective response. If the current plan
already covers a concern, cite its exact step and evidence, retain that obligation, and reject only
the redundant proposed addition. Uncertainty alone is not a demonstrated defect.

## Evidence Sufficiency Gate

A passing test or test suite is baseline evidence for its exact assertions, inputs, execution path,
fixtures, and environment, not proof that intent or complete functionality was implemented. It does
not by itself establish completeness, integration, security, usability, or operational correctness. A test may be
adequate for a deliberately narrow test-contract claim; otherwise match the proof to the claim.

For every material finding and proposed fix, state:

- the narrow claim being evaluated;
- what the tests actually exercise and leave unproven;
- the source control point, contract, or data flow that should implement the intent;
- one plausible way the tests could pass while the implementation is still wrong, or `none` when
 the claim is genuinely limited to the tested contract;
- the cheapest check that could falsify that possibility; and
- proof status: `baseline-only`, `adequate`, or `inadequate`.

`baseline-only` means passing checks exist but their sufficiency for the claim is not established;
`adequate` means evidence supports the bounded claim; `inadequate` means a material evidence gap
remains. Distinguish checks executed on the reviewed state from supplied or stale results, and report
relevant commands, outcomes, and limits. Mocks do not prove an unexercised assembled workflow.

Separate decision-critical premises from proof of future implementation. Resolve premises needed to
choose a responsible route now, or report an exact blocker; merely adding a later test does not
settle a premise that could invalidate the approach. For behavior not yet implemented, define the
minimum acceptance evidence and when it must pass in the proposed sequence. Its present absence is
not itself a plan defect or a reason to demand implementation during review.

Do not automatically demand full suites, E2E, browser, manual checks, or new durable tests. Use only
available focused checks that respect read-only constraints. Do not install dependencies, update
locks, auto-fix, or mutate application or external state to obtain proof. Name evidence that cannot
be obtained safely instead of claiming success. Narrow overstated claims without removing agreed
requirements. Do not recommend proceeding while a decision-critical premise remains unsupported;
keep future implementation proof explicit rather than presenting it as already established.

## Dispatch Requirements

Use `runSubagent` for a new challenge on every invocation, with these exact choices:

- Omit `agentName`. Do not use `Explore`, `planner-challenger`, `build-reviewer`, or any other
 named/prepared role. This creates a fresh, un-specialized subagent, but it still receives active
 workspace instructions; do not describe it as context-free or assume it has the caller's full
 context.
- Set `model` to exactly `Claude Opus 5 (copilot)`.
- Set `description` to a short phrase such as `Challenge technical plan`.
- Tell the subagent to be read-only: no file edits, branches, commits, destructive commands,
 external mutations, publication, finalization, or lifecycle transitions. Apply the same constraint
 to caller reconciliation.
- Give it the user's request, intended outcome and primary use cases, current plan, known repository
 facts, plan/source identity, uncertainties, and the decision that needs challenging.
- Include the full Decision Frame And Necessity Gate, Evidence Sufficiency Gate, Evidence To Request,
 Required Challenger Memo, and Recommendation definitions below in the dispatch. Do not assume the
 subagent sees this prompt or the full conversation; do not reuse an old memo instead of inspecting
 the current plan and its premises.
- Instruct it to verify the frame independently and distinguish verified facts, assumptions,
 evidenced risks, missing proof, and recommendations.
- If the tool or exact model is unavailable, report that capability problem. Do not silently
 substitute another model or present caller-only analysis as the requested independent challenge.

## Evidence To Request

Use targeted source reads, relevant history, tests, and safe runtime evidence that fit the proposal.
For runtime or support-floor proposals only, inspect declared floors, development pins, lock metadata,
dependency groups, imports, and actual execution evidence. Dependency resolution alone does not prove
runtime compatibility. A compiler version alone does not promise browser support: inspect emitted
targets, bundler and CSS targets, and browsers actually exercised.

Propose any required installation, synchronization, or build proof as an explicit step with a success
criterion rather than executing it during read-only review. Do not introduce platform concerns when
the proposal has no relevant compatibility dimension.

## Required Challenger Memo

Ask for these sections, in this order:

1. Reviewed plan/source identity, corrected decision frame, and evidence limits.
2. Severity-ordered material findings: evidence or locator, affected workflow, consequence and
 plausible trigger, confidence, falsifying check, and independent finding/fix dispositions when
 they differ. Detail the five highest-impact findings; summarize each additional material finding
 in one line with evidence, consequence, and disposition. The limit is on detail, not disclosure.
 Omit speculative filler; briefly explain rejections that affect the decision.
3. Compact intent-to-plan mapping: each material outcome or constraint, the step that addresses it,
 relevant control point, evidence for the premise, and required acceptance proof. Include material
 gaps, hidden surfaces, and prior decisions or reversals that change the recommendation.
4. Smallest revised sequence as deltas to the supplied plan, or `no change`, with proof gates for
 accepted changes. Separate decision-critical missing evidence from future implementation proof.
5. Advisory recommendation using the definitions below, exact blockers and minimum resolving actions,
 or `none`. This is input to caller reconciliation, not approval authority.

## Reconciliation After The Subagent

Do not forward the memo uncritically. Verify each high-impact, scope-expanding, or recommendation-
determining claim through focused read-only checks, prioritizing the primary workflow and connected risks.
Reconcile the findings against the original user intent and the direction the revised plan would
take. This is neither a defense exercise nor an automatic remediation exercise.
Address material requirements the reviewer missed. If the plan or source premises changed during
review, identify what was and was not reviewed; do not transfer the recommendation without checking
the changed state.

For each material finding and proposed fix, record exactly one of `fix-now`, `reject`, or `block`
with a concise reason. The caller owns the final applicability, value-versus-cost, and
signal-versus-noise judgment; the reviewer's confidence or fix suggestion is evidence, not authority.
Accept a concern only when its concrete impact merits a current-plan change, and accept its fix only
when it is necessary and proportionate. Reject unsupported doubt, alternate implementation taste,
and overcompensation without reflexively defending the plan. A blocker is not a parking lot: use it
only when the missing evidence or stakeholder decision genuinely prevents a responsible choice.
Normalize any invalid challenger disposition before reporting it. Before recommending implementation,
confirm every material finding and proposed fix has one valid disposition, decision-critical premises
are adequately supported, and future implementation proof has explicit gates in the sequence. Do not
erase requirements to narrow claims, dismiss a valid concern because its suggested fix is too broad,
or turn lack of proof into an invented defect or unsupported endorsement. State the resulting plan
delta or `no change`.

Do not expand task count, scope tier, or architecture solely for a low-confidence edge case. An
expansion requires an accepted finding with a named user-facing or connected operational impact and
proportionate proof. Keep this reconciliation compact: one line per material finding rather than
reproducing the memo.

### Recommendation

Judge the supplied plan, not a silently assumed repaired version:

- `plan-sound`: the route covers material intent and constraints, decision-critical premises are
 adequately supported, and no necessary plan correction or blocker remains. Future implementation
 proof is specified, not claimed complete. This is not implementation authorization.
- `revision-required`: necessary, proportionate plan corrections can be specified. Give the exact
 deltas and remaining evidence limits; do not treat the proposed revision as already reviewed.
- `blocked`: an exact missing fact or stakeholder decision prevents responsible route selection.
 Report already-established plan defects alongside the blocker rather than concealing them.

Keep the final report compact: lead with material findings and reconciled dispositions, or state
that none were found; then give the recommendation, reviewed scope, plan deltas, refined sequence,
proof boundaries, and exact blockers. Confirm whether a fresh unnamed Claude Opus 5 review actually
ran. Do not reproduce the entire memo.

Stop after the challenge and proposed plan revision. Do not edit, commit, publish, finalize, or perform
lifecycle transitions unless the user separately authorizes implementation after the challenge.
