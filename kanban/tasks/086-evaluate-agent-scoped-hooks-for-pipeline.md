---
id: 86
title: Evaluate agent-scoped hooks for pipeline enforcement (scoped AC)
status: in-progress
priority: nice-to-have
created: 2026-03-27T13:36:44.4394535+01:00
updated: 2026-03-27T22:29:07.1011738+01:00
tags:
    - research
    - phase-1
    - scope:agents
    - hooks
class: standard
---

## Context

- See docs/research/agent-md-format.md section 7 and section 9.
- This task supersedes placeholder task #37, which was blocked due to empty body and missing acceptance criteria.
- Goal: determine whether agent-scoped hooks should be enabled for the OwlBear pipeline and define safe rollout guardrails.

## Acceptance Criteria

- [ ] Review VS Code hook capabilities relevant to agents used in OwlBear (`preToolUse`, `postToolUse`, `stop`) and summarize constraints/limits.
- [ ] Evaluate at least three concrete pipeline enforcement candidates (for example: claim enforcement, post-edit lint checks, pre-exit commit guard), including trade-offs and failure modes.
- [ ] Produce a recommendation matrix with options, confidence scores, and a clear recommended path.
- [ ] Document findings in `docs/research/agent-scoped-hooks-pipeline-enforcement.md`.
- [ ] Include explicit rollout guidance: prerequisites, required settings, phased adoption plan, and when not to use hooks.

[[2026-03-27]] Fri 14:30
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Review VS Code hook capabilities (preToolUse, postToolUse, stop) | Clear: specific hook types named, deliverable is constraints summary | None |
| Evaluate at least three pipeline enforcement candidates | Clear: minimum count specified, trade-offs and failure modes required | None |
| Produce recommendation matrix with confidence scores | Clear: specific deliverable format | None |
| Document findings in docs/research/agent-scoped-hooks-pipeline-enforcement.md | Clear: exact file path | None |
| Include rollout guidance with 4 specific components | Clear: prerequisites, settings, phased plan, anti-patterns all enumerable | None |

### Architecture Notes
Well-scoped research task with verifiable AC. Each line is pass/fail checkable.

**Important distinction for researcher:** OwlBear has TWO hook layers. (1) Internal `HookRegistry` in `core/hooks.py` which is explicitly observational and non-blocking per architecture-standards. (2) VS Code agent-scoped hooks (`preToolUse`, `postToolUse`, `stop`) in `.agent.md` frontmatter, which are the subject of this research. These are different mechanisms. The research should clearly separate them and note that any enforcement behavior from VS Code hooks must not conflict with the internal hook contract.

No existing VS Code hook usage in current `.agent.md` files (clean slate). Setting `chat.useCustomAgentHooks: true` is a prerequisite noted in docs/research/agent-md-format.md section 7.

### Changes Made
- No AC changes needed (already well-scoped)
- Approved to todo

### Dependencies
- None listed, none missing
- Supersedes #37 (blocked at ideation, properly recorded)
