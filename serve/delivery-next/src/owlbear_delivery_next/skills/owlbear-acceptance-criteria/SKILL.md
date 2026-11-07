---
name: owlbear-acceptance-criteria
description: "Acceptance criteria that can be checked, and how a change is proven: existing tests plus one real run"
user-invocable: false
---

# Acceptance Criteria and Proof

Every criterion must be checkable by someone who cannot ask its author what was meant. Use this to
write or judge a criterion, and to choose the proof that shows it is met.

## Proof

A change is proven by the existing tests plus one real run of the changed behaviour: the command, the
endpoint, one browser look at each page where something becomes visible. One run may cover several
criteria. Say what that leaves unproven.

A check that ran before the commit under review, or against a later changed worktree, does not prove
that commit.

For startup and side-effect claims, a zero exit status is not a positive result by itself. Name the
observable signal that shows the boundary ran: a recognized startup marker, a non-empty emitted
artifact, a persisted record, or an observed state change. Empty output, skipped checks, and the
absence of an error are not enough when the criterion claims that something started, emitted,
persisted, or changed.

A reviewer judges the exact commit and its claimed boundary, not the builder's summary.

A defect fix's real run shows the defect gone where it appeared. A bug that came back gets its new test,
which fails on the commit before the fix and passes on the fix.

## New Tests

Proof is not automatically a durable test. A search, diff, lint, type check or build supports the proof without
becoming a committed test. A test that only confirms that text, a file or a symbol exists or is gone
freezes the change instead of protecting behaviour.

- Add a new test only for a bug that came back, or one per new security or data-loss boundary, at that
  boundary; no case matrix.
- Assertions test behaviour, not implementation: meaningful input through the boundary callers use, and an
  observable output, state, error or side effect. Ask which plausible regression would make the test fail;
  without an answer, choose another proof.

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
