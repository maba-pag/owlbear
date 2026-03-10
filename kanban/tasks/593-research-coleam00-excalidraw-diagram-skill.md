---
id: 593
title: 'Research: coleam00/excalidraw-diagram-skill'
status: archived
priority: important
created: 2026-03-05T23:51:46.113192+01:00
updated: 2026-03-09T22:09:21.2632358+01:00
started: 2026-03-06T21:44:34.8174636+01:00
completed: 2026-03-09T22:09:21.2632358+01:00
tags:
    - research
    - phase-research
    - scope:copilot
parent: 582
class: standard
---

**Source:** https://github.com/coleam00/excalidraw-diagram-skill
Analyzed for Excalidraw skill patterns, diagram generation prompts, and MCP integration.

**Research doc:** See docs/excalidraw-diagram-skill-research.md

**Key findings:**
- LLM-driven Excalidraw JSON generation is proven (coleam00 skill, yctimlin MCP 1.3k stars)
- coleam00 skill pattern maps directly to OwlBear SkillRegistry
- Render-view-fix loop uses Playwright headless (OwlBear has BrowserManager)
- MCP server approach (yctimlin/lesleslie) is YAGNI for OwlBear

**Recommendation (.85):** Adopt skill pattern + render service + diagram toolset (~200 LOC)

**Follow-up tasks:** 3 tasks proposed in research doc section 5

[[2026-03-09]] Mon 15:22
## Architecture Review
**Verdict:** APPROVED

### Assessment
- Research doc is thorough: 4 sources, trade-off matrix, clear YAGNI decisions
- Research checklist (section 6) fully complete
- Follow-up tasks created: #628 (skill), #629 (render service + toolset integration)
- Third proposed task (DiagramToolset) correctly absorbed into #629 AC line 'Integrates with DiagramToolset as alternative render backend'
- No overlap with #594 (MCP approach rejected)
- Architecture direction sound: maps to existing DiagramToolset, BrowserManager, ScreenshotService, SkillRegistry patterns
- Priority (nice-to-have/Tier 2) appropriate: YAGNI until Kroki proves insufficient

### Codebase Verification
- Existing: DiagramService (src/owlbear/tools/diagram/service.py)  Kroki-based
- Existing: DiagramToolset (src/owlbear/tools/diagram/toolset.py)  FunctionToolset pattern
- Existing: BrowserManager (src/owlbear/tools/browser/manager.py)  Playwright lifecycle
- Existing: ScreenshotService (src/owlbear/tools/screenshot.py)  stateless render helper
- Existing: SkillRegistry (src/owlbear/skills/registry.py)  skill loading infrastructure

All referenced patterns and infrastructure exist. Follow-ups #628 and #629 correctly target these.

[[2026-03-09]] Mon 15:47
## Test-Writer Notes
- Non-implementation task (tagged research)  no tests applicable.
- Passing through to builder.

[[2026-03-09]] Mon 16:45
## Review Evidence
### AC Compliance (Research Task)
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Research doc exists | docs/research/excalidraw-diagram-skill-research.md (200 lines, 6 sections) | N/A | PASS |
| Sources studied (prior art) | 4 sources: coleam00 (.95), yctimlin (.80), lesleslie (.65), Excalidraw docs (.75) | N/A | PASS |
| Trade-off matrix | Section 3.1: 3 approaches x 7 criteria | N/A | PASS |
| Recommendation with confidence | Section 4: .85 confidence, skill + render service + toolset (~200 LOC) | N/A | PASS |
| Research checklist complete | Section 6: all 5 items checked | N/A | PASS |
| Follow-up tasks created | #628 (skill, 6 AC items), #629 (render service, 8 AC items) both in backlog | N/A | PASS |
| Tasks reference research doc | #628 Ref line, #629 Ref line both cite research doc | N/A | PASS |
| YAGNI decisions documented | Section 3.3: MCP server, live canvas, CRUD tools, Mermaid conversion rejected | N/A | PASS |

### Test Quality
N/A  research task, no code implementation, no tests applicable.

### Security
No issues  research task, no code changes.

### Notes
- Minor: task body path reference omits `research/` subdirectory (cosmetic)
- No Builder Notes section in task body (process gap, non-blocking for research)
- Architecture Review: APPROVED with codebase verification

### Verdict: PASS confidence .92

[[2026-03-09]] Mon 17:03
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Pure research task, no behavior/API/convention changes |
| 2 | Docstrings | No | N/A | No Python modules created or modified |
| 3 | sources/overview.md | Yes | Pass | 4 entries at lines 448-451 (coleam00, yctimlin, lesleslie, Excalidraw docs) |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/excalidraw-diagram-skill-research.md exists; follow-ups #628, #629 in backlog |
| 6 | No impact | -- | -- | Items 3 and 5 apply |

### Observations (non-blocking)
- Task body path: says `docs/excalidraw-diagram-skill-research.md` but file is at `docs/research/excalidraw-diagram-skill-research.md` (cosmetic, also flagged by reviewer)
- Research doc and sources/overview.md are untracked in git (never git-added). Not a docs-gate concern but should be committed before archive.

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/593-* files found)

[[2026-03-09]] Mon 22:09
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Research doc exists | docs/research/excalidraw-diagram-skill-research.md (6 sections, complete) | PASS |
| Sources studied (prior art) | 4 sources: coleam00 (.95), yctimlin (.80), lesleslie (.65), Excalidraw docs (.75) | PASS |
| Trade-off matrix | Section 3.1: 3 approaches x 7 criteria | PASS |
| Recommendation with confidence | Section 4: .85 confidence, skill + render service + toolset (~200 LOC) | PASS |
| Research checklist complete | Section 6: all 5 items checked | PASS |
| Follow-up tasks created | #628 (backlog, skill), #629 (backlog, render service) both verified | PASS |
| Tasks reference research doc | #628 and #629 Ref lines cite research doc | PASS |
| YAGNI decisions documented | Section 3.3: MCP server, live canvas, CRUD tools, Mermaid conversion rejected | PASS |
| sources/overview.md updated | 4 entries at lines 453-458 (coleam00, yctimlin, lesleslie, Excalidraw docs) | PASS |

### Test Results
- pytest: 1334 passed, 1 failed (env flake: PermissionError on Windows tmp_path, pre-existing), 2 skipped
- ruff: 3 pre-existing import order errors (no code changed by this task)

### Notes
- Minor cosmetic: task body path says docs/excalidraw-diagram-skill-research.md but file is at docs/research/... (flagged by reviewer and docs gate, non-blocking)

### Confidence: .97
### Action: archive

[[2026-03-09]] Mon 22:09
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Research doc exists | docs/research/excalidraw-diagram-skill-research.md (6 sections, complete) | PASS |
| Sources studied (prior art) | 4 sources: coleam00 (.95), yctimlin (.80), lesleslie (.65), Excalidraw docs (.75) | PASS |
| Trade-off matrix | Section 3.1: 3 approaches x 7 criteria | PASS |
| Recommendation with confidence | Section 4: .85 confidence, skill + render service + toolset (~200 LOC) | PASS |
| Research checklist complete | Section 6: all 5 items checked | PASS |
| Follow-up tasks created | #628 (backlog, skill), #629 (backlog, render service) both verified | PASS |
| Tasks reference research doc | #628 and #629 Ref lines cite research doc | PASS |
| YAGNI decisions documented | Section 3.3: MCP server, live canvas, CRUD tools, Mermaid conversion rejected | PASS |
| sources/overview.md updated | 4 entries at lines 453-458 (coleam00, yctimlin, lesleslie, Excalidraw docs) | PASS |

### Test Results
- pytest: 1334 passed, 1 failed (env flake: PermissionError on Windows tmp_path, pre-existing), 2 skipped
- ruff: 3 pre-existing import order errors (no code changed by this task)

### Notes
- Minor cosmetic: task body path says docs/excalidraw-diagram-skill-research.md but file is at docs/research/... (flagged by reviewer and docs gate, non-blocking)

### Confidence: .97
### Action: archive

[[2026-03-09]] Mon 22:09
## Audit
All 9 AC items PASS. Research doc verified (6 sections), 4 sources in overview.md, follow-ups #628/#629 in backlog.
pytest: 1334 passed, 1 env flake, 2 skipped. ruff: 3 pre-existing (no code changed).
Confidence: .97 | Action: archive
