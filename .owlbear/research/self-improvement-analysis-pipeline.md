# Self-Improvement Analysis Pipeline

> **Owning task:** #31 — Self-improvement analysis pipeline
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #31 asks for an analysis pipeline that reads the audit log (#21), detects performance patterns (error rates, slow tasks, repeated failures), and generates typed improvement proposals as review artifacts. v1 had `ImprovementProposals` (~142 LOC) analyzing tool-level `EventStore` data. v2 operates at dispatch granularity (per-agent-invocation), requiring a redesigned analysis approach. Key questions: (a) What patterns to detect from dispatch-level data? (b) What proposal schema fits v2? (c) CLI integration approach?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | v1 `improvement_proposals.py` | `v1/src/owlbear/core/improvement_proposals.py` | .95 |
| 2 | v1 `observability.py` (EventStore) | `v1/src/owlbear/core/observability.py` | .85 |
| 3 | v1 `retrospective_hook.py` | `v1/src/owlbear/core/retrospective_hook.py` | .75 |
| 4 | AutoGen event logging | `autogen-core/src/autogen_core/logging.py` | .70 |
| 5 | LangSmith evaluation concepts | `docs.langchain.com/langsmith/evaluation-concepts` | .65 |
| 6 | OwlBear audit log research (#21) | `docs/research/orchestrator-audit-log.md` | .95 |
| 7 | Conductor retrospective pattern | `docs/research/conductor-orchestrator-superpowers.md` | .70 |

## 3. Analysis

### 3.1 v1 vs v2 Data Granularity

| Aspect | v1 (EventStore) | v2 (Audit Log) |
|--------|----------------|----------------|
| Granularity | Per-tool-call | Per-agent-dispatch |
| Event volume | Hundreds per session | Tens per session |
| Error signals | Tool failure rate, tool latency | Agent failure rate, task duration |
| Identity | tool_name + agent_name | agent + task_id |
| Pattern target | "Tool X fails 80% for agent Y" | "Agent Y fails 60% of dispatches" |

v2's coarser data yields agent-level and task-level insights rather than tool-level. This is *more actionable* for the v2 model where agents are Copilot CLI invocations dispatched by the orchestrator.

### 3.2 Pattern Detectors

| Pattern | Input | Threshold | v1 Equivalent |
|---------|-------|-----------|---------------|
| High agent error rate | CompletionEvents per agent | ≥40% failure rate, ≥3 dispatches | `_ERROR_RATE_THRESHOLD` (50%) |
| Slow agent | CompletionEvents per agent | avg duration > 2× global avg, ≥3 dispatches | `_HIGH_LATENCY_THRESHOLD_MS` |
| Repeated task failure | CompletionEvents per task_id | ≥2 failures on same task | None (new) |
| Stale tasks | DispatchEvents with no completion | Dispatch with no matching completion >1h | None (new) |

### 3.3 Design Options

| Criterion | A: Pure stats (.85) | B: LLM-assisted (.55) | C: Rule engine (.60) |
|-----------|---------------------|-----------------------|----------------------|
| New deps | 0 | Copilot CLI invocation | 0 |
| LOC | ~120 | ~200+ | ~180 |
| KISS | High | Low — LLM for stats is overkill | Medium |
| Deterministic | Yes | No | Yes |
| Offline usable | Yes | Needs network | Yes |
| YAGNI risk | Low | High — premature sophistication | Medium — rule engine for 4 rules |

LangSmith uses LLM-as-judge for production evals but acknowledges code evaluators work well for deterministic checks (structure, metrics, patterns). v2's patterns are statistical — no LLM needed.

### 3.4 Proposed Proposal Schema

```python
class AnalysisProposal(BaseModel, frozen=True):
    target_agent: str  # Which agent to improve
    category: str  # "reliability" | "performance" | "stability"
    pattern: str  # Machine-readable pattern ID
    rationale: str  # Human-readable explanation
    evidence: dict[str, Any]  # Numeric evidence backing the claim
    suggested_action: str  # What to change (review artifact only)
```

v1 used `change_category` with values like "prompt"/"tools"/"skills" — too prescriptive for v2 where the human decides what to change. v2 uses descriptive categories tied to the detected pattern.

### 3.5 CLI Integration

AC requires `owlbear analyze`. The orchestrator package has no CLI yet. Options:

| Approach | Complexity | Fit |
|----------|-----------|-----|
| Standalone script (`scripts/analyze.py`) | Low | Immediate, no package infra needed |
| Module entrypoint (`python -m owlbear_orchestrator.analyze`) | Low | Standard Python, discoverable |
| Future CLI command | Deferred | When `owlbear` CLI exists |

**Recommendation:** Module entrypoint (`-m`) for now; wrap in `owlbear analyze` when CLI materializes. YAGNI on the CLI framework.

### 3.6 Output Formats

AC says "structured data (JSON or markdown report)." Support both:

- **JSON** (default): `list[AnalysisProposal]` serialized via Pydantic — machine-readable, pipeable
- **Markdown** (flag): formatted report with tables — human-readable

## 4. Recommendation (.85 confidence)

**Option A: Pure statistical analysis** with typed Pydantic proposals. ~120 LOC in `packages/orchestrator/src/owlbear_orchestrator/analysis/`. Four pattern detectors (error rate, duration outlier, repeated failure, stale dispatch). JSON + markdown dual output. Module entrypoint for CLI.

**Rationale:** KISS — dispatch-level data is simple enough for threshold-based detection. LLM analysis is overkill for counting errors and computing averages. v1 validated this approach (~142 LOC, no LLM, highly testable). The pattern extends naturally as more detectors are needed.

**Risks:**

| Risk | Mitigation |
|------|------------|
| Audit log format changes before analysis ships | Depend on #21's Pydantic models directly; schema changes propagate |
| Thresholds too aggressive/conservative | Make thresholds configurable constants; document defaults |
| No audit data yet to test against | Generate synthetic JSONL fixtures in tests (v1 pattern) |

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement analysis module with pattern detectors" --priority needed --status ideation --tags "phase-2,scope:orchestrator,type:build" --depends-on 21 --body "Create packages/orchestrator/src/owlbear_orchestrator/analysis/ with:\n- models.py: AnalysisProposal frozen Pydantic model (target_agent, category, pattern, rationale, evidence, suggested_action)\n- detectors.py: four pattern detectors (high_error_rate, slow_agent, repeated_failure, stale_dispatch)\n- analyze.py: analyze(audit_dir: Path, window: timedelta | None) entrypoint consuming audit log JSONL\n- formatters.py: JSON and markdown output formatters\n\nAC:\n- [ ] AnalysisProposal Pydantic model with 6 fields\n- [ ] analyze() reads DispatchEvent + CompletionEvent from audit JSONL files\n- [ ] High error rate detector: >= 40% failure, >= 3 dispatches per agent\n- [ ] Slow agent detector: avg duration > 2x global avg, >= 3 dispatches\n- [ ] Repeated failure detector: >= 2 failures on same task_id\n- [ ] Stale dispatch detector: dispatch with no completion > 1h\n- [ ] JSON output (default): serialized list of proposals\n- [ ] Markdown output (flag): formatted report with tables\n- [ ] No side effects, no file writes, no autonomous mutation\n- [ ] Unit tests with synthetic JSONL fixtures\n- [ ] Depends on #21 audit log Pydantic models\n\nSee docs/research/self-improvement-analysis-pipeline.md"

kanban\kanban-md.exe create "Add CLI entrypoint for analysis pipeline" --priority important --status ideation --tags "phase-2,scope:orchestrator,type:build,cli" --depends-on 31 --body "Add python -m owlbear_orchestrator.analyze entrypoint:\n- __main__.py in analysis/ package\n- Args: --window (hours, default all), --format (json|markdown, default json), --audit-dir (default data/audit/)\n- Reads audit JSONL, runs analyze(), prints output to stdout\n\nAC:\n- [ ] python -m owlbear_orchestrator.analyze runs analysis\n- [ ] --window filters by time window\n- [ ] --format json prints JSON array of proposals\n- [ ] --format markdown prints formatted report\n- [ ] Exit code 0 on success, 1 on error\n- [ ] No proposals scenario prints empty array or 'No issues detected'\n\nSee docs/research/self-improvement-analysis-pipeline.md S3.5"
```
