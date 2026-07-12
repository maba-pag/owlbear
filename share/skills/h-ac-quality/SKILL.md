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

### B1 Example (Function-Scoped)

- Bad: "System handles archival requests."
- Good: "POST /api/tasks/{id}/release records archival_reason in the archived task metadata."

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

1. Enum/union literals (`CardSignal`)

- Bad: "Task cards must show green/yellow/red/gray/stale status labels in Cockpit."
- Good: "Task cards use `CardSignal` literals from `serve/cockpit/web/src/utils/computeSignal.ts`: `dr-pending | blocked | claimed | deps-unmet | ready | unknown`."

2. PDS design token

- Bad: "Use standard medium spacing for card gaps."
- Good: "Use `--pds-spacing-md` from `serve/cockpit/web/src/tokens.css` for card gap spacing."

3. CSS custom property

- Bad: "Claimed cards should use the purple claimed color variable."
- Good: "Claimed cards use `--pds-signal-claimed` from `serve/cockpit/web/src/tokens.css`."

### 5-Step Verifier Procedure

1. Identify each literal in the AC line (enum value, token name, prop value, or CSS custom property).
2. Locate the canonical source file for that literal category.
3. Confirm exact spelling and allowed values via `grep_search` or `read_file`.
4. Compare AC wording to the canonical source; treat paraphrased labels as mismatch.
5. Rewrite AC to cite the exact literal and source path when any mismatch is found.

### Canonical Source Map

| Category | Source file | Example |
|----------|-------------|---------|
| Enum/union state literals | `serve/cockpit/web/src/utils/computeSignal.ts` | `CardSignal values: dr-pending, blocked, claimed, deps-unmet, ready, unknown` |
| PDS design tokens used in Cockpit styles | `serve/cockpit/web/src/tokens.css` | `--pds-spacing-md` |
| CSS custom properties for semantic signals | `serve/cockpit/web/src/tokens.css` | `--pds-signal-claimed`, `--pds-notification-warning` |
| PDS component prop/type literals | `@porsche-design-system/components-react` type exports | component prop union literal from package type definitions |

For repositories outside the examples above, the shaper records the applicable canonical source in
`## Shape Notes`. Generated operation inventories, public command trees, schemas, official external
documentation, and bounded verified production observations may be canonical authorities for their
specific claims. Evidence scope must remain explicit; a sampled production envelope does not prove
unobserved variants.

## Validation Checklist

Use this checklist for both drafting and validation.

### Shaper Draft Checklist

- [ ] Line has exactly one primary target (B1 or P1 scope).
- [ ] Line includes concrete input and concrete observable output when behavior-related (B2).
- [ ] Line contains none of the 7 banned words unless exhaustively enumerated (B3).
- [ ] Process line names agent/skill/stage (P1).
- [ ] Process line states inspectable artifact or board-state delta (P2).
- [ ] Process line includes explicit verification method (P3).
- [ ] Numbering is stable and unambiguous.
- [ ] Line can be verified without author intent.
- [ ] Cross-boundary line names the normal assembled boundary and replaces only lower dependencies.

### Shaper/Challenger Validation Checklist

- [ ] Mechanical pass complete: B3 banned words, P1 token, numbering.
- [ ] Semantic pass complete: independent verifiability confirmed per line.
- [ ] Hidden assumptions removed from each line.
- [ ] Every line has objective pass/fail evidence path.
- [ ] Integration proof does not inject or mock the boundary whose behavior is claimed.
- [ ] Vague phrasing rewritten to executable, inspectable statements.
- [ ] Rule violations are returned with bad -> good rewrite guidance.
