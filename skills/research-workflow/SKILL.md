---
name: research-workflow
description: "Structured research workflow: clarify scope → gather sources → analyze with trade-off matrices → write doc → create follow-up tasks. Used by the researcher agent."
user-invocable: false
---

# Research Workflow

Step-by-step process for investigating a topic and producing structured, actionable findings.

## kanban-md Commands

See kanban-md skill for claiming protocol and pitfalls. Key researcher commands:

| Action | Command |
|--------|--------|
| Create follow-up | `kanban\kanban-md.exe create "TITLE" --priority P --status ideation --tags T` |

## Research checklist

Before a task can leave `ideation`, complete this checklist. Items 1–6 are **mandatory**;
items 7–8 are **recommended**.

1. **Theoretical validity** — Is this a sound concept? Does the abstraction make sense? Is it the right approach?
2. **Environment audit** — Is this capability already provided by the IDE, runtime, installed extensions, or existing tooling? Check VS Code built-in features, extension-provided servers, and installed packages before recommending additions.
3. **Prior art** — Find 2+ GitHub repos, articles, or docs showing how others solved this problem.
4. **Technical feasibility** — Will it work in our stack (Python 3.12, PydanticAI, etc.)? Any blockers or dependencies?
5. **Architecture fit** — How does it integrate with existing OwlBear components? What interfaces does it touch?
6. **Implementation approach** — What patterns, idioms, and data structures should we adopt from prior art?
7. **Testing strategy** _(recommended)_ — How will we test this? Unit, integration, mocks? Coverage approach?
8. **Findings documented** _(recommended)_ — Brief notes in task body, or linked `docs/research/{slug}.md` for complex research.

For trivial tasks (rename, typo, config tweak): items 1–4 get a one-liner
`N/A — trivial change, rationale: X` and the task moves through quickly. **The gate
still exists** — it just doesn't create busywork.

## Step 0 — Claim

Claim by ID per kanban-md skill → Claiming Protocol.

## Step 1 — Clarify scope

**Fail fast on invalid inputs before starting any research:**

- If the task is a placeholder (`TEMP-*` title or empty/unscoped body), refuse dispatch immediately. See agent-common → **Placeholder and unscoped task rejection**. Example: a task titled `TEMP-planner-test` with no scoped body must be blocked or handed off — it must not be clarified by question or have scope invented for it. See `docs/research/planner-temp-task-hygiene.md`.

If the task has scoped content but needs clarification:

- Present structured options to the user (what aspects? what decision? what constraints?)
- Read `.github/copilot-instructions.md` for tech stack and principles

## Step 1.5 — Pre-flight: check for existing research

Before gathering any sources, confirm no prior research exists for this task:

1. **Scan docs/research/**: `file_search("docs/research/**")` or `grep_search` the task ID and topic keywords. If a doc references this task, read it before doing anything else.
2. **Check the task body**: look for `See docs/research/` links — a prior researcher may have completed the work but failed to advance the task status.
3. **If a complete, recent doc exists**: do a validation pass instead of full research — confirm the doc is current, verify codebase state, then skip to Step 5 if findings still hold. See process-patterns "Validation-only research when prior research exists".

> Skipping this check is the most common research time-sink — multiple prior instances wasted partial or full research cycles because existing docs were missed.

## Step 2 — Gather sources

Find 2+ authoritative sources per claim:

- **Codebase:** search tools for related existing code
- **Web:** `fetch_webpage` for docs, articles, GitHub repos
- **Clone for deep analysis:** `docs/scratch/research/{repo-name}/` → analyze → delete when done

Track: name, URL, what was taken, relevance score (0.0–1.0).

## Step 3 — Analyze and compare

Structure analysis as trade-off matrices, not prose:

- Comparison tables (rows = options, columns = criteria)
- Confidence scores on recommendations (.0–1.0)
- Risks and mitigations for each option
- Apply KISS, YAGNI, DRY principles

## Step 3.5 — Challenge proposed recommendation

Before writing the research document, challenge your Step 3 recommendation using the Challenger subagent.

**Trigger conditions:**

| Research type | Challenge? |
|--------------|------------|
| Step 3 produces a recommendation (section 4 will contain a recommendation with confidence score) | **Mandatory** |
| Info-only or trivial research with no recommendation | Skip |

**Prompt construction** — pass these fields to the challenger subagent:

| Field | Value |
|-------|-------|
| `task_id` | The research task ID |
| `proposed_verdict` | Your Step 3 recommendation text + confidence score |
| `reasoning` | Your Step 3 analysis summary |
| `ac_lines` | The research question/scope |
| `codebase_evidence` | Codebase findings from Step 2 |
| `research_doc` | Path to draft if already written; omit if none |

**Integration protocol:**

| Challenger output | Researcher action |
|-------------------|------------------|
| `proceed` + confidence ≥ .80 | Continue with original recommendation. Note challenge in doc section 4. |
| `reconsider` OR confidence < .80 | Revise recommendation/confidence or justify override with rebuttal. |
| `block` | Revisit research scope; must provide rebuttal if proceeding. Distinct from T3 DR workflow. |

**Researcher retains final authority.** The Challenger advises only — never decides.

**Sequential fallback:** If `runSubagent` errors (timeout, tool error, malformed response):

1. Proceed without challenge
2. Note in doc section 4: `Challenge: FALLBACK — {reason}`
3. No recommendation change required — the researcher's own analysis stands

**Research doc (section 4)** must include a brief challenge note:

    Challenge: {proceed|reconsider|block} — confidence in original: {score}
    (fallback: Challenge: FALLBACK — {reason})

**Kanban body** must include challenge details (append via Channel B before advancing):

    ## Challenge Results
    - Challenger recommendation: {proceed|reconsider|block} (or FALLBACK — {reason})
    - Confidence in original: {score}
    - Key challenges: {list}
    - Researcher response: {accepted|rebutted|revised} — {brief rationale}

## Step 4 — Write research document

Create `docs/research/{slug}.md`:

```markdown
# {Title}

> **Owning task:** #{id} — {title}
> **Date:** {date} **Status:** Complete

## 1. Context and Question

## 2. Sources Studied (table)

## 3. Analysis (trade-off matrices)

## 4. Recommendation (with confidence)

## 5. Follow-up Tasks (kanban commands)
```

Max 200 lines. Every claim needs a source reference.

## Step 5 — Classify outcome and create follow-up tasks

### Tier classification (do this first)

Classify every research finding before acting on it:

| Tier | Category | Decision required? | Examples |
|------|----------|--------------------|----------|
| **T1: Autonomous** | Bug fix, refactor, config, perf | None — proceed directly | Root cause analysis, linter config, dep bump |
| **T2: Advisory** | Approach with trade-offs, no T3 triggers | Advisory DR (5-day auto-resolve) | Library selection, pattern choice |
| **T3: Mandatory** | New feature, arch change, security/process/breaking change | Blocking DR (no auto-resolve) | New agent capability, pipeline change, module restructure |

**T3 triggers (deterministic — ANY one makes it T3):**

- Adds a capability that doesn't currently exist
- Changes the architecture of one or more modules
- Modifies agent instructions, skills, or pipeline behavior
- Alters security policy or safety boundaries
- Changes user-facing behavior or external interfaces
- Proposes deprecation or removal of existing functionality

**Decision tree:**

1. Check T3 triggers → any match? → **T3**: use the **scribe** agent to create a blocking DR (no auto-resolve), task gets blocked automatically
2. No T3 triggers + multiple valid approaches with trade-offs? → **T2**: create advisory DR (5-day auto-resolve)
3. No T3 triggers + no meaningful trade-offs? → **T1**: proceed directly

### Create follow-up tasks

Generate `kanban-md create` commands for every actionable finding.
**Execute them** to create tasks at `ideation` status — the architect still gates them before `todo`.

If a finding requires a user decision with no clear winner, use the **scribe** agent
to check/create a decision request. The scribe checks for duplicates, creates the DR
if needed, and blocks the task automatically. Move on to other work if available.

## Step 6 — Finalize

1. Add rows to `docs/sources/overview.md` for any external sources used
2. Delete any cloned repos from `docs/scratch/research/`
3. Advance and release:

```powershell
kanban\kanban-md.exe edit {id} --status backlog --release
```

## Self-critique checklist

Before submitting:

- [ ] Every claim has ≥ 2 sources
- [ ] Analysis uses comparison tables
- [ ] Confidence scores on recommendations
- [ ] Research doc ≤ 200 lines
- [ ] Follow-up kanban tasks are concrete and actionable
- [ ] Did NOT create/edit source code
- [ ] External sources logged in sources/overview.md
- [ ] Cloned repos deleted
- [ ] Task advanced to `backlog` and claim released
- [ ] Verified no environment duplication
- [ ] Recommendations align with KISS/YAGNI
