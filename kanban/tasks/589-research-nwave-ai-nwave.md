---
id: 589
title: 'Research: nWave-ai/nWave'
status: archived
priority: important
created: 2026-03-05T23:50:59.1498927+01:00
updated: 2026-03-07T18:08:11.0254887+01:00
started: 2026-03-06T21:26:12.8014455+01:00
completed: 2026-03-07T18:08:11.0254887+01:00
tags:
    - research
    - phase-research
    - scope:agent
parent: 580
class: standard
---

**Source:** https://github.com/nWave-ai/nWave (MIT)
Analyzed for multi-agent delegation, orchestration patterns, and task execution logic.

**Findings:** See docs/research/nwave.md

**Key patterns identified:**
- P1: Rigor Profile System (.85) - configurable quality-vs-speed profiles per task
- P2: Structured Reviewer Pairing (.80) - specialist + cheaper-model reviewer agents
- P3: Blocking Pre-Tool Hooks (.75) - validate delegation prompts before execution
- P4: Stale Execution Detection (.70) - detect tasks stuck in IN_PROGRESS
- P5: Turn Limits Per Task Type (.70) - budget turns by complexity

**Research checklist:**
1. Theoretical validity: Sound wave-based pipeline with enforcement hooks (2 sources)
2. Prior art: nWave + CrewAI (hierarchical process, reviewer patterns)
3. Technical feasibility: All patterns portable to PydanticAI (config + hooks + delegation)
4. Architecture fit: Rigor profiles map to OwlBear config; stale detection fits daemon loop; reviewer pairing extends existing reviewer agent
5. Implementation approach: Config-driven profiles (owlbear.toml), periodic stale scan, per-specialist reviewer registration
