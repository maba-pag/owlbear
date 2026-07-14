---
name: w-spec-shaping
description: "Workflow: Review an OpenSpec change with the user, resolve its implementation design, and create an approved Kanban graph"
user-invocable: false
---

# Spec Shaping

Turn an OpenSpec change into implementation work through a user-facing technical review. OpenSpec
artifacts are generated planning input, not evidence that the user understands or approves the
implementation design. The shaper owns the bridge from that input to Kanban.

## Companion Skills

Load these via `read_file` when needed:

| Skill | Load when |
|-------|-----------|
| `w-task-decomposition` | Drafting and committing the task graph |
| `w-research` | Local evidence is insufficient to assess a material claim |
| `h-ac-quality` | Drafting or reviewing task acceptance criteria |
| `h-codebase-orientation` | Locating and verifying current owners and interfaces |
| `h-module-design` | Assessing architecture and task boundaries |

## Step 1 - Resolve The Planning Package

Run `openspec status --change <name> --json` and use its resolved paths. Read every existing
Proposal, Spec, Design, and Tasks artifact reported by the CLI. Do not assume stock paths or invoke
another `/opsx:*` command.

Treat the package as an unreviewed technical draft:

- Proposal expresses generated product intent and recorded decisions, but the user may challenge it.
- Specs express generated normative behavior, but the user may correct or supersede it.
- Design expresses a proposed technical plan, not approved architecture.
- Tasks are advisory suggestions only.

Identify contradictions among artifacts before presenting the package as coherent.

If the package records an approved ideation Brief path, read that Brief and use it as additional
product-promise evidence. Do not search unrelated draft directories or assume an unrecorded Brief
relationship. The staged user review remains mandatory either way.

## Step 2 - Ground The Draft

Use `h-codebase-orientation` and `h-module-design` to verify the smallest sufficient current-source
surface. Establish:

- current behavioral owners and public interfaces;
- proposed ownership and interface changes;
- exposed commands, tools, endpoints, schemas, or other user-visible contracts;
- consequential dependencies, migrations, removals, security boundaries, and open facts;
- the normal assembled proof boundary.

Use bounded codebase, documentation, and web research autonomously when it is necessary to assess
the design. Ask before an exceptional-cost investigation, executing external code, or expanding
research materially beyond the change. Write a research document only when the findings have
durable value beyond the shaping conversation.

## Step 3 - Conduct The Staged Implementation Review

Review the implementation with the user before decomposition. Organize the conversation around the
thing being built, not around OpenSpec filenames.

### Stage A - Product And Scope

Explain at moderate depth:

- the user outcome and normal workflow;
- visible failure behavior;
- in-scope work, exclusions, removals, and deferred outcomes;
- any mismatch with the user's stated idea or prior decisions.

### Stage B - Architecture And Interfaces

Explain at high, adaptive depth:

- the current and proposed module ownership;
- important control and data flow;
- changed or new public interfaces;
- exposed command, tool, endpoint, and schema details;
- why the proposed boundaries fit the current system;
- concrete weaknesses and meaningful alternatives.

Do not enumerate every internal function. Go deeper where novelty, coupling, irreversible choices,
or user concern warrant it. Take an opinionated evidence-based position and recommend changes when
the generated design is weak; do not manufacture alternatives when it is sound.

### Stage C - Trade-offs And Completion

Explain proportionally:

- consequential trade-offs, breaking changes, migration, and unresolved facts;
- the normal-path evidence that would demonstrate the implementation;
- what makes the change complete.

Proof mechanics normally need less detail than architecture unless they expose product or delivery
risk.

Use normal prose questions for understanding and follow-up. For a material fork that changes
product behavior, scope, architecture, compatibility, security, or the task graph, present one
decision at a time with status quo, problem, options, trade-offs, recommendation, and expected
outcome through `askQuestions`.

## Step 4 - Reconcile The OpenSpec Artifacts

When the user accepts a material change, update the artifact that owns the changed claim before
drafting tasks:

| Changed claim | Owning artifact |
|---------------|-----------------|
| Product outcome, scope, exclusion, or material user decision | Proposal |
| Normative observable behavior | Spec |
| Architecture, interface, migration, or technical trade-off | Design |
| Advisory implementation suggestion only | Tasks, when retaining it remains useful |

Keep Proposal, Specs, and Design coherent. Do not bury an accepted departure only in Shape Notes or
create a competing Kanban specification. Validate the reconciled change with the OpenSpec CLI before
decomposition.

## Step 5 - Draft And Challenge The Graph

Load `w-task-decomposition` and draft the complete task graph without creating or editing Kanban
tasks. Use provisional task keys until commit. The draft must include:

- outcomes, boundaries, acceptance criteria, and proof guidance;
- dependencies, priorities, tags, and aggregate routing;
- Change Module Map and Product Invariant Map ownership;
- explicit coverage of the complete active Product Promise.

Call `shaper-challenger` on this complete pre-write graph. Supply the reconciled planning package,
readiness evidence, contract authorities, maps, provisional tasks, dependencies, statuses, and full
Product Promise. Resolve correctable findings in the draft. Surface any material challenger finding
that requires a user choice instead of deciding it silently.

## Step 6 - Obtain Graph Approval

Present the hardened graph to the user before board mutation. Show the task outcomes, boundaries,
dependency order, aggregate closure, and any remaining assumption or explicit exclusion. Ask the
user to approve, revise, or stop.

Approval authorizes only the presented graph. If later investigation changes intent, architecture,
acceptance meaning, or the graph materially, return to the relevant review stage and obtain new
approval.

## Step 7 - Commit And Audit The Graph

After approval, use `w-task-decomposition` to create or update the Kanban graph. Replace provisional
keys with concrete task IDs, then audit statuses, parent links, dependencies, acceptance criteria,
and Product Promise coverage. This post-write audit is mechanical; do not introduce substantive
scope after approval.

Record `## Shape Notes` in the aggregate task or existing parent. For a standalone graph, record
them in the created task that represents the approved outcome. Include planning sources,
user-approved decisions, artifact revisions, readiness, contract authorities, maps, final graph,
challenger result, and board audit.

## Step 8 - Return A Human Summary

Summarize for the user:

- what implementation and architecture they approved;
- OpenSpec artifacts changed;
- tasks created or updated and their dependency shape;
- unresolved facts or deliberately deferred work.

Do not use a pipeline verdict as the user interface. Channel B remains the durable board history.

## Commit Gate

Before any Kanban task creation or substantial rewrite, all must be true:

- the staged implementation review is complete;
- material decisions are resolved and written to their owning artifacts;
- the reconciled OpenSpec change validates;
- the complete draft graph has passed shaper-challenger;
- the user approved that graph.

## Known Pitfalls

- **Artifact recital:** Reading Proposal, Specs, Design, and Tasks in order is not a technical review.
- **Diff-only discussion:** The user cannot approve deviations from a design they have not understood.
- **Silent improvement:** Strong evidence does not authorize an unreviewed architecture change.
- **Post-write challenge:** Concrete task IDs do not justify creating the graph before it is challenged.
- **Split authority:** Shape Notes must not silently supersede stale OpenSpec intent, behavior, or design.
