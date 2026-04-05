# Council System — Multi-Agent Debate Research

> **Owning task:** #145 — Council system — multi-agent structured debate with consensus
> **Date:** 2026-03-24 **Status:** Complete

## 1. Context and Question

Task #145 proposes assigning N agents with different perspectives to debate a topic, producing consensus or a differentiated opinion document. The architect blocked it (2026-03-21) citing: no prior-art synthesis of debate literature, no protocol specification, no scope narrowing, and bundled use cases. This research addresses all four gaps. [S1–S10]

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | Du et al. "Improving Factuality through Multiagent Debate" (ICML 2024) | .90 | Convergent debate: N agents propose, see each other's responses, K rounds, arrive at common answer |
| S2 | Liang et al. "MAD: Multi-Agent Debate" (EMNLP 2024) | .90 | Adversarial debate with judge; addresses Degeneration-of-Thought; adaptive round termination |
| S3 | Chan et al. "ChatEval" (arXiv 2308.07201) | .80 | Multi-agent referee team for evaluation via debate; human-mimicking assessment |
| S4 | Irving et al. "AI Safety via Debate" (arXiv 1805.00899) | .75 | Foundational: two-player zero-sum debate game, human judge, PSPACE theory |
| S5 | composable-models/llm_multiagent_debate | .85 | Reference implementation of Du et al. (516 stars, ICML 2024) |
| S6 | Skytliang/Multi-Agents-Debate | .85 | Reference implementation of Liang et al. MAD (539 stars, EMNLP 2024) |
| S7 | PydanticAI multi-agent docs | .95 | Agent delegation + programmatic hand-off patterns |
| S8 | OwlBear orchestration-agent-frameworks.md | 1.0 | Prior rejection: "Board of Directors — token-expensive, YAGNI at daemon scale" |
| S9 | OwlBear conductor-orchestrator-superpowers.md | 1.0 | Prior rejection: "Board of Directors — NOT recommended (5 LLM calls per decision)" |
| S10 | OwlBear quoroom-room.md | 1.0 | Prior rejection: "Skip quorum governance — human-gated approval more appropriate" |

## 3. Analysis

### 3.1 Protocol Family Comparison

| Protocol | Roles | Stop Condition | Token Cost (per session) | Prior Art |
|----------|-------|----------------|--------------------------|-----------|
| **A. Convergent debate** | N agents (no judge) | K fixed rounds or early consensus | N×K calls | Du et al. [S1, S5] |
| **B. Adversarial with judge** | 2 debaters + 1 judge | Judge declares winner or K-round limit | 2K + K judge calls | Liang et al. [S2, S6] |
| **C. Parallel-then-synthesize** | N perspective agents + 1 moderator | 1 round parallel + 1 synthesis | N + 1 calls | ChatEval [S3] |
| **D. Zero-sum alignment debate** | 2 agents + human judge | Human selects winner | 2K + human time | Irving et al. [S4] |

### 3.2 OwlBear Fit Assessment

| Criterion | A. Convergent | B. Adversarial | C. Parallel-synth | D. Zero-sum |
|-----------|:------------:|:--------------:|:-----------------:|:-----------:|
| KISS | Medium | Low | **High** | Low |
| YAGNI | Low | Low | Medium | Low |
| Token cost (3 agents, 2 rounds) | 6 calls | 6 calls | **4 calls** | 4+human |
| PydanticAI fit | Hand-off loop | Hand-off loop | Parallel delegation | Hand-off loop |
| Copilot rate-limit safety | Risk | Risk | **Low risk** | N/A |
| Implementation LOC | ~80 | ~120 | **~50** | N/A |

### 3.3 Use Case Narrowing

The architect flagged that architecture decisions, code review, and risk assessment have different evidence standards. [S8, S9] Analysis:

| Use Case | Current OwlBear Gate | Debate Added Value | Recommendation |
|----------|---------------------|-------------------|----------------|
| Architecture decisions | Single architect agent | Medium — catches KISS/YAGNI/security blind spots | **Primary candidate** |
| Code review | Reviewer + auditor (2 gates) | Low — already multi-perspective | Skip |
| Risk assessment | No formal risk gate | Medium — but risk is subjective | Defer to decision request |

### 3.4 Existing Pipeline Multi-Perspective Coverage

OwlBear already provides structured multi-perspective review without a council system:

| Pipeline Stage | Agent | Perspective |
|----------------|-------|-------------|
| ideation → backlog | researcher | Prior art, feasibility |
| backlog → todo | architect | KISS/YAGNI, AC quality, scope |
| review | reviewer | Test quality, security, correctness |
| done → archived | auditor | Full integration, AC compliance |

This 4-agent pipeline produces 4 independent evaluations per task at existing token cost. A council adds N×K *additional* calls per decision on top of the existing pipeline. [S7, S8, S9, S10]

### 3.5 Token Cost Analysis

OwlBear uses GitHub Copilot (rate-limited). Minimum viable council (Protocol C, 2 perspectives + moderator):

| Scenario | LLM Calls | Approximate Tokens | Frequency |
|----------|-----------|--------------------:|-----------|
| Single architect gate (current) | 1 | ~4K | Every backlog task |
| Council (Protocol C, 2+1) | 3 | ~12K | Selected tasks only |
| Council (Protocol A, 3 agents, 2 rounds) | 6 | ~24K | Selected tasks only |

3× token cost for Protocol C; 6× for Protocol A — on a rate-limited endpoint. [S7, S8]

### 3.6 Prior OwlBear Rejections

Three independent research docs rejected related patterns:

1. **orchestration-agent-frameworks.md §3.4**: "Board of Directors (multi-persona deliberation) — token-expensive for daemon scale" (.40 confidence → Skip) [S8]
2. **conductor-orchestrator-superpowers.md §4f**: "Board of Directors — NOT recommended. 5 parallel LLM calls per decision. OwlBear's single architect gate is sufficient for the project's scale." [S9]
3. **quoroom-room.md §4**: "Skip quorum governance. OwlBear's human-gated approval system is more appropriate." (.40 confidence) [S10]

## 4. Recommendation (.35 confidence — defer)

**Defer.** The existing 4-agent pipeline already provides multi-perspective review at lower token cost. Three prior research docs independently rejected multi-persona deliberation for OwlBear. The marginal quality improvement does not justify the 3–6× token cost increase on a rate-limited Copilot endpoint.

**If revisited later** (.65 confidence for Protocol C if token budget expands):

- Narrow to architecture decisions only (§3.3)
- Use Protocol C — parallel-then-synthesize (§3.1, lowest token cost)
- 2 perspective agents (e.g., simplicity-advocate, security-advocate) + 1 moderator
- Output: structured Pydantic model with `{positions: list, consensus: str | None, dissent: list, confidence: float}`
- Opt-in via kanban task tag `council:arch` or CLI flag
- Human approval gate on output (no autonomous action)
- Implementation: ~50 LOC using PydanticAI programmatic hand-off (level 3) [S7]

**Risk:** Even Protocol C costs 3 LLM calls per arch decision. With ~5 architecture decisions per orchestration session, that's 15 extra calls — potentially 50% of a rate-limit window. Mitigation: use only for tasks tagged `priority:needed` or higher.

## 5. Follow-up Tasks

Given the defer recommendation, creating one minimal follow-up task to keep the option tracked without pipeline overhead. The architect will decide whether to approve it into `todo` if/when the token budget constraint relaxes.

```
kanban\kanban-md.exe create "Council system — minimal Protocol C for architecture decisions" --priority someday --status ideation --tags "agent,phase-14,research" --body "Implement opt-in parallel-then-synthesize council for architecture gate decisions only. See docs/research/council-debate-system.md §4. AC: (1) 2 perspective agents + 1 moderator agent using PydanticAI programmatic hand-off. (2) Council output is a structured Pydantic model with positions, consensus, dissent, and confidence. (3) Triggered only by kanban task tag council:arch. (4) Human approval gate on council output. (5) Token cost per session ≤ 4 LLM calls. (6) No changes to default pipeline — council is opt-in only. Depends on: none (P8 agent framework is complete)."
```
