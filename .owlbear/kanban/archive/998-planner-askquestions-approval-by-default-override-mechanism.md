---
id: 998
title: 'Planner: askQuestions approval by default + override mechanism'
status: backlog
priority: important
created: 2026-04-18T21:26:18.196561+00:00
updated: 2026-04-18T21:55:07.862243+00:00
tags:
- type:improvement
- scope:agents
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Problem
The planner agent (`share/agents/planner.agent.md`) returns a decomposition plan and asks "Approve this plan to create all N subtasks?" — then exits. This forces the caller (ideator or user) to either re-invoke planner with explicit "create now" or create the tasks manually.

Observed during ideation #973: planner returned 10-task decomposition with dependency graph, asked for approval, then exited stateless. Mediator created tasks manually.

## Fix (per user direction)
The planner should ask for approval **by default** using askQuestions (not freeform prose). If the caller wants auto-creation, they prompt planner with explicit "skip approval, create immediately" instruction.

This needs to be expressed in:
1. **Planner agent instructions** — default behavior is "present plan, askQuestions for approval, then create on approve".
2. **Ideator agent instructions** — when invoking planner from M6, decide whether to pass the auto-create instruction or let planner ask. Default: let planner ask (user gets a veto checkpoint).
3. **User-facing convention** — document that calling planner directly will get an approval prompt unless `--auto-create` style instruction is given.

## Acceptance Criteria
- planner.agent.md has explicit default-approval-via-askQuestions behavior documented.
- planner.agent.md describes the override mechanism (caller prompt to skip approval).
- ideator.agent.md M6 handoff section documents the choice (default: let planner ask; override available).
- Subagent stateless-ness handled: if planner asks via askQuestions, the answer must reach planner — possibly by having the subagent end with the question and the calling agent (ideator or user) re-invoke planner with the answer. Design needs to address how stateless askQuestions answers reach a stateless subagent.

## Open question for architect
Subagents are stateless — they exit after returning a result. Can a subagent's askQuestions answer be passed to a fresh planner invocation, or does the calling agent need to interpret the answer and proceed differently? This may need a small protocol design.

## Context
Surfaced during ideation session for #973.
[[2026-04-18]]
## Research
- Research doc: .owlbear/research/998-planner-askquestions-approval.md
- Sources: 7 studied, 5 high-relevance
- Recommendation: Explicit mode prefix convention — callers specify "Plan and create: #{id}" for dispatch mode (auto-create) vs "Plan: ..." for user mode (askQuestions approval). Replaces fragile NL-based parent-task-ID detection. (confidence: 0.80)
- Challenge: reconsider (0.45 on original). Revised from NL detection to explicit prefix after challenger identified 4 issues: unreliable parent-ID signal, undiagnosed #973 root cause, fragile override keyword, and missing architect path. All addressed in revision.
- Root cause of #973: ideator M6 dispatch prompt lacked structured task ID — planner couldn't detect dispatch context.
- Follow-up tasks created: #1005, #1006, #1007, #1008 (all at research)
- Decision requests: none — T1 classification (user-directed change, agent instructions only)