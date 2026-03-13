# Conversation Router — Intent Detection and Agent Dispatch

> **Owning task:** #296 — Conversation router — intent detection and agent dispatch
> **Date:** 2026-03-01
> **Status:** Complete

## 1. Context and Question

The orchestrator agent has a `delegate_to_agent` tool and access to six specialist agents (planner, coder, researcher, reviewer, writer, orchestrator-self), but no mechanism for detecting user intent and dispatching to the correct specialist. When a user says "I have an idea" vs. "fix this bug" vs. "what's the status", the same orchestrator runs with no structured routing. This research answers: what is the simplest, most effective pattern for intent detection and agent dispatch within our PydanticAI + markdown-defined agent architecture?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| PydanticAI multi-agent docs | <https://ai.pydantic.dev/multi-agent-applications/> | .95 | Agent delegation pattern, output functions for hand-off, `RunContext.usage` propagation |
| PydanticAI structured output | <https://ai.pydantic.dev/output/> | .90 | `output_type=SomeModel` for structured classification, union return types |
| AutoGen SelectorGroupChat | <https://github.com/microsoft/autogen> (`_selector_group_chat.py`) | .85 | LLM-based speaker selection with prompt template, `selector_func` override, `candidate_func` filtering, retry with feedback |
| Semantic Router (aurelio-labs) | <https://github.com/aurelio-labs/semantic-router> | .80 | Embedding-based intent routing (no LLM call), `Route` objects with utterances, sub-10ms decisions |
| CrewAI hierarchical process | <https://docs.crewai.com/concepts/crews> | .70 | `manager_agent` delegates to crew members, `Process.hierarchical`, role/goal/backstory |
| OwlBear prior research | `docs/pydantic-ai-multi-agent-research.md`, `docs/agent-patterns-research.md` | .95 | Confirmed level-2 delegation, DelegationToolset, AgentRegistry, role policies |
| OwlBear current codebase | `src/owlbear/core/delegation.py`, `src/owlbear/agents/orchestrator.md` | 1.0 | Existing `delegate_to_agent` tool, orchestrator system prompt, agent definitions |

## 3. Analysis

### 3.1 Routing Strategy Comparison

| Approach | How it works | Complexity | Latency | Testability | OwlBear fit |
|----------|-------------|------------|---------|-------------|-------------|
| **A. Prompt-based (orchestrator decides)** | Routing rules in orchestrator system prompt; LLM picks agent via `delegate_to_agent` tool | Low | 1 LLM call (part of normal turn) | Medium — test via mock model responses | **.85** |
| **B. Structured output classifier** | Dedicated routing agent with `output_type=IntentClassification`; returns intent enum + agent name, then application code delegates | Medium | 1 extra LLM call for classification | High — Pydantic model validates output | .80 |
| **C. Embedding-based (semantic-router)** | Pre-defined utterance vectors per route; cosine similarity selects agent in <10ms; no LLM call | Medium | ~5ms (no LLM) | High — deterministic | .55 |
| **D. Hybrid (embedding pre-filter + LLM)** | Semantic-router narrows to 2-3 candidates, LLM picks final | High | ~5ms + 1 LLM call | Medium | .50 |
| **E. `selector_func` pattern (AutoGen-style)** | Code-based function inspects message, returns agent name or None (falls back to LLM selection) | Medium | ~0ms for code path | High — pure function | .75 |

### 3.2 Evaluation Criteria

| Criterion | A. Prompt | B. Structured | C. Embedding | D. Hybrid | E. Selector |
|-----------|-----------|---------------|--------------|-----------|-------------|
| **KISS** | High | Medium | Medium | Low | High |
| **YAGNI** | High | Medium | Low (needs embeddings infra) | Low | High |
| **Accuracy** | Good (LLM understands nuance) | Good (forced structure) | Decent (fails on novel phrasing) | Best | Good (keywords) |
| **Mid-conversation reroute** | Native (LLM sees full context) | Needs re-classification | Needs message window | Complex | Manual rules |
| **Fallback to ask_user** | Prompt instructs "when unsure, ask" | `intent: ambiguous` variant | No match → None → ask | Same | Return None → ask |
| **New dependency** | None | None | `semantic-router` + embeddings | `semantic-router` | None |
| **Token cost** | Zero extra (routing is part of normal orchestration) | +~200 tokens per classification | Zero | +~200 tokens | Zero |

### 3.3 Prior Art Patterns — Key Takeaways

**AutoGen SelectorGroupChat** uses a prompt template with `{roles}`, `{participants}`, `{history}` variables. The LLM returns a single speaker name. If parsing fails, it retries up to `max_selector_attempts` with corrective feedback. A `selector_func` override (pure Python) can short-circuit the LLM call. This is over-engineered for our case (we have one orchestrator, not a group chat) but the retry-with-feedback idea is valuable.

**Semantic Router** defines `Route` objects with `name` and `utterances` (example phrases). At runtime, the user's message is embedded and compared against route centroids. Sub-10ms classification. Excellent for deterministic, high-throughput routing (hotlines, chatbots). But it requires maintaining utterance lists, adds an embedding dependency, and struggles with novel phrasing without LLM fallback. Not aligned with KISS/YAGNI for our six-agent system.

**PydanticAI's native pattern** is simplest: the orchestrator agent already has `delegate_to_agent` as a tool. The LLM naturally decides which agent to call based on the user's message and the tool description. The only missing piece is explicit routing instructions in the system prompt that enumerate intents and map them to agent names.

### 3.4 Intent Taxonomy

Based on OwlBear's agent inventory and AC, six intents:

| Intent | Trigger patterns | Target agent | Delegation style |
|--------|-----------------|--------------|------------------|
| `plan` | "I have an idea", "let's plan", "break this down", "new feature" | `planner` | delegate |
| `build` | "fix", "implement", "code", "add a test", "refactor" | `coder` | delegate |
| `research` | "research", "investigate", "compare", "what's the best way to" | `researcher` | delegate |
| `review` | "review", "check", "verify", "is this correct" | `reviewer` | delegate |
| `status` | "status", "progress", "what's on the board", "standup" | orchestrator (self) | direct |
| `question` | ambiguous / general question / neither of the above | orchestrator + `ask_user` | clarify |

## 4. Recommendation (.85 confidence)

**Approach A — Prompt-based routing in the orchestrator's system prompt.** Rationale:

1. **Zero new infrastructure.** The `delegate_to_agent` tool and `AgentRegistry` already exist. We only need to update the orchestrator's markdown definition with explicit routing rules.
2. **KISS/YAGNI.** No new dependencies, no new Pydantic models, no embedding pipeline. The LLM already reasons about which tool to call — we just need to give it a clear decision framework.
3. **Mid-conversation rerouting is free.** The LLM sees full conversation history and can switch agents when the user redirects ("actually, let's research this first").
4. **Fallback is natural.** The prompt instructs "when intent is ambiguous, use `ask_user` to clarify before delegating."
5. **Testable.** PydanticAI's `TestModel` / `FunctionModel` can return predetermined tool calls. Tests verify that given a user message, the orchestrator calls `delegate_to_agent` with the expected agent name.

**What to add to `orchestrator.md`:**

A structured routing section in the system prompt with:

- Intent-to-agent mapping table (the taxonomy from §3.4)
- Decision rules: "Read the user's message. Classify it as one of: plan, build, research, review, status, question. Then delegate to the matching agent."
- Fallback rule: "If the intent is unclear, ask the user to clarify."
- Mid-conversation rule: "Re-evaluate intent on each turn. If the user changes direction, delegate to the new agent."

**What NOT to do (YAGNI):**

- No dedicated `RouterAgent` — the orchestrator IS the router
- No `IntentClassification` Pydantic model — structured output adds a classification LLM call before the orchestrator can even begin reasoning
- No semantic-router dependency — embedding-based routing is for high-throughput APIs, not a 6-agent dev system with ~1 req/min
- No `pydantic-graph` FSM — the routing decision is a single step, not a state machine

**Risk:** Prompt-based routing accuracy depends on the LLM's ability to parse routing instructions. Mitigation: the intent taxonomy is small (6 categories) and the agent descriptions are clear. If accuracy is insufficient in practice, Approach E (selector_func short-circuit for obvious keywords) can be layered on top without architectural change.

## 5. Follow-up Tasks

### 5.1 Implementation tasks

```
kanban\kanban-md.exe create "Update orchestrator system prompt with intent routing rules" --priority needed --tags "phase-12,agent,routing" --body "Add structured routing section to src/owlbear/agents/orchestrator.md:\n- [ ] Intent-to-agent mapping table (plan→planner, build→coder, research→researcher, review→reviewer, status→self, question→ask_user)\n- [ ] Decision framework: classify intent then delegate\n- [ ] Mid-conversation rerouting rule\n- [ ] Fallback: ambiguous → ask_user\n- [ ] Keep system prompt under 1500 tokens\nSee docs/conversation-router-research.md §4"

kanban\kanban-md.exe create "Unit tests for intent routing — mock LLM delegation paths" --priority needed --tags "phase-12,agent,routing,test" --body "Test each intent classification path using PydanticAI TestModel/FunctionModel:\n- [ ] 'I have an idea for a feature' → delegates to planner\n- [ ] 'Fix the bug in config.py' → delegates to coder\n- [ ] 'Research how others do X' → delegates to researcher\n- [ ] 'Review the changes in PR #5' → delegates to reviewer\n- [ ] 'What's the status of the board?' → orchestrator handles directly\n- [ ] Ambiguous message → calls ask_user for clarification\n- [ ] Mid-conversation reroute: user says 'actually research this first' → switches to researcher\n- [ ] Verify delegate_to_agent called with correct agent_name and task\nSee docs/conversation-router-research.md §3.4"

kanban\kanban-md.exe create "Add agent descriptions to delegate_to_agent tool context" --priority important --tags "phase-12,agent,routing" --body "Ensure the orchestrator's system prompt or delegation tool description includes all available agent names and their one-line descriptions (from AgentRegistry.definitions). This helps the LLM pick the right agent:\n- [ ] Inject agent catalog into orchestrator system prompt at build time (build_agent method or bootstrap)\n- [ ] Or document static list in orchestrator.md (simpler, less dynamic)\n- [ ] Unit test: orchestrator knows about all registered agents\nSee docs/conversation-router-research.md §4"
```

### 5.2 Dependency note

These tasks depend on #293 (agent registry wiring, per task #296's `depends_on`). The routing tests depend on the orchestrator prompt update being done first.
