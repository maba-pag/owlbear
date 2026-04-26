# Agent ↔ File Mapping Tables

> Generated during agent ecosystem audit. Two-way mapping of every agent and prompt to every relevant file (skills, instructions).

## Connection Methods

| Code | Meaning |
|------|---------|
| `req` | Listed in agent's `<required_reading>` — read at session start |
| `applyTo:pattern` | Instruction fires when agent touches files matching glob |
| `auto` | Always loaded as workspace instructions (copilot-instructions.md) |
| `companion:skill` | Listed in a required skill's Companion Skills table — formal contract |
| `inline-ref:skill` | Cross-referenced in a required skill's body text — advisory |
| `body-ref` | Agent body mentions skill (not in required_reading) |
| `prompt-ref` | Prompt body instructs agent to load this |
| `directed:skill` | Skill explicitly instructs "load X when condition Y" |
| `organic` | Domain affinity — agent may load based on task context, no explicit instruction |

## Nesting Depth (ND3 Agents)

Agents marked **(ND3)** may be called at nesting depth ≥3 and require `disable-model-invocation: false`. At depth ≥2, VS Code does not inject the agents catalog — dispatching agents rely on their `<agents>` body section for subagent discovery.

| ND3 Agent | DMI | Called by (ND2) |
|----------|-----|----------------|
| challenger | `false` | architect, researcher |
| scribe | `false` | architect, researcher, builder, reviewer, test-writer, doc-writer, auditor |
| planner | `false` | architect |
| fix-attempt | `false` | builder |
| code-reader | `false` | reviewer |
| ideation-critic | `false` | ideation-architect, ideation-data, ideation-enduser, ideation-security |
| quality-runner | `false` | builder, reviewer, test-writer, auditor |

All other agents keep `disable-model-invocation: true`. Built-in agents (`Explore`, `General Purpose`) resolve at any depth.

## Universal Files (apply to ALL agents/prompts)

These are omitted from per-agent rows to avoid noise:

| File | Type | Connection | Frequency |
|------|------|-----------|-----------|
| `.github/copilot-instructions.md` | workspace instructions | `auto` | every turn |
| `owlbear-system.instructions.md` | instruction | `applyTo: **` | every turn (any file touch) |

---

## Table 1: Agent/Prompt → Relevant Files

### T1 — Orchestrators

| Agent | Regularly (90%+) | Connection | Seldom (<90%) | Connection |
|-------|-------------------|------------|---------------|------------|
| **orchestrator** | r-pipeline-protocol | `req` | h-mcp-kanban | `companion:r-pipeline-protocol` |
| | w-orchestration | `req` | | |
| | pipeline-agents.instructions | `applyTo:r-pipeline-protocol/**` | | |

### T2 — Pipeline Agents

| Agent | Regularly (90%+) | Connection | Seldom (<90%) | Connection |
|-------|-------------------|------------|---------------|------------|
| **builder** | r-pipeline-protocol | `req` | h-mcp-kanban | `body-ref` |
| | w-tdd-green | `req` | r-project-standards | `companion:r-pipeline-protocol` |
| | pipeline-agents.instructions | `applyTo:r-pipeline-protocol/**` | frontend.instructions | `applyTo:*.tsx` (cockpit work) |
| | python.instructions | `applyTo:*.py` | | |
| **test-writer** | r-pipeline-protocol | `req` | h-mcp-kanban | `body-ref` |
| | w-tdd-red | `req` | | |
| | pipeline-agents.instructions | `applyTo:r-pipeline-protocol/**` | | |
| | python.instructions | `applyTo:*.py` | | |
| **reviewer** | r-pipeline-protocol | `req` | h-mcp-kanban | `body-ref` |
| | w-code-review | `req` | | |
| | pipeline-agents.instructions | `applyTo:r-pipeline-protocol/**` | frontend.instructions | `applyTo:*.tsx` (cockpit reviews) |
| | python.instructions | `applyTo:*.py` | | |
| **doc-writer** | r-pipeline-protocol | `req` | h-mcp-kanban | `body-ref` |
| | w-doc-update | `req` | python.instructions | `applyTo:*.py` (docstrings) |
| | pipeline-agents.instructions | `applyTo:r-pipeline-protocol/**` | research-docs.instructions | `applyTo:.owlbear/research/*.md` |
| | | | doc-standards.instructions | `applyTo:README.md,serve/*/README.md,...` |
| | | | h-excalidraw-diagram | `directed:w-doc-update` |
| **auditor** | r-pipeline-protocol | `req` | h-mcp-kanban | `body-ref` |
| | w-task-verification | `req` | | |
| | pipeline-agents.instructions | `applyTo:r-pipeline-protocol/**` | | |
| | python.instructions | `applyTo:*.py` | | |
| **architect** | r-pipeline-protocol | `req` | h-mcp-kanban | `body-ref` |
| | w-arch-review | `req` | r-architecture-standards | `inline-ref:w-arch-review` |
| | pipeline-agents.instructions | `applyTo:r-pipeline-protocol/**` | | |
| **researcher** | r-pipeline-protocol | `req` | h-excalidraw-diagram | `organic` |
| | w-research | `req` | h-visual-output | `organic` |
| | pipeline-agents.instructions | `applyTo:r-pipeline-protocol/**` | h-knowledge-ops | `organic` |
| | research-docs.instructions | `applyTo:.owlbear/research/*.md` | h-mcp-kanban | `body-ref` |

### T3 — Support Agents

| Agent | Regularly (90%+) | Connection | Seldom (<90%) | Connection |
|-------|-------------------|------------|---------------|------------|
| **planner** | r-pipeline-protocol | `req` | r-architecture-standards | `body-ref` |
| | w-task-decomposition | `req` | h-mcp-kanban | `body-ref` |
| | pipeline-agents.instructions | `applyTo:r-pipeline-protocol/**` | | |
| **scribe** | r-pipeline-protocol | `req` | — | — |
| | w-decision-routing | `req` | | |
| | pipeline-agents.instructions | `applyTo:r-pipeline-protocol/**` | | |
| **memory-curator** | r-pipeline-protocol | `req` | h-mcp-kanban | `body-ref` |
| | w-mem-curation | `req` | h-mcp-memory | `companion:w-mem-curation` |
| | pipeline-agents.instructions | `applyTo:r-pipeline-protocol/**` | h-memory-structure | `directed:w-mem-curation` |

### T1 — Ideation Orchestrators

| Agent | Regularly (90%+) | Connection | Seldom (<90%) | Connection |
|-------|-------------------|------------|---------------|------------|
| **ideation-discoverer** | h-ideation | `req` | — | — |
| | w-ideation-discovery | `req` | | |
| **ideation-mediator** | h-ideation | `req` | — | — |
| | w-ideation-mediation | `req` | | |

### T4 — Ideation Panel (9 agents)

All 9 agents (critic, pragmatist, simplifier, outsider, ideation-architect, data, enduser, firstprinciples, security) share the same mapping:

| Agent | Regularly (90%+) | Connection | Seldom (<90%) | Connection |
|-------|-------------------|------------|---------------|------------|
| **ideation-panel ×9** | h-ideation-panel | `req` | — | — |

### T4 — Utility Agents

| Agent | Regularly (90%+) | Connection | Seldom (<90%) | Connection |
|-------|-------------------|------------|---------------|------------|
| **quality-runner** | h-quality-runner | `req` | — | — |
| | h-pytest-and-linting | `req` | | |
| | python.instructions | `applyTo:*.py` | | |
| **code-reader** | w-code-review | `req` | — | — |
| | python.instructions | `applyTo:*.py` | | |
| **fix-attempt** | w-fix-attempt | `req` | — | — |
| | python.instructions | `applyTo:*.py` | | |
| **test-curator** | w-test-curation | `req` | h-pytest-and-linting | `companion:w-test-curation` |
| | python.instructions | `applyTo:*.py` | h-python-conventions | `companion:w-test-curation` |
| **challenger** | r-pipeline-protocol | `req` | python.instructions | `applyTo:*.py` (reads .py) |
| | pipeline-agents.instructions | `applyTo:r-pipeline-protocol/**` | | |

### Prompts

| Prompt | Invokes Agent | Skill References | Connection |
|--------|---------------|-----------------|------------|
| **orchestrate** | orchestrator | — | agent invocation |
| **ideation-discover** | ideation-discoverer | — | agent invocation |
| **ideation-mediate** | ideation-mediator | — | agent invocation |
| **test-curation** | test-curator | — | agent invocation |
| **agent-audit** | (inline, no agent) | h-agent-structure, h-memory-structure, r-pipeline-protocol, r-project-standards | `prompt-ref` |
| **doc-audit** | (inline, no agent) | r-doc-standards | `prompt-ref` |
| **design-context** | (inline, no agent) | h-frontend-design | `prompt-ref` |
| **frontend-audit** | (inline, no agent) | h-frontend-design | `prompt-ref` |
| **frontend-normalize** | (inline, no agent) | h-frontend-design | `prompt-ref` |
| **frontend-polish** | (inline, no agent) | h-frontend-design | `prompt-ref` |

---

## Table 2: File → Agents/Prompts (Inverse)

### Skills

| Skill | Regularly (90%+) | Connection | Seldom (<90%) | Connection |
|-------|-------------------|------------|---------------|------------|
| **r-pipeline-protocol** | orchestrator, builder, test-writer, reviewer, doc-writer, auditor, architect, researcher, planner, scribe, memory-curator, challenger | `req` | — | — |
| **w-orchestration** | orchestrator | `req` | — | — |
| **w-tdd-green** | builder | `req` | — | — |
| **w-tdd-red** | test-writer | `req` | — | — |
| **w-code-review** | reviewer, code-reader | `req` | — | — |
| **w-doc-update** | doc-writer | `req` | — | — |
| **w-task-verification** | auditor | `req` | — | — |
| **w-arch-review** | architect | `req` | — | — |
| **w-research** | researcher | `req` | — | — |
| **w-task-decomposition** | planner | `req` | — | — |
| **w-decision-routing** | scribe | `req` | — | — |
| **w-mem-curation** | memory-curator | `req` | — | — |
| **w-fix-attempt** | fix-attempt | `req` | — | — |
| **w-test-curation** | test-curator | `req` | — | — |
| **h-ideation** | ideation-discoverer, ideation-mediator | `req` | — | — |
| **w-ideation-discovery** | ideation-discoverer | `req` | — | — |
| **w-ideation-mediation** | ideation-mediator | `req` | — | — |
| **h-ideation-panel** | 9× ideation panel | `req` | — | — |
| **h-quality-runner** | quality-runner | `req` | — | — |
| **h-pytest-and-linting** | quality-runner | `req` | test-curator | `companion` |
| **h-mcp-kanban** | — | — | 12× pipeline agents | `companion:r-pipeline-protocol` |
| **r-project-standards** | — | — | 12× pipeline agents | `companion:r-pipeline-protocol` |
| | | | agent-audit prompt | `prompt-ref` |
| **r-architecture-standards** | — | — | architect (via w-arch-review), planner | `inline-ref` / `body-ref` |
| **r-doc-standards** | — | — | doc-audit prompt | `prompt-ref` |
| | | | (any agent editing doc files) | `applyTo` via doc-standards.instructions |
| **h-python-conventions** | — | — | test-curator (via w-test-curation) | `companion` |
| **h-frontend-design** | — | — | design-context, frontend-audit, frontend-normalize, frontend-polish prompts | `prompt-ref` |
| **h-frontend-conventions** | — | — | — (only via frontend.instructions stub) | `applyTo` stub target |
| **h-excalidraw-diagram** | — | — | doc-writer | `directed` |
| | | | researcher | `organic` |
| **h-visual-output** | — | — | researcher | `organic` |
| **h-knowledge-ops** | — | — | researcher | `organic` |
| **h-mcp-memory** | — | — | memory-curator (via w-mem-curation) | `companion` |
| **h-memory-structure** | — | — | memory-curator | `directed` |
| | | | agent-audit prompt | `prompt-ref` |
| **h-agent-structure** | — | — | agent-audit prompt | `prompt-ref` |
| ~~w-ideation~~ | — | — | — | Does not exist (phantom — only w-ideation-discovery and w-ideation-mediation) |

### Skills with ZERO regular consumers

| Skill | Only Consumer | Connection |
|-------|--------------|------------|
| h-agent-structure | agent-audit prompt | `prompt-ref` |
| h-excalidraw-diagram | doc-writer, researcher | `directed` / `organic` |
| h-frontend-conventions | (none — stub target only) | `applyTo` stub |
| h-frontend-design | 4 frontend prompts | `prompt-ref` |
| h-knowledge-ops | researcher | `organic` |
| h-memory-structure | memory-curator, agent-audit | `directed` / `prompt-ref` |
| h-mcp-kanban | 9 pipeline agents | `body-ref` |
| h-mcp-memory | memory-curator | `companion` |
| h-python-conventions | test-curator | `companion` |
| h-visual-output | researcher | `organic` |
| r-architecture-standards | architect, planner | `inline-ref` / `body-ref` |
| r-doc-standards | doc-audit prompt; applyTo stub | `prompt-ref` / `applyTo` stub |
| r-project-standards | all pipeline agents | `companion` (commits) |

### Instructions

| Instruction | Regularly (90%+) | Connection | Seldom (<90%) | Connection |
|-------------|-------------------|------------|---------------|------------|
| **copilot-instructions.md** | ALL agents, ALL prompts | `auto` | — | — |
| **owlbear-system.instructions** | ALL agents, ALL prompts | `applyTo: **` | — | — |
| **pipeline-agents.instructions** | 12× pipeline agents + challenger | `applyTo: r-pipeline-protocol/**` | — | — |
| **python.instructions** | builder, test-writer, reviewer, auditor, quality-runner, code-reader, fix-attempt, test-curator | `applyTo: *.py` | doc-writer, challenger | `applyTo: *.py` (occasionally) |
| **frontend.instructions** | — | — | builder, reviewer | `applyTo: *.tsx` (cockpit work) |
| **research-docs.instructions** | researcher | `applyTo: .owlbear/research/*.md` | doc-writer | `applyTo: .owlbear/research/*.md` |
| **agent-ecosystem.instructions** | — | — | any agent editing share/ files | `applyTo: share/agents/**,...` |
| **doc-standards.instructions** | — | — | any agent editing doc files | `applyTo: README.md,serve/*/README.md,...` |

---

## Table 3: Subagent Dependencies

Impact analysis: which agents break when a subagent is unavailable.

| Subagent | Invoking Skills | Affected Agents |
|----------|----------------|-----------------|
| **quality-runner** | w-tdd-green, w-tdd-red, w-code-review, w-task-verification, w-test-curation | builder, test-writer, reviewer, auditor, test-curator |
| **fix-attempt** | w-tdd-green | builder |
| **code-reader** | w-code-review | reviewer |
| **challenger** | w-arch-review, w-research | architect, researcher |
| **scribe** | w-arch-review, w-research, w-doc-update, w-mem-curation, w-orchestration | architect, researcher, doc-writer, memory-curator, orchestrator |
| **planner** | w-arch-review, w-ideation-mediation | architect, ideation-mediator |
| **ideation panelists** | w-ideation-discovery, w-ideation-mediation | ideation-discoverer, ideation-mediator |
| **memory-curator** | w-orchestration | orchestrator |

---

## Gap Analysis

### Potential Gaps (file has no regular consumer)

| File | Status | Notes |
|------|--------|-------|
| **h-frontend-conventions** | Stub-only | Only referenced as `applyTo` target by frontend.instructions stub. No agent or prompt lists it. By design — fires when frontend files are touched. |
| **frontend.instructions** | No regular consumer | Only fires for cockpit work (builder/reviewer). Acceptable — suspenders-only safety net. |
| **doc-standards.instructions** | No regular consumer | Fires when any agent edits doc files (README.md, SECURITY.md, setup/*.md, etc.). Acceptable — suspenders-only. |
| **agent-ecosystem.instructions** | No regular consumer | Fires when any agent edits share/ files. Acceptable — suspenders-only. |

### Potential Gaps (agent has sparse file coverage)

| Agent | Files Loaded | Notes |
|-------|-------------|-------|
| **ideation-panel ×9** | 1 skill only (h-ideation-panel) | By design — minimal context, focused role. |
| **fix-attempt** | 1 skill only (w-fix-attempt) | By design — fresh-context single-shot repair. |
| **scribe** | 2 skills (r-pipeline-protocol, w-decision-routing) | Sufficient — narrow role. |
| **code-reader** | 1 skill only (w-code-review) | By design — read-only analysis. |

### Observation

`w-ideation` does not exist as a standalone skill — only `w-ideation-discovery` and `w-ideation-mediation` exist. Both are properly wired to their respective agents.
