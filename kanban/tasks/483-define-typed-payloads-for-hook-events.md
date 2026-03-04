---
id: 483
title: Define typed payloads for hook events
status: ideation
priority: important
created: 2026-03-04T07:38:00.5039018+01:00
updated: 2026-03-04T07:38:00.5039018+01:00
tags:
    - audit
    - refactor
    - hooks
class: standard
---

ARC-08/F-18/INT-05: Handler=Callable[[object],object] provides no type safety. Different events expect different shapes. POST_TOOL_USE shape differs between HookedToolset and ApprovalGateToolset. Define TypedDict per event (ToolUsePayload, ErrorPayload, etc). AC: typed payloads, Handler type narrowed. See docs/architecture-audit.md, docs/code-quality-audit.md, docs/integration-audit.md.
