---
id: 46
title: Add agent-client-protocol to orchestrator deps
status: archived
priority: medium
created: 2026-03-26 18:56:04.399233+01:00
updated: 2026-03-29 09:18:41.391010+02:00
started: 2026-03-29 08:44:15.335912+02:00
completed: 2026-03-29 09:18:41.090494+02:00
tags:
- phase-1
- scope:orchestrator
- config
depends_on:
- 7
class: standard
archival_reason: completed
archival_refs: []
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

[[2026-03-29]] Sun 07:55
## Builder Notes
- Files changed: packages/orchestrator/pyproject.toml (dependency already present)
- AC verification:
  - agent-client-protocol>=0.9.0,<1.0.0 confirmed in [project.dependencies]
  - uv lock --check: Resolved 306 packages in 6ms — no conflicts
  - from acp import Client, connect_to_agent: Import OK
- No code changes needed (config already in place)
- Lint: N/A (no Python files changed)

[[2026-03-29]] Sun 08:43
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Config-only dep add; ACP already documented in tech stack table and directory structure |
| 2 | Docstrings | No | N/A | No Python modules created or modified â€” only pyproject.toml changed |
| 3 | docs/sources/overview.md | No | N/A | ACP Python SDK (v0.9.0, Apache-2.0) already attributed from research phase |
| 4 | README.md | No | N/A | No CLI commands added or changed |
| 5 | Research doc | Yes | Pass | docs/research/acp-protocol.md exists and is linked in task body (section 3.7) |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/46-* files found)

[[2026-03-29]] Sun 09:18
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| agent-client-protocol added with pin >=0.9.0,<1.0.0 | pyproject.toml L7: agent-client-protocol>=0.9.0,<1.0.0 | PASS |
| uv lock succeeds with no resolution conflicts | uv lock --check: Resolved 306 packages in 6ms, exit 0 | PASS |
| Import works: from acp import Client, connect_to_agent | Both imports succeed, exit 0 | PASS |

### Test Results
- pytest: 1 passed (full suite, no failures)
- ruff: All checks passed

### Commit Verification
- Deliverable committed in a2bdc11 (batched refactor commit)
- packages/orchestrator/pyproject.toml tracked and clean (no diff vs HEAD)

### AC Quality Score: 5/5
AC was specific, complete, and led to clean implementation. Each line is directly verifiable with clear pass/fail. Architecture notes correctly scoped as config-only.

### Confidence: .97
### Action: archive
