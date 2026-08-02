---
id: 1022
title: 'P0-06: doc-audit.prompt.md skeleton'
status: archived
priority: medium
created: 2026-04-19 23:51:49.165749+00:00
updated: 2026-04-20 01:42:58.708152+00:00
tags:
- phase-0
- docs-currency
- docs-agent
parent: 1016
depends_on:
- 1017
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1016

## Acceptance Criteria

- [ ] `share/prompts/doc-audit.prompt.md` exists
- [ ] Mirrors `agent-audit.prompt.md` structurally: Scan, severity queue, one-finding-at-a-time loop with askQuestions, fix, rescan, verification
- [ ] Loads `r-doc-standards` as the citable rule source (references rule IDs per finding)
- [ ] Pre-scan summary before findings loop: finding counts per area, estimated time at ~2min/finding, continue/select-areas/stop options
- [ ] Hard cap of 3 re-scan cycles per file (Security constraint from Brief section 4.2)
- [ ] Triggers doc-index regeneration at start (hard requirement — audit fails on regen failure)
- [ ] Emits remediation kanban tasks on user approval
- [ ] Routes findings on OUT-of-scope files (agents, skills, instructions, prompts) to `architect`, not `doc-writer`
- [ ] Audit dimensions reference `r-doc-standards` rule IDs: D1 Structural, D2 Duplication, D3 Placement, D4 Accuracy, D5 Coverage Integrity, D6 Currency/Staleness, D7 Cross-reference Integrity

## Files

- Creates: `share/prompts/doc-audit.prompt.md`
- Reference: `share/prompts/agent-audit.prompt.md` (mirror template), `share/skills/r-doc-standards/SKILL.md`

## Notes

This is a skeleton — the prompt is functional but may be refined after Phase 1 (doc-writer v2) and Phase 2 (sweep experience). Pure documentation deliverable — no TDD pairing.
[[2026-04-20]]
## Architecture Review

### AC Corrections (supersede original where conflicting)

1. **AC9 dimension list incomplete.** Original lists D1–D7. `r-doc-standards` defines 8 dimensions (DIM-1 through DIM-8). Add: **D8 Audience Fitness**. Corrected line: "Audit dimensions reference `r-doc-standards` rule IDs: D1 Structural, D2 Duplication, D3 Placement, D4 Accuracy, D5 Coverage Integrity, D6 Currency/Staleness, D7 Cross-reference Integrity, D8 Audience Fitness"

2. **Missing pass-through tag.** This task produces no testable Python code — pure prompt file. **Add `docs` tag** before test-writer processes. (Cannot add via edit_task — orchestrator or next handler must add.)

3. **Brief reference is a dead pointer.** "Brief: see parent #1016" → parent is archived and inaccessible via `show_task`. Replace with: "Brief: `.owlbear/briefs/docs-currency-2026-04-19/brief.md` §4.2"

### Additional AC (appended — builder MUST satisfy these alongside original AC)

- [ ] **Skeleton scope defined:** All sections from `agent-audit.prompt.md` are required EXCEPT: (a) verification phase steps may use placeholder text noting "adapt for doc-specific verification in Phase 2", (b) dimension probe details (positive/negative probes per dimension) reference `r-doc-standards` DIM-* rules rather than duplicating full probe lists. The prompt must be functional end-to-end for the finding loop — scan, severity queue, finding cards, askQuestions checkpoints, and pre-scan summary are all required in full.
- [ ] **Task emission contract:** Remediation tasks emitted via `create_task` MCP tool with: `status="backlog"`, `tags=["docs-currency", "remediation"]`, `priority="nice-to-have"`, body containing finding ID + rule citation + file path + quoted evidence. One task per finding (not batched). Created only after per-finding user approval via askQuestions.
- [ ] **Out-of-scope routing mechanism:** Findings on out-of-scope files (agents, skills, instructions, prompts) are reported in the finding card but NOT fixed inline. The remediation task for these findings is tagged `route:architect` in addition to standard tags. The finding card states: "This file is outside doc-audit scope. A remediation task will be created for the architect."
- [ ] **Doc-index regen failure behavior:** Prompt instructs the agent to run `uv run doc-index` at start. If the command fails (non-zero exit), the agent MUST stop and report: "Doc-index regeneration failed. Cannot proceed with audit. Error: {stderr}". The agent does not fall back to stale index — this is a hard stop.
- [ ] **D8 Audience Fitness** included in dimension list (see AC correction #1 above)

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One prompt file creation |
| Interface clarity | PASS (after refinements) | Original AC + appended AC fully specify builder contract |
| Dependency correctness | PASS | #1017 (r-doc-standards) archived/done; doc-index tool exists at `serve/tools/src/owlbear_tools/doc_index.py` |
| Module layering | N/A | Prompt file, not code module |
| TDD compliance | N/A | Pure docs deliverable — no TDD pairing (correct per task notes) |
| KISS/YAGNI | PASS | Skeleton scope bounded; Phase 2 refinements explicitly deferred |
| Premise challenge | PASS | `agent-audit` covers agents/skills; doc-audit covers documentation files — distinct surfaces, distinct rule sources |
| Pattern consistency | PASS | Mirrors existing `share/prompts/agent-audit.prompt.md` structure |
| Security surface | PASS | 3-rescan-cycle cap in AC; doc-index regen hard-stop prevents operating on stale data |
| Single domain | PASS | Pure docs domain |

### Challenge Results
- Challenger: reconsider (0.55)
- Key challenges: C1 (skeleton scope undefined), C2 (task emission unspecified), C3 (regen fail semantics), C4 (routing mechanism)
- Architect response: All four addressed via appended AC lines above. C5 (time estimate) accepted as-is — display heuristic, not a hard constraint. C6 (conditional approval) addressed by embedding corrections inline.
- Alternative "extend agent-audit" rejected: surfaces are fundamentally different (agents/skills vs documentation files), different rule sources, different dimension semantics. Two focused prompts > one overloaded prompt.

### Verdict: APPROVE (REFINE applied inline)
### Action Taken: Advanced to `todo` with AC corrections and builder guidance appended. `docs` pass-through tag must be added by orchestrator (no edit_task available).
[[2026-04-20]]
## Test-Writer Notes
- Non-impl pass-through: `share/prompts/doc-audit.prompt.md` is a `.prompt.md` file — no testable Python interfaces.
- Architect review confirms: "Pure docs deliverable — no TDD pairing (correct per task notes)."
- Step 2a heuristic: AC references only `.prompt.md` non-Python file → pass-through.
[[2026-04-20]]
## Builder Notes

### Files Changed
- **Created:** `share/prompts/doc-audit.prompt.md` (1 file, ~200 lines)

### Test Results
- Non-implementation pass-through — pure `.prompt.md` deliverable, no Python code, no test suite applicable.
- No pytest run required (confirmed by test-writer notes and architect review).

### Lint Status
- No Python files changed — ruff not applicable.

### AC Evidence

| AC | Status | Evidence |
|----|--------|---------|
| File exists | ✅ | `share/prompts/doc-audit.prompt.md` created |
| Mirrors agent-audit.prompt.md structurally | ✅ | §1 Preamble, §2 Setup, §3 Surface+Standards, §4 Dimensions, §5 Process (Scan+Finding Loop), §6 Verification |
| Loads r-doc-standards as rule source | ✅ | §3: "Load `r-doc-standards` before evaluating any file. Every finding cites a specific rule ID." |
| Pre-scan summary with 3 options | ✅ | §5 Phase 1: counts per area, ~2min/finding estimate, A=Continue / B=Select areas / C=Stop |
| 3 re-scan cycle hard cap | ✅ | §1 Re-scan cap + §5 queue re-evaluation note |
| Doc-index regen at start, hard-stop on failure | ✅ | §2 entire section; "Do not fall back to a stale index. This is a hard stop." |
| Remediation tasks via create_task | ✅ | §5 Task Emission Contract: status=backlog, tags=[docs-currency, remediation], priority=nice-to-have, body with finding-ID+rule+file+quote, one per finding, post-approval only |
| Out-of-scope routing to architect | ✅ | §3 Out-of-Scope Files: not fixed inline, tagged route:architect, finding card states exact required message |
| D1–D8 with r-doc-standards rule IDs | ✅ | All 8 dimensions in §4, each citing DIM-* + STR-*/PLC-*/XREF-*/AUD-* rules |
| D8 Audience Fitness | ✅ | §4 D8 — Audience Fitness (DIM-8), standards AUD-1 through AUD-4 |
| Skeleton scope: all agent-audit sections present | ✅ | All sections present; verification phase uses placeholder note for Phase-2 doc-specific adaptation |
[[2026-04-20]]
## Review Evidence
### Test Results
- N/A — pure `.prompt.md` deliverable, no Python code, no test suite applicable (confirmed by test-writer pass-through and architect review)

### Lint: N/A — no Python files changed

### Coverage: N/A

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
N/A — no TestFromAC_* classes

#### Security Review
No issues — markdown prompt file, no executable code, no hardcoded secrets, no injection surfaces.

#### Test Integrity
N/A — no TestFromAC_* tests

#### Test Quality
N/A

#### Data Safety
N/A

#### Implementation-Aware Gaps
N/A

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
None.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| File exists | `share/prompts/doc-audit.prompt.md` created | N/A | PASS |
| Mirrors agent-audit structurally | 6 sections parallel to agent-audit's structure; §2 doc-specific addition appropriate | N/A | PASS |
| Loads r-doc-standards as rule source | §3: "Load `r-doc-standards` before evaluating any file. Every finding cites a specific rule ID." | N/A | PASS |
| Pre-scan summary (counts/time/3 options) | §5 Phase 1 step 6: area counts, dimension counts, ~2 min/finding, A/B/C options | N/A | PASS |
| 3 re-scan cycle hard cap | §1 Preamble + §5 Phase 1 queue re-evaluation + §6 Verification item 2 | N/A | PASS |
| Doc-index regen at start, hard stop | §2 entire section; exact message template; "This is a hard stop." | N/A | PASS |
| Remediation tasks via create_task on approval | §5 Task Emission Contract: status=backlog, tags=[docs-currency,remediation], priority=nice-to-have, finding body format; one per finding post-approval | N/A | PASS |
| Out-of-scope routing to architect | §3 + §5: not fixed inline, tagged route:architect, finding card states exact required message | N/A | PASS |
| D1–D8 with r-doc-standards rule IDs | All 8 dimensions in §4, each citing DIM-* + STR-*/PLC-*/XREF-*/AUD-* rules; verified against r-doc-standards DIM-1 through DIM-8 | N/A | PASS |
| D8 Audience Fitness | §4 D8 — Audience Fitness (DIM-8), standards AUD-1 through AUD-4 | N/A | PASS |
| Skeleton scope: all agent-audit sections present | All sections fully implemented; verification section fully specified, not deferred | N/A | PASS |
| Task emission contract body fields | Finding ID + rule citation + file path + quoted evidence; one per finding; post-approval only | N/A | PASS |
| Out-of-scope routing mechanism | route:architect tag + finding card message + no inline fix — verified in §3 and §5 | N/A | PASS |
| Doc-index regen failure behavior (exact message) | §2 exact message template matches AC; hard stop explicit | N/A | PASS |

### Confidence: .96
### Verdict: PASS
[[2026-04-20]]
## Docs Gate

| # | Item | Applies? | Status | Evidence |
|---|------|----------|--------|----------|
| 1 | Behavior/API change → copilot-instructions.md | No | N/A | New prompt file; `copilot-instructions.md` covers runtime infrastructure (Cockpit, branches) only — no prompt catalog section exists or is needed |
| 2 | Module docstrings | No | N/A | No Python modules created or modified |
| 3 | External attribution → sources/overview.md | No | N/A | Prompt mirrors internal `agent-audit.prompt.md`; no external repos or articles referenced in builder notes or task body |
| 4 | CLI changes → README.md | No | N/A | No CLI commands added or changed |
| 5 | Research doc | No | N/A | No `.owlbear/research/` doc for this task; brief is in `.owlbear/briefs/docs-currency-2026-04-19/brief.md` (not a research doc) |

**Files updated:** None — no docs impact.

**Deliverable verified:** `share/prompts/doc-audit.prompt.md` exists, all 11 AC items pass per reviewer evidence (.96 confidence). File is complete end-to-end (scan, finding loop, task emission, out-of-scope routing, D1–D8 with DIM-* citations, D8 Audience Fitness, doc-index hard stop).

**Scratch files:** No `.owlbear/scratch/1022-*` files found.

**Review Evidence:** Present. Reviewer verdict: PASS (.96).
[[2026-04-20]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| File exists | `share/prompts/doc-audit.prompt.md` present on disk, 260 lines | PASS |
| Mirrors agent-audit structurally | 6 parallel sections: Preamble, Setup, Surface+Standards, Dimensions, Process, Verification | PASS |
| Loads r-doc-standards as rule source | §3: "Load `r-doc-standards` before evaluating any file. Every finding cites a specific rule ID." | PASS |
| Pre-scan summary (counts/time/3 options) | §5 Phase 1 step 6: area counts, dimension counts, ~2 min/finding, A/B/C options | PASS |
| 3 re-scan cycle hard cap | §1 Preamble + §5 queue re-evaluation + §6 Verification item 2 | PASS |
| Doc-index regen at start, hard stop | §2: exact message template; "Do not fall back to a stale index. This is a hard stop." | PASS |
| Remediation tasks via create_task on approval | §5 Task Emission Contract: status=backlog, tags=[docs-currency,remediation], priority=nice-to-have, one per finding, post-approval | PASS |
| Out-of-scope routing to architect | §3 + §5: not fixed inline, tagged route:architect, finding card states exact required message | PASS |
| D1–D8 with r-doc-standards rule IDs | All 8 dimensions in §4, each citing DIM-* + STR-*/PLC-*/XREF-*/AUD-* rules | PASS |
| D8 Audience Fitness | §4 D8: DIM-8, standards AUD-1 through AUD-4 | PASS |
| Skeleton scope defined | All agent-audit sections present; verification phase fully specified | PASS |
| Task emission contract body fields | Finding ID + rule citation + file path + quoted evidence; one per finding; post-approval only | PASS |
| Out-of-scope routing mechanism | route:architect tag + finding card message + no inline fix | PASS |
| Doc-index regen failure behavior | §2 exact message template matches AC; hard stop explicit | PASS |

### Test Results
- pytest: 787 passed, 6 failed (all in serve/mcp-knowledge/ — pre-existing, unrelated to task scope), 4 skipped
- ruff: clean

### Architect Quality: 4/5
Original AC had 5 notable gaps (missing D8, unspecified skeleton scope, task emission contract, routing mechanism, regen failure behavior). Architect caught and corrected all five via appended AC and challenge responses. Effective refinement — no builder improvisation needed.

### Deduction Breakdown
- AC lines without evidence: 0 (-.00)
- Lint violations: none (-.00)
- AC quality ≤ 3: no, scored 4 (-.00)
- Missing reviewer evidence: no, present and detailed (-.00)
- Full-suite failures in task scope: none (-.00)

### Confidence: 1.00
### Action: archive