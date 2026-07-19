# Agent <-> File Mapping Tables

Current two-way wiring for the active OwlBear agent ecosystem.

## Nesting Depth (ND3 Agents)

Agents marked `(ND3)` may be called at nesting depth >= 3 and require `disable-model-invocation: false`.

| ND3 Agent | DMI | Called by |
|-----------|-----|-----------|
| shaper-challenger | `false` | shaper |
| builder-challenger | `false` | builder |
| verifier-challenger | `false` | verifier |

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
| shaper | r-pipeline-protocol, r-workspace-governance | `req` | w-spec-shaping or w-task-repair after mode selection; w-task-decomposition, w-research, h-ac-quality, h-codebase-orientation, h-module-design, h-mcp-kanban when triggered; h-mcp-memory when recall returns entries | `directed` / `companion` |

### User Planning And Design

| Prompt              | Regularly                                                                          | Connection  | Seldom                   | Connection |
| ------------------- | ---------------------------------------------------------------------------------- | ----------- | ------------------------ | ---------- |
| ideate              | w-idea-refinement                                                                  | `directed`  | OpenSpec `/opsx:propose` | `handoff`  |
| architecture-review | h-module-design, h-codebase-orientation, h-visual-output, w-idea-refinement | `companion` | `/opsx:propose`, `/shape` | `handoff`  |

### Execution Board

| Agent | Regularly | Connection | Seldom | Connection |
|-------|-----------|------------|--------|------------|
| builder | r-pipeline-protocol, r-workspace-governance, h-codebase-orientation | `req` | h-module-design, h-mcp-kanban, h-mcp-memory when recall returns entries, python/frontend instructions | `companion` / `applyTo` |
| verifier | r-pipeline-protocol, r-workspace-governance, h-codebase-orientation | `req` | h-module-design, h-mcp-kanban, h-mcp-memory when recall returns entries, python/frontend instructions | `companion` / `applyTo` |
| collector | r-pipeline-protocol, r-workspace-governance | `req` | h-mcp-kanban; h-mcp-memory when recall returns entries | `companion` |

### Pipeline Challengers

| Agent | Regularly | Connection | Seldom | Connection |
|-------|-----------|------------|--------|------------|
| shaper-challenger | h-ac-quality, h-module-design, r-pipeline-protocol | `req` | python.instructions | `applyTo` |
| builder-challenger | r-pipeline-protocol | `req` | h-pytest-and-linting, h-vitest-and-linting, python/frontend instructions | `organic` / `applyTo` |
| verifier-challenger | r-pipeline-protocol | `req` | python/frontend instructions | `applyTo` |

### Support

| Agent | Regularly | Connection | Seldom | Connection |
|-------|-----------|------------|--------|------------|
| test-curator | w-test-curation | `req` | h-memory-structure and h-mcp-memory when saving a qualifying insight; h-python-conventions, h-vitest-and-linting | `directed` / `companion` |
| memory-curator | w-mem-curation | `req` | h-mcp-memory, h-memory-structure | `companion` / `directed` |

### Knowledge

| Agent Group | Regularly | Connection |
|-------------|-----------|------------|
| knowledge-ingestor, knowledge-enricher | h-knowledge-ops | `req` |

## File -> Agents

| File | Regular Consumers |
|------|-------------------|
| r-pipeline-protocol | orchestrator, shaper, builder, verifier, collector, shaper-challenger, builder-challenger, verifier-challenger |
| w-spec-shaping | shaper |
| w-task-repair | shaper |
| w-orchestration | orchestrator |
| w-research | shaper through w-spec-shaping when evidence is needed |
| w-task-decomposition | shaper through w-spec-shaping or w-task-repair |
| w-idea-refinement | ideate prompt, architecture-review prompt |
| w-test-curation | test-curator |
| w-mem-curation | memory-curator |
| h-ac-quality | shaper, shaper-challenger |
| h-codebase-orientation | shaper workflows, builder, and verifier |
| h-module-design | shaper workflows on demand, shaper-challenger, and builder/verifier on demand |
| r-workspace-governance | shaper, builder, verifier, and collector |
| h-mcp-kanban | pipeline/support agents on demand |
| h-mcp-memory | task-owning pipeline agents through r-pipeline-protocol when recall returns entries; save-capable agents through always-loaded Memory Governance; memory-curator through w-mem-curation |
| h-memory-structure | save-capable agents through always-loaded Memory Governance; memory-curator through w-mem-curation |
| h-pytest-and-linting | builder-challenger/test-curator on demand |
| h-vitest-and-linting | builder-challenger/test-curator/frontend work on demand |
| h-python-conventions | Python editing/curation on demand |
| h-knowledge-ops | knowledge agents |

## Subagent Dependencies

| Subagent | Affected Agents | Failure Mode |
|----------|-----------------|--------------|
| shaper-challenger | shaper | Shape approval loses cross-check |
| builder-challenger | builder | Build DONE loses cheap lint/proof/adversarial cross-check |
| verifier-challenger | verifier | PASS loses cheap intent/code/proof/scope cross-check |
