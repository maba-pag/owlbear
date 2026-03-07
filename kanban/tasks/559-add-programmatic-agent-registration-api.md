---
id: 559
title: Add programmatic agent registration API
status: backlog
priority: someday
created: 2026-03-04T07:39:02.2025079+01:00
updated: 2026-03-07T02:27:30.0227369+01:00
started: 2026-03-07T02:20:42.0718486+01:00
tags:
    - audit
    - refactor
    - scope:core
class: standard
---

ARC-16: AgentRegistry.scan() only supports file-based agent definitions (globs .md files). No register(defn) method for dynamic agents. Add register() alongside scan(). AC: both file and programmatic registration supported. See docs/architecture-audit.md.

Research complete (2026-03-07). See docs/programmatic-agent-registration-research.md.

Findings: AgentDefinition is already decoupled from filesystem. Adding register(defn) is ~8 LOC. scan() clears all (including programmatic) which is acceptable per KISS. Prior art (PydanticAI, CrewAI) confirms programmatic registration as first-class pattern.

AC refined:
1. register(defn) adds definition to _definitions dict
2. get() returns agent built from registered definition
3. Re-register evicts stale cache entry
4. scan() still clears all including programmatic registrations
5. list_agents() and definitions include programmatic entries
6. Pydantic validation at AgentDefinition construction time (no extra validation needed)
