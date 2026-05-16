---
task_id: 1593
agent: builder
request_type: action
created: '2026-05-16'
response: resolved
resolved: '2026-05-16'
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

## Resolution (2026-05-16)

Chose option 2 (reclassify) with refinement:

1. **AC rewritten** from implementation-behavior to test-artifact criteria — deliverable is the test file itself, not runtime scroll behavior.
2. **proof_bundle changed** from `behavioral` to `skip` — suppresses automated test execution (tests are expected to fail); reviewer checks test quality via AC.
3. **Test file committed** as `5d46b499`.
4. **Task unblocked** — builder can now commit and advance; reviewer checks test-artifact quality.
5. **Prevention rule** to be added to `w-task-decomposition` — TDD-paired test-only tasks must use `skip` bundle with test-artifact AC.