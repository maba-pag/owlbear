---
name: owlbear-acceptance
description: "Acceptance criteria that can be checked, and the cheapest proof that can falsify each one"
user-invocable: false
---

# Acceptance Criteria and Proof

Every criterion must be checkable by someone who cannot ask its author what was meant. Use this to
write or judge a criterion, and to choose the proof that shows it is met.

## Proof Selection

Choose the cheapest proof that can falsify the boundary the criterion names. Escalate when the claim
crosses an assembly or user-facing boundary:

| Claimed boundary | Preferred proof |
| --- | --- |
| Pure logic, state transition, serialization, or supported component interaction | Focused public-function or component test |
| Assembled command, endpoint, generated operation, or workflow | Integration test or the real assembled boundary, with dependencies replaced only below it |
| Browser journey, layout, focus, geometry, or viewport behavior | A real-browser proof |
| Startup, persistence, emitted side effect, publication, or visible status change | A command or procedure with a positive marker, artifact, or observed state change in addition to its exit status |

A check that ran before the commit under review, or against a later changed worktree, does not prove
that commit.

For startup and side-effect claims, a zero exit status is not a positive result by itself. Name the
observable signal that shows the boundary ran: a recognized startup marker, a non-empty emitted
artifact, a persisted record, or an observed state change. Empty output, skipped checks, and the
absence of an error are not enough when the criterion claims that something started, emitted,
persisted, or changed.

A reviewer judges the exact commit and its claimed boundary, not the builder's summary.

## Rules for a Criterion

### C1 - One Observable Boundary

Each criterion names one observable boundary or maintained artifact: a public function, endpoint,
command, user workflow, rendered page, persisted record, schema, or generated output.

- Reject: a criterion that names only a feature area.
- Reject: a criterion that requires a private implementation detail when the behavior is observable
  through a public boundary.
- Pass: the criterion names where pass or fail is observed.

### C2 - Input and Output

Each criterion states a concrete input condition and a concrete observable output.

- Input: parameters, payload, flags, precondition state, or triggering event.
- Output: return value, error, emitted event, persisted artifact, or visible status change.

### C3 - No Naked Quantifiers

A criterion does not use these words without an exhaustive list that makes pass or fail mechanical:
all, every, correctly, properly, exactly, valid, appropriate.

### C4 - Proof at the Claimed Boundary

When a criterion claims integration, command, endpoint, generated-operation or user-journey
behavior, its proof crosses that assembled boundary and observes the result there.

- A mock or injected dependency may replace only a layer below the boundary being proved.
- An injected completed workflow cannot prove command registration or application assembly.
- A fixture proves normalization only when its shape comes from the named contract's source.

### C5 - Literals From Their Source

Enum values, tokens, props, events, flags, commands and field names in a criterion match the
strongest source in the project, in this order: a checked-in schema, type, configuration or public
declaration; a generated inventory, command tree or API schema; installed dependency types or
package metadata; version-matched official documentation; a bounded runtime observation. A test
fixture or a paraphrased UI label is not that source when a stronger one exists. Treat an invented
alias or an unsupported value as a contradiction, not a paraphrase.

## Bad and Good

| Rule | Bad | Good |
| --- | --- | --- |
| C1 | "The system handles exports." | "`export --format csv` writes one CSV file with a header row to the path given by `--out`." |
| C2 | "Stale input gives an error." | "Given an order id that does not exist, `GET /orders/{id}` returns HTTP 404 and changes nothing." |
| C3 | "Every status is handled correctly." | "POST /orders accepts `pending`, `paid` and `cancelled`; any other status returns HTTP 422." |
| C4 | "Given an injected workflow runner, the command prints JSON." | "The real command, with only its remote HTTP calls replaced, prints one JSON document to stdout." |
| C5 | "Use the standard medium spacing." | "The result grid uses the project's `spacing-medium` token for its column and row gaps." |
