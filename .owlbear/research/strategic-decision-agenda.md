# Strategic Decision Agenda

> **Owning task:** #1968 - Replace the OwlBear delivery pipeline
> **Date:** 2026-08-02
> **Question:** Which remaining strategic consequences require user guidance, in what order, and what must agents prepare before asking?
> **Status:** Staged discussion agenda. It requests no decision in this document.

## 1. Confirmed Foundation

The current collaboration direction is confirmed:

- The user originates goals, intent, priorities, and unacceptable outcomes.
- Agents contribute progressively more through outcomes, constraints, acceptance, strategy, and
  implementation details.
- Material tradeoffs are discussed through consequences, not recommended-option prompts.
- User review operates on understandable high-level abstractions.
- Agents and independent reviewers own detailed completeness, technical coherence, and proof.
- Routine mechanics do not become user ceremony.

This agenda identifies only decisions where differing consequences need user priorities. It does not
ask the user to choose schemas, files, IDs, algorithms, tools, or lifecycle internals.

## 2. User-Owned Decision Test

A question needs user guidance when credible paths differ materially in one or more of:

- promised value or normal workflow;
- what remains possible, preserved, or excluded;
- interaction frequency or degree of autonomous progress;
- quality, independence, or failure-detection guarantees;
- compatibility, migration loss, downtime, or reversibility;
- operating burden, resource cost, privacy, or understandable oversight.

If paths differ only in implementation mechanics, agents decide and reviewers challenge the result.

## 3. Remaining Strategic Decisions

### S1. Semantic completeness before Delivery

**Question:** How settled must outcomes, material constraints, acceptance meaning, and strategy
consequences be before implementation can proceed?

**Why user-owned:** This trades earlier conversation and stability against later adaptation and
re-review. It controls what admission promises, not the file schema used to express it.

**Agent preparation required:** Show one ordinary feature and one infrastructure-heavy change at
different completeness depths. For each, explain what can safely adapt later, what could erode value,
and what rework or user interruption each depth creates.

**User review object:** Two short end-to-end change stories, not graph records.

### S2. Human checkpoint cadence

**Question:** Which semantic developments should pause for user guidance, which should be grouped for
review, and which may proceed with visible notification?

**Why user-owned:** This determines the actual balance between collaboration and ceremony.

**Agent preparation required:** Map intent, outcome, constraint, acceptance, strategy, and correction
events to their consequences. Estimate interruption count for ordinary, high-risk, and corrective
work. Distinguish a new material consequence from additional technical detail.

**User review object:** A sample change timeline showing what the user sees and when progress waits.

### S3. Assurance and independence appetite

**Question:** Which risks justify fresh independent challenge, build review, node acceptance, and
whole-change audit, and where may assurance scale down?

**Why user-owned:** Stronger independence can catch expensive failures but adds agent starts, context
loading, proof time, and correction cycles.

**Agent preparation required:** Use observed planning cost and representative failure classes. Show
what each assurance boundary detects, what another boundary already covers, and the cost of uniform
versus risk-adaptive application. Agents derive exact reviewer and retry mechanics afterward.

**User review object:** Risk-to-assurance map with concrete caught and uncaught failure examples.

### S4. Material-change and correction routing

**Question:** When later evidence changes a plan, what may agents repair inside reviewed meaning, and
what consequence changes must return to collaborative Specification or Planning?

**Why user-owned:** Too broad an agent repair authority can silently change value; too narrow a rule
turns ordinary implementation learning into repeated approval.

**Agent preparation required:** Classify real examples from DN-003 and an ordinary feature as local
detail, strategy adjustment, acceptance change, outcome change, or intent change. Explain the user-
visible consequence and proposed return layer for each.

**User review object:** A small correction-routing scenario set, not invalidation algorithms.

### S5. User-facing transparency and evidence depth

**Question:** What must be understandable at a glance, what should be one drill-down away, and what
may remain technical audit evidence?

**Why user-owned:** The product must provide confidence without requiring reconstruction from YAML,
while retaining enough evidence for scrutiny and recovery.

**Agent preparation required:** Prototype meaning, semantic-contract, and technical-trace views using
the same real change. Demonstrate interruption recovery and explain what information each view hides
or preserves.

**User review object:** Working Cockpit projections or faithful mockups, not an abstract field list.

### S6. Migration and cutover tolerance

**Question:** What downtime, compatibility loss, active-work disposition, rollback capability, and
self-hosting risk are acceptable when the redesigned pipeline replaces the current one?

**Why user-owned:** These are direct operational consequences. Store relocation, selectors, carrier
topology, and transaction sequence are engineering consequences of the tolerance, not user choices.

**Agent preparation required:** Inventory current valuable state, active work, reversible boundaries,
failure recovery, and the cost of retaining or removing compatibility. Explain what is lost, frozen,
migrated, or recoverable under each credible cutover path.

**User review object:** Operational cutover story with failure and recovery walkthroughs.

## 4. Discussion Order

Do not ask all six questions now.

1. Resolve S1 and S2 before finalizing authority or plan schemas.
2. Use those answers to prepare S3 and S4 with realistic lifecycle examples.
3. Prototype S5 after semantic projections are known; review it visually rather than abstractly.
4. Resolve S6 only after the target system and current-state inventory are concrete.

Within each discussion, follow `graduated-semantic-collaboration.md`: establish the reviewed parent
meaning, explain credible paths through comparable consequences, state the technical assessment after
the comparison, and ask what consequence best fits the user's intent or remains missing.

## 5. Agent-Owned Work

The following require no standalone user decision unless evidence exposes a new consequence:

- YAML versus another storage syntax and exact file count;
- stable ID formats, digests, receipt envelopes, and job allocation;
- graph validation, currentness, closure, replay, and transaction algorithms;
- package, class, function, adapter, and transport placement;
- test commands, partitions, fixtures, and collected-case hashes;
- exact reviewer retry limits derived from the accepted assurance and interruption policy;
- generated Cockpit fields below the reviewed meaning/semantic/technical projection contract.

Agents document and independently review these choices. They return to the user only when alternatives
change a strategic consequence above.

## 6. Progress Checklist

- [x] Define graduated collaboration and enabled review.
- [x] Prepare evidence and concrete examples for S1 in `s1-semantic-completeness-examples.md`.
- [x] Discuss and record S1 in `semantic-commitment-policy.md`: plans adapt, while user-requested and explicitly important meaning receives graded protection and focused Decision Request routing.
- [x] Prepare ordinary and infrastructure timelines for S2 in `s2-checkpoint-cadence-examples.md`.
- [x] Discuss and record S2 in `checkpoint-cadence-policy.md`: requests block the task needing input and its true dependents; unrelated ready work continues.
- [x] Prepare S3 assurance evidence in `s3-assurance-boundary-examples.md`.
- [x] Discuss and record S3 in `assurance-cadence-policy.md`: use isolated challenge per distinct claim, with outcome or change Assembly only where composition creates a broader claim.
- [x] Prepare S4 correction evidence in `s4-correction-routing-scenarios.md` using actual DN-003 repair, replanning, proof-guarantee, and lifecycle-correction cases.
- [x] Discuss and record S4 in `correction-authority-policy.md`: reviewers bind the submitted artifact; builders repair only implementation; task and solution-plan owners receive typed returns; user collaboration resumes only for protected meaning or material guarantees.
- [x] Define the S5 unified work-board projection in `s5-unified-work-board-model.md`: visible work items span user-started Design through conditional Assembly while immutable jobs remain technical trace.
- [x] Prototype and independently review S5 at-a-glance, semantic detail, and technical trace views; distinguish user attention from agent activity and make work-item scope explicit.
- [x] Remove priority from the S5 target: independent ready outcomes run concurrently, hard dependencies determine sequence, and stable creation order resolves capacity ties.
- [x] Collapse post-implementation work into conditional Assembly: inline challenge proves each task, Assembly proves only new composition claims, and passing work moves to completed/archive storage.
- [x] Remove per-job Cancel; replace the owner-scoped Release claim board control with explicit early recovery when a prior orchestration session is known dead, retaining expiry recovery as fallback.
- [x] Route removal of an unwanted outcome through collaborative Design and replanning; do not expose direct outcome Cancel, Delete, or Withdraw controls.
- [x] Omit Pause and Stop controls: orchestration is an on-demand Copilot chat loop, stopping the chat stops dispatch, and Design re-entry remains a separate semantic action.
- [x] Approve S5's global portfolio and task-card hierarchy, with one writable worktree per change and concurrent writers only across changes.
- [x] Accept the compact PDS candidate as an approximate hierarchy and density reference; preserve the existing Cockpit dashboard shell, navigation, header rhythm, responsiveness, and visual language in the real implementation.
- [ ] Prove high-volume portfolio behavior during implementation beyond the prototype's representative cards.
- [x] Inventory and resolve S6 in `s6-cutover-inventory.md`: use a receipt-bound clean cutover, preserve all current evidence as a verified read-only snapshot, reintroduce reviewed unfinished meaning, and do not migrate stale job positions or add dual-write compatibility.
- [ ] Derive technical architecture and mechanics from the resulting strategic constraints.

## 7. Recommendation, Confidence, And Limits

**Recommendation:** Treat S1-S6 as the complete current user-owned strategic agenda. Begin by having
agents prepare concrete S1 examples; do not ask the user to choose a completeness policy from abstract
labels.

**Confidence:** High that these six questions cover the remaining user-visible consequences in the
current redesign. Medium that no additional strategic question will emerge from ordinary-feature
examples or the cutover inventory.

**Limits:** This agenda identifies decision surfaces and preparation obligations. It does not contain
the alternatives, select an answer, or authorize authority/schema implementation.