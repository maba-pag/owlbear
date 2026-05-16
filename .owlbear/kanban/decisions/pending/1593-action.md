---
task_id: 1593
agent: builder
request_type: action
created: '2026-05-16'
response: pending
---

Dependency/routing correction requested.

Observed state:
- Task #1593 (tests) AC checks are RED in current workspace via quality-runner (2 failed, eslint clean).
- Task #1596 (implementation) is currently blocked by dependency on #1593.
- #1593 body marks implementation out of scope, so GREEN for #1593 is structurally unreachable until #1596 runs.

Requested action:
1) Remove or invert dependency so #1596 can execute before #1593 GREEN gating, OR
2) Reclassify #1593 as explicit non-implementation pass-through with accepted RED evidence criteria.

Evidence source: quality-runner scoped execution on serve/cockpit/web/e2e/board-scroll-1593.spec.ts returned:
- scrollWidth 864 == clientWidth 864 (expected >)
- offsetTop values wrapped across rows [145,145,145,337,337,337,528].