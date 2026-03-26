---
id: 5
title: Copilot Memory boundary testing
status: ideation
priority: important
created: 2026-03-26T17:18:48.5935306+01:00
updated: 2026-03-26T17:18:48.5935306+01:00
tags:
    - research
    - phase-1
    - scope:knowledge
class: standard
---

## Objective
Research Copilot Memory behavior and test boundary instructions to control what gets memorized.

## Acceptance Criteria
- [ ] Document how Copilot Memory works (storage, retrieval, scope)
- [ ] Test what Copilot memorizes by default during a coding session
- [ ] Write boundary instruction: 'Only memorize tool usage patterns, CLI flags, agent behavior. Do NOT memorize architecture decisions, research findings, or project-specific patterns.'
- [ ] Test boundary instruction effectiveness - verify it constrains memorization
- [ ] Document memory persistence across sessions and workspaces
- [ ] Document memory management commands (view, delete, export)
- [ ] Write findings to docs/research/copilot-memory.md
- [ ] Create follow-up tasks for any gaps discovered

## Context
Copilot Memory is the top layer of our three-layer knowledge architecture. It handles agent-centric learning (tool patterns, CLI flags, what worked/failed). We need boundary instructions to prevent it from duplicating what belongs in the general or project KB layers.
