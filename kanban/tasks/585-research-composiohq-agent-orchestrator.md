---
id: 585
title: 'Research: ComposioHQ/agent-orchestrator'
status: archived
priority: important
created: 2026-03-05T23:50:34.946634+01:00
updated: 2026-03-07T18:08:08.933592+01:00
started: 2026-03-06T21:12:52.6217146+01:00
completed: 2026-03-07T18:08:08.933592+01:00
tags:
    - research
    - phase-research
    - scope:agent
parent: 580
class: standard
---

**Source:** https://github.com/ComposioHQ/agent-orchestrator
**License:** MIT
**Findings:** See docs/agent-orchestrator-research.md

**Research checklist:**
1. Theoretical validity -- Sound concept: parallel AI agent orchestration with plugin architecture. Different paradigm than OwlBear (process mgmt vs in-process agents).
2. Prior art -- AutoGen SelectorGroupChat, PydanticAI multi-agent, OpenClaw (prior research #22).
3. Technical feasibility -- Patterns transferable (reaction engine, notification routing, prompt layering). Core process-management architecture not applicable to Python/PydanticAI stack.
4. Architecture fit -- Three adoptable patterns extend existing hooks, Slack channel, and agent prompts. No architectural changes needed.
5. Implementation approach -- Each pattern is ~50-100 LOC, extending existing subsystems.

**Adoptable patterns (.75 confidence):**
- A. Reaction engine: config-driven event->action routing with retry/escalation (extends hooks)
- B. Priority-routed notifications (extends Slack channel)
- C. Runtime context injection in agent prompts (extends agent dispatch)

**Not applicable:** git worktree isolation, tmux/Docker runtimes, external agent adapters, session metadata files, web dashboard, PR auto-merge.
