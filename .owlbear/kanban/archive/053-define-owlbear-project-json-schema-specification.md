---
id: 53
title: Define owlbear-project.json schema specification
status: archived
priority: medium
created: 2026-03-26 19:11:49.390721+01:00
updated: 2026-03-27 08:49:23.282795+01:00
started: 2026-03-27 08:49:07.235593+01:00
completed: 2026-03-27 08:49:07.235593+01:00
tags:
- phase-1
- scope:mcp
- research
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Define the canonical owlbear-project.json schema shared by setup script (#12), mcp-project scaffold (#41), and mcp-project server (#17).

## Acceptance Criteria
- [ ] Research doc at docs/research/owlbear-project-json-schema.md defines all 5 fields: schema_version (int), name (string), type (enum), owlbear_path (string), created_at (ISO 8601) with types and constraints
- [ ] Validation rules documented: all fields required; format constraints specified per field (research doc section 3.3)
- [ ] Versioning strategy documented: integer schema_version with open schema / additionalProperties: true (research doc sections 3.2, 3.4)
- [ ] Location convention documented: owlbear-project.json at project workspace root (research doc section 3.5)
- [ ] Follow-up implementation tasks created: #68 (Pydantic model), #69 (setup script generation)

## Context
See docs/research/scaffold-mcp-project-server.md section 3.2 for initial schema analysis.

## Research
Doc: docs/research/owlbear-project-json-schema.md

Key findings:
- 5 required fields: schema_version (int), name (string), type (enum), owlbear_path (string), created_at (ISO 8601)
- Integer schema_version=1 for versioning (.85 confidence) -- simple, KISS-aligned
- Open schema (additionalProperties: true) -- additive fields don't require version bump
- Pydantic model with extra='allow' for validation
- File lives at project workspace root (written by setup script, read by mcp-project server)

Follow-up tasks created:
- #68 Implement OwlbearProjectFile Pydantic model in mcp-project (ideation)
- #69 Add owlbear-project.json generation to setup script (ideation)

[[2026-03-26]] Thu 21:29
## Test-Writer Notes
- Non-implementation task (tagged research) — no tests applicable.
- Passing through to builder.

[[2026-03-27]] Fri 02:59
## Builder Notes
- Files changed: docs/research/owlbear-project-json-schema.md
- Tests: N/A (research task, no code execution changes)
- Lint: N/A (no Python source changes)
- Evidence: Created missing schema spec doc with required sections 3.2, 3.3, 3.4, 3.5 and follow-up task references #68 and #69
- Fixes applied: Recreated docs/research/owlbear-project-json-schema.md to satisfy AC path and schema constraints

[[2026-03-27]] Fri 05:04
## Review Evidence

## Review: #53 - Define owlbear-project.json schema specification

### Test Results
- pytest: N/A. This is a research-only task with no executable deliverable and no task-scoped test target.

### Lint Results
- ruff: N/A. The reviewed deliverable is markdown plus kanban follow-up tasks; no task-scoped Python files changed.

### Coverage
- N/A. No Python module was delivered by this task.

### Pass 1 - CRITICAL
- Test-Writer AC Coverage: No TestFromAC classes exist. The task body correctly marks this as a non-implementation research task.
- Security Review: No security issues found in the reviewed artifacts. The task delivers documentation and board entries only.
- Test Integrity: Not applicable. No TestFromAC classes or builder-authored test edits exist for this task.
- Test Quality: Not applicable. No task-scoped tests exist for this research card.
- Data Safety: No runtime behavior, persistence logic, or concurrency changes were delivered.
- Implementation-Aware Test Gaps: No implementation was delivered in this task, so there are no hidden runtime branches or recovery paths to test.

### Pass 2 - INFORMATIONAL
- Source attribution for the research doc is recorded in docs/sources/overview.md:93-100.
- Follow-up task 68 links back to the research doc at kanban/tasks/068-implement-owlbearprojectfile-pydantic-model-in-mcp.md:18 and :28.
- Follow-up task 69 links back to the research doc at kanban/tasks/069-add-owlbear-project-json-generation-to-setup.md:29.

### AC Compliance
1. PASS - docs/research/owlbear-project-json-schema.md:28-38 defines all five fields with explicit types and constraints.
2. PASS - docs/research/owlbear-project-json-schema.md:49-60 documents all fields required and per-field validation rules.
3. PASS - docs/research/owlbear-project-json-schema.md:40-46 and 62-67 document integer schema_version versioning and an open schema with additionalProperties true.
4. PASS - docs/research/owlbear-project-json-schema.md:71-77 documents the workspace-root location convention.
5. PASS - docs/research/owlbear-project-json-schema.md:163-166 records created task IDs 68 and 69; kanban/tasks/068-implement-owlbearprojectfile-pydantic-model-in-mcp.md:2-3 and kanban/tasks/069-add-owlbear-project-json-generation-to-setup.md:2-3 confirm both tasks exist.

### Verdict: PASS

### Action Taken
- Appended review evidence, moved task 53 to docs, and released the reviewer claim.

## Review Evidence
- PASS.

### Detailed Evidence
- Test Results: pytest not applicable because task 53 is a research-only deliverable and no executable code or task-scoped tests were introduced.
- Lint Results: ruff not applicable because the reviewed artifacts are markdown and kanban tasks only.
- Critical checks: no TestFromAC classes exist, no builder-authored test edits exist, and the task introduces no executable code, security surface, or data-safety surface.
- AC 1 PASS: docs/research/owlbear-project-json-schema.md:28-38 defines schema_version, name, type, owlbear_path, and created_at with explicit types and constraints.
- AC 2 PASS: docs/research/owlbear-project-json-schema.md:49-60 states all five fields are required and lists per-field validation rules.
- AC 3 PASS: docs/research/owlbear-project-json-schema.md:40-46 and 62-67 document integer schema_version versioning and open-schema behavior with additionalProperties true.
- AC 4 PASS: docs/research/owlbear-project-json-schema.md:71-77 documents the workspace-root location convention.
- AC 5 PASS: docs/research/owlbear-project-json-schema.md:163-166 records created task IDs 68 and 69; kanban/tasks/068-implement-owlbearprojectfile-pydantic-model-in-mcp.md:2-3 and kanban/tasks/069-add-owlbear-project-json-generation-to-setup.md:2-3 confirm both follow-up tasks exist.
- Informational: docs/sources/overview.md:93-100 records the research attribution for task 53.
- Verdict: PASS with confidence .95.
