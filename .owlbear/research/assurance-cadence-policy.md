# Assurance Cadence Policy

> **Owning task:** #1968 - Replace the OwlBear delivery pipeline
> **Date:** 2026-08-02
> **Question:** When should independent adversarial review occur, and what distinct claim should each review prove?
> **Status:** S3 resolution derived from current user input; exact correction mechanics remain for S4.

## 1. Governing Principle

Independent challenge is a regular part of every major stage, not a rare exception and not a gate
after every artifact. Reviews may combine adjacent work when the bundle presents one coherent claim.
They must not repeat merely because wording, generated identity, or another technical detail changed.

Review is relatively inexpensive compared with implementation and late correction because it mainly
consumes model input and reasoning. Use it often enough to catch blind spots near their source, while
requiring each review to name the distinct claim it proves.

## 2. Independence and Model Roles

- The primary planning agent uses Opus 5 by preference for high-level synthesis and planning.
- Each adversarial review uses GPT-5.6 sol by preference in a separate context.
- The reviewer receives the authoritative artifacts, relevant source, and proof needed for its claim,
  but not the primary agent's persuasive discussion or presumed conclusion.
- Different model families are intentional: correlated blind spots are less useful than independent
  judgment from another top-capability model.
- Model availability and exact runtime identifiers are configuration concerns. A substitution must
  preserve independent context and comparable reasoning capability rather than silently weakening the
  role.

## 3. Shaping and Planning Reviews

### Early meaning challenge

Intent is the anchor used to judge every later stage, so it is eligible for adversarial review. It
does not necessarily require a standalone review immediately after drafting. Intent may be reviewed
with outcomes, constraints, acceptance meaning, or another coherent next step when that gives the
critic enough substance to expose misunderstanding.

The bundle closes when the reviewer can answer one question: does this describe the right result,
including material exclusions and failure consequences, without replacing user intent with agent
preference?

### Scoped intermediate challenges

Run additional isolated reviews when a major shaping or planning stage establishes a consequential
claim that should not wait until coding readiness. Candidate bundles include:

- intent plus the integrated semantic contract;
- architecture and operating consequences;
- deliverable decomposition and dependency strategy; and
- destructive migration, cutover, security, concurrency, or proof strategy.

Several of these may be reviewed together. The number of files or lifecycle labels does not determine
the number of reviews.

### Mandatory pre-coding review

Before any coding starts, one independent reviewer examines the complete chain from intent through
outcomes, constraints, acceptance, architecture, deliverables, dependencies, implementation tasks,
and planned proof. This is the final large coherence check.

Earlier scoped reviews do not replace it. They reduce the chance that this broad review discovers a
foundational defect only after detailed planning.

## 4. Implementation Reviews

Independent review is integral to implementation:

1. The builder completes one task and its focused proof.
2. A separate reviewer inspects the exact committed code, required outputs, and proof in isolation.
3. The reviewer returns one actionable disposition: acceptable, needs repair, restart the task, or
   return the task for redesign/replanning.
4. The original builder remains available with its implementation context and performs permitted
   repairs. S4 defines when correction must instead return to an earlier stage or to the user.

This review checks the task's implementation. It must not restate successful deterministic checks or
reopen unchanged intent without concrete contradictory evidence.

## 5. Composition Reviews

### Outcome assembly

When multiple reviewed tasks must compose one outcome, an independent reviewer checks only the new
claim: that the pieces work together and satisfy the outcome's acceptance meaning. It must not repeat
each task review. A one-task outcome whose implementation review already covered the complete outcome
has no broader composition claim and closes without another model review.

### Change assembly

When multiple completed outcomes must compose one change, an independent reviewer evaluates their
interactions against the full intent and cross-outcome acceptance. This catches omissions, migration
failures, and individually correct work that does not form the promised result. If one outcome already
spans the complete change and no broader claim exists, this check also collapses into the earlier one.

Task, outcome, and change checks are not fixed lifecycle quotas. Retain a broader check only when it
can falsify composition that narrower checks could not. Otherwise it is ceremony.

## 6. Cadence Controls

- Review after each major claim, not after each document mutation.
- Combine stages when reviewing them together improves the critic's ability to judge coherence.
- Split reviews when one bundle would hide a distinct high-consequence claim or overload useful
  context.
- Re-review changed claims and affected dependents, not unchanged material by default.
- Do not run an unlimited fresh-review loop. Preserve unresolved findings and route disagreement
  explicitly; the correction and escalation rules are resolved in S4.
- Deterministic validation runs before adversarial review so model reasoning is spent on judgment.

## 7. Proportional Review Depth

Independent review does not mean full implementation research at every stage. Before starting, the
owning workflow states the claim being reviewed and selects the least expensive action that can
falsify it:

1. **Critical reading:** look for contradiction, omission, ambiguity, or erosion in the supplied
  meaning. This often fits intent and outcome review.
2. **Direction and coherence check:** compare adjacent stages and representative source to determine
  whether work is heading toward the intended result. This often fits intermediate architecture or
  deliverable review.
3. **Focused contract or execution check:** inspect named parameters, interfaces, boundaries, and run
  the defined test or workflow. This fits task plans, committed implementation, and acceptance.
4. **In-depth source or prior-art research:** investigate common implementations, external contracts,
  security, concurrency, destructive migration, or unfamiliar architecture when the earlier actions
  cannot resolve a consequential uncertainty.

These are available review actions, not four mandatory passes. A reviewer may combine them. It goes
deeper only when novelty, consequence, irreversibility, or unresolved evidence makes the cheaper
action insufficient. The evidence must state what was actually inspected or executed so a critical
read cannot be presented as implementation research.

For this change, intent may receive critical reading plus a direction check; the complete pre-coding
review needs source-grounded architecture and proof checks; task review inspects exact plans and
focused contracts; build review inspects the exact diff and focused proof; outcome and change assembly
checks execute only their distinct composition boundaries.

## 8. S3 Resolution

For the delivery-pipeline replacement:

- challenge intent, either alone or bundled with the next coherent semantic stage;
- challenge consequential shaping and planning bundles as required;
- require one comprehensive intent-to-tasks review before coding;
- require isolated adversarial review as part of every implementation task;
- require outcome assembly only where multiple reviewed tasks create a new composition claim; and
- require change assembly only where completed outcomes create a new cross-outcome claim.

The rule is one independent review per distinct claim, with broader checks only where composition
creates something narrower reviews could not prove. Assurance scales by claim, not lifecycle labels.

## 9. Confidence and Limits

**Confidence:** High in the stage boundaries and preference for regular cross-model review because the
user specified them directly. Medium in the best grouping of early reviews until exercised against a
revised semantic contract and implementation plan.

**Limits:** Model names require mapping to runtime-supported identifiers. Exact tool permissions and
evidence envelopes for each review action remain implementation mechanics.