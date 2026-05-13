---
name: h-ac-quality
description: "Handbook: Unified two-tier acceptance-criteria quality schema for planner drafting and architect/challenger validation"
user-invocable: false
---

# AC Quality Schema

Single authority for writing and validating acceptance criteria (AC) lines in the pipeline.

## Meta-Rule

Every AC line must be independently verifiable by a downstream agent without access to the author's intent.

## Tier 1 - Behavior AC (Code Changes)

Use Tier 1 for requirements that change runtime behavior, interfaces, or outputs.

### B1 - Function-Scoped

Each AC line names the concrete target under test (function, endpoint, command, class method, or module entrypoint).

- Reject: AC line references only a feature area with no executable target.
- Pass: AC line identifies one concrete callable or endpoint name.

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

## Tier 2 - Process AC (Workflow Changes)

Use Tier 2 for requirements that change agent behavior, stage transitions, or pipeline policy.

### P1 - Agent/Stage-Scoped

Each AC line explicitly names the responsible agent, skill, or pipeline stage.

- Reject: "The task should be advanced with notes."
- Pass: "Builder appends Builder Notes and advances in-progress -> review."

### P2 - Observable Artifact or State Change

Each AC line describes a before -> after difference in an inspectable artifact or board state.

- Artifact examples: task body section, file created, field populated, section header present.
- State examples: status transition, dependency link created, tag or priority changed.

### P3 - Verification Method Stated

Each AC line states how downstream agents verify completion.

Allowed methods:

- artifact inspection
- stage-transition audit
- field-presence check
- diff comparison

## Two-Pass Validation

Run validation in order:

1. Mechanical lint pass

- Check B3 banned words are absent unless exhaustively enumerated.
- Check P1 agent/stage token is present for Tier 2 lines.
- Check AC numbering is present and stable.

2. Semantic review pass

- Confirm each line has sufficient detail for independent verification.
- Confirm scope is not split across multiple hidden assumptions.
- Confirm pass/fail is objective and does not require author interpretation.

Mechanical pass failing means rewrite before semantic review. Semantic failure means clarify scope, inputs, outputs, or verification method.

## Bad -> Good Transformations

### B1 Example (Function-Scoped)

- Bad: "System handles archival requests."
- Good: "POST /api/tasks/{id}/release records archival_reason in the archived task metadata."

### B2 Example (Input -> Output)

- Bad: "When a task is blocked, the API responds with an error."
- Good: "Given task_id=42 with blocked=true, GET /api/tasks/42 returns HTTP 423 with error.code='TASK_BLOCKED'."

### B3 Example (No Naked Quantifiers)

- Bad: "Reviewer checks all AC lines correctly."
- Good: "Reviewer checks AC-1 through AC-4 and records one evidence row per AC line in Review Evidence."

### P1 Example (Agent/Stage-Scoped)

- Bad: "Add validation before moving tasks."
- Good: "Architect validates AC quality in backlog before moving task backlog -> todo."

### P2 Example (Observable Artifact/State)

- Bad: "Planner should prepare decomposition output."
- Good: "Planner creates one backlog follow-up task with depends_on set to the parent implementation task IDs."

### P3 Example (Verification Method)

- Bad: "Auditor confirms the handoff is complete."
- Good: "Auditor verifies handoff completeness by artifact inspection of '## Review Evidence' in the task body and stage-transition audit of review -> docs."

## Validation Checklist

Use this checklist for both drafting and validation.

### Planner Draft Checklist

- [ ] Line has exactly one primary target (B1 or P1 scope).
- [ ] Line includes concrete input and concrete observable output when behavior-related (B2).
- [ ] Line contains none of the 7 banned words unless exhaustively enumerated (B3).
- [ ] Process line names agent/skill/stage (P1).
- [ ] Process line states inspectable artifact or board-state delta (P2).
- [ ] Process line includes explicit verification method (P3).
- [ ] Numbering is stable and unambiguous.
- [ ] Line can be verified without author intent.

### Architect/Challenger Validation Checklist

- [ ] Mechanical pass complete: B3 banned words, P1 token, numbering.
- [ ] Semantic pass complete: independent verifiability confirmed per line.
- [ ] Hidden assumptions removed from each line.
- [ ] Every line has objective pass/fail evidence path.
- [ ] Vague phrasing rewritten to executable, inspectable statements.
- [ ] Rule violations are returned with bad -> good rewrite guidance.
