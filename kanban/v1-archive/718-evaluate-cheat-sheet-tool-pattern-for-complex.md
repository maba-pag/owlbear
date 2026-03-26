---
id: 718
title: Evaluate cheat-sheet tool pattern for complex toolsets
status: archived
priority: nice-to-have
created: 2026-03-09T23:06:33.8890974+01:00
updated: 2026-03-21T12:27:45.7997969+01:00
started: 2026-03-10T04:41:00.3600922+01:00
completed: 2026-03-21T12:27:26.720466+01:00
tags:
    - research
    - tooling
    - scope:core
class: standard
---

Investigate adding read_me-style companion tools to complex OwlBear toolsets (KnowledgeToolset, KanbanToolset) that pre-load format/schema context before the main tool call. Inspired by excalidraw-mcp read_me pattern. See docs/research/excalidraw-mcp.md S3.2.

[[2026-03-13]] Fri 09:12

## AC
- [ ] Research doc at docs/research/cheat-sheet-tool.md
- [ ] Evaluate read_me pattern from excalidraw-mcp for KnowledgeToolset and KanbanToolset
- [ ] Compare: inline tool descriptions vs companion read_me tool vs structured prompt injection
- [ ] Recommendation with confidence score
- [ ] Follow-up kanban tasks for adopted patterns

[[2026-03-13]] Fri 10:43
## Research
- Recommendation (.80): Don't add companion read_me tools. SkillRegistry already provides progressive disclosure.
- Follow-ups: #773, #774, #775
- Doc: docs/research/cheat-sheet-tool.md

[[2026-03-21]] Sat 03:22
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Research doc at docs/research/cheat-sheet-tool.md | Present and aligned with the task topic. | Pass |
| Evaluate read_me pattern for KnowledgeToolset and KanbanToolset | The research compares the excalidraw-mcp pattern against both OwlBear toolsets and checks the existing SkillRegistry mechanism. | Pass |
| Compare inline tool descriptions vs companion read_me tool vs structured prompt injection | Section 3.1 provides a three-way comparison table covering token cost, extra tool calls, implementation cost, and fit. | Pass |
| Recommendation with confidence score | Section 4 gives a .80 recommendation against companion read_me tools. | Pass |
| Follow-up kanban tasks for adopted patterns | Follow-ups exist: #773 created and archived, #774 created then superseded by #781, and #775 created and remains actionable. | Pass |

### Architecture Notes
- Existing progressive disclosure already exists in src/owlbear/skills/registry.py via list_skills and load_skill, which is the OwlBear-native analogue to a companion read_me tool.
- The recommendation is KISS and YAGNI aligned: do not add a second disclosure mechanism when skill loading already covers the need.
- The codebase state matches the recommendation: .github/skills/knowledge-ops/SKILL.md now exists, KanbanToolset description enrichment landed under #773, and researcher/curator agent definitions still show the remaining gap tracked by #775.
- This is a research task, not an implementation contract. TDD is not applicable for #718 itself; the actionable implementation work is isolated in the follow-up tasks.

### Changes Made
- Claimed #718 as quill-pond
- Appended architecture review evidence
- Prepared #718 to advance from backlog to todo

### Dependencies
- Verified follow-up lineage: #773 archived, #774 superseded by #781, #775 backlog
- Verified related interfaces: src/owlbear/skills/registry.py, src/owlbear/agents/researcher.md, src/owlbear/agents/curator.md, .github/skills/knowledge-ops/SKILL.md

[[2026-03-21]] Sat 03:51
## Test-Writer Notes
- Non-implementation task (tagged: research) -- deliverable is a research doc, no new Python code.
- AC items cover research artifacts: doc, evaluation comparison, recommendation, follow-up tasks.
- Architecture Review confirmed: TDD not applicable for #718 itself.
- Passing through to builder.

[[2026-03-21]] Sat 05:49
## Builder Notes
- Non-implementation task -- no code changes needed.
- Research doc verified: docs/research/cheat-sheet-tool.md exists.
- Follow-up tasks verified: #773, #774, #775 created in kanban/tasks/.
- Passing through to review.

[[2026-03-21]] Sat 06:24
## Review Evidence
## Review: #718 - Evaluate cheat-sheet tool pattern for complex toolsets

### Test Results
- Scoped pytest (task-relevant): uv run pytest tests/test_agent_registry.py -q --tb=short
- Result: 20 passed, 2 warnings (optional qdrant_client dependency missing warnings from 	ests/conftest.py)
- Additional broader check: uv run pytest tests/test_agent_registry.py tests/test_agent_definitions.py -q --tb=short returned 2 failures in 	est_skills_match[researcher] and 	est_skills_match[curator]; those failures align with open follow-up implementation path (#775 depends on #885) and are not introduced by #718's research artifact.

### Lint Results
- Command: uv run ruff check src/ tests/
- Result: FAIL with 461 findings (repo-wide baseline; #718 scope is research/task metadata, not Python implementation)

### Coverage
- N/A - research-only task; no Python code changes in #718 scope.

### Pass 1 - CRITICAL
#### Security Review
- Reviewed docs/research/cheat-sheet-tool.md and task artifacts: no hardcoded secrets, injection sinks, path traversal vectors, unsafe deserialization, dependency changes, or secret leakage introduced by this task.

#### Test Integrity (TestFromAC comparison)
- N/A - no TestFromAC_* classes were added/modified in #718 scope.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | N/A | #718 did not add or modify tests. |
| Negative/error paths | N/A | #718 did not add or modify tests. |
| Mutation reasoning | N/A | No implementation diff in scope to mutate-test. |
| Test independence | N/A | #718 did not add or modify tests. |
| Descriptive names | N/A | #718 did not add or modify tests. |

#### Data Safety
- No runtime data flow/storage code changes in scope; no data-safety regression identified.

### Pass 2 - INFORMATIONAL
- docs/research/cheat-sheet-tool.md includes a clear three-way comparison matrix and a confidence-scored recommendation.
- Follow-up lineage is present and traceable in board state: #773 (archived), #774 (superseded/ideation), #775 (backlog).

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Research doc at docs/research/cheat-sheet-tool.md | Verified document exists and contains full analysis sections (Context, Analysis, Recommendation, Follow-up Tasks). | Artifact verification (read_file) | PASS |
| Evaluate read_me pattern from excalidraw-mcp for KnowledgeToolset and KanbanToolset | Section 1 frames the pattern; Sections 3.2 and 3.3 evaluate current OwlBear infrastructure and gaps for both toolsets. | Artifact verification (read_file) | PASS |
| Compare: inline tool descriptions vs companion read_me tool vs structured prompt injection | Section 3.1 provides explicit A/B/C comparison table across token cost, call overhead, implementation cost, and fit. | Artifact verification (read_file) | PASS |
| Recommendation with confidence score | Section 4 states recommendation with .80 confidence. | Artifact verification (read_file) | PASS |
| Follow-up kanban tasks for adopted patterns | Verified tasks #773, #774, #775 exist and correspond to the three proposed follow-ups. | Board verification (kanban-md show) | PASS |

### Verdict
- PASS
- Confidence: .93

### Action Taken
- Pending status transition to docs.

[[2026-03-21]] Sat 12:27
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Research doc at docs/research/cheat-sheet-tool.md | Verified: 150-line doc with context, sources, 3-way comparison, gap analysis, recommendation. Committed (42ff2c6). | PASS |
| Evaluate read_me pattern for KnowledgeToolset and KanbanToolset | Sections 3.2-3.3 assess OwlBear SkillRegistry as functional equivalent, with gap analysis table. | PASS |
| Compare inline descriptions vs companion read_me vs structured prompt injection | Section 3.1 provides explicit A/B/C matrix across token cost, call overhead, implementation cost, KISS. | PASS |
| Recommendation with confidence score | Section 4: .80 confidence against companion read_me tools, 3 concrete alternatives proposed. | PASS |
| Follow-up kanban tasks for adopted patterns | #773 (archived), #774 (ideation, superseded by #781), #775 (backlog, depends #885). All created and traceable. | PASS |

### Research Task Checklist
- Research doc exists: PASS
- Follow-up tasks created at ideation or higher: PASS (3 tasks)
- Follow-up tasks link back to research doc: PASS (#775 explicit ref, #718 body traces all 3)

### Test Results
- pytest full suite: 3689 passed, 92 failed (all pre-existing: numpy compat, slack_sdk, bootstrap line count, CLI refactoring, pipeline roles)
- No failures attributable to #718 (research-only, no code changes)
- ruff: 460 findings (repo-wide baseline, no new issues from #718)

### Confidence: .97
### Action: archive

[[2026-03-21]] Sat 12:27
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 524795c | chore | kanban/tasks/718-*.md | #718 |
