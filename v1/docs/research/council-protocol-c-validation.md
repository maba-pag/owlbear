# Council Protocol C — Implementation Validation

> **Owning task:** #976 — Council system — minimal Protocol C for architecture decisions
> **Date:** 2026-03-24 **Status:** Complete

## 1. Context and Question

Task #976, created as a follow-up from `docs/research/council-debate-system.md` (#145),
asks whether OwlBear should implement a minimal parallel-then-synthesize council for
architecture gate decisions. The parent research recommended deferral at .35 confidence.
This validation re-examines that recommendation against the current codebase state and
PydanticAI capabilities.

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | PydanticAI multi-agent docs (v1.63+) | .95 | Level 3 programmatic hand-off and agent delegation patterns [confirmed] |
| S2 | PydanticAI beta graph parallel execution | .80 | Broadcasting + join for formal fan-out/fan-in; beta since v1.x |
| S3 | Chan et al. "ChatEval" (arXiv 2308.07201) | .80 | Parallel referee team evaluation — closest match for Protocol C |
| S4 | OwlBear council-debate-system.md (#145) | 1.0 | Parent research: Protocol C recommended at .65 if token budget expands |
| S5 | OwlBear conductor-orchestrator-superpowers.md | 1.0 | Prior: "Board of Directors — NOT recommended. 5 LLM calls per decision." |
| S6 | OwlBear orchestration-agent-frameworks.md | 1.0 | Prior: "Board of Directors — token-expensive for daemon scale" (.40) |
| S7 | OwlBear quoroom-room.md | 1.0 | Prior: "Skip quorum governance — human-gated approval more appropriate" |
| S8 | OwlBear delegation.py, agent_registry.py | 1.0 | Existing delegation infra (DelegationToolset, DispatchContext, AgentRegistry) |

## 3. Analysis

### 3.1 Technical Feasibility (.85 confidence — feasible)

| Concern | Assessment | Evidence |
|---------|-----------|----------|
| Parallel agent runs | Supported | `asyncio.gather(agent_a.run(...), agent_b.run(...))` works with PydanticAI [S1] |
| Structured council output | Supported | Existing pattern: `RetroFindings`, `ExtractionResult`, `ProjectDefinition` [S8] |
| `pydantic_graph` needed? | No | `asyncio.gather` suffices for 2 parallel agents; graph adds beta dep, YAGNI [S2] |
| PydanticAI version | OK | v1.63.0 installed; all required features (structured output, multi-agent) stable |
| Estimated LOC | ~50 | One module, 2 perspective agents, 1 moderator, 1 Pydantic output model |

### 3.2 Architecture Fit (.75 confidence — clean but unnecessary)

| Criterion | Rating | Evidence |
|-----------|--------|---------|
| Integration surface | Small | New `council.py` module; architect agent reads output; tag-triggered |
| Pipeline disruption | None | Opt-in via `council:arch` tag per AC; default pipeline unchanged |
| Existing infra reuse | High | Uses `AgentRegistry`, `OwlBearDeps`, structured output — no new patterns |
| Dependency additions | None | No new packages; uses existing PydanticAI + asyncio |

### 3.3 Token Cost vs. Existing Coverage

The existing pipeline already provides 4 independent perspectives at zero additional cost:

| Stage | Agent | Perspective | Calls |
|-------|-------|-------------|-------|
| ideation to backlog | researcher | Prior art, feasibility | 1+ |
| backlog to todo | architect | KISS/YAGNI, AC quality, scope | 1 |
| review | reviewer | Test quality, security, correctness | 1 |
| done to archived | auditor | Full integration, AC compliance | 1 |

Protocol C council adds 3 LLM calls per tagged task on top of the architect's existing
call. With ~5 arch decisions per orchestration session, that is 15 extra calls —
potentially 50% of a Copilot rate-limit window [S4, S5, S6].

### 3.4 Changed-Circumstances Check

| Factor | Status at parent research | Status now | Impact |
|--------|--------------------------|------------|--------|
| PydanticAI parallel support | Level 3 hand-off available | Same + beta graph available | Marginal: graph is YAGNI; asyncio.gather was always sufficient |
| Copilot rate limit | Binding constraint | Still binding (api.individual.githubcopilot.com) | None — the core blocker is unchanged |
| Pipeline agent count | 4 agents (researcher, architect, reviewer, auditor) | Same 4 agents + hooks | None — multi-perspective coverage already in place |
| Architect quality gaps | No evidence cited | No evidence in board history | None — no observed failures justifying a council |
| Prior rejections | 3 independent rejections | Still 3 rejections, no counter-evidence | None |

## 4. Recommendation (.40 confidence — keep deferred)

**Maintain deferral.** Nothing material has changed since the parent research.

- The Copilot rate limit is still the binding constraint (3 extra calls x 5 decisions = 15 calls/session).
- The existing 4-agent pipeline provides adequate multi-perspective coverage with zero additional cost.
- Three prior research docs independently rejected multi-persona deliberation for OwlBear [S5, S6, S7].
- No evidence of architect-gate quality failures that a council would have caught.
- The implementation is technically straightforward (~50 LOC, asyncio.gather) and can be built quickly if the trigger condition is met.

**Trigger condition for revisiting** (any of):

1. Copilot switches to a non-rate-limited plan or a higher-throughput endpoint
2. Evidence that single-architect decisions produced quality defects a council would catch
3. OwlBear manages external projects where the architect lacks domain context

**If implemented:** Use the AC as-is — it correctly specifies Protocol C with asyncio.gather
(not pydantic_graph), structured Pydantic output, tag-based opt-in, and human approval gate.

## 5. Follow-up Tasks

No new tasks needed. Task #976 should advance to `backlog` at `someday` priority so the
architect can park it. The AC is already well-specified for future implementation.
