---
id: 50abdfe3-4574-4258-96a3-24bf6bdab75b
title: Test-writer path guard blocks e2e/ writes after initial creation
categories:
- pitfall
- env-context
confidence: 0.95
state: curated
scope_agents:
- test-writer
- architect
source_agent: test-writer
created_at: '2026-05-15T01:09:12.038386Z'
updated_at: '2026-05-15T03:02:55.509407Z'
approved_at: null
---

Test-writer VS Code path guard allows CREATING new e2e/*.spec.ts files but blocks EDITING them in retry cycles. Allowed write targets: tests/, __tests__/, .owlbear/scratch/. The serve/cockpit/web/e2e/ directory is blocked for edits. When AC requires updating an existing E2E spec, the test-writer cannot do it — this creates a deadlock if builder also can't write tests. Architect must either: (a) accept unit test proof as sufficient, (b) create a separate user-action or out-of-band task, or (c) adjust path guard scope.
