---
id: 169
title: Document multi-project setup experience and sharing guide
status: archived
priority: medium
created: 2026-03-29 19:49:38.970111+02:00
updated: 2026-03-30 00:56:09.504217+02:00
started: 2026-03-30 00:55:20.089115+02:00
completed: 2026-03-30 00:55:20.089115+02:00
tags:
- phase-2
- scope:build
- type:docs
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Write end-to-end documentation for the multi-project setup experience and a 'How to share owlbear' guide.

## Acceptance Criteria
- [ ] docs/setup-guide.md: step-by-step from clone to working (prerequisites, setup.py invocation, VS Code opening, verification steps)
- [ ] docs/setup-guide.md: troubleshooting section (MCP server fails, agents not appearing, instructions not loading)
- [ ] docs/setup-guide.md: project-specific customization section (adding local agents, overriding instructions, adding MCP servers)
- [ ] docs/sharing-guide.md: how to share owlbear with teammates (clone, setup, verify)
- [ ] Both docs reference the VS Code Diagnostics view for debugging
- [ ] Both docs note the cross-drive Windows limitation
See docs/research/multi-project-setup-test.md for research context.

[[2026-03-29]] Sun 20:41
## Architecture Review
**Verdict:** Approve

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| docs/setup-guide.md: step-by-step | Specific file path, clear content scope | OK |
| docs/setup-guide.md: troubleshooting | Three named scenarios (MCP, agents, instructions) | OK |
| docs/setup-guide.md: customization | Clear subtopics (agents, instructions, MCP) | OK |
| docs/sharing-guide.md: sharing workflow | Specifies clone/setup/verify steps | OK |
| Both reference Diagnostics view | Grep-verifiable cross-file constraint | OK |
| Both note cross-drive limitation | Grep-verifiable cross-file constraint | OK |

### Architecture Notes
- Pure docs task; no code changes. TDD not applicable.
- Research doc (docs/research/multi-project-setup-test.md) provides comprehensive source material including VS Code resolution mechanisms, known risks, and override behavior.
- Target files: docs/setup-guide.md, docs/sharing-guide.md (neither exists yet).
- scripts/setup.py exists and is the primary subject of the documentation.
- Optional soft dependency on #167 (manual validation) which may surface additional troubleshooting items, but research doc is sufficient to write accurate initial docs.
- Duplicates exist at ideation (#171, #172, #174, #175) with cleanup task #182. This task (#169) is the canonical version at backlog.

### Changes Made
- Approved as-is; AC is precise and verifiable.

### Dependencies
- No hard dependencies. Research doc complete.
- Soft: #167 (manual validation) may inform updates but is not a blocker.

[[2026-03-29]] Sun 21:10
## Test-Writer Notes
- Non-implementation task (tagged type:docs) - no tests applicable.
- Passing through to builder.

[[2026-03-29]] Sun 21:45
## Research Docs Reference
- docs/research/setup-and-sharing-docs.md (original research, canonical source)
- docs/research/multi-project-doc-guide.md (doc structure, VS Code features, troubleshooting scenarios)
- docs/research/multi-project-setup-docs.md (setup flow analysis, prior art comparison)
All three docs provide complementary coverage for the AC in this task.

[[2026-03-29]] Sun 22:09
## Builder Notes
- Files changed: docs/setup-guide.md (new, 154 lines), docs/sharing-guide.md (new, 123 lines)
- Both docs include: Prerequisites, Quick Start, What Setup Creates table, Verify checklist, Troubleshooting table, cross-drive Windows limitation note, VS Code Diagnostics view reference
- setup-guide.md: customization section (local agents, override instructions, add MCP servers)
- sharing-guide.md: sharing model, shared vs project-local table, team conventions, org-level sharing
- Lint: N/A (docs task)
- Commit: ddaaabf

[[2026-03-30]] Mon 00:55
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| setup-guide.md: step-by-step | Prerequisites table L6-13, Quick Start L22-38, Verify section L66-80 | PASS |
| setup-guide.md: troubleshooting | Troubleshooting table L139-151 covers MCP, agents, instructions | PASS |
| setup-guide.md: customization | Customization section L88-135 (agents, instructions, MCP) | PASS |
| sharing-guide.md: clone/setup/verify | Set Up for Teammate section L27-51 | PASS |
| Both reference Diagnostics view | setup-guide L66,69,70,74-76,145; sharing-guide L48-49 | PASS |
| Both note cross-drive limitation | setup-guide L17-19,L149; sharing-guide L20-22 | PASS |

### Test Results
- pytest: 1072 passed, 64 failed (all pre-existing, unrelated to docs task)
- ruff: all checks passed (tests/)

### AC Quality Score: 4/5
AC was specific with grep-verifiable cross-file constraints. Minor gap: no TDD applicable for docs task.

### Pipeline Quality Note
Missing Review Evidence and Docs Gate sections in task body. Reviewer and writer did not leave evidence. Process gap only, not blocking.

### Confidence: .96
### Action: archive

[[2026-03-30]] Mon 00:56
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 323ca9f | chore | kanban/tasks/169-*.md | #169 |
