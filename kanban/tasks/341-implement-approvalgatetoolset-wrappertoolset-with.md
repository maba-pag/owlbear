---
id: 341
title: Implement ApprovalGateToolset — WrapperToolset with channel-based approval flow
status: archived
priority: needed
created: 2026-03-01T11:18:51.8730156+01:00
updated: 2026-03-01T17:10:10.5094597+01:00
started: 2026-03-01T11:21:46.0883655+01:00
completed: 2026-03-01T17:10:10.5094597+01:00
tags:
    - phase-12
    - agent
    - safety
depends_on:
    - 340
class: standard
---

## Acceptance Criteria
- [ ] Create ApprovalGateToolset(WrapperToolset) in src/owlbear/core/approval.py
- [ ] Constructor: wrapped toolset, policy (ApprovalPolicy), session (ApprovalSession), channel (ChannelPlugin), hooks (HookRegistry | None)
- [ ] Override call_tool(): check policy -> check pre-grants -> prompt user -> proceed or cancel
- [ ] Prompt format: 'Action requires approval: {tool_name}({args_summary}). Approve? (yes/no/approve all {tool})'
- [ ] On approve: proceed with wrapped.call_tool() and return result
- [ ] On deny: return 'Action {tool_name} denied by user.' (string, not exception)
- [ ] On timeout (asyncio.wait_for on channel.receive): return 'Action {tool_name} timed out — cancelled (safe default).'
- [ ] On 'approve all {tool}': session.grant(tool_name), proceed
- [ ] Log approval events via hooks.emit(POST_TOOL_USE, ...) with event_type='approval_gate'
- [ ] Nests outside HookedToolset in the wrapping chain

See docs/research/approval-gates.md S3.5
