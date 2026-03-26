---
id: 288
title: Analyze and enforce reviewer/writer agent dispatch in orchestrator
status: archived
priority: critical
created: 2026-03-01T01:15:27.8941661+01:00
updated: 2026-03-01T17:08:09.3141524+01:00
started: 2026-03-01T01:19:05.0663361+01:00
completed: 2026-03-01T17:08:09.3141524+01:00
tags:
    - process
    - docs
    - agent
    - orchestrator
class: standard
---

## Problem
The orchestrator consistently skips dispatching reviewer and writer agents during the review -> docs -> done pipeline. Across 13 tasks in the latest orchestration run, ZERO reviewer or writer agents were dispatched. The orchestrator ran pytest + ruff itself and rubber-stamped the moves.

## Impact
- No real documentation review has happened for any recent feature
- copilot-instructions.md, README.md, architecture.md are likely stale
- New public APIs have no docs coverage beyond docstrings
- The reviewer agent's AC compliance check was never performed
- The writer agent's docs-gate checklist was reduced to a superficial mental note

## Root Cause Analysis
Five gaps in orchestrator.agent.md enable this failure:
1. Step 7 'Advance (three-step)' conflates orchestrator verification with the reviewer/writer role — the orchestrator does Stage 1 + Stage 2 itself, then moves review -> docs -> done in a single pass
2. Boundaries section says 'Always verify subagent work' but never mandates dispatching reviewer or writer subagents
3. Self-critique checklist has no 'I dispatched a reviewer/writer agent' items
4. The dispatch routing table (Step 6, points 4-5) mentions reviewer/writer dispatch parenthetically, not as mandatory sub-steps
5. orchestrate.prompt.md says 'deliverables are working code and passing tests, not documents' — actively discourages docs attention

## Acceptance Criteria (changes to .github/agents/orchestrator.agent.md)

### Step 7 rewrite
- [ ] Rewrite 'Advance (three-step)' to enforce mandatory subagent dispatch:
      After builder completes + orchestrator Stage 1+2 pass -> move to 'review' -> dispatch 'reviewer' subagent -> wait for PASS verdict -> move to 'docs' -> dispatch 'writer' subagent -> wait for PASS verdict -> move to 'done'
- [ ] Remove the docs-gate checklist duplication from Step 7 (it belongs in the writer agent, not the orchestrator)

### Boundary rules
- [ ] Add boundary: 'NEVER move a task from review -> docs without dispatching a reviewer subagent and receiving a PASS verdict'
- [ ] Add boundary: 'NEVER move a task from docs -> done without dispatching a writer subagent and receiving a PASS verdict'
- [ ] Add these two scenarios to the 'Red flags' list
- [ ] Add entries to 'Common failure rationalizations' table for rubber-stamping reviewer/writer roles

### Self-critique additions
- [ ] Add after-wave item: 'I dispatched a reviewer subagent for every task moving review -> docs'
- [ ] Add after-wave item: 'I dispatched a writer subagent for every task moving docs -> done'
- [ ] Add after-wave item: 'I did not perform the docs-gate checklist myself — the writer subagent handled it'

### Bad example
- [ ] Add bad_example showing orchestrator running pytest+ruff itself and moving review -> docs -> done without dispatching reviewer or writer subagents

### Prompt file fix
- [ ] In .github/prompts/orchestrate.prompt.md: amend 'deliverables are working code and passing tests, not documents' to include 'dispatch reviewer and writer agents for the review -> docs -> done pipeline'

## Design Note
Structural enforcement (preventing kanban-md move calls without subagent dispatch proof) is out of scope — that would require runtime tooling changes. The fix here is prompt-level: make the rules unambiguous, add failure examples, and add self-critique checkpoints. If prompt-level enforcement proves insufficient, a follow-up task can explore runtime constraints.

## Files
- .github/agents/orchestrator.agent.md (primary edit target)
- .github/prompts/orchestrate.prompt.md (minor edit)
- .github/agents/reviewer.agent.md (read-only reference)
- .github/agents/writer.agent.md (read-only reference)
