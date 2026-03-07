---
id: 538
title: Evaluate declarative tool registration for toolsets
status: backlog
priority: nice-to-have
created: 2026-03-04T07:38:43.2377201+01:00
updated: 2026-03-07T00:42:29.1013988+01:00
started: 2026-03-07T00:36:38.943944+01:00
tags:
    - audit
    - yagni
    - tools
class: standard
---

YAGNI-01 evaluation complete. Decision: DEFER. The _register_tools ceremony is harmless -- no bugs, consistent pattern, PydanticAI native API. Building a custom declarative layer (decorator or ClassVar) would add 30-80 LOC of framework code to save ~3 LOC per toolset, violating KISS/YAGNI. If PydanticAI adds class-level declarative registration, adopt it then. See docs/declarative-tool-registration-research.md.
