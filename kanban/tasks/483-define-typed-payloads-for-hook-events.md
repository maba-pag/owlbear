---
id: 483
title: Define typed payloads for hook events
status: backlog
priority: important
created: 2026-03-04T07:38:00.5039018+01:00
updated: 2026-03-09T00:05:55.4045347+01:00
started: 2026-03-06T23:05:05.2610742+01:00
tags:
    - audit
    - refactor
    - hooks
class: standard
---

ARC-08/F-18/INT-05: Handler=Callable[[object],object] provides no type safety. Different events expect different shapes. POST_TOOL_USE shape differs between HookedToolset and ApprovalGateToolset. Define TypedDict per event (ToolUsePayload, ErrorPayload, etc). AC: typed payloads, Handler type narrowed. See docs/architecture-audit.md, docs/code-quality-audit.md, docs/integration-audit.md.

[[2026-03-09]] Mon 00:05
## Research
Recommendation (.90): TypedDict per event - zero runtime cost, backward-compatible, KISS-aligned.

Key findings:
- 10 events cataloged, 10 consumer hooks use defensive isinstance guards (eliminable)
- POST_TOOL_USE has 2 incompatible shapes (INT-05) - resolved via NotRequired fields
- Handler type fix: Callable[[object], object] to Callable[[dict[str, Any]], None] (F-18)
- Internal precedent: TestResult(TypedDict) in test_hook.py; external: pluggy HookspecOpts

Follow-up tasks: see docs/typed-hook-payloads-research.md section 6
Doc: docs/typed-hook-payloads-research.md | Sources: docs/sources.md updated
