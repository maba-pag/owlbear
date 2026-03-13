# GCP generative-ai Repo Audit: Reusable Patterns for OwlBear (2025+)

> **Owning task:** #702 — Audit GCP generative-ai repo for other reusable patterns
> **Date:** 2026-03-09 **Status:** Complete

## 1. Context and Question

GoogleCloudPlatform/generative-ai is a large sample repo mixing 2023-era and 2026-era content.
Task #700 already covers the `always-on-memory-agent` subdirectory. This audit scans the
**remaining** directories — agents, evaluation, function-calling, orchestration, responsible-ai,
use-cases/graphrag — for patterns OwlBear could adopt. Only 2025+ content considered.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | GCP generative-ai repo (agents/) | <https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/agents> | .90 |
| 2 | GCP generative-ai repo (evaluation/) | <https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/evaluation> | .85 |
| 3 | GCP generative-ai repo (use-cases/graphrag/) | <https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/use-cases/graphrag> | .80 |
| 4 | GCP generative-ai repo (responsible-ai/) | <https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/responsible-ai> | .60 |
| 5 | GCP generative-ai repo (orchestration/) | <https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/orchestration> | .40 |
| 6 | GCP generative-ai repo (function-calling/) | <https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/function-calling> | .40 |
| 7 | OwlBear codebase — safety, eval, routing | `src/owlbear/safety/`, `tests/benchmarks/`, `docs/research/` | 1.0 |
| 8 | OwlBear conversation-router-research.md | `docs/research/conversation-router-research.md` | 1.0 |
| 9 | OwlBear evaluator-agent-final-disposition.md | `docs/research/evaluator-agent-final-disposition.md` | .95 |

## 3. Directory Inventory with Freshness

| Directory | Last Commit | Substantive? | Fresh? |
|-----------|------------|--------------|--------|
| agents/always-on-memory-agent | Mar 2026 (1 wk) | Yes — new demo | YES (covered by #700) |
| agents/genai-experience-concierge | Nov 2025 (4 mo) | Yes — 4 design pattern notebooks | YES |
| agents/research-multi-agents | Apr 2025 (11 mo) | Partial — ev_agent is older | BORDERLINE |
| evaluation/*.ipynb | Nov–Jan 2026 | Yes — agent/ADK eval | YES |
| function-calling/ | Feb 2026 | No — Gemini 2→3 migration only | NO (cosmetic) |
| orchestration/ | Feb 2026 | No — model version bumps only | NO (cosmetic) |
| responsible-ai/ | Jan 2026 | No — core content 2+ years old | NO (cosmetic) |
| use-cases/graphrag | Feb 2026 (3 wk) | Yes — agentic GraphRAG with Neo4j+ADK | YES |

## 4. Analysis: Shortlisted Patterns

### 4.1 Comparison Table

| Pattern | Source | OwlBear Gap? | Gemini-Locked? | Adapt Cost | Verdict |
|---------|--------|-------------|---------------|-----------|---------|
| Agentic GraphRAG | use-cases/graphrag | No — KnowledgeToolset + graph expansion | ADK + Neo4j | N/A | **SKIP** (.90) |
| Guardrail Classifier | concierge/guardrail | Partial | LangGraph + Gemini | Medium | **SKIP** (.80) |
| Semantic Router | concierge/semantic-router | No — already solved (#296) | LangGraph + Gemini | N/A | **SKIP** (.90) |
| Task Planner | concierge/task-planner | No — we have planner agent | LangGraph + Gemini | N/A | **SKIP** (.90) |
| Agent Behavioral Eval | evaluation/create_agent*.ipynb | **YES** — no agent-level eval | Vertex AI Eval SDK | High | **ADAPT** (.75) |
| Tool Trajectory Eval | evaluation/evaluating_adk_agent | **YES** — no tool selection tests | Vertex AI Eval SDK | Medium | **ADAPT** (.80) |
| Prompt Attack Labs | responsible-ai/ | Marginal — security audit covers this | GCP APIs (DLP, NL) | High | **SKIP** (.85) |

### 4.2 Why Most Patterns Are SKIP

**Agentic GraphRAG:** Our `KnowledgeToolset` + SQLite graph + Qdrant vectors + BGE-M3 already
implements this pattern. The GCP demo uses Neo4j (graph DB) + ADK (agent framework); we use
SQLite FTS + Qdrant + PydanticAI. Same concept, different stack. Benchmark results in
`docs/graph-expansion-benchmark-results.md` confirm multi-hop graph expansion works.

**Guardrail Classifier:** GCP's pattern is an LLM-based input classifier (block/allow) before
the chat node. OwlBear gates at tool execution time via `ApprovalGateToolset` + `CommandSafetyGuard`.
Input-level LLM guardrails are for adversarial user scenarios (customer-facing chatbots). OwlBear
is single-user, laptop-resident — the user IS the operator. YAGNI (sources 1, 7).

**Semantic Router:** GCP implements LLM-based intent classification → conditional routing to
sub-agents. OwlBear researched this in `conversation-router-research.md` and chose prompt-based
routing (.85 confidence) — simpler, zero extra LLM calls, mid-conversation rerouting is free.
The GCP implementation validates the pattern concept but uses LangGraph state machines we
explicitly rejected for KISS reasons (sources 1, 8).

### 4.3 Patterns Worth Adapting

**Agent Behavioral Evaluation** — The GCP notebooks demonstrate a workflow we lack:

1. Define evaluation dataset: prompts + expected agent behaviors
2. Run agent inference → capture `intermediate_events` (tool calls, reasoning)
3. Evaluate against expectations using metrics (tool selection, response quality)
4. Report results with statistical analysis

OwlBear has IR benchmarks (ranx/BEIR for retrieval quality) and pipeline E2E tests
(`test_pipeline_e2e.py` — 4-step delegation chain), but NO systematic agent behavioral
evaluation. The gap: we can't answer "does the builder consistently pick the right tool
for a given task type?" or "does the orchestrator route correctly 95% of the time?"

**Tool Trajectory Evaluation** — The ADK evaluation notebook introduces `trajectory_single_tool_use`
metrics. This tests: given prompt X, did the agent call the expected tool? OwlBear's
`test_agent_definitions.py` verifies agent metadata (tools, roles, skills) but never tests
actual tool selection behavior under realistic prompts.

### 4.4 Adaptation Path for Evaluation Patterns

The Vertex AI Eval SDK is Gemini-specific and cannot be used directly. However, the
**pattern** is framework-agnostic:

| GCP Component | OwlBear Equivalent | Status |
|--------------|-------------------|--------|
| ADK Agent | PydanticAI Agent + `OwlBearAgent` | Exists |
| Vertex AI Eval SDK | Custom eval harness (extend `tests/benchmarks/`) | **Build** |
| Eval dataset (prompts) | Test fixtures with expected tool calls | **Build** |
| `intermediate_events` | PydanticAI `RunResult.all_messages()` | Exists |
| `trajectory_single_tool_use` | Custom metric: compare actual vs expected tool calls | **Build** |
| Eval Management Service | Markdown report in `docs/` | **Build** (lightweight) |

Implementation cost is MEDIUM: ~200 LOC for a lightweight eval harness that:
- Takes a list of (prompt, expected_tool_calls) pairs
- Runs each through a FunctionModel/TestModel agent
- Compares actual tool calls against expectations
- Reports accuracy, missed tools, unexpected tools

## 5. Recommendation (.80 confidence)

**Adapt the agent behavioral evaluation pattern.** Build a lightweight tool-trajectory
evaluation harness in `tests/benchmarks/` that validates agent tool selection behavior.
Skip all other GCP patterns — they're either already implemented in OwlBear, Gemini-locked,
or YAGNI for our single-user dev assistant use case.

**Risk:** Agent behavioral eval with mock models tests routing logic, not real LLM behavior.
Mitigation: start with FunctionModel-based tests (deterministic, CI-safe), add optional
`@pytest.mark.api` tests with real models later.

## 6. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Design agent tool-trajectory evaluation harness" --priority nice-to-have --status backlog --tags "scope:core,test,evaluation,phase-research" --body "Adapt the GCP generative-ai evaluation pattern for OwlBear. Design a lightweight eval harness in tests/benchmarks/ that:\n- [ ] Takes (prompt, expected_tool_calls) pairs as eval dataset\n- [ ] Runs each prompt through agent with FunctionModel\n- [ ] Compares actual tool_call sequence against expected\n- [ ] Reports per-agent accuracy (tool selection hit rate)\n- [ ] Outputs markdown report\nInspired by GCP evaluating_adk_agent.ipynb trajectory_single_tool_use metric. See docs/research/gcp-generative-ai-audit-research.md §4.3-4.4."

kanban\kanban-md.exe create "Create eval dataset: orchestrator routing test cases" --priority nice-to-have --status backlog --tags "scope:copilot,test,evaluation" --body "Define a set of 20+ (prompt, expected_agent_delegation) pairs for orchestrator routing evaluation:\n- [ ] 'I have an idea for a feature' → planner\n- [ ] 'Fix the bug in config.py' → builder\n- [ ] 'Research how others do X' → researcher\n- [ ] etc. per taxonomy in conversation-router-research.md §3.4\n- [ ] Include ambiguous cases that should trigger ask_user\nDepends on: evaluation harness task. See docs/research/gcp-generative-ai-audit-research.md §4.3."
```
