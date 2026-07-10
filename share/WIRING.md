# Agent <-> File Mapping Tables

Current two-way wiring for the active OwlBear agent ecosystem.

## Nesting Depth (ND3 Agents)

Agents marked `(ND3)` may be called at nesting depth >= 3 and require `disable-model-invocation: false`.

| ND3 Agent | DMI | Called by |
|-----------|-----|-----------|
| shaper-challenger | `false` | shaper |
| builder-challenger | `false` | builder |
| verifier-challenger | `false` | verifier |
| ideation-critic | `false` | ideation-architect, ideation-data, ideation-enduser, ideation-security |

Built-in agents (`Explore`, `General Purpose`) resolve at any depth.

## Universal Files

| File | Type | Connection |
|------|------|------------|
| `.github/copilot-instructions.md` | workspace instructions | `auto` |
| `owlbear-system.instructions.md` | instruction | `applyTo: **` |

## Agent -> Files

### Orchestration

| Agent | Regularly | Connection | Seldom | Connection |
|-------|-----------|------------|--------|------------|
| orchestrator | w-orchestration | `req` | h-mcp-kanban, r-pipeline-protocol | `companion` |

### Shape Entry

| Agent | Regularly | Connection | Seldom | Connection |
|-------|-----------|------------|--------|------------|
| shaper | r-pipeline-protocol, h-ac-quality, w-task-decomposition, w-research | `req` | h-code-orientation, h-mcp-kanban, r-project-standards | `companion` |

### Execution Board

| Agent | Regularly | Connection | Seldom | Connection |
|-------|-----------|------------|--------|------------|
| builder | r-pipeline-protocol | `req` | h-code-orientation, h-mcp-kanban, r-project-standards, python/frontend instructions | `companion` / `applyTo` |
| verifier | r-pipeline-protocol | `req` | h-code-orientation, h-mcp-kanban, r-project-standards, python/frontend instructions | `companion` / `applyTo` |
| collector | r-pipeline-protocol | `req` | h-mcp-kanban, r-project-standards | `companion` |

### Pipeline Challengers

| Agent | Regularly | Connection | Seldom | Connection |
|-------|-----------|------------|--------|------------|
| shaper-challenger | h-ac-quality, r-pipeline-protocol | `req` | python.instructions | `applyTo` |
| builder-challenger | r-pipeline-protocol | `req` | h-pytest-and-linting, h-vitest-and-linting, python/frontend instructions | `organic` / `applyTo` |
| verifier-challenger | r-pipeline-protocol | `req` | python/frontend instructions | `applyTo` |

### Support

| Agent | Regularly | Connection | Seldom | Connection |
|-------|-----------|------------|--------|------------|
| test-curator | w-test-curation | `req` | h-python-conventions, h-vitest-and-linting | `companion` |
| memory-curator | w-mem-curation | `req` | h-mcp-memory, h-memory-structure | `companion` / `directed` |

### Ideation And Knowledge

| Agent Group | Regularly | Connection |
|-------------|-----------|------------|
| ideation-discoverer | h-ideation, w-ideation-discovery | `req` |
| ideation-mediator | h-ideation, w-ideation-mediation | `req`; dispatches shaper at M6 |
| ideation panel agents | h-ideation-panel | `req` |
| knowledge-ingestor, knowledge-enricher | h-knowledge-ops | `req` |

## File -> Agents

| File | Regular Consumers |
|------|-------------------|
| r-pipeline-protocol | orchestrator, shaper, builder, verifier, collector, shaper-challenger, builder-challenger, verifier-challenger, memory-curator |
| w-orchestration | orchestrator |
| w-research | shaper |
| w-task-decomposition | shaper |
| w-test-curation | test-curator |
| w-mem-curation | memory-curator |
| h-ac-quality | shaper, shaper-challenger |
| h-code-orientation | shaper, builder, verifier on demand |
| h-mcp-kanban | pipeline/support agents on demand |
| h-pytest-and-linting | builder-challenger/test-curator on demand |
| h-vitest-and-linting | builder-challenger/test-curator/frontend work on demand |
| h-python-conventions | Python editing/curation on demand |
| h-ideation, w-ideation-discovery, w-ideation-mediation, h-ideation-panel | ideation agents |
| h-knowledge-ops | knowledge agents |

## Subagent Dependencies

| Subagent | Affected Agents | Failure Mode |
|----------|-----------------|--------------|
| shaper-challenger | shaper | Shape approval loses cross-check |
| builder-challenger | builder | Build DONE loses cheap lint/proof/adversarial cross-check |
| verifier-challenger | verifier | PASS loses cheap intent/code/proof/scope cross-check |
| ideation-critic | ideation panel agents | Ideation challenge loop degraded |
