---
name: w-research
description: "Workflow: Research — source-grounded shaping research for uncertain scope, architecture, or prior art"
user-invocable: false
---

# Research

Investigate a shaping question, produce structured findings with trade-off matrices, write a focused research document when useful, and convert findings into buildable `shape` tasks or decision/action requests.

This workflow is owned by `shaper`. It is not a separate kanban status.

**Kanban operations:** See `h-mcp-kanban` skill — section `## Agent Lifecycle Pattern`.

## Step 0 — Setup

Read `r-pipeline-protocol` and `h-ac-quality` if not already loaded.

Run this only after shaper has claimed a `shape` task with `start_work`. Use the claimed task body as the research context. Do not claim a second task and do not move the task into any `research` status.

Research is required before `APPROVED -> build` when any condition applies:

- Architecture, dependency, storage, security, or user-facing behavior choice is not obvious from the codebase.
- The task asks for a new capability or a meaningful change to agent/pipeline behavior.
- Existing code has no clear owner or precedent for the requested pattern.
- External API/library/tool behavior affects feasibility.
- A previous research doc is cited but may be stale.

For trivial edits, local code search plus a one-line rationale in `## Shape Notes` is enough.

## Research Gate Checklist

Before research can justify `APPROVED -> build`, complete the relevant checklist items. Items 1–6 are mandatory for non-trivial shaping research; items 7–8 are recommended.

1. **Theoretical validity** — Sound concept? Right approach?
2. **Environment audit** — Capability already provided by IDE, runtime, extensions, or existing tooling?
3. **Prior art** — 2+ GitHub repos, articles, or docs showing how others solved this.
4. **Technical feasibility** — Works in our stack (Python 3.12, FastMCP, VS Code + Copilot)? Blockers?
5. **Architecture fit** — Integrates with existing OwlBear components? Interfaces?
6. **Implementation approach** — Patterns, idioms, data structures to adopt.
7. **Testing strategy** _(recommended)_ — How to test? Unit, integration, mocks? Coverage?
8. **Findings documented** _(recommended)_ — Notes in `## Shape Notes` or linked `.owlbear/research/{slug}.md`.

For trivial tasks (rename, typo, config tweak): items 1–4 get a one-liner `N/A — trivial change, rationale: X`.

## Step 1 — Clarify Scope

**Fail fast on invalid inputs.** `TEMP-*` titles or empty bodies = use `askQuestions` if the user is present; otherwise create a blocking request via `create_request` and block the task.

If the task has scoped content but needs clarification:

- Present structured options to the user.
- Follow `h-codebase-orientation` to establish the local stack and project boundaries. Apply principles
 from shared OwlBear rules, not from project-specific instructions.

## Step 2 — Check Existing Research

Before gathering sources:

1. Search `.owlbear/research/` for the task ID and topic keywords. If a doc references this task, read it first.
2. Check task body for `See .owlbear/research/` links.
3. If a complete, recent doc exists: do a validation pass instead of full research — confirm the doc is current, verify codebase state, skip to Step 8 if findings hold.

> Skipping this check is the most common research time-sink.

## Step 3 — Research Scope Gate

Bounded read-only research needed to assess the active shaping question is autonomous. This includes
local code and documentation, focused web/source-page lookups, and a proportionate multi-source or
comparative check when architecture, contracts, or prior art require it.

Obtain explicit user approval through `askQuestions` before:

- an exceptional-cost or open-ended investigation whose scope materially exceeds the active change;
- cloning a large external repository when source pages or focused retrieval are insufficient;
- executing external code, setup scripts, package installs, hooks, or other untrusted operations.

Present the remaining question, why bounded research is insufficient, proposed scope, expected outcome,
cost level, and a narrower alternative. If the user is unavailable, create a blocking request and
keep the task in `shape`.

For an approved clone, use `.owlbear/scratch/research/{repo-name}/`, inspect it only, record the repository URL and resolved commit/ref in the research findings, and delete the clone in Step 9. Do not execute repository code, setup scripts, package installs, or hooks.

## Step 4 — Gather Sources

Find 2+ authoritative sources per claim:

- **Codebase:** follow `h-codebase-orientation` for indexes, exact search, and Semble. Use direct reads
  and exact tools to ground findings.
- **Explore:** use the `Explore` subagent for broad read-only codebase context when local search would be noisy.
- **Web:** use the `web` toolset for known public pages, browser acquisition for rendered or authenticated pages, and `markitdown/*` for supported document conversion. Open-ended DDGS search is unavailable; do not silently substitute another search provider.
- **External repositories:** prefer source pages, docs, and extracted files. Clone only when the
  approved exceptional investigation needs cross-file source inspection.

Track: name, URL, what was taken, relevance score (0.0–1.0).

## Step 5 — Analyze and Compare

Structure analysis as trade-off matrices:

- Comparison tables (rows = options, columns = criteria).
- Confidence scores on recommendations (0.0–1.0).
- Risks and mitigations for each option.
- Apply KISS, YAGNI, DRY principles.

## Step 6 — Challenge Proposed Recommendation

Before approving a build-bound shape after non-trivial research, challenge the shaping recommendation using `shaper-challenger`. Mandatory when Step 3 produces a recommendation; skip for info-only or trivial research.

**Fallback:** If the subagent call errors, do not approve solely on unchallenged research. Either run a narrower local check, ask the user, or `REFINE -> shape` with the missing challenge noted.

## Step 7 — Write Research Document

Create `.owlbear/research/{slug}.md`:

```markdown
# {Title}

> **Owning task:** #{id} — {title}
> **Date:** {date}
> **Question:** {specific shaping question}

## 1. Context and Question
## 2. Sources Studied (table)
## 3. Analysis (trade-off matrices)
## 4. Recommendation (with confidence)
## 5. Follow-up Tasks
```

Max 200 lines. Every claim needs a source reference.

Include challenge note in section 4 when a recommendation affects build approval: `Challenge: {proceed|reconsider|block} — confidence in original: {score}`

## Step 8 — Classify Outcome and Create Follow-Up Tasks

### Tier Classification

Classify every finding before acting:

| Tier | Category | Action |
|------|----------|--------|
| T1 — Autonomous | Bug fix, refactor, config, perf | Shape directly — update AC/notes or create routed follow-up tasks |
| T2 — Advisory | Trade-offs, no T3 triggers | Ask the user via `askQuestions` when present; otherwise create advisory request via `create_request` |
| T3 — Mandatory | New capability, arch/security/breaking change | Create blocking request via `create_request` |

**T3 triggers (any one makes it T3):** Adds new capability, changes architecture, modifies agent/pipeline behavior, alters security policy, changes user-facing behavior, proposes deprecation.

### Create Follow-Up Tasks

Create concrete follow-up tasks with explicit statuses: build-ready follow-ups in `build`, aggregate follow-ups in `collect`, and no staging task for unresolved findings. Use `w-task-decomposition` for multi-task splits. For findings requiring user decisions, use `askQuestions` when the user is present or `create_request` when an existing board task must be blocked.

## Step 9 — Finalize Artifacts

1. Add rows to `.owlbear/sources/overview.md` for external sources (see
   `r-workspace-governance` → Attribution).
2. Delete any cloned repos from `.owlbear/scratch/research/`.

## Step 10 — Record In Shape Notes And Advance

Include the research summary and challenge results in `## Shape Notes` through the `end_work` note.

Then use shaper's normal route:

- `APPROVED -> build` when research supports buildable AC and shaper-challenger agrees.
- `REFINE -> shape` when research exposes missing scope, dependency, or feasibility work.
- `BLOCK -> shape` when `create_request` is required.

Return Channel A signal per `r-pipeline-protocol`.

## Output Template

Append to task body before advancing:

```
## Research
- Research doc: .owlbear/research/{slug}.md
- Sources: {N} studied, {M} high-relevance
- Recommendation: {brief} (confidence: {.XX})
- Follow-up tasks created: {list of IDs with statuses}
- Decision requests: {N created, or "none"}

## Challenge Results
- Challenger: {proceed/reconsider/block} (or FALLBACK — {reason})
- Confidence in original: {score}
- Key challenges: {list}
- Shaper response: {accepted/rebutted/revised} — {rationale}
```

## Verification Checklist

- [ ] Every claim has 2+ sources
- [ ] Analysis uses comparison tables with confidence scores
- [ ] Research doc 200 lines or fewer
- [ ] Follow-up kanban tasks are concrete and actionable; build-ready follow-ups are created in `build`, aggregate follow-ups in `collect`, and unresolved follow-ups are not created as staging tasks
- [ ] Did NOT create/edit source code
- [ ] External sources logged in `.owlbear/sources/overview.md`
- [ ] Cloned repos deleted from `.owlbear/scratch/research/`
- [ ] Shaper-challenger invoked for build-bound recommendation (or fallback routed to refine/block)
- [ ] Tier classification applied to every finding (T1/T2/T3)
- [ ] Research summary appears in `## Shape Notes`
- [ ] Task either moved to `build`, stayed in `shape`, or was blocked with a request

## Known Pitfalls

- **Skipping pre-flight check:** Multiple research cycles have been wasted because existing docs were missed. Always check `.owlbear/research/` first.
- **Unbounded research:** Bounded evidence gathering is autonomous, but an exceptional-cost or
  materially broader investigation still needs an explicit scope decision.
- **Follow-up tasks without AC:** Every follow-up task needs concrete acceptance criteria. "Improve X" without measurable conditions is not actionable.
- **T3 without request:** New capabilities and architecture changes need a blocking request via `create_request` when the user is not resolving it live. Proceeding without approval risks reversal.
- **Over-long research docs:** 200-line cap exists to force conciseness. If you need more, the analysis is not focused enough.
- **Separate research column:** Keep research inside `shape`; do not reintroduce a separate `research` status.
