---
id: 1934
title: Align Cockpit stable frontend dependencies
status: archived
priority: medium
created: 2026-07-17T02:17:53.787093+02:00
updated: 2026-07-17T02:37:23.851315+02:00
tags:
  - type:build
  - tooling
  - scope:cockpit
  - rigor:lean
parent:
depends_on: []
ac:
  - A clean install resolves the selected stable dependency set without 
    peer-dependency errors.
  - Cockpit typechecks and builds successfully on Node 24 with TypeScript 6.
  - Existing lint configuration executes successfully with the aligned ESLint 
    packages.
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Objective
Update supported stable Cockpit frontend dependencies while retaining TypeScript 6 and Node 24. Keep package metadata and the lockfile reproducible.

## Scope
Vite, ESLint, typescript-eslint, Tailwind CSS and its Vite plugin, React and React DOM manifest alignment, React Router, Playwright manifest alignment, Vitest and coverage manifest alignment, and Node runtime type alignment. Do not adopt TypeScript 7, Node 26, Vitest 5, or unrelated dependency changes.

## Validation
Use installation consistency, lint/typecheck/build, and only existing focused tests needed to distinguish dependency regressions. Do not add source-presence or version-string tests.

[[2026-07-17T02:37:17+02:00]]
## Builder Notes
- Aligned supported stable frontend packages while retaining Node 24 and TypeScript 6.0.3.
- React and React DOM resolve to 19.2.7; React Router to 8.2.0; Vite to 8.1.5; ESLint to 10.7.0; typescript-eslint to 8.64.0; Tailwind and its Vite plugin to 4.3.3; Playwright to 1.61.1; Vitest and coverage to 4.1.10; Node declarations to 24.13.3.
- No durable tests added.
- Proof: clean npm install completed with zero vulnerabilities; top-level dependency tree valid; package-local ESLint passed; TypeScript and Vite production build passed using Vite 8.1.5.
- Builder challenger decision: pass; it independently reran clean install, dependency-tree validation, ESLint, and build with no fixes required.
- Board constraint: completed archival is accepted only from terminal collect, so this task advanced directly to collect for immediate archival.
