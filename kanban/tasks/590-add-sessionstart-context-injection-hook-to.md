---
id: 590
title: Add SessionStart context injection hook to pipeline agents (Phase 4)
status: backlog
priority: someday
created: 2026-04-04T07:56:04.9327665+02:00
updated: 2026-04-04T16:20:32.1606574+02:00
tags:
    - scope:agents
    - hooks
    - type:build
class: standard
---

## Context
See docs/research/agent-scoped-hooks.md §3.2 for lifecycle hook analysis.
Phase 4 of VS Code agent-scoped hooks adoption. SessionStart hooks inject project context (git branch, recent commits) to reduce cold-start errors in pipeline agents.

## Acceptance Criteria
- [ ] Create scripts/hooks/session-context.ps1 that outputs additionalContext with git branch name and last 3 commit subjects
- [ ] Add SessionStart hook to agents/builder.agent.md, test-writer.agent.md, and doc-writer.agent.md frontmatter
- [ ] Script returns empty JSON {} on git failures (non-blocking)
- [ ] Script executes in under 5 seconds
- [ ] Agent files parse as valid YAML frontmatter

[[2026-04-04]] Sat 16:20
## Research
- Research doc: docs/research/sessionstart-context-injection-hook.md
- Sources: 5 studied, 5 high-relevance (all in-repo or already attributed)
- Recommendation: Proceed with agent-scoped SessionStart hooks as specified in AC. ~25 LOC script, follows established hook pattern. (confidence: .72)
- Follow-up tasks created: none (this IS the implementation task)
- Decision requests: none

### Key Findings
1. VS Code SessionStart hook I/O is well-documented: additionalContext output confirmed
2. SessionStart routing for subagent sessions is UNVERIFIED — docs confirm Stop/SubagentStop duality but make no parallel statement for SessionStart
3. Impact if SessionStart doesn't fire for subagents: zero harm (agents proceed without extra context, status quo). Fallback: swap to SubagentStart event (1 YAML line per agent)
4. No dependency on Phase 3 (#589) — different script, different event

### AC Addition (proposed)
- Add TDD verification step: confirm SessionStart fires for subagent sessions via Chat Hooks output channel
- If it doesn't fire, switch from SessionStart to SubagentStart (same script)

## Challenge Results
- Challenger: FALLBACK — challenger subagent not available in researcher toolset
- Codebase exploration found SessionStart-subagent routing ambiguity
- Confidence in original: .72
- Key challenges: SessionStart may not fire for subagent-only agents (unverified in VS Code docs)
- Researcher response: accepted risk as low-impact — hook is purely additive, verifiable during TDD RED, fallback to SubagentStart is trivial
