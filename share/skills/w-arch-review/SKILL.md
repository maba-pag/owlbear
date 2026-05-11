---
name: w-arch-review
description: "Workflow: Architecture review — evaluate design, refine AC, approve for development"
user-invocable: false
---

# Architecture Review

Review researched tasks at `backlog`, refine acceptance criteria, ensure architectural soundness, and approve for development (move to `todo`).

**Kanban operations:** See `h-mcp-kanban` skill — section `## Agent Lifecycle Pattern`.

## Scope

### In Scope

- Validate AC quality via challenger dispatch.
- Evaluate architecture against `r-architecture-standards`.
- Annotate test depth `(td:N)` per AC line.
- Detect missing consolidation-test tasks as a decomposition backstop.
- Approve `backlog -> todo`.
- Run design diverge when two or more valid approaches exist.

### Out of Scope

- AC drafting — planner (`w-task-decomposition`).
- Writing source code — builder (`w-tdd-green`).
- Writing tests — test-writer (`w-tdd-red`).
- Code review — reviewer (`w-code-review`).
- Running full test suite — auditor (`w-task-verification`).
- Documentation updates — doc-writer (`w-doc-update`).

## Step 0 — Setup

Read `r-pipeline-protocol` skill if not already loaded.

Claim the task via `start_work` (atomic claim + retrieves task body). Check the retrieved body for resolved decision/action requests per pipeline-protocol → Task Setup → Resolved Decision Pre-flight.

Verify the task is in `backlog` status. If the task references a research doc (`.owlbear/research/{slug}.md`), read it.

**Decomposition detection:** If the task body contains `"Needs decomposition:"` but does NOT contain a `"## Planning"` section (which the planner appends after decomposition), delegate to the **planner** agent instead of continuing with architecture review. Pass the task ID and feature description from the body. After the planner returns successfully, call `end_work(outcome="success")` to advance the parent task. The planner's appended `## Planning` section serves as the completion marker — do not modify the body to remove the decomposition marker (this would overwrite the planner's additions).

**User-action fast-path:** If the task is tagged `type:user-action` AND the body contains a `## Decision Request` summary with `response: approved`, verify that all AC checkboxes are checked. If complete, advance via `end_work(outcome="success")` — skip Steps 1–3. This task is already resolved.

**Reject placeholders immediately:** `TEMP-*` titles or empty/unscoped bodies — create a DR via `create_dr` explaining the task needs scope, release claim, do not process.

## Step 1 — Analyze Codebase Context

1. Search for related modules, interfaces, and patterns.
2. Read existing code the task will touch via `read_file`.
3. Before asking the user, resolve answerable codebase questions first using `Explore` subagent, `read_file`, `semantic_search`, or `grep_search`.
4. Check `depends_on` — are dependencies actually `done`? Use `show_task` for each dependency if needed.
5. Identify: existing patterns to follow, interfaces to respect, invariants to maintain.
6. Check the task body for prior architecture notes, research pointers, and reviewer feedback from previous cycles.
7. **Brief context (when parent is set):** If the task has a `parent` field, call `show_task(id=parent_id)` and scan for Brief sections (`## Brief`, `## Problem`, `## Outcomes`, `## Approach`, `## Scope`, `## Investment Tier`). When present, use this context to inform AC evaluation and builder guidance.

## Step 2 — Evaluate Architecture

Assess the task against `r-architecture-standards` and general architectural principles:

1. **Single responsibility** — one thing only? If "and" joins unrelated concerns, split.
2. **Interface clarity** — inputs, outputs, side effects clear from AC?
3. **Dependency correctness** — all listed? Any missing?
4. **Module layering** — respect dependency direction from `r-architecture-standards`? No upward imports. For frontend import-shape AC constraints, require a parent→child live-code trace (workspace search or `read_file` evidence) proving the constrained module actually imports from the cited path/barrel before naming that constraint in AC.
5. **TDD compliance** — preceding test task exists? Before defining must-pass durable-suite gates in AC, run a suite-health pre-check and explicitly scope out known pre-existing failures unrelated to the current task.
6. **KISS/YAGNI** — minimal scope? No hypothetical requirements? **Deletion Test (conditional):** If the task introduces a new abstraction (module, interface, adapter, wrapper), apply the Deletion Test from `r-architecture-standards` — if deleting the abstraction would make its callers simpler, it's a pass-through. Reject or propose inlining.
7. **Premise challenge** — should this task exist? Does the capability already exist in: (a) IDE features, (b) runtime/stdlib, (c) existing tooling, or (d) extensions? If so, reject with evidence.
8. **Pattern consistency** — follows existing codebase patterns (protocols, error taxonomy, MCP conventions, config via pydantic-settings)?
9. **Security surface** — new system boundaries (user input, external APIs, file I/O)? If so, AC must include input validation requirements.
10. **Single domain** — exactly one domain (see `r-architecture-standards` domain taxonomy)? Multi-domain means split. Exception: ancillary config field for a feature is not a domain violation.
11. **Failure Mode Map** — if the task introduces or modifies codepaths with failure modes:

    | CODEPATH | FAILURE MODE | EXCEPTION | HANDLED? | USER IMPACT |
    |----------|--------------|-----------|----------|-------------|

12. **Decision-request verification** — if the task references `.owlbear/research/*.md` or is tagged `research`, check the task body for a resolved DR after Cockpit decision resolution applies the response. No approved DR for T3 research = use the REJECT path.

13. **User-action detection** — Does this task require a human physical action with no testable Python interface? Apply the M/S/C rule in order:
    - **Counter-signals (C) — exit immediately if ANY present:** (C1) AC defines a function signature, importable module, or assertion target; (C2) AC specifies expected test outcomes; (C3) task already tagged `type:test` or `type:config`
    - **Mandatory (M) — BOTH required:** (M1) AC defines no testable Python interface; (M2) completion can only be verified by a human, not by running code
    - **Signals (S) — ≥1 required:** (S1) AC uses physical-action verbs (Open, Click, Navigate, Configure via GUI, Deploy manually); (S2) AC names external systems (Teams, Azure portal, GitHub UI, browser, dashboards); (S3) AC lists manual steps the user must physically perform
    - **Outcome:** no counter-signal AND M1+M2 AND ≥1 S → `type:user-action` detected → use BLOCK verdict (Step 3)

## Step 2.1 — Test-Depth Annotation

Annotate each AC line with a test-depth suffix `(td:N)`:

| Depth | Suffix | Meaning | Examples |
|-------|--------|---------|----------|
| 0 | `(td:0)` | No test needed | Mechanical removal, cosmetic fix, "all tests pass", config-only |
| 1 | `(td:1)` | Smoke test — one assertion proves it | Simple rename, add a field, single happy-path |
| 2 | `(td:2)` | Full TDD — multiple paths/edges | New logic, error handling, security boundary |

**Existing-proof guard:** Use `(td:0)` only to skip new test creation. If the AC line says existing tests must pass, a full suite must pass, a quality-runner report is required, or a command must exit 0, include an `Existing proof required: {scope}` note in the Architecture Review verdict. Builder/reviewer must run that proof through `quality-runner` even though test-writer skips new tests.

**Procedure:**

1. For each AC line, assign `(td:N)` based on the line's testability, not the task's overall complexity.
2. Default to `(td:1)` when uncertain — depth can be lowered but never raised after approval.
3. Append the suffix to the AC line text in the task body via `edit_task`.

**Pipeline routing:**

- If ALL AC lines are `(td:0)`: append `Test-writer: SKIP` to the Architecture Review verdict section. The test-writer will pass through without writing tests; existing-proof requirements still apply when named.
- If ANY line is `(td:1)` or `(td:2)`: test-writer processes the task normally, respecting per-line depth.

**Subagent gating:** If ALL AC lines are `(td:0)`, skip the challenger dispatch in Step 2.5.

## Step 2.3 — Conditional Design Diverge

Run this step only when all trigger conditions are met:

- Step 2 reveals at least 2 valid approaches.
- Criteria are split across approaches (for example: approach A passes some criteria while approach B passes different criteria, and neither dominates).
- The architect cannot resolve the trade-off without deeper analysis.

If any trigger condition is not met, skip Step 2.3 entirely (zero overhead).

When triggered, dispatch 2-3 `General Purpose` subagents in parallel. Each prompt must include:

- Task context and AC lines.
- Codebase patterns identified in Step 1.
- One explicit optimization axis (for example: "Design optimizing for minimal interface surface").
- Instruction to return the 5-section output contract below.

Required subagent output contract (exactly 5 sections):

1. `Approach summary` (1-2 sentences)
2. `Structural choices` (bulleted list)
3. `Trade-offs` (pros and cons)
4. `Failure modes` (what can go wrong, with impact)
5. `Codebase fit` (alignment with Step 1 patterns)

Build a comparison matrix from returned approaches across the split criteria. Select one approach or a hybrid approach, then document rationale in the architecture review output.

**Fallback:** If any subagent call fails (timeout, crash, exception), skip design-diverge and continue with single-pass evaluation. Record: `Design-diverge: FALLBACK — {reason}`.

## Step 2.5 — Challenge Proposed Verdict

After Step 2.3 selection (when triggered), challenge APPROVE verdicts using the **challenger** subagent. This is mandatory for APPROVE (unless all AC lines are td:0 — see Step 2.1), optional for REFINE, skip for SPLIT/REJECT.

Pass: task_id, proposed_verdict, reasoning, ac_lines, codebase_evidence, selected_or_hybrid_design (from Step 2.3), sibling_tasks (optional), and research-doc reference. When Step 2.3 is skipped, selected_or_hybrid_design should capture the single-pass design being evaluated.

For AC wording quality, require challenger to validate AC lines using `h-ac-quality` rules and surface issues via `ac-quality` findings. For consolidation-test coverage, pass sibling task metadata so challenger can detect a `consolidation-test-gap` when there are 2 or more sibling implementation tasks under the same parent and no sibling consolidation-test task.

| Challenger output | Architect action |
|-------------------|------------------|
| `proceed` + confidence ≥ Challenger threshold (`r-pipeline-protocol`) | Continue with original verdict |
| `reconsider` OR confidence below threshold | Re-evaluate, may revise or justify override |
| `ac-quality` | REFINE AC wording before approval |
| `consolidation-test-gap` | Dispatch planner follow-up for consolidation-test coverage before approval |
| `block` | Strong signal to reject to research; must provide rebuttal if overriding |

The architect retains final authority.

**Fallback:** If `runSubagent` errors, proceed without challenge. Note: `Challenge: FALLBACK — {reason}`.

## Step 3 — Decide and Act

| Verdict | When | Action |
|---------|------|--------|
| **APPROVE** | AC precise, architecture sound | Advance via `end_work` (moves to `todo` + releases claim) |
| **REFINE** | Good concept, AC needs tightening | Use temp-file pattern to rewrite body via `edit_task`, then approve |
| **SPLIT** | Multiple responsibilities | Delegate to planner with `Plan and create: #{id} — {split scope}` for decomposition, then update deps, edit/delete original, and release |
| **MERGE** | Two tasks = one logical change | Edit one task, delete redundant, release |
| **REJECT** | Missing prerequisite or unclear | Move to `research` via `end_work(outcome="reject")`, appending findings |
| **BLOCK** | `type:user-action` detected (Step 2 criterion 13) | Create AR via `create_dr(task_id={id}, agent="architect", request_type="action", body="{markdown AR payload}")`, tag task `type:user-action` if missing, `end_work(outcome="block", block_reason="AR pending: {filename}")` |

<!-- NON_IMPL_TAGS: This is the authoritative list. Secondary copy:
     skills/w-tdd-red/SKILL.md (Step 1 item 3) -->

| Task status   | Dispatch agent | Pipeline action                                          | Non-impl pass-through? |
| ------------- | -------------- | -------------------------------------------------------- | ---------------------- |
| `research`    | researcher     | Research investigation, move to `backlog`                | No                     |
| `backlog`     | architect      | Architecture review, move to `todo`                      | No                     |
| `todo`        | test-writer    | Write failing tests (RED phase), move to `in-progress`   | Yes — tags `research`, `docs`, `type:config`, `type:docs`, `test`, `type:test`, `agent`, `quality`, `type:user-action` |
| `in-progress` | builder        | GREEN phase, move to `review`                            | Yes — if test-writer passed through |
| `review`      | reviewer       | Quality verification, move to `docs`                     | No                     |
| `docs`        | doc-writer     | Documentation gate, move to `done`                       | No                     |
| `done`        | auditor        | Exit gate verification, archive                          | No                     |

**Non-implementation tasks:** Tasks tagged with pass-through tags still flow through the standard pipeline. The test-writer recognizes them and passes through without writing tests (see `w-tdd-red` Step 1a). The architect is responsible for tagging tasks correctly during backlog approval.

**Non-implementation tagging:** Before approving, verify tasks producing no testable Python code carry at least one pass-through tag: `research`, `docs`, `type:config`, `type:docs`, `test`, `type:test`, `agent`, `quality`, `type:user-action`. Add the bare tag if missing.

**Always move to `todo`, never to `in-progress`.** The test-writer must process every task to write a pass-through note. Skipping causes Gate 4 violations downstream.

Include the architecture review in your `end_work` note.

Return Channel A signal per `r-pipeline-protocol`.

## Output Template

Append to task body before advancing:

```
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS/FAIL | {notes} |
| Interface clarity | PASS/FAIL | {notes} |
| Dependency correctness | PASS/FAIL | {notes} |
| Module layering | PASS/FAIL | {notes} |
| TDD compliance | PASS/FAIL | {notes} |
| KISS/YAGNI | PASS/FAIL | {notes} |
| Premise challenge | PASS/FAIL | {notes} |
| Pattern consistency | PASS/FAIL | {notes} |
| Security surface | PASS/FAIL | {notes} |
| Single domain | PASS/FAIL | {notes} |

### Failure Mode Map (if applicable)
| Codepath | Failure Mode | Exception | Handled? | User Impact |

### Design Diverge (optional)
- Trigger: {triggered with reason / skipped with reason / fallback}
- Approach summaries: {1-2 lines per approach}
- Comparison matrix:

    | Criterion | Approach A | Approach B | Approach C (optional) |
    |-----------|------------|------------|------------------------|
    | {criterion} | PASS/FAIL | PASS/FAIL | PASS/FAIL |

- Selection rationale: {chosen or hybrid approach and why}

If fallback triggered, include only: `Design-diverge: FALLBACK — {reason}`.

### Challenge Results
- Challenger: {proceed/reconsider/reject} (or FALLBACK / SKIPPED — all td:0)
- Architect response: {accepted/rebutted/revised}

### Test Depth
- Max depth: {0/1/2}
- Test-writer: {SKIP (all td:0) / PROCEED}

### Verdict: {APPROVE/REFINE/SPLIT/REJECT}
### Action Taken: {description}
```

## Verification Checklist

- [ ] Read full task details and research doc (if referenced)
- [ ] Searched codebase for related patterns
- [ ] Checked task body for prior context (architecture notes, reviewer feedback)
- [ ] For frontend import-shape AC constraints, captured a parent→child live-code import trace via workspace search or `read_file` evidence before naming path/barrel constraints
- [ ] For frontend tasks referencing Briefs with design-system components, AC names exact selectors and assertion strategies (not generic HTML elements)
- [ ] Ran durable-suite health pre-check before defining must-pass suite gates; documented and excluded known unrelated pre-existing failures
- [ ] All 13 Step 2 criteria evaluated
- [ ] Each AC line annotated with `(td:N)` (Step 2.1)
- [ ] Design-diverge evaluated (triggered / skipped with reason / fallback noted)
- [ ] Challenger invoked for APPROVE verdicts (or fallback noted)
- [ ] `type:user-action` tasks blocked (BLOCK verdict) rather than approved
- [ ] Non-impl tasks tagged with pass-through tag before approving
- [ ] Did NOT create/edit `.py`, `.toml`, or test files
- [ ] Architecture review included in `end_work` note

## Known Pitfalls

- **Skipping to `in-progress`:** Always move to `todo`, never `in-progress`. The test-writer must process every task for the pipeline to work.
- **Missing non-impl tags:** Tasks without pass-through tags cause the test-writer to attempt writing tests for non-code deliverables, wasting a pipeline cycle.
- **Body content escaping:** `--body` writes literal `\n` instead of newlines. Always use the temp-file pattern for multi-line AC.
- **T3 research without DR:** If a task originated from T3 research with no approved decision request, reject it. Proceeding without approval risks reversal.
- **Premise challenge skip:** The challenger is easy to skip but catches real issues. The mandatory trigger on APPROVE exists for a reason.
- **#1225 import-shape drift:** Do not author frontend import-path/barrel AC constraints from assumption. Confirm the parent→child import chain in live code first, then write the constraint.
- **#1225 suite gate debt inheritance:** Do not gate builders on durable suites with known unrelated failures. Pre-check suite health and scope those failures out in AC gate wording.
- **#1250 PDS contract carry-forward:** When a Brief or research doc specifies design-system components (PDS or equivalent), AC lines must carry exact component contracts into testable criteria. Instead of generic "select" wording, name the exact PDS selector (for example `p-select`). Instead of "populated from priorities prop," specify exact-ordered-match assertions when order matters. Instead of "does not render controls," state whether the proof requires DOM absence or visual/a11y hiding. Instead of "preserving other fields" with one broad check, require per-control verification for each affected control.
