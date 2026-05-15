---
id: deee4549-2e24-4e7f-a7fc-2cf7a20df076
title: Frontend behavioral reviews need Vitest coverage beside Playwright proof
categories:
- process
- tool-usage
- pitfall
confidence: 0.88
state: curated
scope_agents:
- reviewer
source_agent: reviewer
created_at: '2026-05-14T22:37:44.024402Z'
updated_at: '2026-05-15T03:02:50.987871Z'
approved_at: null
---

When a Cockpit frontend behavioral task uses Playwright E2E as its main proof and the builder leaves coverage as N/A, run quality-runner with the named Playwright spec plus the smallest adjacent Vitest component tests to get scoped coverage. Playwright pass alone is not enough to clear the behavioral coverage gate or distinguish proof debt from implementation debt.
