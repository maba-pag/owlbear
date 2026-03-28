---
id: 46
title: Add agent-client-protocol to orchestrator deps
status: in-progress
priority: needed
created: 2026-03-26T18:56:04.3992332+01:00
updated: 2026-03-28T04:21:59.3219512+01:00
tags:
    - phase-1
    - scope:orchestrator
    - config
depends_on:
    - 7
claimed_by: builder
claimed_at: 2026-03-28T04:21:59.3219512+01:00
class: standard
---

## Objective

Add agent-client-protocol SDK as dependency to packages/orchestrator pyproject.toml.

## AC

- [ ] agent-client-protocol added to [project.dependencies] with pin >=0.9.0,<1.0.0
- [ ] uv lock succeeds with no resolution conflicts
- [ ] Import works: from acp import Client, connect_to_agent

## Research

See docs/research/acp-protocol.md section 3.7 for SDK assessment.
Package: agent-client-protocol v0.9.0 (PyPI, Apache-2.0). Only runtime dep: pydantic>=2.7.

[[2026-03-26]] Thu 20:03

## Architecture Review

**Verdict:** Approve

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| agent-client-protocol added with pin >=0.9.0,<1.0.0 | Precise, verifiable | Kept (tightened from 'pinned') |
| uv lock succeeds with no resolution conflicts | Clear pass/fail | Kept (added 'no resolution conflicts') |
| Import works: from acp import Client, connect_to_agent | Clear pass/fail, validated against SDK **all** | Kept |

### Architecture Notes

Config-only task: add a single dependency to pyproject.toml. No code, no new interfaces. The SDK (v0.9.0, Apache-2.0) brings only pydantic>=2.7 as transitive dep. Pin range >=0.9.0,<1.0.0 is correct for pre-1.0 semver. No TDD test task needed (no application code produced).

### Changes Made

- Added depends_on: [7] (monorepo skeleton, currently ideation)
- Tightened AC: explicit pin range, 'no resolution conflicts' qualifier
- Stripped stale research notes from body (info preserved in docs/research/acp-protocol.md)

### Dependencies

- Added: #7 (monorepo skeleton) - must complete first to create packages/orchestrator/

## Test-Writer Notes

- Non-implementation task (tagged config) — no tests applicable.
- Architect explicitly noted: No TDD test task needed (no application code produced).
- Passing through to builder.
