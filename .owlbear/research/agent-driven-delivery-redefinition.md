# Agent-Driven Delivery Redefinition

> **Owning task:** #1968 - Replace the OwlBear delivery pipeline
> **Date:** 2026-08-02
> **Question:** How should OwlBear preserve valuable agent-led specification, planning, review, and acceptance while removing mechanical repetition and unbounded review churn?
> **Status:** Working redesign plan. This supports discussion and does not modify admitted change authority.

## 1. Context and Question

The current replacement correctly gives agents an active role throughout Specification, Planning,
Build, Acceptance, and Audit. Collaboration follows `graduated-semantic-collaboration.md`: the user
leads intent, outcomes are shared, and the agent's contribution grows through constraints,
acceptance, strategy, and details while user guidance and review move to higher-level consequences.

The redesign must not optimize for minimum document length. It must distinguish valuable semantic
reasoning from lifecycle data that code can derive, validate, or generate. A plan may be substantial
when the outcome is complex, but each substantial section must help a human or downstream agent make
a decision, implement safely, or verify the result.

### Non-negotiable guardrails

- [ ] Apply the graduated collaboration model: distinct methods, user actions, agent actions, review abstractions, and gates for intent, outcomes, constraints, acceptance, strategy, and details.
- [ ] Preserve one-question intent refinement and explicit material user decisions.
- [ ] Preserve complete outcome ownership, dependencies, interfaces, migration, risks, and proof.
- [ ] Preserve agent-led, user-guided implementation strategy and discriminating acceptance scenarios, with consequence-level user review and detailed agent review.
- [ ] Preserve independent semantic challenge, exact-commit acceptance, and whole-change audit.
- [ ] Preserve enough rationale for interruption recovery without replaying chat history.
- [ ] Treat prior `accepted` decisions as hypotheses until their alternatives and consequences are revalidated with the user.
- [ ] Keep option sets open; do not use an implausible foil, hide free-text alternatives, or treat a recommendation as consent.
- [ ] Do not use line count as an acceptance criterion.
- [ ] Do not rewrite current authority or historical evidence until this redesign is approved.

## 2. Sources Studied

| Source | Relevant fact |
|---|---|
| `intent.md` | The Product Promise requires one agent-guided path and four purpose-specific Delivery transformations. |
| `design.md` | Authority, work, evidence, and Git have distinct responsibilities; jobs must not copy normative truth. |
| `decisions.yaml` DEC-008, DEC-028..033 | These record prior selections, but `accepted` status alone does not prove an informed or freely framed choice; revalidation is required. |
| `delivery/nodes.yaml` DN-003 | The admitted node already owns its outcome, obligations, modules, interfaces, dependencies, risks, and proof. |
| `delivery/contracts.yaml` IF-003 and PROOF-003 | Runtime invariants and the canonical proof boundary already exist before packet planning. |
| `plans/DN-003.yaml` | The plan repeats canonical ownership and proof data, then stores six prose pass explanations. |
| `native_runtime.py::_validate_node_plan` | Code primarily validates plan mode, packet identity/dependencies, allowed references, and impact closures. |
| `DeliveryGraphOutline.tsx` | Cockpit currently exposes IDs and closure data but omits most plan rationale and acceptance meaning. |
| Unpublished DN-003 planner result | Useful implementation findings were surrounded by repeated contract and thirteen review iterations. |
| `graduated-semantic-collaboration.md` | Defines layer-specific collaboration depth, consequence dialogue, enabled review, and semantic re-entry. |
| `strategic-decision-agenda.md` | Limits remaining user-owned choices to six staged consequence questions and assigns preparation obligations to agents. |

## 3. Analysis

### 3.1 Keep the phase model

| Phase | User-guided, agent-assisted semantic work | Mechanical support owned by code |
|---|---|---|
| Specification | Intent reflection, shared outcome shaping, consequence-led constraint discussion, acceptance storyboards, and strategy narratives use the depth and review gates in `graduated-semantic-collaboration.md` | IDs, schema, reference integrity, ownership coverage, graph legality, digesting, admission transaction |
| Planning | Agents lead repository grounding and detailed strategy; users guide material priorities and review packet consequences, behavioral meaning, exclusions, and irreversible choices rather than technical traces | Execution identity, inherited context expansion, allowed-reference checks, dependency validation, currentness, job allocation, publication transaction |
| Build | Implementation, proportionate tests/docs/migration, local tradeoffs, repair of reviewer findings | Claim/lease enforcement, diff capture, command execution records, receipt construction |
| Acceptance | Independent interpretation of node intent, adversarial proof, finding classification | Exact checkout, evidence collection, predecessor/currentness validation, immutable receipt publication |
| Audit | Independent whole-product workflow and intent-compliance judgment | Exact checkout, completeness queries, evidence linking, closure transaction |

### 3.2 Plan content disposition

| Content | Disposition | Reason |
|---|---|---|
| Packet outcome and why this boundary exists | **Keep** | Carries implementation intent and makes decomposition reviewable. |
| Implementation approach, key invariants, and meaningful tradeoffs | **Keep** | This is the planner's highest-value repository-grounded reasoning. |
| Packet DAG and dependency rationale | **Keep** | Ordering can be valid mechanically but still be a poor implementation design. |
| Required durable outputs | **Keep** | Prevents code-only completion and late discovery of docs, clients, fixtures, or migration. |
| Local in-scope work and non-obvious exclusions | **Keep** | Defines the implementation contract and forbidden shortcuts. |
| Detailed, discriminating packet acceptance scenarios | **Keep** | Gives builders, reviewers, and acceptors a shared observable target. |
| Proof strategy and focused execution recipe | **Keep** | Selection of meaningful evidence is semantic work. |
| Risks, uncertainties, and Specification re-entry triggers | **Keep** | Makes uncertainty and authority boundaries explicit. |
| Packet allocation across obligations, interfaces, and risks | **Keep selected scope** | The planner explicitly assigns and explains packet responsibility; code expands inherited context without replacing that choice. |
| Global policy exclusions repeated in each packet | **Drop from packet prose** | Enforce once in planner policy and validation; retain only local exceptions. |
| One repeated packet AC for each unchanged node obligation | **Drop** | Inherit high-level node acceptance; add packet ACs only for implementation-specific discrimination. |
| Canonical proof method copied verbatim into every plan | **Compress** | Reference the proof contract and record focused additions or justified substitutions. |
| Candidate revision, generation, predecessor IDs, and downstream job IDs | **Derive** | These are lifecycle identity, not planner judgment. |
| Allowed authority-target expansion | **Derive** | Compute from the node, selected allocation, and predecessor contracts. |
| Semantic authority scope | **Keep selected/consumed/excluded scope** | The planner records meaningful authority choices and predecessor-coverage rationale; code compiles the exhaustive canonical target set. |
| Path impact closure | **Keep, tool-assisted** | Invalidating proof by changed path needs an explicit reviewed boundary; tools should propose and normalize it. |
| Identical packet and top-level impact closures | **Derive union** | The node closure is a deterministic union, not a second authored list. |
| Domain, capability, and context envelope | **Keep, advisory** | Feasibility and expected live/tracked scope are semantic; code may suggest tools, skills, and file counts. |
| Full prose for successful mechanical review rows | **Drop** | Store validator results and only explain warnings, failures, and non-obvious semantic passes. |
| Raw reviewer transcript and iteration history | **Evidence only** | Retain for audit without making it current plan authority or normal UI content. |
| Receipt payload, digest, timestamp, replay, and currentness facts | **Generated evidence** | These certify work already done and must not be planner-authored predictions. |

### 3.3 Two-level acceptance

Specification owns high-level node acceptance: the externally meaningful outcome, important failure
behavior, and proof boundary. Planning inherits it and adds only implementation-specific scenarios
that discriminate the chosen packet strategy. The engine generates a coverage projection linking
node obligations to inherited node acceptance and packet-specific acceptance.

A planner may refine an inherited scenario, but may not weaken or silently replace it. A gap in the
high-level outcome returns to Specification. A detailed scenario needed only because of the chosen
implementation remains in the packet plan.

### 3.4 Two-level review

Run deterministic validation first for schema, IDs, references, acyclicity, inherited coverage,
canonical paths, lifecycle identity, and publication legality. Do not ask a language model to narrate
those checks.

Then require an independent agent to review:

1. intent, Product Promise, and value fidelity;
2. technically-done-but-wrong outcomes and rejected-alternative regression;
3. packet cohesion, implementation approach, allocation, and dependency rationale;
4. legal refinement inside admitted authority and correct Specification re-entry;
5. acceptance-scenario quality, obligation coverage, and proof-to-outcome alignment;
6. local scope, exclusions, predecessor coverage, and hidden material expansion; and
7. feasibility, uncertainty, capabilities, and context risk.

The plan stores the semantic disposition, concise rationale, and actionable findings. Full reasoning
and superseded review attempts remain evidence. Review must have a bounded convergence policy, but
the exact repair budget remains an explicit decision below.

### 3.5 Human-facing projection

Cockpit should default to: outcome, rationale, approach, packets, acceptance, risks, review findings,
and current status. Inherited contracts should be expandable links. Paths, IDs, digests, attempts,
raw receipts, and review transcripts remain available under technical or evidence detail.

## 4. Proposed Target Plan Shape

```yaml
summary: <why this plan is the right implementation of the node>
rationale: [<key choices, tradeoffs, and rejected alternatives>]
packets:
  - id: <stable packet identity>
    outcome: <coherent implementation result>
    approach: [<key implementation choices and invariants>]
    allocation: {owns: [], consumes: [], excludes: []}
    scope: [<local work>]
    exclusions: [<non-obvious local exclusions>]
    required_outputs: [{output: <durable result>, producer: <role>, evidence: <path>}]
    dependencies: [{packet: <ID>, reason: <semantic ordering reason>}]
    acceptance: [{id: <AC-ID>, covers: [<authority IDs>], scenario: <observable result>}]
    proof:
      contract: <PROOF-ID>
      builder_actions: [<commands or observations owned during implementation>]
      acceptance_observations: [<independent read-only evidence>]
    impact: {paths: [], predecessor_coverage: <rationale when relevant>}
    risks: [<packet-specific uncertainty or re-entry trigger>]
    profile: {domain: <context>, capabilities: [], envelope: <expected scope>}
    recovery: <bounded explanation of choices a resumed agent must not rediscover>
review: {disposition: <pass|warning|error>, rationale: <concise>, findings: []}
collaboration_review: {layer: <acceptance|strategy>, consequence_summary: <meaning>, user_guidance: [], status: <state>}
```

The lifecycle envelope supplies candidate revision, generation, predecessor identities, inherited
contracts, canonical expansion of explicitly selected authority, node closure, downstream job
identities, and receipt fields. It must not erase the planner's allocation or rationale.

## 5. Implementation Plan

- [ ] D0. Apply `inherited-decision-framing-audit.md`; retain only choices revalidated against credible open alternatives or explicitly delegated as engineering decisions.
- [x] D1. Define graduated collaboration and enabled-review methods in `graduated-semantic-collaboration.md`.
- [ ] D2. Work through user-owned S1-S6 in `strategic-decision-agenda.md`, one evidence-prepared consequence discussion at a time.
- [ ] D3. Derive field classification and acceptance storage after S1 and S5; independently review the engineering result.
- [ ] D4. Derive packet allocation references and lifecycle expansion from reviewed semantic authority.
- [ ] D5. Derive exact review and retry budgets from S2 interaction priorities and S3 assurance appetite.
- [ ] D6. Derive evidence retention and Cockpit defaults from S5 transparency and S6 cutover constraints.
- [ ] I1. Amend intent/design/decisions only after D1-D6 are resolved; create one new semantic digest intentionally.
- [ ] I2. Define versioned target plan, review, and generated lifecycle-envelope schemas.
- [ ] I3. Build a deterministic plan compiler/validator for inherited context, coverage, closures, IDs, and publication inputs.
- [ ] I4. Rewrite planner and challenger contracts around semantic planning and review responsibilities.
- [ ] I5. Make receipts compact generated attestations with links to durable evidence rather than repeated plan prose.
- [ ] I6. Add Cockpit summary, inherited-contract drill-down, semantic findings, and technical evidence views.
- [ ] I7. Migrate one representative simple node and DN-003; compare information preservation, review quality, and effort.
- [ ] I8. Test reconciliation, corrective planning, verification-only planning, interruption resume, and exact-commit acceptance.
- [ ] I9. Migrate remaining current plans without rewriting immutable historical attempts or receipts.
- [ ] I10. Run independent whole-change review against the Product Promise before admitting the redesign.

### Completion checks

- [ ] A resumed agent can recover intent, strategy, constraints, acceptance, and unresolved risk without chat history.
- [ ] A reviewer can detect value erosion, hidden expansion, weak proof, and poor packet boundaries.
- [ ] No semantic field is removed without a named remaining owner or generated projection.
- [ ] Mechanical lineage is reproducible from authority and runtime identity without agent-authored duplication.
- [ ] Cockpit presents semantic meaning first and preserves full technical evidence on demand.
- [ ] Representative plans retain useful depth without repeating inherited contracts or successful mechanical checks.

## 6. Recommendation, Confidence, And Limits

**Recommendation:** Preserve the current phase boundaries and use graduated collaboration rather than
one universal approval gate. Redefine the planner's draft as a rich implementation contract plus
detailed discriminating acceptance; expose consequence-level review to the user and technical depth
to agents, then compile reviewed meaning with engine-owned lifecycle context into executable work.

**Confidence:** High that this addresses the observed churn without discarding the system's valuable
agent reasoning. Medium on the exact target schema until D2-D5 are discussed against at least one
simple node and DN-003.

**Limits:** This document does not authorize authority edits, schema migration, lifecycle publication,
or implementation. It intentionally leaves material choices visible rather than selecting them from
the audit alone. The 200-line repository limit applies to each research note, not to total analysis;
focused decision notes should be linked when a question needs more room.