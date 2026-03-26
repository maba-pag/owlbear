# Stripe Minions Agentic Toolchain — Research

> **Owning task:** #647 — Research: Stripe Minions agentic toolchain (blog series)
> **Date:** 2026-03-08 **Status:** Complete

## 1. Context and Question

Stripe's "Minions" are unattended, one-shot coding agents producing 1,300+ merged PRs/week
with zero human-written code. The blog series (Part 1: developer experience, Part 2:
implementation) describes their architecture. This research extracts patterns relevant to
OwlBear and identifies gaps worth closing.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | Stripe Minions Part 1 | <https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents> | .95 |
| 2 | Stripe Minions Part 2 | <https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents-part-2> | .95 |
| 3 | Anthropic — Building Effective Agents | <https://www.anthropic.com/engineering/building-effective-agents> | .80 |

## 3. Key Architectural Patterns

### 3a. Blueprints — Hybrid Workflow + Agent Orchestration

Stripe's core innovation is "blueprints": state machines that **intermix deterministic code
nodes** (git ops, linters, push) **with free-flowing agent nodes** ("implement task", "fix CI
failures"). This maps directly to Anthropic's taxonomy: blueprints combine the predictability
of workflows with agent flexibility (Sources 2, 3).

**OwlBear equivalent:** The orchestrator + planner architecture is structurally identical.
The planner runs 5 deterministic gate checks (status, dependency, atomicity, TDD, clarity),
builds a DAG, and produces a WAVE_PLAN. The orchestrator mechanically dispatches specialized
agent nodes (builder, reviewer, test-writer). This is already a blueprint pattern.

**Gap:** OwlBear's deterministic steps live in the planner; Stripe also puts deterministic
nodes *within* each agent loop (e.g., "always lint before push"). OwlBear's builder runs
ruff as an LLM-decided step, not a guaranteed deterministic post-step.

### 3b. Shift-Left Feedback with Iteration Caps

Stripe enforces local lint on every push (<5s), then at most 2 CI rounds. Autofix results
are applied automatically; only non-autofixable failures go back to the agent (Sources 1, 2).

**OwlBear equivalent:** Max 2 retries per task per pipeline stage (orchestrator enforces).
Builder runs pytest + ruff before advancing. Reviewer independently re-runs tests.

**Gap:** No autofix integration. No deterministic post-implementation lint node that runs
*before* the builder declares completion (the builder can skip or forget).

### 3c. Scoped Rule Files

Stripe uses almost exclusively directory-scoped rules, avoiding global rules that fill
context windows. They standardized on Cursor rule format and sync to Claude Code format for
cross-agent compatibility (Source 2).

**OwlBear equivalent:** `.instructions.md` files with `applyTo` glob patterns provide
identical scoping. Agent-specific skills and boundaries constrain each agent's context.

**Gap:** No cross-format sync (not needed — OwlBear agents share one format). Potentially
worth auditing whether too many global rules exist vs. scoped ones.

### 3d. Centralized MCP Tool Registry with Curated Subsets

Stripe's "Toolshed" hosts ~500 MCP tools. Each agent gets a curated subset; adding a tool
to Toolshed makes it available to all agents. Security controls prevent destructive actions
(Source 2).

**OwlBear equivalent:** Per-agent `tools:` arrays in `.agent.md` files provide explicit
tool subsetting. No centralized registry — tools are declared per-agent.

**Gap:** No dynamic tool discovery or centralized registry. Currently manageable (few agents,
small tool set), but worth tracking as the tool set grows.

### 3e. Context Pre-Hydration

Stripe deterministically runs MCP tools on "likely-looking links" *before* the agent run
starts, to hydrate context without spending agent tokens (Source 1).

**OwlBear equivalent:** None. Agents gather context ad-hoc during their runs.

**Gap:** This is the most actionable new pattern. Pre-hydrating task context (reading linked
files, fetching URLs from task body) before dispatching could save tokens and reduce
first-turn hallucination.

### 3f. Isolated Execution Environments

Stripe uses pre-warmed devboxes (EC2 instances, 10s spin-up, QA-only, no production access,
no internet egress). Agents operate with full permissions inside the sandbox (Source 2).

**OwlBear equivalent:** Three-layer safety: `ApprovalPolicy` gates, `sandbox_path()`
confinement, `CommandSafetyGuard` blocklist. Runs on the developer's laptop (not isolated).

**Gap:** No process-level isolation. Appropriate for laptop-resident architecture — devboxes
solve Stripe's scale problem (1,300 PRs/week), not OwlBear's single-developer use case.

## 4. Comparison: Stripe Minions vs OwlBear

| Pattern | Stripe Minions | OwlBear | Gap? |
|---------|---------------|---------|------|
| Hybrid workflow+agent | Blueprints | Orchestrator+Planner WAVE_PLAN | Minimal |
| Deterministic lint nodes | Within agent loop | LLM-decided (builder) | **Yes** |
| Scoped rules | Dir-scoped Cursor format | `applyTo` globs | Minimal |
| Tool subsetting | Toolshed + curated subsets | Per-agent `tools:` arrays | Minimal |
| Iteration caps | Max 2 CI rounds | Max 2 retries per stage | Minimal |
| Context pre-hydration | Deterministic MCP pre-run | None | **Yes** |
| Autofix integration | Auto-apply CI autofixes | None | Moderate |
| Process isolation | Devboxes (EC2) | sandbox_path() + approval gates | N/A (different scale) |
| Multi-entry (Slack/CLI/web) | All three | CLI + Slack | Minimal |

## 5. Recommendation (.80 confidence)

Two patterns worth adopting:

1. **Context pre-hydration (.80)** — Before dispatching an agent, deterministically extract
   URLs and file paths from the task body and pre-fetch them. Pass the results as
   pre-loaded context to the agent. Saves tokens, reduces hallucination, low complexity.

2. **Deterministic post-implementation lint step (.75)** — Add a mandatory, non-LLM lint
   step that runs after the builder's implementation and before the task advances to review.
   Currently the builder *should* run ruff, but it's LLM-decided. Making it deterministic
   matches Stripe's "contained boxes" philosophy and OwlBear's existing retry cap pattern.

Patterns NOT worth adopting now (YAGNI): centralized tool registry (too few tools),
process isolation (laptop-resident), autofix integration (no CI system yet).

## 6. Follow-up Tasks

```
kanban\kanban-md.exe create "Design context pre-hydration for agent dispatch" --priority important --status backlog --tag "phase-research,scope:core,agent" --body "Before dispatching an agent, extract URLs and file paths from the task body and pre-fetch them into a context bundle. Pass as structured pre-context to the agent prompt.\n\nAC:\n- [ ] Define a pre-hydration function that parses task body for URLs and file paths\n- [ ] Fetch URLs (via trafilatura) and read files into a context dict\n- [ ] Integrate into orchestrator dispatch step (Step 3)\n- [ ] Add config toggle to enable/disable\n- [ ] Tests for URL extraction, file path extraction, and error handling\n\nSee docs/research/stripe-minions.md §3e and §5 for rationale."
```

```
kanban\kanban-md.exe create "Add deterministic post-implementation lint gate" --priority important --status backlog --tag "phase-research,scope:core,agent,tooling" --body "Add a non-LLM deterministic lint step that runs after builder implementation, before advancing to review. Currently ruff is run by the builder (LLM-decided), which can be skipped.\n\nAC:\n- [ ] Define a deterministic lint check in the orchestrator pipeline between builder completion and review dispatch\n- [ ] Lint step runs ruff check + ruff format --check on changed files\n- [ ] On lint failure: auto-retry builder with lint errors as context (counts toward retry cap)\n- [ ] On lint pass: proceed to reviewer dispatch\n- [ ] Document in orchestrator.agent.md and builder.agent.md\n\nSee docs/research/stripe-minions.md §3b and §5 for rationale."
```

```
kanban\kanban-md.exe create "Audit global vs scoped instruction file ratio" --priority nice-to-have --status ideation --tag "phase-research,scope:core,docs" --body "Stripe avoids global agent rules to save context window space. Audit OwlBear's .instructions.md files to check if any global rules (applyTo: '**') could be scoped more narrowly.\n\nAC:\n- [ ] List all .instructions.md files and their applyTo patterns\n- [ ] Identify any with applyTo: '**' that could be narrowed\n- [ ] Propose scoping changes if any found\n\nSee docs/research/stripe-minions.md §3c for rationale."
```
