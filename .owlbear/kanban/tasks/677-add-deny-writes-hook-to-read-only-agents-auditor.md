---
id: 677
title: Add deny-writes hook to read-only agents (auditor, code-reader, challenger)
status: backlog
priority: nice-to-have
created: 2026-04-08T18:30:31.9568749+02:00
updated: 2026-04-08T18:30:31.9568749+02:00
tags:
    - scope:agents
    - ' type:safety'
    - ' source:analysis'
class: standard
---

## Context

Analysis synthesis identified that 18 of 23 agents have no hooks. Among these, several are designed to be read-only by convention (prompt instructions) but have no enforcement via PreToolUse hooks.

The existing `deny-writes.ps1` hook (used by reviewer) blocks all write tools. This same hook can be referenced by other read-only agents.

## Agents to add deny-writes hook

| Agent | Current hooks | Rationale |
|-------|--------------|-----------|
| auditor | none | Designed as read-only verifier; should not write code |
| code-reader | none | "Strictly read-only" per agent definition |
| challenger | none | "Strictly read-only; no state mutations" per agent definition |
| quality-runner | none | "Read-only except .owlbear/scratch/ cleanup" — needs investigation |

**Note:** quality-runner has an exception for `.owlbear/scratch/` cleanup. It may need a dedicated hook (allow `.owlbear/scratch/` writes only) rather than full deny-writes.

## Acceptance Criteria

- [ ] AC1: `auditor.agent.md` references `deny-writes.ps1` as PreToolUse hook
- [ ] AC2: `code-reader.agent.md` references `deny-writes.ps1` as PreToolUse hook
- [ ] AC3: `challenger.agent.md` references `deny-writes.ps1` as PreToolUse hook
- [ ] AC4: Decide on quality-runner: full deny-writes or scratch-only-allow hook
- [ ] AC5: Existing tests for deny-writes.ps1 still pass
- [ ] AC6: Verify the 3 agents (auditor, code-reader, challenger) can still perform their read-only workflows
