# Agent Quality Analysis — Structural Refactoring Plan

> **Date:** 2026-02-04 (updated 2026-02-05)
> **Status:** In Progress — prior art research complete, awaiting user approval on refactoring plan
> **Trigger:** User observed two systemic quality problems during Wave 4–6 orchestration, then escalated to a full structural review

## 1. Context and Question

During Waves 4–6, two recurring problems degraded agent quality:

1. **Task batching** — The orchestrator dispatched multiple kanban tasks to a single subagent (e.g., "Build: #410+#411+#412", "Build: #401+#405", "Build: #416+#419"), defeating task granularity and prioritizing speed over quality.
2. **Terminal output re-running** — Agents wasted 2–3 tool calls per command by re-running with different PowerShell piping strategies (`Select-Object -Last 15`, then `-Last 20`, then no piping) trying to capture truncated output.

The question: are these instruction problems, or are the instructions too dense for the critical rules to stick?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| VS Code Custom Agents docs | <https://code.visualstudio.com/docs/copilot/customization/custom-agents> | 0.9 — Defines agent.md format, frontmatter properties, handoffs |
| VS Code Subagents docs | <https://code.visualstudio.com/docs/copilot/agents/subagents> | 0.95 — Orchestration patterns, `agents` property, coordinator-worker |
| GitHub Custom Instructions docs | <https://docs.github.com/en/copilot/customizing-copilot/adding-custom-instructions-for-github-copilot> | 0.7 — Instruction file patterns, path-specific instructions |
| OwlBear orchestrator.agent.md | .github/agents/orchestrator.agent.md (404 lines) | 1.0 — Contains the serial chain optimization that enables batching |
| OwlBear builder.agent.md | .github/agents/builder.agent.md (346 lines) | 1.0 — Contains "one task at a time" boundary that gets overridden |

## 3. Root Cause Analysis

### Problem 1: Task Batching

**Direct cause:** The orchestrator's step 4 defines a "Serial chain optimization":

> *"If tasks A → B form a chain touching the same files (e.g., test + implementation for the same module), combine them into a single subagent run."*

The good_example shows test+impl pairs (#45+#47, #46+#48) as the intended use. But the language "touching the same files" is vague enough to justify batching any related tasks.

**Contradiction in the system:** The builder's boundaries state:

> *"One task at a time — never work on multiple tasks simultaneously"*

But the orchestrator's step 6 says:

> *"For serial chains (test + impl pairs on same module): dispatch ONE builder subagent that executes both tasks sequentially"*

The orchestrator wins this conflict because it writes the dispatch prompt. The builder receives "Build: #410+#411+#412" and complies because the instruction came from its coordinator. **The builder's boundary is unenforceable when the orchestrator overrides it.**

**Evidence from this session:**

| Dispatch | Task types | Was this a test+impl pair? |
|----------|-----------|---------------------------|
| Build: #410+#411+#412 | 3 separate implementation tasks (provenance chain) | No |
| Build: #401+#405 | BookmarkToolset impl + tests | Loosely related, not a TDD pair |
| Build: #416+#419 | Slack approval + Slack tests | Loosely related, not a TDD pair |

None of these were the canonical test+impl pairs the optimization was designed for.

### Problem 2: Terminal Output Re-running

**Direct cause:** No agent definition contains guidance on terminal output handling. The system prompt mentions a 60KB truncation limit, but:

- It's in the VS Code system context, not in agent files
- No remediation strategy is provided
- Each agent improvises differently

**Contributing factors:**

- No standard patterns for common commands (git, pytest, kanban-md)
- No guidance on when to redirect output to a file vs. pipe
- No mention of `get_terminal_output` tool as a recovery mechanism
- Agents default to trial-and-error with PowerShell piping

### Problem 3: Instruction Density (underlying both)

| Agent | Lines | Critical rules buried in |
|-------|-------|------------------------|
| orchestrator | 404 | Step 4 (serial chain), boundaries list |
| builder | 346 | Single bullet in boundaries |
| reviewer | 425 | Scattered across boundaries + examples |
| writer | 366 | Workflow steps |
| closer | 303 | Boundaries section |
| architect | 371 | Workflow steps |
| researcher | 319 | Boundaries section |
| kanban-planner | 314 | Context section |

Critical rules compete with workflow steps, tables, examples, and anti-patterns for attention. The most important constraints (like "one task at a time") are single bullet points in multi-page files. There is no priority hierarchy — a critical rule like "never batch tasks" has the same visual weight as a formatting preference.

## 4. Prior Art Research

Three reference repositories were analyzed in depth, plus Anthropic's canonical "Building effective agents" guide.

### 4.1 Repositories Analyzed

| Repository | Agents | Architecture | Agent Length |
|------------|--------|-------------|-------------|
| [TheSoftwareHouse/copilot-collections](https://github.com/TheSoftwareHouse/copilot-collections) | 12 | Orchestrator → researcher/creator/reviewer/engineer | 100–200 lines |
| [rjmurillo/ai-agents](https://github.com/rjmurillo/ai-agents) | 25+ | Orchestrator → analyst/implementer/critic/qa/security/memory | 500–1500 lines |
| [doggy8088/github-copilot-configs](https://github.com/doggy8088/github-copilot-configs) | 150+ (community) | gem-orchestrator → gem-researcher/planner/implementer/reviewer | 60–130 lines |
| [Anthropic blog](https://www.anthropic.com/research/building-effective-agents) | — | Patterns: orchestrator-workers, prompt chaining, ACI design | — |

### 4.2 Key Patterns Discovered

#### Pattern A: Strict separation of concerns (TSH)

TSH defines a clean ontology:

- **Agent** (.agent.md) = WHO — persona, behavior, responsibilities, tool access
- **Skill** (SKILL.md) = HOW — reusable workflows, domain knowledge, step-by-step processes
- **Prompt** (.prompt.md) = WHAT — workflow trigger, task starter, routes to agent + model
- **Instructions** (.instructions.md) = RULES — coding standards, project conventions, always-applied

Their orchestrator states: *"Context is precious — your conversation context should contain only user interactions, design decisions, and synthesized worker summaries. Never raw research output, intermediate file contents, or documentation dumps. Every token in your context must earn its place."*

**Progressive disclosure tiers:** Discovery (~100 tokens: name + description) → Activation (<5,000 tokens: body loaded on trigger) → Resource (on demand: templates, examples).

**Our gap:** We mix workflow steps, rules, examples, anti-patterns, and tool guidance in each agent. Skills contain reference material (kanban-md CLI) rather than reusable workflows. No progressive disclosure.

#### Pattern B: Structured delegation protocol (gem-orchestrator)

gem-orchestrator defines typed delegation parameters per agent:

```yaml
delegation_protocol:
  base_params: [task_id, plan_id, plan_path, task_definition]
  agent_specific_params:
    gem-implementer: [tech_stack, test_coverage, estimated_lines]
    gem-reviewer: [review_depth, security_sensitive, review_criteria]
```

The orchestrator also uses `disable-model-invocation: true`, making it pure delegation with no own generation.

**Our gap:** Our orchestrator has a natural-language workflow (steps 1–7) with the delegation logic embedded in prose. No structured parameters, no routing table.

#### Pattern C: Agent capability matrix (rjmurillo)

rjmurillo maintains an explicit routing table:

| Work Type | Route To | What They Do | What They Can't |
|-----------|----------|-------------|----------------|
| Code changes | implementer | Production code, tests, commits | Plan-dependent |
| Plan validation | critic | Scope, risk, alignment | No code |
| Investigation | analyst | Root cause, API research | Read-only |

Plus explicit architecture constraint: *"One level deep — subagents CANNOT delegate to other subagents."*

**Our gap:** We have no capability matrix. The orchestrator makes routing decisions from its persona description, not from structured routing logic.

#### Pattern D: XML structuring for clear sections (gem, TSH)

Both gem and TSH agents use XML tags for section boundaries:

```xml
<role>Code Implementer: executes architectural vision</role>
<workflow>Analyze → Execute (TDD) → Handle Failure → Reflect → Return</workflow>
<operating_rules>YAGNI, KISS, DRY, never TBD/TODO...</operating_rules>
<verification_criteria>get_errors → typecheck → unit tests → failure modes</verification_criteria>
```

This gives the LLM clear structure markers vs. flat markdown.

**Our gap:** We use `<persona>` and `<multi_agent_context>` but the rest is flat markdown with `##` headings.

#### Pattern E: Verification criteria built into agents (gem)

gem-implementer defines explicit verification steps:

```yaml
- step: "Run get_errors (compile/lint)"
  pass_condition: "No errors or warnings"
  fail_action: "Fix all errors before proceeding"
```

**Our gap:** Our builder says "run pytest + ruff" in the workflow but has no structured pass/fail criteria.

#### Pattern F: Triage before orchestrating (rjmurillo, Anthropic)

rjmurillo orchestrator does mandatory triage:

| Task Type | Minimum Agents | Example |
|-----------|---------------|---------|
| Question | Answer directly | "How does X work?" |
| Documentation | implementer → critic | "Update README" |
| Code changes | implementer → critic → qa → security | "Fix the bug" |

Anthropic: *"Finding the simplest solution possible, and only increasing complexity when needed."*

**Our gap:** Our orchestrator always runs the full pipeline. No triage step.

### 4.3 Quantitative Comparison

| Metric | OwlBear | TSH | gem | rjmurillo |
|--------|---------|-----|-----|-----------|
| Avg agent lines | 348 | ~150 | ~100 | ~700 |
| Skills referenced | 3 (reference docs) | 18 (workflow modules) | 0 (inline) | 0 (memory-based) |
| Instruction files | 2 (python, research-docs) | 0 (copilot-instructions only) | 0 | 5 (agent-prompts, skills, docs, security, testing) |
| XML structuring | Partial (`<persona>`, `<multi_agent_context>`) | Full | Full | None (markdown) |
| Delegation protocol | Prose workflow | Per-agent decision logic | Typed params per agent | Routing table + OODA |
| Critical rules prominence | Buried in boundary lists | `<principles>` at top | `<operating_rules>` section | "Core Identity" paragraph |
| Frontmatter `agents:` | Not used | Used (orchestrator lists 4 workers) | Not used | Not used |
| `user-invokable: false` | Not used | Not used | Not used | Not used |
| Verification criteria | Informal ("run pytest + ruff") | Skill-based checklists | Structured YAML | Memory-based |

## 5. Decisions Already Made

These were discussed and approved in the prior session:

| # | Decision | Confidence | User selection |
|---|----------|-----------|---------------|
| D1 | Remove serial chain optimization | .95 | "one task per agent, multiple agents in parallel" |
| D2 | Create shared terminal.instructions.md | .90 | Prevention (concise flags) + scratch file fallback |
| D3 | Add critical rules sections + shared instruction file | .90 | Both approaches combined |

## 6. Refactoring Plan

Based on prior art analysis, the refactoring targets three layers of improvement.

### Layer 1: Content Architecture (biggest impact)

**Goal:** Apply TSH's separation principle — agents define WHO, skills define HOW, instructions define RULES. Reduce agent length from ~350 to ~150 lines.

#### 6.1 Extract reusable workflows into skills

| New Skill | Extracted From | Content |
|-----------|---------------|---------|
| `tdd-workflow` | builder | TDD cycle: read AC → write failing test → implement → verify → advance. Currently 80+ lines in builder. |
| `code-review` | reviewer | Review checklist: run tests → lint → read code → verify each AC line → verdict. Currently 100+ lines in reviewer. |
| `docs-gate` | writer | Docs-gate checklist: check copilot-instructions, docstrings, sources.md, README, research docs. Currently in copilot-instructions.md AND writer agent (duplicated). |
| `task-verification` | closer | Verification protocol: check AC with evidence, score confidence, archive. Currently 60+ lines in closer. |

Each skill becomes a `SKILL.md` file in `.github/skills/<name>/` containing the step-by-step workflow. Agents reference skills but don't inline them.

#### 6.2 Create cross-agent instructions

| New Instruction | `applyTo` | Content |
|----------------|-----------|---------|
| `terminal.instructions.md` | `"**"` | Terminal output handling: concise flags, scratch file fallback, never re-run for different piping (D2) |
| `agent-common.instructions.md` | `".github/agents/**"` | Rules shared across all agents: confidence scores in askQuestions, manage_todo_list usage, kanban-md compact flag, surgical changes, evidence over self-reports |

**Rationale:** Rules currently duplicated across 4+ agents (e.g., "use manage_todo_list extensively", "confidence scores in askQuestions") move to a single instruction file that auto-applies to all agent files.

#### 6.3 Slim agents to ~150 lines (excluding examples)

The ~150 line target applies to the structural content. Concise good/bad examples are kept separately and don't count toward this budget.

Each agent keeps ONLY:

1. **Frontmatter** — name, description, tools, `agents:` (if dispatching), `user-invokable`
2. **`<persona>`** — 3–5 sentences defining WHO this agent is, with emotional motivation that makes quality intrinsic rather than directive
3. **`<critical_rules>`** — 3–5 non-negotiable rules, bolded (D3)
4. **`<multi_agent_context>`** — Pipeline position, handoff points
5. **`<responsibilities>`** — What this agent does (not how — that's in skills)
6. **`<constraints>`** — Hard boundaries (read-only, no code, one task at a time)
7. **`<output_format>`** — What the response should look like
8. **`<examples>`** — Concise good/bad examples (exempt from line budget)

**Emotional motivation in personas:** The persona should encode values that make correct behavior emerge naturally, not just enforce rules. Examples:

- Builder: *"You take pride in your test suite — a test that passes on first write is suspicious, not a victory. You want each test to catch a real bug."*
- Reviewer: *"You protect the team from shipping broken code. Every rubber-stamp PASS you issue is a debt you'll pay in production."*
- Orchestrator: *"Each task deserves full attention from its agent. Cramming multiple tasks into one dispatch is disrespectful to the work."*

These implicit rules are more durable than explicit directives because they shape reasoning rather than constraining outputs.

Everything else (workflow steps, detailed examples, anti-patterns, tool guidance) moves to skills or instructions.

### Layer 2: Orchestrator Redesign

#### 6.4 Add structured delegation logic

Replace the orchestrator's prose workflow (steps 1–7) with:

- **Triage table** — classify task type, determine minimum agent sequence
- **Agent capability matrix** — per-agent routing table with "route to / best for / can't do"
- **Delegation template** — structured prompt format for each agent type
- **One-task-per-dispatch rule** — in `<critical_rules>`, not buried in workflow (D1)

#### 6.5 Add triage step

Before dispatching, orchestrator classifies the work:

| Complexity | Agents Needed | Example |
|-----------|--------------|---------|
| Trivial (config, rename) | builder only | "Rename function X" |
| Standard (implementation) | builder → reviewer → writer → closer | "Implement feature Y" |
| Complex (multi-module) | researcher → builder → reviewer → writer → closer | "Add subsystem Z" |
| Research | researcher only | "Investigate approach for W" |

### Layer 3: Platform Features

#### 6.6 Adopt `agents` frontmatter

```yaml
# orchestrator.agent.md
agents: [builder, reviewer, writer, closer, architect, researcher, kanban-planner]

# No other agent gets `agents:` — only orchestrator dispatches
```

#### 6.7 Mark pipeline agents as non-user-invokable

| Agent | `user-invokable` | Rationale |
|-------|-----------------|-----------|
| orchestrator | true | User entry point for board execution |
| kanban-planner | true | User entry point for task creation |
| researcher | true | User entry point for investigations |
| architect | true | User entry point for design review |
| builder | false | Only dispatched by orchestrator |
| reviewer | false | Only dispatched by orchestrator |
| writer | false | Only dispatched by orchestrator |
| closer | false | Only dispatched by orchestrator |

**Trade-off:** User loses direct invocation of builder/reviewer/writer/closer. This matches all three reference repos' approach and the Anthropic pattern.

## 7. Comparison: Current vs. Proposed

| Aspect | Current | Proposed |
|--------|---------|---------|
| Agent length | 300–425 lines | ~150 lines |
| Skills | 3 reference docs | 3 reference + 4 workflow skills |
| Instructions | 2 code-scoped | 2 code-scoped + 2 cross-agent |
| Workflow details | Inline in each agent | Extracted to skills |
| Common rules | Duplicated across agents | Single `agent-common.instructions.md` |
| Terminal guidance | None | `terminal.instructions.md` |
| Critical rules | Buried in boundaries | `<critical_rules>` at top of each agent |
| Orchestrator delegation | Prose steps 1–7 | Triage + routing table + delegation template |
| Task isolation | Contradictory (orchestrator vs. builder) | Single rule in orchestrator `<critical_rules>` |
| XML structure | Partial | Full (`<persona>`, `<critical_rules>`, `<responsibilities>`, `<constraints>`, `<output_format>`) |
| Frontmatter | Basic | + `agents:`, `user-invokable: false` |

## 8. Implementation Sequence

| # | Task | Priority | Depends On |
|---|------|---------|-----------|
| T1 | Create `terminal.instructions.md` | needed | — |
| T2 | Create `agent-common.instructions.md` | needed | — |
| T3 | Extract `tdd-workflow` skill from builder | needed | — |
| T4 | Extract `code-review` skill from reviewer | needed | — |
| T5 | Extract `docs-gate` skill from writer | needed | — |
| T6 | Extract `task-verification` skill from closer | needed | — |
| T7 | Rewrite orchestrator with triage + routing table + `agents:` frontmatter | needed | T1, T2 |
| T8 | Slim builder to ~150 lines + `<critical_rules>` + ref skill | needed | T1, T2, T3 |
| T9 | Slim reviewer to ~150 lines + `<critical_rules>` + ref skill | needed | T1, T2, T4 |
| T10 | Slim writer to ~150 lines + `<critical_rules>` + ref skill | needed | T1, T2, T5 |
| T11 | Slim closer to ~150 lines + `<critical_rules>` + ref skill | needed | T1, T2, T6 |
| T12 | Slim architect to ~150 lines + `<critical_rules>` | needed | T1, T2 |
| T13 | Slim researcher to ~150 lines + `<critical_rules>` | needed | T1, T2 |
| T14 | Slim kanban-planner to ~150 lines + `<critical_rules>` | needed | T1, T2 |
| T15 | Set `user-invokable: false` on builder/reviewer/writer/closer | important | T8–T11 |
| T16 | Update copilot-instructions.md agent/skill/instruction inventories | needed | T1–T14 |
| T17 | End-to-end test: run orchestrator on a real task through the pipeline | needed | T7–T14 |

## 9. Sources

| Source | URL | What | Where Used |
|--------|-----|------|-----------|
| TheSoftwareHouse/copilot-collections | <https://github.com/TheSoftwareHouse/copilot-collections> | Separation of concerns ontology, progressive disclosure, delegation decision logic | Section 4.2 Pattern A, agent template |
| rjmurillo/ai-agents | <https://github.com/rjmurillo/ai-agents> | Agent capability matrix, OODA triage, one-level-deep constraint, critic pattern | Section 4.2 Pattern C/F, orchestrator redesign |
| doggy8088/github-copilot-configs | <https://github.com/doggy8088/github-copilot-configs> | XML structuring, typed delegation protocol, disable-model-invocation, verification criteria | Section 4.2 Pattern B/D/E, agent template |
| Anthropic | <https://www.anthropic.com/research/building-effective-agents> | ACI design, simplicity principle, orchestrator-workers pattern | Section 4.2 Pattern F, overall philosophy |
