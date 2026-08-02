---
id: 25
title: Multi-project setup test
status: archived
priority: medium
created: 2026-03-26 17:23:32.282707+01:00
updated: 2026-03-30 15:35:59.569613+02:00
started: 2026-03-30 15:18:47.020136+02:00
completed: 2026-03-30 15:18:47.020136+02:00
tags:
- phase-2
- scope:build
- type:test
depends_on:
- 12
- 18
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Validate the multi-project model: create a test project, run setup, verify agents/skills/MCP servers work correctly from the project context.

## Acceptance Criteria
- [ ] Create a test project directory (e.g., test-project/)
- [ ] Run owlbear setup from the test project
- [ ] Verify .vscode/settings.json points to owlbear agents and skills
- [ ] Verify .vscode/mcp.json references owlbear MCP servers
- [ ] Open test project in VS Code and verify agents appear in agent picker
- [ ] Verify skills auto-load when relevant topics are discussed
- [ ] Verify MCP tools are callable from Copilot Chat
- [ ] Verify project-level copilot-instructions.md overrides work
- [ ] Test adding a project-specific agent override in .github/agents/
- [ ] Document the complete setup-to-working experience

## Context
Depends on F6 (setup script) and M5 (MCP server registry). This validates the 'clone = install' distribution model end-to-end.

[[2026-03-26]] Thu 18:05
## Additional AC
- [ ] Document the multi-project setup experience end-to-end
- [ ] Write a brief 'How to share owlbear with others' guide

[[2026-03-29]] Sun 19:51
## Research
Research complete. See docs/research/multi-project-setup-test.md for full findings.

Key findings:
- AC items 1-4 already covered by 39 unit tests from #12
- AC items 5-9 require manual VS Code validation (not automatable)
- AC items 10+ are documentation tasks
- Only owlbearKanban MCP server is operational; knowledge/project are stubs
- Agent name collision risk: VS Code loads from all locations without dedup

Follow-up tasks created at ideation:
- #167: Manual validation checklist (depends on #18)
- #175: Documentation (setup guide + sharing guide)

[[2026-03-30]] Mon 01:22
test-append

[[2026-03-30]] Mon 01:22
## Architecture Review
**Verdict:** BLOCK (fully superseded)

### AC Assessment
All 11 AC items are fully covered by successor tasks:
- AC items 1-4 (automated tests): #12 archived, 39 passing unit tests
- AC items 5-9 (manual VS Code validation): #167 at ideation
- AC items 10-11 (documentation): #169 archived

### Architecture Notes
Task #25 was an end-to-end integration validation umbrella. Research correctly identified that all AC decomposes into three categories: (a) automated tests already passing in #12, (b) manual VS Code validation requiring human interaction, and (c) documentation already delivered in #169.

No remaining work exists for this task. All successor tasks are created and tracked. Blocking to ideation as superseded; auditor should archive.

### Dependencies
- Verified: #12 (setup script) archived, 39 tests
- Verified: #18 (MCP server registry) done
- Verified: #167 (manual validation) ideation
- Verified: #169 (documentation) archived
- Verified: #175 archived as duplicate of #169

## Audit (manual archival 2026-03-30) Superseded: decomposed into #12 (archived), #167 (in-progress), #169 (archived). No own work remains. Confidence .97.
