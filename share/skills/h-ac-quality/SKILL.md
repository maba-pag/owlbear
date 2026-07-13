---
name: h-ac-quality
description: "Handbook: Unified two-tier acceptance-criteria quality schema for shaper drafting and challenger validation"
user-invocable: false
---

# AC Quality Schema

Single authority for writing and validating acceptance criteria (AC) lines in the pipeline.

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
- tool or API query
- command output

## Two-Pass Validation

Run validation in order:

1. Mechanical lint pass

- Check B3 banned words are absent unless exhaustively enumerated.
- Check P1 agent/stage token is present for Tier 2 lines.
- Check literal tokens (enum values, design tokens, prop values, CSS custom properties) against canonical sources; see `## Canonical Literal Verification`.
- Check AC numbering is present and stable.

2. Semantic review pass

- Confirm each line has sufficient detail for independent verification.
- Confirm scope is not split across multiple hidden assumptions.
- Confirm pass/fail is objective and does not require author interpretation.
- For cross-boundary behavior, confirm the AC names the normal assembled boundary and does not
  replace that boundary in its proof setup.

Mechanical pass failing means rewrite before semantic review. Semantic failure means clarify scope, inputs, outputs, or verification method.

## Bad -> Good Transformations

### B1 Example (Boundary-Scoped)

- Bad: "System handles archival requests."
- Good: "Given an active task, POST /api/tasks/{id}/release records archival_reason in the archived
  task metadata."

### B2 Example (Input -> Output)

- Bad: "When a task is blocked, the API responds with an error."
- Good: "Given task_id=42 with blocked=true, GET /api/tasks/42 returns HTTP 423 with error.code='TASK_BLOCKED'."

### B3 Example (No Naked Quantifiers)

- Bad: "Verifier checks all AC lines correctly."
- Good: "Verifier checks AC-1 through AC-4 and records one evidence row per AC line in Verify Notes."

### B4 Example (Boundary-Valid Proof)

- Bad: "Given an injected workflow runner, the CLI command returns JSON."
- Good: "Given the real CLI application with remote HTTP transport replaced, invoking
  `alerts prepare` resolves normal configuration, crosses the assembled workflow boundary, and
  writes one JSON document to stdout."

### P1 Example (Agent/Stage-Scoped)

- Bad: "Add validation before moving tasks."
- Good: "Shaper validates AC quality in shape before moving task shape -> build."

### P2 Example (Observable Artifact/State)

- Bad: "The decomposition output should be prepared."
- Good: "Shaper creates one `shape` child task with `parent` set to the aggregate parent and `depends_on` set to prerequisite child task IDs."

### P3 Example (Verification Method)

- Bad: "Collector confirms the handoff is complete."
- Good: "Collector verifies aggregate completion by inspecting child status, `## Verify Notes`, and parent/EPIC acceptance criteria."

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
  Notes, for its column and row gaps."

3. Command choice

- Bad: "The export command supports the appropriate output formats."
- Good: "`export --format` accepts the parser-declared literals `json | csv`; `xml` exits non-zero
  and names the accepted values."

4. OwlBear board transition

- Bad: "Shaper moves the task to the next valid status."
- Good: "After AC validation passes, Shaper moves the task from `shape` to `build` and verifies the
  resulting status through the OwlBear Kanban MCP."

### Authority Discovery

Locate the strongest authority available in the target project. Prefer sources in this order:

| Priority | Authority | Suitable claims |
|----------|-----------|-----------------|
| 1 | Checked-in schema, type, configuration, or public source declaration | Allowed literals, fields, transitions, tokens, defaults |
| 2 | Generated public inventory, command tree, API schema, or compiled contract | Registered operations and assembled public surface |
| 3 | Installed dependency types, schema, or package metadata | External component props, events, and supported values |
| 4 | Version-matched official external documentation | Contracts not represented locally |
| 5 | Bounded verified runtime observation | Only the observed request, response, state, or environment |

Do not use a test fixture, stale planning document, or paraphrased UI label as canonical when a
stronger authority exists. A sampled production envelope does not prove unobserved variants.

### Verifier Procedure

1. Identify each literal claim in the AC line: enum value, transition, token, prop, event, flag,
   command choice, field name, or generated operation.
2. Discover the strongest applicable authority using the priority table.
3. Confirm spelling, allowed values, version, and relevant constraints through targeted source or
   structured contract inspection.
4. Record the authority and evidence scope in Shape Notes when it is not already obvious from the AC
   or task context.
5. Compare the AC wording with the authority; treat invented aliases and unsupported values as
   contradictions, not harmless paraphrases.
6. Rewrite the AC with the verified literals. If two credible authorities disagree, record the
   contradiction and block shaping until ownership is resolved; do not choose silently.

## Validation Checklist

Use this checklist for both drafting and validation.

### Shaper Draft Checklist

- [ ] Line has exactly one observable boundary or maintained artifact (B1 or P1 scope).
- [ ] Line includes concrete input and concrete observable output when behavior-related (B2).
- [ ] Line contains none of the 7 banned words unless exhaustively enumerated (B3).
- [ ] Process line names agent/skill/stage (P1).
- [ ] Process line states inspectable artifact or board-state delta (P2).
- [ ] Process line includes explicit verification method (P3).
- [ ] Numbering is stable and unambiguous.
- [ ] Line can be verified without author intent.
- [ ] Cross-boundary line names the normal assembled boundary and replaces only lower dependencies.
- [ ] Literal claims cite or record the strongest applicable canonical authority.

### Shaper/Challenger Validation Checklist

- [ ] Mechanical pass complete: B3 banned words, P1 token, numbering.
- [ ] Semantic pass complete: independent verifiability confirmed per line.
- [ ] Hidden assumptions removed from each line.
- [ ] Every line has objective pass/fail evidence path.
- [ ] Integration proof does not inject or mock the boundary whose behavior is claimed.
- [ ] Canonical authorities were checked and unresolved contradictions block shaping.
- [ ] Vague phrasing rewritten to executable, inspectable statements.
- [ ] Rule violations are returned with bad -> good rewrite guidance.
