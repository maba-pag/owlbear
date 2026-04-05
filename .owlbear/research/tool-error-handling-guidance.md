# Structured Tool-Error Handling Guidance for Agent Instructions

> **Owning task:** #433 — Add structured tool-error handling guidance to agent instructions
> **Date:** 2026-03-30 **Status:** Complete

## 1. Context and Question

OwlBear agents currently have scattered, terminal-focused retry guidance (max 2 retries, re-read skill on failure) but no consolidated section covering structured error capture, alternative approach selection, or tool-type-specific recovery. Task #386's deer-flow analysis identified tool error resilience as a high-priority adoptable pattern (.80 confidence). This research validates the pattern against multiple sources and recommends a concrete section structure for `agent-common.instructions.md`.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| S1 | deer-flow ToolErrorHandlingMiddleware | github.com/bytedance/deer-flow | .90 — converts tool exceptions to structured error ToolMessages; agents receive error context instead of crashing |
| S2 | Anthropic Claude API — Handle Tool Calls | platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls | .85 — `is_error` field in `tool_result` blocks; structured error signaling to model |
| S3 | OpenAI Function Calling — Formatting Results | developers.openai.com/api/docs/guides/function-calling | .80 — return error codes/descriptions as strings; model interprets error context |
| S4 | CrewAI Tools — Error Handling | docs.crewai.com/concepts/tools | .70 — built-in error handling as key tool characteristic; graceful exception management |
| S5 | OwlBear agent-common.instructions.md (current) | instructions/agent-common.instructions.md | .95 — existing scattered guidance: max 2 retries, re-read skill, no brute-force |

## 3. Analysis

### Current state (gaps)

| Existing guidance | Location | Gap |
|-------------------|----------|-----|
| "Max 2 retries" red flag | Red flags section | Only mentions terminal commands; no coverage of built-in tool failures (read_file, search, MCP) |
| "Re-read your skill" | Skill authority section | Good recovery action but only for skill-related commands |
| "No brute-force retries" | Terminal mechanics | Terminal-specific; agents encountering file/search/MCP errors have no guidance |
| (none) | — | No structured error capture pattern (what to record when something fails) |
| (none) | — | No alternative approach selection guidance (what to try instead) |
| (none) | — | No tool-type taxonomy (different tools fail differently) |

### Cross-framework consensus (S1–S4)

All four external frameworks converge on three principles:

| Principle | deer-flow (S1) | Anthropic (S2) | OpenAI (S3) | CrewAI (S4) |
|-----------|----------------|----------------|-------------|-------------|
| **Structured error context** — errors become data, not crashes | ToolMessage with error content | `is_error: true` + content describing what went wrong | Error codes/descriptions as return strings | BaseTool exception handling wraps errors |
| **Error fed back to agent** — agent sees what happened | Error ToolMessage in conversation history | Model receives `tool_result` with `is_error` and adapts | Model interprets error string in next turn | Agent receives error and retries with context |
| **Bounded retries** — prevent infinite loops | LoopDetectionMiddleware (3 warn, 5 stop) | Implicit in agentic loop design | Not specified (application-level) | Configurable retry logic |

### Recommendation (.85 confidence)

Add a consolidated **"Tool failure handling"** section to `agent-common.instructions.md` that covers:

1. **Three-step error protocol:** Capture (read the error), Diagnose (identify root cause), Adapt (choose alternative)
2. **Tool-type recovery table:** Different recovery actions for terminal commands, built-in tools (read/search/edit), and MCP tools
3. **Max retry limits** consolidated from scattered references: 2 attempts per logical operation, then escalate (handoff/block)
4. **Structured error context** in Channel B body when blocking/handing off: what failed, what was tried, what remains

This aligns with KISS (simple 3-step protocol, no middleware framework needed) and fits OwlBear's instruction-based agent model (no code changes required).

## 4. Recommended Section Content

The new section should go after "Skill authority" and before "Self-defense against orchestrator degradation". Suggested structure:

```
## Tool failure handling

Three-step protocol for all tool failures:
1. **Capture** — Read the full error message/output. Note the tool name, inputs, and error.
2. **Diagnose** — Identify the root cause before retrying (wrong path? missing file? bad syntax? permission issue?).
3. **Adapt** — Choose an alternative approach based on tool type (see table below).

### Recovery by tool type

| Tool type | Common failures | Recovery action |
|-----------|----------------|-----------------|
| Terminal (git, pytest, kanban-md) | Bad flags, missing deps, exit code != 0 | Re-read skill for correct syntax; fix input; max 2 retries |
| File ops (read_file, create_file, edit) | File not found, wrong path, match failure | Verify path with file_search/list_dir; check exact string for edits |
| Search (grep, semantic, file_search) | No results, wrong pattern | Broaden query; try alternative search tool; use regex alternation |
| MCP tools (kanban, knowledge) | Connection error, invalid args | Verify tool is loaded (tool_search_tool_regex); check arg format |

### Escalation

After 2 failed attempts at the same logical operation:
- STOP retrying — do not vary flags or arguments hoping to get lucky
- Record what failed and what was tried in the task body (Channel B)
- Hand off or block the task with structured context

### What to record when escalating

- Tool name and inputs that failed
- Error message (abbreviated, not raw dump)
- What alternative approaches were attempted
- What the likely root cause is
```

## 5. Follow-up Tasks

Task #433 already covers the implementation work. No additional tasks needed — the AC is clear and the recommended section content above provides the builder with a concrete template.

The related task #432 (loop detection) is a sibling concern; this research validates that tool error handling and loop detection are complementary but independent. They can proceed in parallel.
