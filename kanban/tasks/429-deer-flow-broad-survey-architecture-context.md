---
id: 429
title: 'deer-flow broad survey: architecture, context engineering, guardrails, tooling patterns'
status: ideation
priority: nice-to-have
created: 2026-03-30T21:18:12.0439613+02:00
updated: 2026-03-30T21:18:12.0439613+02:00
tags:
    - research
    - ' scope:agents'
    - ' phase-2'
depends_on:
    - 386
class: standard
---

## Context

Broad survey of deer-flow's architecture and patterns EXCLUDING the memory system and subagent delegation (covered in #428). This task is open-ended by design — the researcher should discover areas of interest beyond what's listed below.

The deer-flow repo should already be cloned at `docs/scratch/research/deer-flow/` (parent task #386 handles cloning).

## Known Areas of Interest (non-exhaustive)

### Architecture
- **Harness/App split** — `packages/harness/deerflow/` (publishable framework) vs `app/` (application code). Strict one-way dependency enforced by CI test. Is this pattern useful for OwlBear's `packages/` structure?
- **Middleware chain** — 12 middlewares in strict order for agent lifecycle (thread data, uploads, sandbox, dangling tool calls, guardrails, summarization, todo list, title, memory, view image, subagent limit, clarification). Is ordered middleware applicable to OwlBear?

### Context Engineering
- **SummarizationMiddleware** — automatic context reduction approaching token limits. Configurable triggers (tokens, messages, fraction). Keep-recent policy with summarized older messages.
- **Isolated sub-agent context** — each subagent gets clean context, results offloaded to filesystem
- Comparison to OwlBear's subagent nesting context management (#228)

### Guardrails
- **GuardrailProvider protocol** — pre-tool-call authorization. AllowlistProvider (zero deps) or pluggable policy providers. Evaluates each tool call, returns error ToolMessage on deny.
- Could this replace or complement OwlBear's hook-based approach?

### Skills & Tools
- **Progressive skill loading** — only when task needs them, not all at once
- **MCP tool caching** with mtime invalidation
- **ACP agent integration** — external agent delegation via protocol
- **.skill archive installation** via Gateway API

### Other
- **Embedded Python client** (DeerFlowClient) — in-process, no HTTP needed. Gateway conformance tests.
- **Config auto-reload** on mtime change
- **IM channel integration** (Telegram, Slack, Feishu)
- **Virtual path system** for sandbox isolation

### Researcher: discover more
The above is a starting point. Read CLAUDE.md, the README, and explore the codebase. If you find patterns not listed here that would benefit OwlBear, include them in the analysis.

## Acceptance Criteria

- [ ] Survey at LEAST the areas listed above, but discover and analyze additional patterns
- [ ] For each area: document what deer-flow does, how it differs from OwlBear, and whether adoption is recommended (with confidence score)
- [ ] Focus analysis time proportional to relevance — don't spend equal time on everything; deep-dive where it matters, skim where it doesn't
- [ ] Create a decision request with top 3-5 most valuable patterns to adopt (from this non-memory/non-subagent scope), with trade-offs
- [ ] Create follow-up tasks at ideation for approved patterns
