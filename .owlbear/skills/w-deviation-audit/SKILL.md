---
name: w-deviation-audit
description: "Workflow: Classify selected process deviations and route evidence-backed follow-up"
user-invocable: false
---

# Deviation Audit

Review selected process-observation sidecars and decide which existing authority should own any
follow-up. This workflow is report-only. It classifies evidence; it does not edit files, create
Delivery work, mutate lifecycle state, or make a process observation authoritative.

## Boundary

- Read only the observations and evidence needed for the supplied bounded scope.
- Never treat a sidecar as proof of implementation, acceptance, publication, or a Delivery
  transition.
- Never resolve a deviation by editing code, tests, skills, instructions, prompts, hooks, runtime
  state, or the research worklist during this audit.
- Route a proposed change to its owning workflow and require that workflow's normal approval and
  evidence boundary.
- Keep facts, interpretation, placement, and confidence distinct.

## Step 1 - Resolve The Scope

Require one or more explicit observation paths, Change/task/result identities, or a bounded review
scope. Default to one observation. Do not scan session history, all research, or all completed work
unless the user explicitly supplies that bounded scope. If no target is supplied, ask one concise
question before reading.

Read `h-process-observations` before interpreting a sidecar. Confirm that each selected note has the
available Change or task/finalization identity, trigger, observer, time, evidence locators, and
follow-up disposition. A missing or temporary note is an evidence gap, not permission to infer its
contents.

Record `git status --short` before the first terminal command and confirm it is unchanged at close.
Use read-only inspection only; do not run generators, formatters, fixes, or commands that update
snapshots or other workspace state.

## Step 2 - Reconstruct The Evidence Boundary

Inspect only the referenced local artifacts and source needed to test the observation. Bind the
review to the exact Change, task, result, finalization, or commit named by the note when available.
Separate:

- `observed`: directly present in a receipt, review, transition, source file, test, command result,
  or named locator;
- `documented`: stated by a current authority but not independently observed in this review;
- `inferred`: a bounded interpretation that still needs confirmation.

If an exact identity, locator, or reviewer boundary cannot be checked, record the limitation and
lower confidence. Do not reconstruct missing evidence from conversation history or a similar task.

## Step 3 - Classify The Owning Surface

Choose the smallest existing owner that can change the observed outcome:

| Signal | Candidate owner | Route |
| --- | --- | --- |
| Product or implementation behavior is wrong | Source owner and native Delivery | Design or Planning, then bounded Build |
| A durable regression is missing or proof is weak | Domain test owner and `w-test-curation` | Test-curation or native Delivery |
| Task boundary, plan, or accepted intent is incomplete | Design or Planning authority | Return through the owning Delivery stage |
| Reusable agent guidance is missing or contradictory | `share/` or `.owlbear/` skill, instruction, or prompt owner | Agent-ecosystem implementation after approval |
| A deterministic guarantee is absent | Hook, validator, schema, or runtime owner | Owner-specific implementation and proof |
| Loading, routing, or entry-point behavior is wrong | Prompt, agent, skill, or wiring owner | Agent-ecosystem implementation after approval |
| No recurring or material problem is evidenced | No change | Preserve the observation and stop |

Do not promote a process preference into an authority change. A one-off workaround, a completed
task with no trigger, or a report that merely restates a receipt is not sufficient by itself.

## Step 4 - Decide The Follow-Up

For each selected observation, state whether the evidence supports `no-change`, `research`,
`test-curation`, `design`, `planning`, `implementation`, or `agent-ecosystem` follow-up. Explain
why the selected owner is smaller and more authoritative than the alternatives. Record recurrence,
impact, privacy considerations, and confidence. A proposed follow-up is advisory and does not
authorize its own implementation.

## Output Template

Return:

```markdown
## Deviation Audit

- Scope: {selected observation path or bounded identity}
- Evidence boundary: {files, receipts, reviews, or commands inspected}
- Worktree status: {unchanged | bounded read-only failure}

| Observation | Placement | Evidence | Owner and route | Action | Confidence |
| --- | --- | --- | --- | --- | --- |
| {short identity} | {code | test | design | planning | skill | instruction | prompt | hook/runtime | no-change} | {observed | documented | inferred; locators} | {owner; native next workflow} | {bounded recommendation} | {high | medium | low} |

### Limits

- {unverified identity, missing locator, privacy exclusion, or other evidence boundary}

### Authority Boundary

No files, Delivery state, receipts, prompts, skills, hooks, or runtime records were changed by this
audit.
```

## Known Pitfalls

- **Wrong owner:** classify the smallest authority that can change the outcome; do not route every
  deviation to agent guidance.
- **Duplicate code review:** use exact implementation or test review for product correctness; use
  this workflow for the process-placement question.
- **Speculative evolution:** require a concrete trigger or recurring evidence before proposing a new
  rule or workflow.
- **Evidence substitution:** a process observation explains deviation but never replaces a receipt,
  review, test, hook, schema, or Delivery transition.
