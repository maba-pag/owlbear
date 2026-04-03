---
name: arch-review
description: "Architecture review workflow: read task + research → analyze codebase → evaluate architecture → decide (approve/refine/split/merge/block) → produce report. Used by the architect agent."
user-invocable: false
---

# Architecture Review

Step-by-step process for reviewing researched tasks, refining acceptance criteria,
ensuring architectural soundness, and approving tasks for development.

## kanban-md Commands

| Action | Command |
|--------|---------|
| Read task | `kanban\kanban-md.exe show {id}` |
| Claim | `kanban\kanban-md.exe edit {id} --claim <agent>` |
| Append review | `kanban\kanban-md.exe edit {id} -a "## Architecture Review\n{content}" -t --claim <agent>` |
| Approve | `kanban\kanban-md.exe edit {id} --status todo --release` |
| Refine (keep claimed) | See temp-file pattern below |
| Split (create task) | `kanban\kanban-md.exe create "TITLE" --priority P --tags T --depends-on ID --body "AC"` |
| Split (create TDD test) | `kanban\kanban-md.exe create "Test: TITLE" --priority P --tags T,test --body "AC"` |
| Merge (delete redundant) | `kanban\kanban-md.exe delete ID --yes` |
| Block | `kanban\kanban-md.exe edit {id} --status ideation --block "reason" --release` |

No other kanban-md commands needed. See kanban-md skill for claiming protocol and pitfalls.

**Refine (AC rewrite) pattern:** `--body` writes literal `\n` instead of newlines. Always use the temp-file pattern for multi-line AC:

```powershell
[IO.File]::WriteAllText("docs/scratch/$id-ac.tmp", $revisedAc, [Text.UTF8Encoding]::new($false))
$body = Get-Content "docs/scratch/$id-ac.tmp" -Raw
kanban\kanban-md.exe edit $id --body $body --claim <agent>
Remove-Item "docs/scratch/$id-ac.tmp"
```

## Step 1 — Read task and research

Read the single task dispatched to you:

1. `kanban\kanban-md.exe show {id}` — read full details, verify `backlog` status
2. `kanban\kanban-md.exe edit {id} --claim <agent>` — claim by ID (never use `pick`)
3. If task references a research doc (`docs/research/{slug}.md`), read it
4. Note each AC line for evaluation
5. **Reject placeholder inputs.** If the task is a placeholder (`TEMP-*` title or empty/unscoped body), do not proceed to Step 2. Block back to `ideation` (see Step 4). See agent-common → **Placeholder and unscoped task rejection**.

## Step 2 — Analyze codebase context

1. Use `search` to find related modules, interfaces, patterns
2. Use `read_file` to examine existing code the task will touch
3. Check `depends_on` — are dependencies actually `done`?
4. Identify: existing patterns to follow, interfaces to respect, invariants to maintain
5. Check the task body for prior context — architecture notes, research pointers,
   reviewer feedback from previous cycles.

## Step 3 — Evaluate architecture

Assess the task against the codified standards in the `architecture-standards` skill
(read it with `read_file` if not already loaded)
and general architectural principles:

1. **Single responsibility** — one thing only? If "and" joins unrelated concerns, split.
2. **Interface clarity** — inputs, outputs, side effects clear from AC?
3. **Dependency correctness** — all listed? any missing?
4. **Module layering** — does the proposed change respect the dependency direction
   defined in the `architecture-standards` skill? No upward imports.
5. **TDD compliance** — preceding test task exists?
6. **KISS/YAGNI** — minimal scope? no hypothetical requirements?
7. **Premise challenge** — Should this task exist? Does the capability already exist in:
   (a) IDE features (built-in MCP, IntelliSense, Git integration, terminal),
   (b) runtime (Python stdlib, installed packages, OS utilities),
   (c) existing tooling (scripts/, MCP servers, kanban-md features), or
   (d) extensions (Copilot built-in server, VS Code extensions)?
   If the capability exists, block to ideation with evidence. Applies to ALL tasks
   including ones labeled trivial.
8. **Pattern consistency** — follows existing codebase patterns (protocols, error taxonomy,
   toolset wrapping, config via pydantic-settings)?
9. **Security surface** — does the task introduce new system boundaries (user input,
   external APIs, file I/O)? If so, AC must include input validation requirements.
10. **Single domain** — does this task target exactly one domain (see `architecture-standards`
    skill → **Domain taxonomy**)? Multi-domain → split. Edge case: an ancillary `config.py`
    field addition for a feature is NOT a domain violation — domain = primary concern.
11. **Failure Mode Map** — if the task introduces or modifies codepaths with potential
    failure modes, fill in the template below. Skip for docs/config-only tasks.

    | CODEPATH | FAILURE MODE | EXCEPTION | HANDLED? | USER IMPACT |
    |----------|--------------|-----------|----------|-------------|
    | `store()` | DB write fails | `sqlite3.OperationalError` | Yes — retry 2× | Stale data until next sync |

12. **Decision-request verification** — if the task body references `docs/research/*.md`
    or the task is tagged `research`, use the **scribe** agent in query mode to check
    for an approved decision request for the owning task of the research doc. If the
    scribe returns no approved DR, note the gap and apply the T3 research block path
    in Step 4. Skip this check for tasks with no research reference.

## Step 3.5 — Challenge proposed verdict

Before deciding in Step 4, challenge your reasoning for APPROVE verdicts using the Challenger subagent.

**Trigger conditions:**

| Proposed verdict | Challenge? |
|-----------------|------------|
| APPROVE | **Mandatory** |
| REFINE | Optional (architect's judgment) |
| SPLIT | Skip |
| BLOCK | Skip |

**Prompt construction** — pass these fields to the challenger subagent:

| Field | Value |
|-------|-------|
| `task_id` | The dispatched task ID |
| `proposed_verdict` | Your Step 3 conclusion (APPROVE or REFINE) |
| `reasoning` | Your Step 3 evaluation summary |
| `ac_lines` | The refined AC being approved |
| `codebase_evidence` | Files examined and patterns found (Step 2 findings) |
| `research_doc` | Task body reference to `docs/research/*.md` if present; omit if none |

**Integration protocol:**

| Challenger output | Architect action |
|-------------------|------------------|
| `proceed` + confidence ≥ .80 | Continue with original verdict. Note challenge results in body. |
| `reconsider` OR confidence < .80 | Re-evaluate. May revise AC, change verdict, or justify override with rebuttal. |
| `block` | Strong signal to move task to ideation. Must provide rebuttal if overriding. |

**Architect retains final authority.** The Challenger advises only — never decides.

**Sequential fallback:** If `runSubagent` errors (timeout, tool error, malformed response):

1. Proceed without challenge
2. Note in Challenge Results: `Challenge: FALLBACK — {error reason}`
3. No verdict change required — the architect's own analysis stands

## Step 4 — Decide and act

| Verdict     | When                              | Action                                                                  |
| ----------- | --------------------------------- | ----------------------------------------------------------------------- |
| **Approve** | AC precise, architecture sound    | `kanban\kanban-md.exe edit {id} --status todo --release`               |
| **Refine**  | Good concept, AC needs tightening | Use temp-file pattern (see command table above) to rewrite `--body` |

<!-- NON_IMPL_TAGS: Authoritative list at skills/dispatch-planning/SKILL.md
     (agent dispatch table). Update there first, then sync here. -->
> **Non-implementation tagging:** Before approving, verify tasks that produce no testable
> Python code (agent files, skill files, config-only, docs) carry at least one pass-through
> tag from the non-impl list: `research`, `docs`, `type:config`, `type:docs`, `test`,
> `type:test`, `agent`, `quality`. The `scope:*` prefix tags (e.g. `scope:agents`) are
> categorization — they do NOT trigger test-writer pass-through. Add the bare tag if missing
> (e.g. `--tags agent` alongside `scope:agents`).

> **Always move to `todo`, never to `in-progress`.**  Even when TDD is not applicable
> (e.g., `.agent.md` or `.instructions.md` files), the test-writer must process the task
> to write a pass-through note. The builder depends on that note to decide its own workflow.
> Skipping the test-writer causes tasks to be stuck at `in-progress` with Gate 4 blocking
> further dispatch.
| **Split**   | Multiple responsibilities         | Create new tasks, update deps, edit/delete original, then `--release`   |
| **Merge**   | Two tasks = one logical change    | Edit one, delete redundant, then `--release`                            |
| **Block**   | Missing prerequisite or unclear   | `kanban\kanban-md.exe edit {id} --status ideation --block "reason" --release` |

> **T3 research block path:** If sub-step 12 finds no approved decision request for a task originating from T3 research, use the Block path with reason `"T3 research outcome requires approved decision request"`.

## Step 5 — Produce report

Output a structured ArchitectReview for the task (see agent output format).

## Self-critique checklist

Before submitting:

- [ ] Read full task details and research doc
- [ ] Searched codebase for related patterns
- [ ] Checked task body for prior context on these modules
- [ ] Every AC line evaluated individually
- [ ] No vague AC remains
- [ ] TDD compliance checked
- [ ] Module layering validated against `architecture-standards` skill
- [ ] Security surface assessed (new boundaries have validation AC)
- [ ] Did NOT create/edit .py, .toml, or test files
- [ ] Dependency graph has no cycles
- [ ] Single-domain verified — task targets exactly one domain from the canonical list
- [ ] Premise challenge applied — verified capability is not already provided by environment (IDE/runtime/tooling/extensions)
- [ ] Failure mode map assessed (for tasks with new/modified codepaths)
