---
id: 340
title: Test ApprovalGateToolset — approve/deny/timeout/pre-grant paths with mock channel
status: archived
priority: needed
created: 2026-03-01T11:18:40.7868378+01:00
updated: 2026-03-01T17:10:09.6680859+01:00
started: 2026-03-01T11:21:45.0933214+01:00
completed: 2026-03-01T17:10:09.6680859+01:00
tags:
    - phase-12
    - agent
    - safety
    - test
depends_on:
    - 339
class: standard
---

## Acceptance Criteria
- [ ] Test call_tool() with tool requiring approval: sends approval prompt via channel.send()
- [ ] Test approve path: channel.receive() returns 'yes' -> tool call proceeds, returns normal result
- [ ] Test deny path: channel.receive() returns 'no' -> tool call skipped, returns 'Action denied by user'
- [ ] Test timeout path: channel.receive() returns None after timeout -> tool call skipped, returns cancellation message
- [ ] Test pre-grant path: ApprovalSession.is_pre_granted() True -> no prompt, tool call proceeds
- [ ] Test 'approve all {tool}' response: adds to pre-grants, proceeds with tool call
- [ ] Test tool NOT in policy: call_tool proceeds without prompting
- [ ] Test observability: approval events logged via hooks (PRE_TOOL_USE data extended)
- [ ] Mock channel (send queue + receive queue) and inner toolset

See docs/research/approval-gates.md S3.5, S3.6
