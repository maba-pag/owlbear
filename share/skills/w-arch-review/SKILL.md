---
name: w-arch-review
description: "Workflow: Architecture review — evaluate design, refine AC, approve for development"
user-invocable: false
---

# Architecture Review

Review researched tasks at `backlog`, refine acceptance criteria, ensure architectural soundness, and approve for development (move to `todo`).

**Kanban operations:** See `h-mcp-kanban` skill — section `## Agent Lifecycle Pattern`.

## Step 0 — Setup

Read `r-pipeline-protocol` skill if not already loaded.

Claim the task via `start_work` (atomic claim + retrieves task body). Check the retrieved body for resolved decision/action requests per pipeline-protocol → Task Setup → Resolved Decision Pre-flight.

Verify the task is in `backlog` status. If the task references a research doc (`.owlbear/research/{slug}.md`), read it.

**Reject placeholders immediately:** `TEMP-*` titles or empty/unscoped bodies — create a DR via scribe explaining the task needs scope, release claim, do not process.

## Step 1 — Analyze Codebase Context

1. Search for related modules, interfaces, and patterns.
2. Read existing code the task will touch via `read_file`.
3. Check `depends_on` — are dependencies actually `done`? Use `show_task` for each dependency if needed.
4. Identify: existing patterns to follow, interfaces to respect, invariants to maintain.
5. Check the task body for prior architecture notes, research pointers, and reviewer feedback from previous cycles.

## Step 2 — Evaluate Architecture

Assess the task against `r-architecture-standards` and general architectural principles:

1. **Single responsibility** — one thing only? If "and" joins unrelated concerns, split.
2. **Interface clarity** — inputs, outputs, side effects clear from AC?
3. **Dependency correctness** — all listed? Any missing?
4. **Module layering** — respect dependency direction from `r-architecture-standards`? No upward imports.
5. **TDD compliance** — preceding test task exists?
6. **KISS/YAGNI** — minimal scope? No hypothetical requirements?
7. **Premise challenge** — should this task exist? Does the capability already exist in: (a) IDE features, (b) runtime/stdlib, (c) existing tooling, or (d) extensions? If so, reject with evidence.
8. **Pattern consistency** — follows existing codebase patterns (protocols, error taxonomy, MCP conventions, config via pydantic-settings)?
9. **Security surface** — new system boundaries (user input, external APIs, file I/O)? If so, AC must include input validation requirements.
10. **Single domain** — exactly one domain (see `r-architecture-standards` domain taxonomy)? Multi-domain means split. Exception: ancillary config field for a feature is not a domain violation.
11. **Failure Mode Map** — if the task introduces or modifies codepaths with failure modes:

    | CODEPATH | FAILURE MODE | EXCEPTION | HANDLED? | USER IMPACT |
    |----------|--------------|-----------|----------|-------------|

12. **Decision-request verification** — if the task references `.owlbear/research/*.md` or is tagged `research`, query the scribe to check for an approved DR. No approved DR for T3 research = use the REJECT path.

## Step 2.5 — Challenge Proposed Verdict

Before deciding in Step 3, challenge APPROVE verdicts using the **challenger** subagent. This is mandatory for APPROVE, optional for REFINE, skip for SPLIT/REJECT.

Pass: task_id, proposed_verdict, reasoning, ac_lines, codebase_evidence, and research-doc reference.

| Challenger output | Architect action |
|-------------------|------------------|
| `proceed` + confidence 0.80+ | Continue with original verdict |
| `reconsider` OR confidence < 0.80 | Re-evaluate, may revise or justify override |
| `block` | Strong signal to reject to ideation; must provide rebuttal if overriding |

The architect retains final authority.

**Fallback:** If `runSubagent` errors, proceed without challenge. Note: `Challenge: FALLBACK — {reason}`.

## Step 3 — Decide and Act

| Verdict | When | Action |
|---------|------|--------|
| **APPROVE** | AC precise, architecture sound | Advance via `end_work` (moves to `todo` + releases claim) |
| **REFINE** | Good concept, AC needs tightening | Use temp-file pattern to rewrite body via `edit_task`, then approve |
| **SPLIT** | Multiple responsibilities | Create new tasks via `create_task`, update deps, edit/delete original, then release |
| **MERGE** | Two tasks = one logical change | Edit one task, delete redundant, release |
| **REJECT** | Missing prerequisite or unclear | Move to `ideation` via `end_work(outcome="reject")`, appending findings |

<!-- NON_IMPL_TAGS: Authoritative list at w-dispatch-planning. -->

> **Non-implementation tagging:** Before approving, verify tasks producing no testable Python code carry at least one pass-through tag: `research`, `docs`, `type:config`, `type:docs`, `test`, `type:test`, `agent`, `quality`. Add the bare tag if missing.

> **Always move to `todo`, never to `in-progress`.** The test-writer must process every task to write a pass-through note. Skipping causes Gate 4 violations downstream.

Append the architecture review to the task body via `edit_task` (with `append_body` and `timestamp=True`) before the final status move.

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

### Challenge Results
- Challenger: {proceed/reconsider/reject} (or FALLBACK)
- Architect response: {accepted/rebutted/revised}

### Verdict: {APPROVE/REFINE/SPLIT/REJECT}
### Action Taken: {description}
```

## Verification Checklist

- [ ] Read full task details and research doc (if referenced)
- [ ] Searched codebase for related patterns
- [ ] Checked task body for prior context (architecture notes, reviewer feedback)
- [ ] All 12 Step 2 criteria evaluated
- [ ] Challenger invoked for APPROVE verdicts (or fallback noted)
- [ ] Non-impl tasks tagged with pass-through tag before approving
- [ ] Did NOT create/edit `.py`, `.toml`, or test files
- [ ] Architecture review appended to task body via `edit_task`

## Known Pitfalls

- **Skipping to `in-progress`:** Always move to `todo`, never `in-progress`. The test-writer must process every task for the pipeline to work.
- **Missing non-impl tags:** Tasks without pass-through tags cause the test-writer to attempt writing tests for non-code deliverables, wasting a pipeline cycle.
- **Body content escaping:** `--body` writes literal `\n` instead of newlines. Always use the temp-file pattern for multi-line AC.
- **T3 research without DR:** If a task originated from T3 research with no approved decision request, reject it. Proceeding without approval risks reversal.
- **Premise challenge skip:** The challenger is easy to skip but catches real issues. The mandatory trigger on APPROVE exists for a reason.
