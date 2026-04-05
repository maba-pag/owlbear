# Ruflo Enterprise AI Orchestration Platform - Research Analysis

> **Owning task:** #947 - Research ruflo Enterprise AI Orchestration Platform
> **Date:** 2026-03-23 **Status:** Complete

## 1. Context and Question

Ruflo is a Node/TypeScript orchestration platform that exposes a CLI, MCP server,
markdown or TOML agent surfaces, and a large catalog of swarm, hook, memory, and
plugin capabilities. OwlBear already has an always-on Python daemon, markdown agent
definitions, kanban pipeline agents, and its own hook and knowledge systems. The
decision is therefore three-way: direct dependency, selective adaptation, or
inspiration-only reference. [S1, S2, S6, S7]

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | ruvnet/ruflo README (`README.md`, raw + repo page) | .95 | Product surface, 60+ agents, hooks, workers, MCP tools, swarms, and programmatic SDK |
| S2 | ruvnet/ruflo `package.json` | .95 | Published package shape, Node 20 requirement, CLI bin, optional packages, and runtime surface |
| S3 | ruvnet/ruflo `AGENTS.md` | .90 | Codex/Claude execution model, core agent taxonomy, coordination rules, and prompt surfaces |
| S4 | ruvnet/ruflo `agents/*.yaml`, `.agents/README.md`, and agent directory pages | .90 | Agent definition format and compatibility with OwlBear agent files |
| S5 | ruvnet/ruflo `v3/` README and directory page | .85 | Modular package layout, MCP-first and plugin or microkernel claims |
| S6 | OwlBear `.github/agents/*.agent.md` | 1.0 | Current agent inventory, markdown prompt structure, and pipeline roles |
| S7 | OwlBear `.github/copilot-instructions.md` and `docs/research/agent-orchestrator.md` | 1.0 | Python daemon constraints, existing hook or toolset architecture, and prior external-orchestrator fit analysis |
| S8 | ruvnet/ruflo `LICENSE` | .95 | MIT reuse terms for copied or adapted code and configuration |

## 3. Analysis

### 3.1 Architecture Fit

| Criterion | Ruflo | OwlBear | Verdict |
|-----------|-------|---------|---------|
| Runtime | Node 20+, TypeScript packages, CLI and MCP-first surface [S1, S2, S5] | Python 3.12, PydanticAI, always-on daemon, VS Code agent files [S6, S7] | Direct code import: reject |
| Agent definitions | Terse YAML capability files plus `.agents` or `AGENTS.md` coordination docs [S3, S4] | Rich markdown agent files with persona, rules, workflow, and output contracts [S6] | Adapt ideas, not files |
| Execution model | Swarms, queens, background workers, and external executors such as Claude Code or Codex [S1, S3] | In-process kanban pipeline with orchestrator, planner, researcher, builder, reviewer, writer, auditor [S6, S7] | Swarm model is inspiration-only |
| Packaging | Published JS packages and CLI bin; optional ecosystem packages for memory, guidance, plugins, and codex [S2, S5] | No Node runtime in the core product path; Python modules are the source of truth [S7] | Sidecar possible, but low-value |
| Licensing | MIT permits copy, modify, and redistribution with preserved notice [S8] | OwlBear can legally adapt small portions with attribution, but should not verbatim-clone large prompt packs unnecessarily [S6, S7] | Legally compatible, operationally unattractive |

### 3.2 Agent Overlap Map

| Ruflo role | Ruflo evidence | Closest OwlBear analog | Reuse verdict |
|------------|----------------|------------------------|---------------|
| coordinator or queen | swarm and hive-mind coordinator roles [S1, S3] | orchestrator plus planner plus kanban-planner [S6] | Adapt taxonomy only |
| coder | `coder.yaml`, README core development agents [S1, S4] | builder [S6] | Inspiration only |
| tester | `tester.yaml`, worker taxonomy [S1, S4] | test-writer plus reviewer evidence gate [S6] | Adapt responsibility split, not prompt text |
| reviewer | `reviewer.yaml`, README core roles [S1, S4] | reviewer [S6] | Adapt capability framing only |
| architect | `architect.yaml`, README core roles [S1, S4] | architect [S6] | Adapt capability framing only |
| researcher | worker taxonomy and AGENTS guide [S1, S3] | researcher [S6] | Adapt workflow ideas only |
| documenter | worker taxonomy [S1] | writer [S6] | Adapt concept only |
| security-architect or performance-engineer | specialized roles in README and AGENTS guide [S1, S3, S4] | no dedicated OwlBear agent today [S6] | Potential future specialization, not immediate |

### 3.3 Adoption Modes

| Option | Benefits | Costs | Verdict |
|--------|----------|-------|---------|
| Direct adoption: import `claude-flow` or `@claude-flow/*` packages | Immediate access to swarms, hooks, workers, MCP tools, and plugin ecosystem [S1, S2, S5] | Requires a Node sidecar, duplicates OwlBear orchestration, and does not map to OwlBear markdown agent schema or Python toolsets [S2, S4, S6, S7] | Reject |
| Direct adoption: copy ruflo agent files or AGENTS docs | MIT allows copying with notice [S3, S4, S8] | The files are too shallow for OwlBear's agent contract and would still need Python-specific rewrite [S4, S6, S7] | Reject |
| Adapt selected patterns into OwlBear subsystems | Low implementation cost because hooks, daemon, notifications, and prompt assembly already exist [S1, S3, S6, S7] | Requires disciplined scoping to avoid importing swarm complexity or Node-specific assumptions [S1, S5, S7] | Recommend |
| Inspiration-only reference | Lowest risk; keeps OwlBear's single-source-of-truth intact [S1, S3, S7] | No direct implementation leverage [S1, S5] | Use for swarm or hive-mind only |

### 3.4 Highest-Value Patterns To Adopt First

| Pattern | Ruflo evidence | OwlBear fit | Follow-up |
|---------|----------------|-------------|-----------|
| Hook-triggered background workers for `audit`, `map`, `testgaps`, `document` | README workers and daemon sections, AGENTS guide hooks or worker commands [S1, S3] | Strong: OwlBear is already an always-on daemon with hook events and long-running context [S7] | #949 |
| Config-driven event-to-action reaction routing | README hook and routing sections; prior orchestration research reached the same conclusion [S1, S7] | Strong: extends the existing hook system instead of replacing it [S6, S7] | #950 |
| Runtime task or workspace or channel prompt assembly | AGENTS guide layered coordination context and runtime instruction surfaces [S3, S4] | Strong: OwlBear agents already use markdown prompts, but static files currently carry most context [S6, S7] | #951 |
| Priority-routed notifications | README operational routing concepts; prior research already identified the same seam [S1, S7] | Medium: useful once workers and reactions produce more events [S6, S7] | #952 |

### 3.5 Patterns To Leave Alone

- Do not import Ruflo's 60-agent catalog, hive-mind topologies, or 259-tool MCP surface into OwlBear's core product. Those features assume a Claude or Codex-centered external-executor model and a much larger operational footprint than OwlBear's kanban pipeline needs today. [S1, S3, S5, S7]
- Do not adopt the JS package stack as a hidden sidecar dependency just to reuse a few patterns. The packaging and runtime mismatch means OwlBear would still re-implement the integration layer in Python. [S2, S5, S7]
- Do not copy prompt or skill text wholesale. MIT permits it, but OwlBear's richer agent contracts and different tool names make verbatim reuse a maintenance trap. [S4, S6, S8]

## 4. Recommendation (.84 confidence)

Use an adaptation-only strategy.

1. Treat Ruflo as a high-value pattern library for daemon workers, reaction routing, runtime prompt assembly, and notification prioritization. [S1, S3, S6, S7]
2. Do not import Ruflo packages or copy its agent files directly. The runtime, config, and execution-model mismatch would erase most of the time saved. [S2, S4, S6, S7]
3. Keep swarm and hive-mind concepts as inspiration only until OwlBear has proven need for parallel multi-role execution beyond the current kanban pipeline. [S1, S3, S5, S7]
4. If future work explores a Node sidecar or external MCP bridge, spin that into a separate research track rather than coupling it to these follow-ups. [S2, S5, S7]

## 5. Follow-up Tasks

1. #949 - Design hook-triggered background worker pilot for audit map testgaps and document flows.
   Priority rationale: highest leverage pattern for an always-on daemon.
   Dependencies: none.
   One-line AC: define one safe worker pilot and trigger model using existing daemon and hook boundaries without bypassing kanban approvals.
   Created: `kanban\kanban-md.exe create "Design hook-triggered background worker pilot for audit map testgaps and document flows" ...`

2. #950 - Implement config-driven HookEvent reaction routing with retry and escalation.
   Priority rationale: turns hook events into reusable control flow instead of one-off logic.
   Dependencies: none.
   One-line AC: map HookEvent categories to notify, retry, or escalate actions with bounded retry counts and clear failure routing.
   Created: `kanban\kanban-md.exe create "Implement config-driven HookEvent reaction routing with retry and escalation" ...`

3. #951 - Inject runtime task and workspace context into dispatched agent prompts.
   Priority rationale: best low-diff way to capture Ruflo's layered prompt and context pattern.
   Dependencies: none.
   One-line AC: dispatched agents receive current task, workspace, and channel context through a runtime prompt-assembly layer without duplicating static prompt text.
   Created: `kanban\kanban-md.exe create "Inject runtime task and workspace context into dispatched agent prompts" ...`

4. #952 - Add priority-routed notifications for daemon and pipeline events.
   Priority rationale: useful once workers and reaction routing increase event volume.
   Dependencies: none.
   One-line AC: classify notifications by priority and route urgent events differently from informational events across CLI and Slack.
   Created: `kanban\kanban-md.exe create "Add priority-routed notifications for daemon and pipeline events" ...`
