---
id: 611
title: Bootstrap should gracefully handle missing optional tools
status: archived
priority: critical
created: 2026-03-07T03:09:06.1128725+01:00
updated: 2026-03-07T18:08:19.8759984+01:00
started: 2026-03-07T04:10:13.0832651+01:00
completed: 2026-03-07T18:08:19.8759984+01:00
tags:
    - bugfix
    - config
    - phase-9
class: standard
---

## Problem
3 pipeline_e2e[researcher] tests fail because the researcher agent definition lists knowledge as a required tool. When qdrant-client isn't installed, bootstrap raises KeyError instead of degrading gracefully.

## Root Cause
The _resolve closure in build_agent_registry() raises KeyError for unknown tools. AgentRegistry._build_agent() uses a list comprehension that propagates this. The knowledge toolset is conditionally created in build_toolsets() (returns None when qdrant-client missing), but the agent definition still references it.

## Research Findings
See docs/research/optional-tool-graceful-degradation.md

**Approved approach (.90 confidence):** Catch-and-skip in _build_agent -- change the list comprehension to a loop with try/except KeyError, log WARNING per skipped tool. Consistent with 8 existing catch-and-skip patterns in bootstrap.py.

## Architectural Decision
- Fix location: AgentRegistry._build_agent() in src/owlbear/core/agent_registry.py lines 172-174
- Pattern: Replace list comprehension with loop + try/except KeyError
- Log: logger.warning('Agent %r: skipping unavailable tool %r', defn.name, tool_name)
- Scope: Catches both standard tool KeyError and mcp: tool KeyError
- No changes to _resolve_tool, _resolve closure, or build_toolsets
- No changes to agent definition files
- No new abstractions (no optional_tools field, no resolver contract change)

## Split into child tasks (TDD order)
- Test task first (TDD red phase)
- Impl task second (TDD green phase)

## AC (parent -- verified via children)
- [ ] _build_agent catches KeyError per tool and continues with remaining tools
- [ ] WARNING logged with agent name + tool name for each skipped tool
- [ ] Agent instantiated with reduced toolset (remaining tools only)
- [ ] No behavior change when all tools are present (existing tests still pass)
- [ ] pipeline_e2e[researcher] passes without qdrant-client installed
