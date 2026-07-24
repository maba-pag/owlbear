---
name: w-idea-refinement
description: "Workflow: Refine a rough idea into proposal-ready shared understanding through an evidence-backed, one-question interview"
user-invocable: false
---

# Idea Refinement

Shape a rough idea into confirmed shared understanding without implementing it or forcing the user
to arrive with a plan. The caller owns the destination and maps the final summary into its planning
system.

## When to Use

Use this workflow when an idea, plan, or design is not yet concrete enough for its planning
destination.

Do not use it when:

- the idea is already concrete enough for its planning destination;
- the user wants broad divergent exploration rather than convergence;
- implementation must begin to obtain evidence; use research or a bounded prototype first;
- only harmless implementation details remain for the implementer.

## Core Method

1. **Interview toward shared understanding.** Explore every material aspect of the idea, following
   dependencies between questions instead of walking a generic checklist.
2. **Ask one question at a time.** Wait for the user's answer before continuing. Never bundle a
   questionnaire into one turn.
3. **Recommend an answer.** Do not make the user solve an unframed problem. State the answer that
   currently looks best and why; the user may correct or replace it.
4. **Look up facts; ask about intent.** Investigate repository-answerable facts. Put genuine
   product, scope, behavior, risk, and trade-off choices to the user.
5. **Do not invent decisions.** Most refinement questions clarify the idea. Compare options only
   when materially different choices actually exist.
6. **Preserve the full promise.** Identify the concrete effects that make the idea worth using. Do
   not ask what can arrive first merely to shrink the proposal. If a user-stated outcome may be
   excluded or reduced, present that as a real scope choice and require explicit agreement.
7. **Do not enact the idea.** Stop at confirmed understanding. Do not create code, tasks, or
   destination-specific artifacts unless the caller owns that later step.

## Step 1 - Establish the Rough Idea

Restate the starting point in two to four sentences without pretending it is already a plan:

- what the user wants to exist or become easier;
- who appears to benefit;
- what prompted the idea;
- what is known versus still vague.

Build a private, dependency-ordered question tree from the idea. Potential branches include user
value, workflow, behavior, boundaries, constraints, failure handling, and success. Include only
branches whose answers could materially change the proposal. Do not display the tree.

## Step 2 - Investigate Before Asking

Before each question, inspect the smallest relevant source boundary. Classify load-bearing claims:

| Class | Meaning | Treatment |
|-------|---------|-----------|
| Observed | Verified in source, runtime output, or current behavior | State the evidence briefly |
| Documented | Stated by a controlling document or external contract | Name the authority |
| Assumed | Plausible but not verified | Label it and expose the consequence |
| Confirmed | Explicitly established with the user | Preserve until explicitly changed |

If evidence answers the question, incorporate it into the working understanding and continue to the
next genuine gap. Never poll the user for repository facts.

## Step 3 - Ask the Next Refinement Question

Choose the unresolved question with the highest downstream leverage. A useful question clarifies at
least one of:

- why the idea is worth implementing and for whom;
- which concrete behavior or effect makes the result worth using;
- the normal invocation or operating path;
- observable behavior or result;
- scope boundaries and preserved behavior;
- a constraint or risk that changes the viable shape;
- what success looks like through the assembled workflow.

Use a lightweight Refinement Turn:

```markdown
### Refinement: <one precise question>

**Current understanding:** <what the idea and evidence establish so far>

**Why this matters:** <what this answer changes or unlocks>

**Recommended answer:** <the best current answer and concise reasoning>

<Ask exactly one question.>
```

When genuine alternatives have materially different consequences, expand the same turn with two to
four options and their benefits, costs, risks, and confidence. Do not create an options table for a
simple clarification, and do not pad it with weak choices.

Do not introduce a smaller first delivery as a routine refinement question. This workflow defines
the complete proposed change. State the lost value of any option that weakens a requested outcome,
and record the exclusion only after explicit user acceptance. Call omitted work "deferred" only
when it has a durable destination outside the proposal.

After asking, stop. Wait for the answer before following another branch.

## Step 4 - Update the Working Understanding

After each answer:

1. restate and record the clarification or choice;
2. update dependent questions;
3. surface contradictions;
4. ask before replacing a prior user choice.

Ambiguous answers are not confirmation. Narrow the same branch with the next single Refinement Turn.

## Proposal-Readiness Gate

The idea is refined enough only when:

- the intended outcome and beneficiary are concrete;
- the behaviors or effects that make the result worth using are concrete;
- the normal workflow and observable result are understandable;
- scope boundaries and preserved behavior are explicit where material;
- every reduction of a user-stated outcome is explicitly accepted;
- repository facts have been investigated;
- genuine user-owned choices are confirmed or explicitly deferred;
- assumptions are labeled with an owner or consequence;
- success can be observed through a normal assembled workflow;
- plausible technically-correct-but-wrong outcomes are named;
- no active understanding contradicts another part of the idea.

Present a compact recap and ask one final question: whether it matches the user's idea and is ready
for the caller's planning destination. If the user identifies a gap, resume the relevant branch.

## Refined Idea Summary

After confirmation, produce this summary. Omit a section only when it is genuinely not applicable.

```markdown
## Refined Idea Summary

### Idea and Intended Outcome
<The starting idea, beneficiary, and full promised end state.>

### User Value
- Worth using because: <concrete behavior, interaction, or product effect>
- Active product promise: <the complete outcome represented by this proposal>

### Normal Workflow
<Concrete invocation or operating path and observable result.>

### Boundaries
- In scope: ...
- Out of scope: ...
- Preserved behavior: ...
- Accepted exclusions: <only user-approved reductions of an originally stated outcome, or none>

### Confirmed Refinements and Choices
- <clarification or choice, its basis, and any accepted trade-off>

### Evidence and Assumptions
- Observed: ...
- Documented: ...
- Assumed: ...; owner/consequence: ...

### Success and Proof
- Observable success: ...
- Normal assembled proof boundary: ...

### Technically Done but Wrong
- ...

### Open Facts and Accepted Exclusions
- ...
```

The summary is a communication contract, not a new persistent artifact or a disguised specification.
The caller decides how to use it.

## Examples

**Good:** Source inspection establishes that alerts are synchronous. The workflow recommends a
concrete interpretation of useful action, asks one timing question, and waits.

**Bad:** The first response asks the user to choose queues, retries, webhooks, storage, and UI layout.
This invents a design before the idea's outcome and normal workflow are understood.

## Known Pitfalls

- **Fictional plan:** do not imply settled scope.
- **Low-leverage interrogation:** ask only what sharpens the proposal.
- **Fact polling:** investigate repository behavior.
- **Decision theater:** compare only genuine alternatives.
- **Premature convergence:** use the readiness gate.
- **Disappearing remainder:** require explicit exclusions.
- **Destination leakage:** leave planning mechanics to the caller.
- **Chat-only understanding:** finish with the confirmed Refined Idea Summary.
