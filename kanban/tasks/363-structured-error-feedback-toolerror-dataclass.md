---
id: 363
title: Structured error feedback — ToolError dataclass replacing bare strings
status: archived
priority: needed
created: 2026-03-01T20:12:09.9987183+01:00
updated: 2026-03-02T09:14:37.3920988+01:00
started: 2026-03-01T20:22:26.2699619+01:00
completed: 2026-03-02T09:14:37.3920988+01:00
tags:
    - phase-13
    - agent
    - reliability
depends_on:
    - 357
class: standard
---

## Structured Error Feedback — ToolError

Define ToolError dataclass in src/owlbear/core/errors.py (co-located with ErrorCategory).

### ToolError (frozen dataclass, slots)

Minimal v1 with 4 fields:
- status: Literal['error'] — always 'error'
- error_type: ErrorCategory — from #357
- tool_name: str — which tool/agent failed
- message: str — human-readable error description

to_dict() -> dict — returns JSON-serializable dict for LLM consumption.

### Scope (THIS TASK)

Replace bare error strings in src/owlbear/core/delegation.py ONLY:
- 'Error: agent_registry not configured' -> ToolError(PERMANENT, 'delegate_to_agent', ...)
- 'Error: max delegation depth exceeded' -> ToolError(PERMANENT, 'delegate_to_agent', ...)
- 'Error: agent not found' -> ToolError(TOOL_SEMANTIC, 'delegate_to_agent', ...)
- 'Error: delegation failed' -> ToolError(classify_error(exc), 'delegate_to_agent', ...)

Return json.dumps(error.to_dict()) so LLM receives structured JSON string.

### Out of Scope (follow-up)

- Replacing f'error: {stderr}' in kanban.py, git_local.py, github_api.py
- Adding retry/suggestion/escalation fields (YAGNI until escalation wiring)

### Acceptance Criteria

- [ ] ToolError is a frozen dataclass with 4 fields: status, error_type, tool_name, message
- [ ] ToolError.to_dict() returns {'status': 'error', 'error_type': '...', 'tool_name': '...', 'message': '...'}
- [ ] delegation.py returns json.dumps(ToolError.to_dict()) instead of bare f'Error: ...'
- [ ] Returned JSON is parseable: json.loads(result)['error_type'] works
- [ ] All existing delegation tests still pass (return type is still str)
- [ ] Tests in tests/test_error_classification.py (extend, TDD)
- [ ] Ruff clean

### Architecture Notes

- Depends on #357 for ErrorCategory
- Co-located in core/errors.py with ErrorCategory and classify_error
- v1: 4 fields. Retry/suggestion/escalation fields added when #361/#362 built
- See docs/error-recovery-research.md section 3.5
