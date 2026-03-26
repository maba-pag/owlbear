---
id: 145
title: Council system — multi-agent structured debate with consensus
status: ideation
priority: someday
created: 2026-02-27T14:59:30.0743201+01:00
updated: 2026-03-24T13:18:27.6813721+01:00
started: 2026-03-01T20:08:55.0411741+01:00
tags:
    - agent
    - phase-14
blocked: true
block_reason: 'Research recommends defer (.35 confidence). Three prior OwlBear research docs rejected multi-persona deliberation. AC still vague and scope still bundled. Follow-up #976 captures narrowed Protocol C approach.'
class: standard
---

Assign N agents with different perspectives to debate a topic. Structured protocol: each agent presents position, responds to others, final round produces either consensus or differentiated opinion document.

Use cases: architecture decisions, code review from multiple viewpoints, risk assessment. Requires the agent framework (P8) to be solid. Research multi-agent debate literature (Constitutional AI, debate-as-alignment, etc.) before implementing.

[[2026-03-21]] Sat 13:25
## Architecture Review
**Verdict:** BLOCK

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Assign N agents with different perspectives to debate a topic. | Missing core interface contract: agent selection source, maximum N, perspective definition, and execution model are all unspecified. | Return to ideation for research and scope selection. |
| Structured protocol: each agent presents position, responds to others, final round produces either consensus or differentiated opinion document. | No mechanically verifiable protocol, stop conditions, or output schema are defined. Consensus versus differentiated opinion is a product decision, not an executable AC. | Research and specify the deliberation protocol and result contract before backlog approval. |
| Use cases: architecture decisions, code review from multiple viewpoints, risk assessment. | Bundles multiple domains with different evidence standards and governance paths. Architecture advice, code review, and risk assessment should not share an unspecified umbrella runtime. | Narrow to one primary use case after research, then split follow-up tasks by domain if needed. |
| Requires the agent framework (P8) to be solid. | P8 is now present, but this line is a prerequisite note, not a verifiable acceptance criterion. | Keep as context only; it does not make the feature implementation-ready. |
| Research multi-agent debate literature (Constitutional AI, debate-as-alignment, etc.) before implementing. | This explicitly states the prerequisite research has not been done. No council-specific research doc or recommendation is linked from the task. | Move back to ideation and block pending research. |

### Architecture Notes
- Existing multi-agent execution is synchronous inline delegation via delegate_to_agent; there is no council runtime, participant state model, or turn coordinator in the current codepath.
- Agent definitions and registry wiring support named agents plus builder/validator role policy, but there is no schema for perspectives, no participant selection rules, and no dedicated consensus artifact contract.
- Existing research covers adjacent orchestration patterns only:
  - docs/research/conversation-router.md evaluates SelectorGroupChat for routing, not structured debate.
  - docs/research/quoroom-room.md analyzes quorum/governance and explicitly rejects agent self-governance for OwlBear.
  - docs/research/orchestration-agent-frameworks.md marks board-of-directors style multi-persona deliberation as token-expensive/YAGNI at daemon scale.
- Because the task lacks both prior-art synthesis and a chosen execution model, I cannot approve it into the RED/GREEN pipeline without forcing builders to invent architecture.

### Changes Made
- Claimed #145 as architect-145
- Appended this architecture review
- Planned return of #145 from backlog to ideation pending council-specific research

### Dependencies
- Verified: P8 agent framework is complete in the roadmap and current registry/delegation codepaths
- Missing: council/debate research doc with recommendation, protocol, output schema, and governance boundary
- Reviewed: docs/research/conversation-router.md, docs/research/quoroom-room.md, docs/research/orchestration-agent-frameworks.md, src/owlbear/core/delegation.py, src/owlbear/core/agent_registry.py, src/owlbear/core/roles.py

[[2026-03-24]] Tue 03:04
## Research

- Doc: docs/research/council-debate-system.md

- Sources: 10 (6 external: Du 2023 ICML, Liang 2023 EMNLP, Chan 2023, Irving 2018, composable-models/llm_multiagent_debate, Skytliang/Multi-Agents-Debate; 4 internal: orchestration-agent-frameworks.md, conductor-orchestrator-superpowers.md, quoroom-room.md, PydanticAI docs)

- Key finding: Three prior OwlBear research docs independently rejected multi-persona deliberation (board-of-directors, quorum governance) as token-expensive and YAGNI at daemon scale.

- Protocol comparison: 4 families evaluated (convergent, adversarial-with-judge, parallel-then-synthesize, zero-sum). Protocol C (parallel-then-synthesize) is lowest cost at N+1 LLM calls.

- Scope narrowing: Architecture decisions recommended as sole use case. Code review already has 2 gates (reviewer + auditor). Risk assessment deferred.

- Recommendation (.35 confidence): Defer. Existing 4-agent pipeline provides multi-perspective review at lower token cost. If revisited, Protocol C with 2 perspectives + 1 moderator is the minimum viable approach.

- Follow-up: Created #976 (Protocol C implementation, someday/ideation).

- Sources logged in docs/sources/overview.md.

[[2026-03-24]] Tue 13:18
## Architecture Review (2026-03-24)
**Verdict:** BLOCK

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Assign N agents with different perspectives to debate a topic. | Still unspecified: no interface contract, agent selection, perspective schema, or execution model. Research doc exists but AC was never refined. | Block â€” AC rewrite required if revisited. |
| Structured protocol: each agent presents, responds, produces consensus or differentiated doc. | Research evaluated 4 protocol families and recommends Protocol C (parallel-then-synthesize) if ever implemented. But no verifiable AC exists in the task body. | Block â€” Protocol C details live in research doc and follow-up #976. |
| Use cases: architecture decisions, code review, risk assessment. | Research (section 3.3) explicitly narrows to architecture decisions only. Code review already has 2 gates. Risk assessment deferred. Original task still bundles all three. | Block â€” multi-domain bundling persists. |
| Research multi-agent debate literature before implementing. | DONE. docs/research/council-debate-system.md covers 10 sources, 4 protocol families, token cost analysis, and prior OwlBear rejections. | Research gate satisfied but finding is defer.  |

### Architecture Notes
- Research finding (.35 confidence): Defer. Three prior OwlBear research docs (orchestration-agent-frameworks.md, conductor-orchestrator-superpowers.md, quoroom-room.md) independently rejected multi-persona deliberation as token-expensive and YAGNI at daemon scale.
- Existing 4-agent pipeline (researcher, architect, reviewer, auditor) already provides multi-perspective review at existing token cost.
- Minimum viable council (Protocol C, 2+1) costs 3x tokens per decision on rate-limited Copilot endpoint.
- Follow-up #976 captures the narrowed Protocol C approach at someday/ideation for if/when token budget constraints relax.
- This original #145 is superseded by #976 for practical purposes.

### Changes Made
- Claimed #145 as copilot-architect
- Appended this architecture review
- Blocking #145 to ideation: research recommends defer, AC is still vague, scope is still bundled, and #976 captures the actionable subset.

### Dependencies
- Verified: P8 agent framework is complete
- Verified: Research doc docs/research/council-debate-system.md is complete
- Verified: Follow-up #976 exists at ideation/someday with Protocol C AC
