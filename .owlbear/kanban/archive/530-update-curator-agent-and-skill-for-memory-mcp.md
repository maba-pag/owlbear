---
id: 530
title: Update curator agent and skill for memory-mcp
status: archived
priority: medium
created: 2026-04-01 19:13:05.355839+02:00
updated: 2026-04-04 17:29:26.342067+02:00
started: 2026-04-04 17:29:26.342067+02:00
completed: 2026-04-04 17:29:26.342067+02:00
tags:
- scope:agents
- phase-2
- agent
depends_on:
- 525
- 568
class: standard
archival_reason: completed
archival_refs: []
---

Depends on #525 (memory-mcp tools implemented) and #568 (owlbear-memory tool access added to all agents).

AC:
- [ ] Curator agent persona updated: references MCP memory entries alongside file-based inbox as entry sources
- [ ] Curator agent retains vscode/memory tool for /memories/ and /memories/session/ access
- [ ] Curation-workflow Step 1 updated: add list_entries(status=pending) as primary gather source; retain /memories/repo/inbox/ scan via vscode/memory during migration (per research doc 3F)
- [ ] Curation-workflow Step 4 updated: mark_for-deletion(entry_id) for MCP entries rated LOW/NOISE; retain memory delete for file-based inbox entries during migration
- [ ] New Step 4 CROSS-POLLINATE action: record_learning with agent_id set to curator:cross-pollinate:{original_entry_id}, carrying forward original entry category, confidence at least 0.7
- [ ] Curation-workflow Step 5 report format: include MCP entry IDs with short content preview and recommendation column
- [ ] No changes to curator critical_rules (mark_for-deletion is soft-delete, never-delete-reviewed-lessons rule still applies conceptually)

Implementation notes (for builder):
- owlbear-memory/* tool access comes from #568, not this task. Do NOT edit tools: frontmatter.
- record_learning agent_id param maps to DB source column (lineage tracking, not filtering). list_entries filters on scope_agent, not source.
- Cross-pollinated entries re-enter pending queue intentionally (research doc 3C). Curator evaluates them as regular entries next cycle. No loop risk because curator assesses signal, not auto-cross-pollinates.
- record_learning validates category against: preference, knowledge, context, behavior, goal. Use original entry category.
- record_learning enforces confidence >= 0.7. If original entry lacks numeric confidence, use 0.7 floor.

[[2026-04-03]] Fri 11:10
## Architecture Review
**Verdict:** APPROVE
**DR Verification:** DR #387 resolved (docs/decisions/resolved/387-memory-mcp-architecture.md approved: true); DR #428 resolved. T1 autonomous per researcher.

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| AC1 (curator tools) | Removed: tool access via #568 glob, not this task | Replaced with persona update AC |
| AC2 (retains vscode/memory) | Clear, verifiable | Kept |
| AC3 (Step 1 list_entries) | Gap: said replaces but research 3F says dual-read | Refined: add alongside, retain inbox during migration |
| AC4 (Step 4 mark_for-deletion) | Same gap as AC3 | Refined: MCP entries use mark_for-deletion, inbox files use memory delete |
| AC5 (cross-pollinate) | Wrong param name (source should be agent_id); missing category/confidence guidance | Refined: agent_id param, carry forward category, confidence >= 0.7 |
| AC6 (report format) | Clear, verifiable | Kept |

### Architecture Notes
Non-impl task: edits .agent.md persona + SKILL.md workflow text only. No Python code.
Tool access (owlbear-memory/*) handled by #568 (blanket glob for all 14 agents). This task must NOT edit tools: frontmatter.
record_learning agent_id maps to DB source column (lineage). list_entries filters scope_agent not source. Cross-pollinated entries visible via list_entries(status=pending) naturally.
Category validation enforced by MCP tool: preference, knowledge, context, behavior, goal. Confidence floor 0.7.
Migration dual-read (research 3F) scoped to this task. Cutover (3F phase 4, remove inbox scan) is a future follow-up.

### Changes Made
- Rewrote AC body: removed tool-list edit (deferred to #568), added persona update, corrected param names, added migration dual-read, added category/confidence guidance
- Added depends_on #568 (owlbear-memory tool access prerequisite)
- Added agent tag (non-impl pass-through for test-writer)

### Dependencies
- Verified: #525 (memory-mcp tools) at archived
- Added: #568 (owlbear-memory tool access) at backlog
- Verified: DR #387, DR #428 both resolved/approved

### Challenge Results
- Challenger: block (confidence in original: .45)
- Key challenges: C1 missing #568 dep (accepted, added), C2 agent_id/source mapping (rebutted: lineage tracking not filtering, design correct per 3C), C3 glob vs selective tool access (accepted: deferred to #568, removed tool-list AC from this task), C4 migration exit criteria (noted: future follow-up, not in scope), C5 category/confidence unspecified (accepted: added to AC), C6 persona staleness (accepted: added persona update AC)
- Architect response: accepted C1/C3/C5/C6, rebutted C2, deferred C4. Revised AC confidence: .88

[[2026-04-03]] Fri 17:56
## Test-Writer Notes
- Non-implementation task (tagged `agent`) -- no tests applicable.
- AC deliverables: agents/curator.agent.md (persona update), skills/curation-workflow/SKILL.md (Step 1 + Step 4 + Step 5 workflow updates, new CROSS-POLLINATE action).
- No Python implementation intent found in AC.
- Passing through to builder.

[[2026-04-03]] Fri 19:54
## Builder Notes
- Files changed: agents/curator.agent.md, skills/curation-workflow/SKILL.md
- Tests: N/A (non-implementation task, agent tag)
- Lint: N/A (no Python code)
- Evidence: commit 664bec7 -- 2 files, 45 insertions, 17 deletions
- Fixes: AC1 persona updated; AC2 vscode/memory retained; AC3 Step 1 rewritten with list_entries primary; AC4 mark_for-deletion for MCP entries; AC5 CROSS-POLLINATE action added; AC6 Step 5 entries table added; AC7 critical_rules untouched

[[2026-04-04]] Sat 03:11
## Review Evidence

Files reviewed: commit 664bec7 -- agents/curator.agent.md (+11/-8), skills/curation-workflow/SKILL.md (+34/-9). No Python code; agent-tagged task.

Tests: N/A (agent/skill markdown, tagged agent). Test-writer pass-through confirmed. Lint: N/A. Coverage: N/A.

AC Compliance:
- AC1 (persona references MCP + inbox): PASS
- AC2 (vscode/memory retained): PASS
- AC3 (Step 1 list_entries primary + inbox secondary): PASS
- AC4 (mark_for_deletion for MCP, memory delete for file-based): PASS -- tool name verified tools.py:285
- AC5 (CROSS-POLLINATE agent_id/category/confidence floor 0.7): PASS -- verified tools.py:130
- AC6 (Step 5 Entries table ID/Source/Preview/Rating/Action): PASS
- AC7 (critical_rules unchanged): PASS

Security: PASS. Builder process: CLEAN. Deductions: 0. Confidence: .94 -> PASS

[[2026-04-04]] Sat 16:33
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A — no copilot-instructions update needed | Changes are agent persona + skill workflow (internal curator operation). Memory Governance table already accurately reflects dual-write sources (Repo inbox: "Agent lessons-learned (legacy, dual-write)", Canonical: owlbearMemory). No system-level governance change. |
| 2 | Module docstrings | No | N/A | No Python modules changed. Task tagged `agent`; all changes are .agent.md and SKILL.md markdown files. |
| 3 | External attribution | No | N/A | No new external patterns. Attribution for mem0/LangMem already captured in docs/research/curator-workflow-memory-mcp.md (owning task #528). |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | N/A | Verified | docs/research/curator-workflow-memory-mcp.md exists (owning task #528). AC notes reference §3C and §3F. Task #530 implements that research; it did not produce a new research doc. |

### Files Updated
- None

### Scratch Files Cleaned
- docs/scratch/530-architect.tmp — deleted (stale; from a mistaken arch review that confused #530 with an observability audit task)

[[2026-04-04]] Sat 17:29
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 Persona references MCP + inbox | curator.agent.md persona: "expedition database (owlbearMemory MCP, queried via list_entries) and physical notebooks dropped in the library inbox" | PASS |
| AC2 Retains vscode/memory tool | curator.agent.md tools: list includes vscode/memory | PASS |
| AC3 Step 1 list_entries primary + inbox secondary | w-mem-curation SKILL.md Step 1: "Primary (MCP): Call list_entries(status=pending)" + "Secondary (file-based)" | PASS |
| AC4 mark_for_deletion for MCP, memory delete for file-based | w-mem-curation SKILL.md Step 4 Deletions: both pathways present | PASS |
| AC5 CROSS-POLLINATE agent_id/category/confidence | w-mem-curation SKILL.md Step 4 Cross-pollination: agent_id=curator:cross-pollinate:{id}, category carry-forward, confidence floor 0.7 | PASS |
| AC6 Step 5 report with MCP entry IDs | w-mem-curation SKILL.md Output Template: Deletions table with Source/ID/File columns | PASS |
| AC7 critical_rules unchanged | curator.agent.md critical_rules section intact, no MCP-related additions | PASS |

### Test Results
- pytest: 2784 passed, 403 failed (all pre-existing from directory reorganization, 0 in task scope), 8 skipped, 1 error (unrelated import)
- ruff: N/A (no Python code; agent/skill markdown only)

### Architect Quality: 4/5
Original AC had param name errors (source vs agent_id) and missing migration dual-read guidance. Architect corrected all during review with challenger input. Final AC was specific, verifiable, and complete.

### Deduction Breakdown
- 7 AC lines, all with specific evidence: no deduction
- Lint: N/A (no Python code)
- AC quality 4/5 (above threshold of 3): no deduction
- Reviewer evidence present and detailed (.94 confidence PASS): no deduction
- Full-suite failures in task scope: 0: no deduction

### Confidence: 1.00
### Action: archive

### Commit Integrity
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 664bec7 | feat | agents/curator.agent.md, skills/curation-workflow/SKILL.md | #530 |
