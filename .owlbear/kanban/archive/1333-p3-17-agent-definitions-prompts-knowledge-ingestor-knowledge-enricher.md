---
id: 1333
title: 'P3-17: Agent definitions + prompts (knowledge-ingestor + knowledge-enricher)'
status: archived
priority: medium
created: 2026-05-04T05:48:50.177453+00:00
updated: 2026-05-06T02:32:17.723710+00:00
tags:
- phase-3
- scope:agents
- knowledge
- agent
parent: 1316
depends_on:
- 1328
- 1332
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1316 → `.owlbear/briefs/draft-knowledge-activation/brief.md` (§4.10)

## Acceptance Criteria

- [ ] knowledge-ingestor.agent.md created with tools: ob-knowledge/{ingest_document, refresh_source, list_sources, get_stats, search_knowledge} + vscode/askQuestions (D9) (td:0)
- [ ] knowledge-enricher.agent.md created with tools: ob-knowledge/{get_next_batch, get_consolidation_candidates, store_enrichment, get_stats, search_knowledge} (td:0)
- [ ] Enricher agent specifies model: [GPT-5.4 mini (copilot), GPT-5 mini (copilot), Claude Haiku 4.5 (copilot)] per D8 (td:0)
- [ ] share/prompts/kb-ingest.prompt.md created with agent: knowledge-ingestor binding (td:0)
- [ ] share/prompts/kb-enrich.prompt.md created with agent: knowledge-enricher binding, documents parallelism (1-6 sessions, D7) (td:0)
- [ ] Enricher worker loop documented in agent body (Phase 1: entity extraction, Phase 2: consolidation) (td:0)
- [ ] Agent files follow structural standards (h-agent-structure): frontmatter, persona, required_reading, critical_rules sections (td:0)

## Scope

- **In scope:** Agent .agent.md files, prompt .prompt.md files, enricher worker loop documentation
- **Out of scope:** Entity type schema extension (D13 — deferred to enricher prompt design), batch rebuild prompt (§6)
[[2026-05-05]]
## Research

Research complete. Validated feasibility of knowledge-ingestor and knowledge-enricher agent definitions + prompt files.

**Key findings:**
- All 7/8 tools implemented in MCP server; `get_consolidation_candidates` pending (#1330) but agent def is declarative — no blocker
- VS Code model array syntax supports D8 fallback chain: `[GPT-5.4 mini, GPT-5 mini, Claude Haiku 4.5]`
- D7 parallelism = user opens 1-6 chat sessions; `get_next_batch` coordinates via atomic claims
- 26 existing agents + 12 prompts provide clear structural templates
- Ingestor needs `vscode/askQuestions` for browser detection user validation (D9)
- Both agents: `user-invocable: true`, `disable-model-invocation: true`, no subagent delegation

**Classification:** T1 — Autonomous. Config/documentation work following established patterns.

**Doc:** `.owlbear/research/knowledge-agent-definitions.md`
**Follow-ups:** None — task itself is the implementation unit.
[[2026-05-05]]

## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Two related agents + their prompt triggers — single "agent config" domain |
| Interface clarity | PASS | Tool names match server.py implementations; model array syntax validated |
| Dependency correctness | PASS | #1328 (Phase 1 tools) and #1332 (provenance) both archived/done |
| Module layering | PASS | Agent/prompt files in share/ — no code dependencies |
| TDD compliance | PASS | No testable Python code; agent tag = pass-through |
| KISS/YAGNI | PASS | Minimal config following 26 existing agent templates |
| Premise challenge | PASS | MCP server has 7/8 tools; agents are needed for user-facing workflows |
| Pattern consistency | PASS | Follows h-agent-structure frontmatter, existing prompt format |
| Security surface | PASS | No new system boundaries; content guard wired in #1322 |
| Single domain | PASS | Knowledge domain only |

### AC Refinement
- AC1: Added `vscode/askQuestions` + explicit `ob-knowledge/` prefix — required for D9 browser content user validation
- AC3: Specified exact model array values (from research)
- AC4/AC5: Specified `agent:` binding + file paths in share/prompts/
- All AC lines annotated with test depth (td:0) — declarative config

### Challenge Results
- Challenger: SKIPPED — all td:0, declarative config/documentation work

### Test Depth
- Max depth: 0
- Test-writer: SKIP

### Verdict: APPROVE
### Action Taken: AC tightened (tool prefixes, askQuestions, model array, td annotations), moved to todo
[[2026-05-05]]
Architecture review complete. AC tightened with explicit tool prefixes (ob-knowledge/), vscode/askQuestions for D9, exact model array values, agent: binding in prompt files, and td:0 annotations. All 10 criteria PASS. Challenger skipped (all td:0). Dependencies satisfied (#1328, #1332 archived). Test-writer: SKIP.
[[2026-05-06]]
## Test-Writer Notes
- Non-implementation task (tagged `agent`) — no testable Python interfaces.
- All AC lines annotated td:0 (declarative config/documentation only).
- Architecture review explicitly marked Test-writer: SKIP.
- Passing through to builder.
[[2026-05-06]]
## Builder Notes
- Implementation: created `share/agents/knowledge-ingestor.agent.md`, `share/agents/knowledge-enricher.agent.md`, `share/prompts/kb-ingest.prompt.md`, and `share/prompts/kb-enrich.prompt.md`.
- AC coverage:
  - Added required ingestor tools including `vscode/askQuestions` and `ob-knowledge/{ingest_document,refresh_source,list_sources,get_stats,search_knowledge}`.
  - Added enricher tools `ob-knowledge/{get_next_batch,get_consolidation_candidates,store_enrichment,get_stats,search_knowledge}`.
  - Set enricher model fallback chain exactly to `[GPT-5.4 mini (copilot), GPT-5 mini (copilot), Claude Haiku 4.5 (copilot)]`.
  - Bound prompts with `agent: knowledge-ingestor` and `agent: knowledge-enricher`.
  - Documented D7 parallelism in `kb-enrich.prompt.md` (1-6 sessions) and worker phases.
  - Documented enricher worker loop in agent critical rules (Phase 1 extraction, Phase 2 consolidation).
  - Included structural sections in both agent files: frontmatter, `<persona>`, `<required_reading>`, `<critical_rules>`.
- Quality verification:
  - quality-runner (scoped): tests N/A, lint N/A, coverage N/A (td:0 declarative markdown task).
  - VS Code diagnostics: no errors in all 4 files.
- Commit: `424fcd56` with message `feat: add knowledge ingestor/enricher agents and prompts (#1333, builder)`.
- Evidence summary: task completed as a surgical config/doc change set with no source-code or test-file edits.
[[2026-05-06]]
## Review Evidence
### Test Results
- Max AC depth: td:0. No task-scoped executable tests required.
- Quality-runner skipped: td:0 review has no test artifact inputs in this tool surface, so evidence was gathered by direct file inspection instead.

### Lint Results
- VS Code diagnostics on the four delivered files reported no errors.

### Coverage
- Not applicable for this declarative markdown task.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| knowledge-ingestor.agent.md created with required tools plus vscode/askQuestions | share/agents/knowledge-ingestor.agent.md:2 confirms the agent file; share/agents/knowledge-ingestor.agent.md:8 lists ingest_document, refresh_source, list_sources, get_stats, search_knowledge, and vscode/askQuestions | PASS |
| knowledge-enricher.agent.md created with required tools | share/agents/knowledge-enricher.agent.md:2 confirms the agent file; share/agents/knowledge-enricher.agent.md:9 lists get_next_batch, get_consolidation_candidates, store_enrichment, get_stats, and search_knowledge | PASS |
| Enricher agent specifies the exact model fallback chain | share/agents/knowledge-enricher.agent.md:7 | PASS |
| share/prompts/kb-ingest.prompt.md created with knowledge-ingestor binding | share/prompts/kb-ingest.prompt.md:3 binds the prompt to knowledge-ingestor; share/prompts/kb-ingest.prompt.md:6 provides the ingest entrypoint | PASS |
| share/prompts/kb-enrich.prompt.md created with knowledge-enricher binding and D7 parallelism | share/prompts/kb-enrich.prompt.md:3 binds the prompt to knowledge-enricher; share/prompts/kb-enrich.prompt.md:10 documents 1 to 6 sessions; share/prompts/kb-enrich.prompt.md:16-17 document the two worker phases | PASS |
| Enricher worker loop documented in agent body | share/agents/knowledge-enricher.agent.md:28 opens critical_rules; share/agents/knowledge-enricher.agent.md:31-35 document Phase 1 pull and persist plus Phase 2 consolidation | PASS |
| Agent files include frontmatter, persona, required_reading, and critical_rules sections | share/agents/knowledge-ingestor.agent.md:1-8,11,20,26 and share/agents/knowledge-enricher.agent.md:1-9,12,22,28 | PASS |

### Additional Evidence
- Builder commit 424fcd56 is present in .git/logs/refs/heads/dev:1915 and .git/logs/HEAD:2089.
- Changed-file scope reconstructed from builder notes: share/agents/knowledge-ingestor.agent.md, share/agents/knowledge-enricher.agent.md, share/prompts/kb-ingest.prompt.md, share/prompts/kb-enrich.prompt.md.
- Context only: task history for #1333 explicitly records get_consolidation_candidates as pending elsewhere and treats the agent reference here as declarative, so that unresolved server tool did not count against this td:0 task.

### Deductions
- -0.04 confidence: current tool surface allowed commit-presence checks in .git logs but not a direct git diff or git status check, so dirty-tree contamination could not be independently ruled out.

### Verdict
- PASS with confidence 0.94.

### Action
- Advance to docs.
[[2026-05-06]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Updated | `share/README.md` agent/prompt counts were stale (26 agents, 10 prompts → 28, 14). New agents/prompts added by this task caused the drift. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified. |
| 3 | External attribution | No | N/A | No external patterns used; all work followed existing internal templates. |
| 4 | Research doc | Yes | Verified | `.owlbear/research/knowledge-agent-definitions.md` exists and is linked in task body. Follow-ups: none (task is the implementation unit). |
| 5 | Diagram maintenance (describes match) | No | N/A | No diagram `describes` glob matches `share/agents/**` or `share/prompts/**`. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted; no orphaned IN-scope docs detected. |

### Scope Classification

| File | Scope | Action |
|------|-------|--------|
| `share/agents/knowledge-ingestor.agent.md` | OUT (agent-executable) | N/A |
| `share/agents/knowledge-enricher.agent.md` | OUT (agent-executable) | N/A |
| `share/prompts/kb-ingest.prompt.md` | OUT (agent-executable) | N/A |
| `share/prompts/kb-enrich.prompt.md` | OUT (agent-executable) | N/A |
| `.owlbear/research/knowledge-agent-definitions.md` | IN | Verified (exists, linked) |
| `share/README.md` | IN | Updated (agent count 26→28, prompt count 10→14) |

### Files Updated
- `share/README.md` — ecosystem header + table counts updated (commit `9c641232`)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (`1333-*` scratch files: none existed)
[[2026-05-06]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---|---|---|
| knowledge-ingestor.agent.md with tools + vscode/askQuestions | Direct read: tools array at L8 lists all 5 ob-knowledge tools + vscode/askQuestions | PASS |
| knowledge-enricher.agent.md with required tools | Direct read: tools array at L9 lists get_next_batch, get_consolidation_candidates, store_enrichment, get_stats, search_knowledge | PASS |
| Enricher model fallback chain per D8 | Direct read: L7 `model: [GPT-5.4 mini (copilot), GPT-5 mini (copilot), Claude Haiku 4.5 (copilot)]` | PASS |
| kb-ingest.prompt.md with knowledge-ingestor binding | Direct read: L3 `agent: knowledge-ingestor` | PASS |
| kb-enrich.prompt.md with knowledge-enricher binding + D7 parallelism | Direct read: L3 `agent: knowledge-enricher`, L10 documents 1-6 sessions | PASS |
| Enricher worker loop documented | Direct read: critical_rules L31-35 documents Phase 1 pull+persist, Phase 2 consolidation | PASS |
| Structural standards (frontmatter, persona, required_reading, critical_rules) | Both agents confirmed: frontmatter L1-8/9, persona L11/12, required_reading L20/22, critical_rules L26/28 | PASS |

### Test Results
- Full suite: 4629 passed, 252 failed, 4 skipped
- Failures are pre-existing cross-task regressions (engine accessor, memory model, frontend SSE, MCP kanban server) — none in task scope
- Task is td:0 (declarative markdown); no Python code introduced

### Commit Integrity
- Builder: `424fcd56` feat: add knowledge ingestor/enricher agents and prompts (#1333, builder)
- Doc-writer: `9c641232` docs: update agent/prompt counts in share/README.md (#1333, doc-writer)

### AC Quality Score: 5/5
Specific, complete, unambiguous. Exact tool names with ob-knowledge/ prefixes, exact model array values, D-reference annotations, td:0 annotations. Clean implementation path.

### Deductions
- None. All AC lines have direct file-read evidence. No task-scope failures. Lint N/A (markdown only). Reviewer evidence present and detailed.

### Confidence: 1.00
### Action: Archive