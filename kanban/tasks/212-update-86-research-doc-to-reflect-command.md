---
id: 212
title: 'Update #86 research doc to reflect command-execution hook model'
status: todo
priority: nice-to-have
created: 2026-03-30T08:58:34.3969542+02:00
updated: 2026-03-30T09:46:31.5920961+02:00
tags:
    - docs
    - hooks
    - scope:agents
class: standard
---

## Context

The VS Code hooks API (updated 3/25/2026) uses a command-execution model, not prompt-injection. docs/research/agent-scoped-hooks-pipeline-enforcement.md sections 3.2 and 4 contain incorrect YAML examples using `prompt:` and `when:` keys that no longer match the API.

See docs/research/stop-commit-guard-hooks-phase1.md for full analysis.

## Acceptance Criteria

- [ ] Update YAML examples in sections 3.2 and 4 to use `type: command` format
- [ ] Update section 3.3 constraint table: hooks now support blocking via exit code 2
- [ ] Note PascalCase event names (Stop, PreToolUse, PostToolUse)
- [ ] Keep the recommendation matrix conclusions unchanged (just fix format)

[[2026-03-30]] Mon 09:33
## Research
Updated docs/research/agent-scoped-hooks-pipeline-enforcement.md per AC:
- Sections 3.2 and 4: all YAML examples now use type: command format with PascalCase event names
- Section 3.3: constraint table revised (exit code 2 blocking, permissionDecision deny, command execution)
- Section 3.1: expanded from 3 to 8 hook types per current API
- Section 1: context table updated for command-execution mechanism
- Recommendation matrix conclusions unchanged
- Sources: VS Code Hooks docs (3/25/2026) confirmed via live fetch
No new follow-up tasks needed (existing #209, #210, #211 cover the implementation phases).

[[2026-03-30]] Mon 09:46
## Architecture Review
**Verdict:** Approve

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Update YAML examples in 3.2 and 4 to type: command format | Verified: all YAML blocks use type: command with PascalCase events | None |
| Update 3.3 constraint table: exit code 2 blocking | Verified: table includes exit code 2, permissionDecision deny, Stop decision block | None |
| Note PascalCase event names | Verified: 3.1 table and all YAML examples use PascalCase | None |
| Keep recommendation matrix conclusions unchanged | Verified: Phase 1/2 plan and skip list unchanged | None |

### Architecture Notes
Docs-only task: no code, no TDD requirement. Researcher already applied all four AC changes to docs/research/agent-scoped-hooks-pipeline-enforcement.md (confirmed by reading the file). Task is atomic (single doc update) and correctly scoped. Builder can verify in-place and advance.

### Changes Made
- Approved to todo

### Dependencies
- Verified: no code dependencies (docs-only)
- Downstream: #209, #210, #211 reference this doc but do not depend on this task
