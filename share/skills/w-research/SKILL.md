---
name: w-research
description: "Workflow: Research — structured analysis producing findings and follow-up tasks"
user-invocable: false
---

# Research

Investigate a topic, produce structured findings with trade-off matrices, write a research document, and create actionable follow-up tasks.

**Kanban operations:** See `h-mcp-kanban` skill — section `## Agent Lifecycle Pattern`.

## Step 0 — Setup

Read `r-pipeline-protocol` skill if not already loaded.

Claim the task via `start_work` (atomic claim + retrieves task body). Check the retrieved body for resolved decision/action requests per pipeline-protocol → Task Setup → Resolved Decision Pre-flight.

Verify the task is in `research` status.

## Research Gate Checklist

Before a task can leave `research`, complete this checklist. Items 1–6 are **mandatory**; items 7–8 are **recommended**.

1. **Theoretical validity** — Sound concept? Right approach?
2. **Environment audit** — Capability already provided by IDE, runtime, extensions, or existing tooling?
3. **Prior art** — 2+ GitHub repos, articles, or docs showing how others solved this.
4. **Technical feasibility** — Works in our stack (Python 3.12, FastMCP, VS Code + Copilot)? Blockers?
5. **Architecture fit** — Integrates with existing OwlBear components? Interfaces?
6. **Implementation approach** — Patterns, idioms, data structures to adopt.
7. **Testing strategy** _(recommended)_ — How to test? Unit, integration, mocks? Coverage?
8. **Findings documented** _(recommended)_ — Notes in task body or linked `.owlbear/research/{slug}.md`.

For trivial tasks (rename, typo, config tweak): items 1–4 get a one-liner `N/A — trivial change, rationale: X`.

## Step 1 — Clarify Scope

**Fail fast on invalid inputs.** `TEMP-*` titles or empty bodies = create a DR via `create_dr`, release claim.

If the task has scoped content but needs clarification:

- Present structured options to the user.
- Read `.github/copilot-instructions.md` for tech stack and principles.

### Step 1.5 — Pre-Flight: Check for Existing Research

Before gathering sources:

1. Search `.owlbear/research/` for the task ID and topic keywords. If a doc references this task, read it first.
2. Check task body for `See .owlbear/research/` links.
3. If a complete, recent doc exists: do a validation pass instead of full research — confirm the doc is current, verify codebase state, skip to Step 5 if findings hold.

> Skipping this check is the most common research time-sink.

## Step 2 — Gather Sources

Find 2+ authoritative sources per claim:

- **Codebase:** search tools for related existing code.
- **Web:** use the `web` toolset for direct pages and `ddgs/search_text` / `ddgs/extract_content` for search and extraction; use `markitdown/*` when document conversion is needed.
- **Clone for deep analysis:** `.owlbear/scratch/research/{repo-name}/` — analyze, then delete when done.

Track: name, URL, what was taken, relevance score (0.0–1.0).

## Step 3 — Analyze and Compare

Structure analysis as trade-off matrices:

- Comparison tables (rows = options, columns = criteria).
- Confidence scores on recommendations (0.0–1.0).
- Risks and mitigations for each option.
- Apply KISS, YAGNI, DRY principles.

### Step 3.5 — Challenge Proposed Recommendation

Before writing the research doc, challenge your recommendation using the **challenger** subagent. Mandatory when Step 3 produces a recommendation; skip for info-only or trivial research.

Apply per `r-pipeline-protocol` → Confidence Thresholds (Challenger row).

**Fallback:** If `runSubagent` errors, proceed without challenge. Note: `Challenge: FALLBACK — {reason}`.

## Step 4 — Write Research Document

Create `.owlbear/research/{slug}.md`:

```markdown
# {Title}

> **Owning task:** #{id} — {title}
> **Date:** {date} **Status:** Complete

## 1. Context and Question
## 2. Sources Studied (table)
## 3. Analysis (trade-off matrices)
## 4. Recommendation (with confidence)
## 5. Follow-up Tasks
```

Max 200 lines. Every claim needs a source reference.

Include challenge note in section 4: `Challenge: {proceed|reconsider|block} — confidence in original: {score}`

## Step 5 — Classify Outcome and Create Follow-Up Tasks

### Tier Classification

Classify every finding before acting:

| Tier | Category | Action |
|------|----------|--------|
| T1 — Autonomous | Bug fix, refactor, config, perf | Proceed directly — create follow-up tasks |
| T2 — Advisory | Trade-offs, no T3 triggers | Create advisory DR via `create_dr` (5-day auto-resolve) |
| T3 — Mandatory | New capability, arch/security/breaking change | Create blocking DR via `create_dr` (no auto-resolve) |

**T3 triggers (any one makes it T3):** Adds new capability, changes architecture, modifies agent/pipeline behavior, alters security policy, changes user-facing behavior, proposes deprecation.

### Create Follow-Up Tasks

Delegate follow-up task creation to planner via `Plan and create:` using single-task or decomposition mode as needed, and set status to `research`. For findings requiring user decisions, create a decision request via `create_dr`.

## Step 6 — Finalize Artifacts

1. Add rows to `.owlbear/sources/overview.md` for external sources (see `r-project-standards` → Attribution).
2. Delete any cloned repos from `.owlbear/scratch/research/`.

## Step 7 — Commit & Advance

**Commit your deliverables** (see `r-pipeline-protocol` → Who Commits What):

```shell
git add .owlbear/research/{doc}.md .owlbear/sources/overview.md && git commit -m "docs: research {topic} (#{id}, researcher)"
```

Stage only files you created or modified. Verify with `git diff --cached --name-only` if uncertain.

Include the research summary and challenge results in your `end_work` note.

Then advance via `end_work` (moves to `backlog` + releases claim).

Return Channel A signal per `r-pipeline-protocol`.

## Output Template

Append to task body before advancing:

```
## Research
- Research doc: .owlbear/research/{slug}.md
- Sources: {N} studied, {M} high-relevance
- Recommendation: {brief} (confidence: {.XX})
- Follow-up tasks created: {list of IDs at research}
- Decision requests: {N created, or "none"}

## Challenge Results
- Challenger: {proceed/reconsider/block} (or FALLBACK — {reason})
- Confidence in original: {score}
- Key challenges: {list}
- Researcher response: {accepted/rebutted/revised} — {rationale}
```

## Verification Checklist

- [ ] Every claim has 2+ sources
- [ ] Analysis uses comparison tables with confidence scores
- [ ] Research doc 200 lines or fewer
- [ ] Follow-up kanban tasks are concrete and actionable (created at `research`)
- [ ] Did NOT create/edit source code
- [ ] External sources logged in `.owlbear/sources/overview.md`
- [ ] Cloned repos deleted from `.owlbear/scratch/research/`
- [ ] Challenger invoked for recommendation (or fallback noted)
- [ ] Tier classification applied to every finding (T1/T2/T3)
- [ ] Research files committed before advancing
- [ ] Task advanced to `backlog` and claim released

## Known Pitfalls

- **Skipping pre-flight check:** Multiple research cycles have been wasted because existing docs were missed. Always check `.owlbear/research/` first.
- **Follow-up tasks without AC:** Every follow-up task needs concrete acceptance criteria. "Improve X" without measurable conditions is not actionable.
- **Forgetting to delete cloned repos:** `.owlbear/scratch/research/` repos accumulate if not cleaned. Delete after analysis.
- **T3 without DR:** New capabilities and architecture changes MUST have a blocking DR via `create_dr`. Proceeding without approval risks reversal.
- **Over-long research docs:** 200-line cap exists to force conciseness. If you need more, the analysis is not focused enough.
- **Forgetting to commit:** The commit in Step 7 is a hard gate — never call `end_work` with uncommitted files. If in doubt, run `git status` to check.
