# Inter-Agent Communication Protocol: Task Body as Shared Memory

> **Owning task:** #684 — Inter-agent communication protocol: task body as shared memory
> **Date:** 2026-03-08 **Status:** Complete

## 1. Context and Question

The orchestrator accumulates 2000–15000 tokens of stale subagent output across waves. Two consumers need different data: the orchestrator needs routing signals (pass/fail, next status); the next-pipeline agent needs rich context (evidence, tables, findings). Currently both go through the same return channel. Should we split into two channels: (a) routing signal returned to caller, (b) rich context written to kanban task body?

## 2. Sources Studied

| # | Source | URL | Relevance | What we took |
|---|--------|-----|-----------|--------------|
| 1 | LangGraph Agent Supervisor | blog.langchain.com/langgraph-multi-agent-workflows | .90 | Independent scratchpads per agent; only final responses to supervisor |
| 2 | OpenAI Swarm `Result` | github.com/openai/swarm | .85 | `Result(value, agent, context_variables)` — explicit separation of routing data vs shared state |
| 3 | Blackboard pattern (Wikipedia) | en.wikipedia.org/wiki/Blackboard_(design_pattern) | .80 | Structured global memory (blackboard) + control component reads selectively |
| 4 | CrewAI task context | docs.crewai.com/concepts/collaboration | .75 | `context=[previous_task]` passes task output downstream; lead sees delegation results only |
| 5 | PydanticAI structured output | ai.pydantic.dev/multi-agent-applications | .85 | `output_type=TaskResult` gives orchestrator structured routing data, not prose |

## 3. Analysis

### 3.1 Pattern Comparison

| Criterion | Shared scratchpad (LangGraph collab) | Supervisor + independent scratchpads (LangGraph supervisor) | Swarm Result separation | Blackboard |
|-----------|--------------------------------------|-------------------------------------------------------------|-------------------------|------------|
| Orchestrator sees | Everything | Final response only | `value` string only | Reads selectively |
| Context growth | O(agents × steps) | O(agents × 1 summary) | O(1) per handoff | Bounded by read policy |
| Next-agent context | Full history | Must explicitly fetch | Via `context_variables` | Reads from blackboard |
| OwlBear fit | Current (broken) state | **Best fit** | Close match | Conceptual ancestor |

**Finding:** All 4 sources confirm the same principle — the coordinator should receive minimal routing data while rich context lives in shared state. LangGraph's "Agent Supervisor" and Swarm's `Result` both implement this pattern explicitly.

### 3.2 Two-Channel Model for OwlBear

**Channel A — Routing Signal** (returned to caller, max 2 lines):

```
{VERDICT} #{id} -> {target_status} | {one-line evidence}
```

Examples:

- `DONE #480 -> review | 12 passed, ruff clean, 94% coverage`
- `PASS #480 -> docs | confidence .95, all AC met`
- `FAIL #480 -> todo | AC line 3 unmet: missing error handling test`
- `APPROVED #480 -> todo | AC refined, no splits needed`

**Channel B — Task Body Section** (written via `kanban-md edit ID -a "TEXT" -t`):

Each agent appends a headed section. Next-pipeline agent reads via `kanban-md show ID`.

### 3.3 Routing Signal Format Per Agent

| Agent | Verdict tokens | Format | Target status |
|-------|---------------|--------|---------------|
| builder | `DONE` / `BLOCKED` | `DONE #{id} -> review \| {test_count} passed, ruff {status}` | review / todo |
| reviewer | `PASS` / `FAIL` | `PASS #{id} -> docs \| confidence {.XX}` | docs / todo / backlog |
| writer | `DONE` / `REJECTED` | `DONE #{id} -> done \| docs gate passed` | done / review |
| auditor | `ARCHIVED` / `REJECTED` | `ARCHIVED #{id} \| confidence {.XX}` | archived / review / backlog |
| architect | `APPROVED` / `REFINE` / `SPLIT` / `BLOCK` | `APPROVED #{id} -> todo \| {one-liner}` | todo / ideation |
| researcher | `DONE` | `DONE #{id} -> backlog \| doc: docs/{slug}.md` | backlog |
| kanban-planner | `DONE` | `DONE \| {N} tasks created` | N/A (no target) |
| curator | `DONE` | `DONE \| {N} promoted, {M} pruned` | N/A |
| orchestrator | N/A (not a subagent) | N/A | N/A |

### 3.4 Task Body Section Format Per Agent

| Agent | Section header | Content | Est. tokens |
|-------|---------------|---------|-------------|
| builder | `## Builder Notes` | Files changed, coverage %, fixes applied, evidence details | 150–300 |
| reviewer | `## Review Evidence` | AC compliance table, test quality matrix, security findings, rejection details | 200–600 |
| writer | `## Docs Gate` | Checklist table, files updated, scratch cleaned | 100–200 |
| auditor | `## Audit` | Evidence summary, confidence score, action taken | 100–200 |
| architect | `## Architecture Review` | AC assessment table, architecture notes, dependencies | 150–400 |
| researcher | `## Research` | Pointer: `See docs/{slug}.md` + 1-line summary | 20–40 |
| kanban-planner | `## Planning` | Task breakdown table, dependency graph | 200–400 |
| curator | `## Curation` | Statistics, promotions, conflicts | 150–300 |

### 3.5 Full Audit: Current Output Fields → Channel Assignment

**Builder** (current: 150–400 tokens returned):

| Field | Channel | Rationale |
|-------|---------|-----------|
| `Task: #{id} — {title}` | Signal | Routing identity |
| `Tests: {N} tests, all passing` | Signal | Binary pass/fail for routing |
| `Lint: ruff clean` | Signal | Binary pass/fail for routing |
| `Files changed: {list}` | Task body | Reviewer needs, orchestrator doesn't |
| `Coverage: {X}% on {module}` | Task body | Reviewer needs for verification |
| `Evidence: pytest output, ruff output` | Task body | Reviewer needs full evidence |

**Reviewer** (current: 300–800 tokens returned):

| Field | Channel | Rationale |
|-------|---------|-----------|
| `Verdict: PASS/FAIL` | Signal | Routing decision |
| `confidence: .XX` | Signal | Orchestrator uses for retry/escalate |
| Test results summary | Task body | Writer/auditor verification |
| Lint results | Task body | Not needed for routing |
| Coverage % | Task body | Not needed for routing |
| Test quality table (5 rows) | Task body | Auditor verification |
| Security review | Task body | Auditor verification |
| AC compliance table | Task body | Auditor verification |
| Rejection details table | Task body | Builder needs for fixes |

**Writer** (current: 200–400 tokens returned):

| Field | Channel | Rationale |
|-------|---------|-----------|
| Action taken (kanban command) | Signal | Routing confirmation |
| Docs-gate checklist table (6 rows) | Task body | Auditor verification |
| Files updated list | Task body | Auditor verification |
| Scratch files cleaned | Task body | Auditor verification |

**Auditor** (current: 200–500 tokens returned):

| Field | Channel | Rationale |
|-------|---------|-----------|
| `ARCHIVED` / `REJECTED` + confidence | Signal | Routing |
| Audit report table | Task body | Historical record |
| Commit log table | Task body | Historical record |
| Push status | Signal | Orchestrator needs confirmation |

**Architect** (current: 200–500 tokens returned):

| Field | Channel | Rationale |
|-------|---------|-----------|
| Verdict (approve/refine/split/block) | Signal | Routing decision |
| Summary table | Signal | Orchestrator batch overview |
| AC assessment table | Task body | Builder needs for implementation |
| Architecture notes | Task body | Builder needs for design guidance |
| Dependencies | Task body | Builder needs |

**Researcher** (current: 500–5000+ tokens returned):

| Field | Channel | Rationale |
|-------|---------|-----------|
| Completion status | Signal | Routing |
| Research document | File reference | Always `docs/{slug}.md` |
| Follow-up task commands | Task body | Architect needs for review |
| Attribution rows | File reference | `docs/sources.md` (already there) |

**Kanban-planner** (current: ~300 tokens returned):

| Field | Channel | Rationale |
|-------|---------|-----------|
| Task count created | Signal | Routing |
| Task breakdown table | Task body | Architect review |
| kanban-md commands | Task body | Execution reference |
| Dependency graph | Task body | Architect review |

**Curator** (current: ~200 tokens returned):

| Field | Channel | Rationale |
|-------|---------|-----------|
| Statistics summary | Signal | Orchestrator awareness |
| Promotions table | Task body | Knowledge record |
| Conflicts table | Task body | Human review |

### 3.6 File-Reference Threshold

**Context budget analysis:**

Typical task body after full pipeline (builder + reviewer + writer + auditor):

- Builder Notes: ~200 tokens
- Review Evidence: ~400 tokens
- Docs Gate: ~150 tokens
- Audit: ~150 tokens
- **Total: ~900 tokens**

Agent context windows (~128K tokens for Claude/GPT-4 class):

- 900 tokens = 0.7% of context — well within budget

**Threshold rule:** A single agent section exceeding **1500 tokens** should use a file reference instead (`See docs/scratch/{task-id}-{agent}.md`). In practice, only the researcher hits this — and it already uses file references.

The 1500-token threshold is derived from: total pipeline budget ~3000 tokens (4 agents × ~750 avg) leaves room for 2× the average per agent before concern. This is conservative — even 5000 tokens total is < 4% of a 128K context window.

### 3.7 Technical Feasibility

| Concern | Assessment | Risk |
|---------|------------|------|
| `kanban-md edit ID -a "TEXT" -t` | Works, appends with timestamp | Low |
| PowerShell escaping of tables/pipes in body text | Double-quote wrapping + backtick-escape for special chars; or pipe via file | Medium |
| LF line endings (known issue) | Agents must ensure LF; use `[IO.File]::WriteAllText` if needed | Low |
| Body field size limits | No limit documented in kanban-md; Go string capacity is effectively unlimited | Low |
| Reading task body (`kanban-md show ID`) | Works, returns full body | Low |
| Section parsing | Agents grep for `## {Header}` to find their predecessor's section | Low |

**Main risk:** PowerShell escaping when appending markdown tables. Mitigation: write body content to a temp file, then use `--body` with file content (or `--append-body` with simple text, avoiding pipes in CLI args).

## 4. Recommendation (.90 confidence)

**Adopt the two-channel model.** It maps directly to proven patterns in LangGraph (Agent Supervisor), OpenAI Swarm (`Result` separation), and the classic Blackboard pattern. All sources agree: coordinators should receive routing signals only; rich context belongs in shared state.

**Implementation approach:**

1. Add communication protocol to `agent-common.instructions.md` (shared rules)
2. Rewrite each agent's `<output_format>` to the two-channel model
3. Update orchestrator to only parse routing signals from subagent returns
4. Each agent calls `kanban-md edit ID -a "## {Section}\n{content}" -t` before returning

**KISS check:** No new infrastructure. Uses existing kanban-md `--append-body`. No new files, services, or dependencies.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement two-channel protocol in agent-common.instructions.md" --priority needed --tags "scope:copilot,agent,phase-agent-arch" --body "Add ## Inter-agent communication protocol section to agent-common.instructions.md with: routing signal format, task body section format, file-reference threshold rule (1500 tokens), PowerShell escaping guidance. Reference: docs/inter-agent-communication-protocol-research.md"

kanban\kanban-md.exe create "Rewrite builder output_format to two-channel model" --priority needed --tags "scope:copilot,agent,phase-agent-arch" --depends-on 684 --body "Split builder.agent.md output_format: routing signal = DONE #{id} -> review | {test_count} passed, ruff {status}. Task body via kanban-md edit -a '## Builder Notes'. Remove files-changed, coverage, evidence from return text."

kanban\kanban-md.exe create "Rewrite reviewer output_format to two-channel model" --priority needed --tags "scope:copilot,agent,phase-agent-arch" --depends-on 684 --body "Split reviewer.agent.md output_format: routing signal = PASS/FAIL #{id} -> {status} | confidence {.XX}. AC compliance table, test quality matrix, security findings, rejection details go to task body via ## Review Evidence."

kanban\kanban-md.exe create "Rewrite writer output_format to two-channel model" --priority needed --tags "scope:copilot,agent,phase-agent-arch" --depends-on 684 --body "Split writer.agent.md output_format: routing signal = DONE #{id} -> done | docs gate passed. Checklist table, files updated go to task body via ## Docs Gate."

kanban\kanban-md.exe create "Rewrite auditor output_format to two-channel model" --priority needed --tags "scope:copilot,agent,phase-agent-arch" --depends-on 684 --body "Split auditor.agent.md output_format: routing signal = ARCHIVED #{id} | confidence {.XX}. Audit report, commit log go to task body via ## Audit."

kanban\kanban-md.exe create "Rewrite architect output_format to two-channel model" --priority needed --tags "scope:copilot,agent,phase-agent-arch" --depends-on 684 --body "Split architect.agent.md output_format: routing signal = APPROVED/REFINE/SPLIT #{id} -> {status} | one-liner. AC assessment, architecture notes, dependencies go to task body via ## Architecture Review."

kanban\kanban-md.exe create "Rewrite researcher + planner + curator output_formats to two-channel model" --priority needed --tags "scope:copilot,agent,phase-agent-arch" --depends-on 684 --body "Three minor rewrites: researcher (already uses file refs, just formalize signal), kanban-planner (DONE | N tasks created), curator (DONE | N promoted, M pruned). Batch because all are small changes."

kanban\kanban-md.exe create "Update orchestrator to parse routing signals only" --priority needed --tags "scope:copilot,agent,phase-agent-arch" --depends-on 684 --body "Update orchestrator.agent.md: after subagent returns, parse only the routing signal line. Never read task bodies for routing decisions. Update wave progress report format to use signal lines. Reference: docs/inter-agent-communication-protocol-research.md section 3.3."
```
