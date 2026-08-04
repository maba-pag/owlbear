---
name: h-ac-quality
description: "Handbook: Two-tier acceptance-scenario quality for native planning and review"
user-invocable: false
---

# AC Quality Schema

Single authority for writing and validating acceptance scenarios in native Specification and Delivery.

## Meta-Rule

Every AC line must be independently verifiable by a downstream agent without access to the author's intent.

## Tier 1 - Behavior AC (Code Changes)

Use Tier 1 for requirements that change runtime behavior, interfaces, or outputs.

### B1 - Boundary-Scoped

Each AC line names one observable boundary or maintained artifact under test, such as a public
function, endpoint, command, user workflow, rendered surface, persisted record, schema, or generated
output.

- Reject: AC line references only a feature area with no observable boundary.
- Reject: AC line requires a private implementation detail when the requested behavior is observable
  through a public boundary.
- Pass: AC line identifies the public surface or durable artifact where pass or fail is observed.

### B2 - Input -> Output Pairs

Each AC line states a concrete input condition and a concrete observable output.

- Input: parameters, payload, flags, precondition state, or triggering event.
- Output: return value, error type, emitted event, persisted artifact, or visible status transition.

### B3 - No Naked Quantifiers

AC lines must not use ambiguous quantifier or quality words without exhaustive enumeration.

Banned words (7):

- all
- every
- correctly
- properly
- exactly
- valid
- appropriate

Allowed exception: a banned word may appear only when followed by exhaustive enumeration that makes pass or fail mechanically decidable.

### B4 - Boundary-Valid Proof

When an AC claims integration, command, endpoint, generated-operation, assembled-context, or user
journey behavior, it names the normal assembled boundary under test and the observable result at
that boundary.

- A mock or injected dependency may replace only a layer below the boundary being proved.
- An injected completed workflow cannot prove CLI registration or application assembly.
- A mocked generated-tool caller cannot prove operation naming or context visibility.
- A fixture may prove normalization behavior only when its shape is grounded in the named contract
  authority.

Reject an AC whose proposed evidence bypasses the callable, command, workflow, or assembled context
that the AC claims works.

## Tier 2 - Process AC (Workflow Changes)

Use Tier 2 for requirements that change agent behavior, lifecycle transitions, or Delivery policy.

### P1 - Agent/Stage-Scoped

Each AC line explicitly names the responsible agent, skill, engine operation, or delivery phase.

- Reject: "The work should be advanced with evidence."
- Pass: "Given an advisory-reviewed Planning claim, `publish_delivery_plan` returns one claim-bound task-chain candidate."

### P2 - Observable Artifact or State Change

Each AC line describes a before -> after difference in an inspectable artifact or native graph state.

- Artifact examples: plan record, receipt, finding, request, file, or populated field.
- State examples: job transition, dependency readiness, invalidation, or change closure.

### P3 - Verification Method Stated

Each AC line states how downstream agents verify completion.

Allowed methods:

- artifact inspection
- lifecycle-transition audit
- field-presence check
- diff comparison
- tool or API query
- command output

## Ordered Validation

Run the mechanical pass before semantic review:

| Pass | Rule | Check |
|------|------|-------|
| Mechanical | B3 | The seven banned words are absent unless exhaustively enumerated. |
| Mechanical | P1 | Every Tier 2 line contains an agent, skill, or stage token. |
| Mechanical | Literal authority | Enum values, transitions, design tokens, props, events, flags, commands, and fields match the strongest canonical source. |
| Mechanical | Numbering | AC numbering is present, stable, and unambiguous. |
| Semantic | B1 / P1 | The line has one observable boundary or maintained artifact and, for process AC, names its responsible agent, skill, or stage. |
| Semantic | B2 | Behavior AC states a concrete input and observable output. |
| Semantic | P2 | Process AC states an inspectable artifact or graph-state delta. |
| Semantic | P3 | Process AC states an explicit verification method. |
| Semantic | Meta-rule | The line is independently verifiable, has objective pass/fail evidence, and contains no hidden assumptions requiring author interpretation. |
| Semantic | B4 | Cross-boundary AC names the normal assembled boundary and replaces only lower dependencies in proof. |
| Semantic | Literal authority | The strongest applicable authority is cited or recorded; unresolved contradictions block planning or admission. |

A mechanical failure requires rewriting before semantic review. For a semantic failure, clarify the
scope, input, output, or verification method and give bad -> good rewrite guidance.

## Bad -> Good Transformations

| Rule | Bad | Good |
|------|-----|------|
| B1 | "System handles planning." | "Given a current Planning claim and complete tasks, `publish_delivery_plan` returns a candidate bound to that claim and task chain." |
| B2 | "When work is stale, the API responds with an error." | "Given a stale claim ID, `publish_delivery_plan` returns `ERR_DELIVERY_RUNTIME_CONFLICT` and creates no candidate." |
| B3 | "Reviewer checks every scenario correctly." | "Plan review returns one evidenced row for packet completeness, admitted references, impact closure, dependency order, proof boundary, and material expansion." |
| B4 | "Given an injected workflow runner, the CLI command returns JSON." | "Given the real CLI application with remote HTTP transport replaced, invoking `alerts prepare` resolves normal configuration, crosses the assembled workflow boundary, and writes one JSON document to stdout." |
| P1 | "Add validation before Delivery." | "Designer runs deterministic validation and complete source-grounded challenge before requesting admission approval." |
| P2 | "The plan should be prepared." | "The plan claim returns one bounded task set, explicit dependencies, and maintained-boundary proof for independent review." |
| P3 | "Review confirms completion." | "Build review compares the exact candidate commit, admitted task claim, complete diff, and focused proof before returning one typed disposition." |

## Canonical Literal Verification

Use this when AC lines cite concrete literals that must match source-of-truth tokens.

### Bad -> Good Examples

1. Enum or union literal

- Bad: "The endpoint accepts every valid order status."
- Good: "POST /orders accepts the `OrderStatus` literals declared by the project schema:
  `pending | paid | cancelled`; any other status returns HTTP 422."

2. Design token

- Bad: "Use standard medium spacing for card gaps."
- Good: "The result grid uses the project's canonical medium-spacing token, identified in Shape
  authority, for its column and row gaps."

3. Command choice

- Bad: "The export command supports the appropriate output formats."
- Good: "`export --format` accepts the parser-declared literals `json | csv`; `xml` exits non-zero
  and names the accepted values."

4. OwlBear native lifecycle transition

- Bad: "Orchestrator moves work to the next valid phase."
- Good: "After Planner returns `AdvanceDelivery`, Orchestrator forwards the unchanged transition to
  `transition_delivery`, then refreshes acquisition."

### Authority Discovery

Locate the strongest authority available in the target project. Prefer sources in this order:

| Order | Authority | Suitable claims |
|----------|-----------|-----------------|
| 1 | Checked-in schema, type, configuration, or public source declaration | Allowed literals, fields, transitions, tokens, defaults |
| 2 | Generated public inventory, command tree, API schema, or compiled contract | Registered operations and assembled public surface |
| 3 | Installed dependency types, schema, or package metadata | External component props, events, and supported values |
| 4 | Version-matched official external documentation | Contracts not represented locally |
| 5 | Bounded verified runtime observation | Only the observed request, response, state, or environment |

Do not use a test fixture, stale planning document, or paraphrased UI label as canonical when a
stronger authority exists. A sampled production envelope does not prove unobserved variants.

### Review Procedure

1. Identify each literal claim in the AC line: enum value, transition, token, prop, event, flag,
   command choice, field name, or generated operation.
2. Discover the strongest applicable authority using the priority table.
3. Confirm spelling, allowed values, version, and relevant constraints through targeted source or
   structured contract inspection.
4. Record the authority and evidence scope in the node plan or review evidence when it is not already
  obvious from the acceptance scenario.
5. Compare the AC wording with the authority; treat invented aliases and unsupported values as
   contradictions, not harmless paraphrases.
6. Rewrite the AC with the verified literals. If two credible authorities disagree, record the
  contradiction and return the owning workflow's blocked or Specification re-entry disposition;
  do not choose silently.
