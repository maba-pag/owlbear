---
id: 146
title: Self-improvement pipeline — analytics to evaluation to human-gated proposals
status: backlog
priority: someday
created: 2026-02-27T14:59:42.7922645+01:00
updated: 2026-03-21T13:20:25.32188+01:00
started: 2026-03-01T20:08:57.7214986+01:00
tags:
    - agent
    - analytics
    - phase-14
depends_on:
    - 142
blocked: true
block_reason: 'Split into #893, #894, #895, #896 - work tracked there'
class: standard
---

The 'agent improver' — but human-gated, never autonomous. Pipeline:
1. Collect: agent analytics (tool usage, errors, latency, task success/failure)
2. Evaluate: compare agent performance against quality criteria
3. Propose: generate improvement suggestions (prompt tweaks, tool changes, skill additions)
4. Review: present proposals to user via ask_user, never auto-apply
5. Apply: user-approved changes applied to agent definitions

This is the most dangerous feature — AI modifying its own instructions can degrade rapidly. The human gate is non-negotiable.

[[2026-03-21]] Sat 13:20
## Architecture Review
**Verdict:** SPLIT -> #893, #894, #895, #896

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. Collect: agent analytics (tool usage, errors, latency, task success/failure) | Existing observability foundation already provides the collection substrate; keeping this on the umbrella card would encourage a duplicate analytics store. | Split into #893/#894 and require reuse of EventStore query/summary/tool_stats. |
| 2. Evaluate: compare agent performance against quality criteria | Missing executable contract: no quality criteria, output schema, or no-op behavior is defined. | Split into #893/#894 with a typed proposal contract and explicit empty-input behavior. |
| 3. Propose: generate improvement suggestions (prompt tweaks, tool changes, skill additions) | Bundled with evaluation and unconstrained target scope. | Split into #893/#894 and constrain outputs to structured agent-definition proposals only. |
| 4. Review: present proposals to user via ask_user, never auto-apply | Correct safety direction, but the review/apply boundary is not mechanically specified. | Split into #895/#896 with explicit denial/timeout and preview requirements. |
| 5. Apply: user-approved changes applied to agent definitions | Highest-risk step; current approval-gate wiring does not cover FileToolset writes. | Split into #895/#896 and isolate this behind a dedicated apply surface limited to .github/agents/*.md. |
| Human gate is non-negotiable | Correct invariant, but not verifiable as written on this umbrella card. | Preserve as a binding safety constraint in #895/#896 AC. |

### Architecture Notes
- Reuse the existing observability path already wired in bootstrap/hooks.py via ObservabilityHook and EventStore. #146 must consume that data, not introduce a second analytics persistence layer.
- Existing human interaction already lives in AskUserToolset, while destructive approvals flow through ApprovalGateToolset. However bootstrap/toolsets.py currently gates TerminalToolset, GitLocalToolset, and GitHubToolset only; FileToolset write/create operations are not approval-gated today.
- Agent definitions are loaded from .github/agents/*.md through parse_agent_definition() and AgentRegistry.scan(). Any apply path must validate modified agent markdown before persisting or reloading so a bad proposal cannot break agent startup.
- RetrospectiveHook already handles a separate learning loop into the knowledge graph. This task should stay limited to proposal generation plus human-gated agent-definition mutation. Scheduling remains out of scope for #146 and belongs with #147.
- Failure-mode guardrails required by the split tasks: empty metrics -> safe no-op proposal set; denied/timeout approvals -> no file mutation; invalid modified markdown -> abort without persisting.

### Changes Made
- Created #893: Test self-improvement proposal pipeline from observability metrics -> todo
- Created #894: Implement self-improvement proposal pipeline from observability metrics -> todo, depends on #893
- Created #895: Test human-gated self-improvement apply workflow for agent definitions -> todo, depends on #894
- Created #896: Implement human-gated self-improvement apply workflow for agent definitions -> todo, depends on #895
- Kept #146 as the umbrella and blocked direct execution; child tasks now track the work.

### Dependencies
- Verified: #142 is archived and its observability intent is already represented in the existing EventStore/ObservabilityHook codepath.
- Added: #893 -> #894 -> #895 -> #896
- Deferred intentionally: any scheduling or periodic trigger remains separate from this split and belongs to #147.
