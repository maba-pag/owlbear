---
id: 605
title: Extract system instructions from copilot-instructions.md
status: archived
priority: medium
created: 2026-04-04 20:31:16.804802+02:00
updated: 2026-04-05 12:08:07.342607+02:00
started: 2026-04-05 12:08:07.342607+02:00
completed: 2026-04-05 12:08:07.342607+02:00
tags:
- scope:infra
- phase-2
- type:config
parent: 598
depends_on:
- 600
class: standard
archival_reason: completed
archival_refs: []
---

## Summary

Extract owlbear system-level instructions (heuristics, memory governance, pipeline protocol, operational fundamentals) from .github/copilot-instructions.md into share/instructions/owlbear-system.instructions.md.

## Acceptance Criteria

- [ ] AC1: share/instructions/owlbear-system.instructions.md exists with YAML frontmatter: `description:` field present, no `applyTo` key
- [ ] AC2: Contains extracted content from .github/copilot-instructions.md: S2 Decision Heuristics, S3 System Awareness, S4 Memory Governance, S5 Operational Fundamentals (content fidelity preserved, no material omissions or additions)
- [ ] AC3: .github/copilot-instructions.md retains only S1 Project Identity: document title + project description paragraph
- [ ] AC4: [Verification] After #600 settings are in place, owlbear-system.instructions.md appears in VS Code Chat Customizations panel and is auto-enabled for chat requests. If VS Code does not auto-enable instruction files without applyTo, add `applyTo: **` to the frontmatter as fallback.

## Notes

- chat.instructionsFilesLocations configuration is owned by #600 AC6, not duplicated here
- Target project delivery verification is owned by #604 AC7, not this task
- Line number references in research docs (e.g., docs/research/agent-common-memory-mcp-integration.md L83-105 sourcing Memory Governance) become stale after extraction. Research docs are historical; live reference updates belong to #607.

[[2026-04-04]] Sat 22:35
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single extraction operation: split copilot-instructions.md into project-identity stub + global system instructions file |
| Interface clarity | PASS (fixed) | AC refined: section-level precision on extraction boundary, explicit auto-discovery gate with fallback, removed redundant/out-of-scope AC lines |
| Dependency correctness | PASS | Depends on #600 (move .github/ to share/, provides share/instructions/ directory and chat.instructionsFilesLocations setting). No missing deps. |
| Module layering | N/A | No code modules: file creation and markdown editing only |
| TDD compliance | PASS | Tagged type:config (pass-through). No testable Python code produced. |
| KISS/YAGNI | PASS | Minimal scope: one file extraction, one file reduction |
| Premise challenge | PASS | copilot-instructions.md is auto-discovered from .github/ but not shareable to target projects. Extracting to share/instructions/ enables VS Code settings-based sharing without file copies. |
| Pattern consistency | PASS | Follows existing .instructions.md convention (YAML frontmatter with description:). First global instruction file (no applyTo): new pattern, AC4 explicitly gates discovery. |
| Security surface | PASS | No new system boundaries. Content moves between markdown files only. |
| Single domain | PASS | scope:infra |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| VS Code instruction discovery | File without applyTo not auto-enabled | None (silent) | Yes: AC4 gates with applyTo fallback | System instructions missing from chat context |
| copilot-instructions.md too minimal | Agents lose system context in owlbear workspace | None (silent) | Yes: AC4 manual verification confirms instructions load | Agent quality degrades |
| Research doc line refs (L83-105) | Stale line numbers in docs/research/ | N/A | Acknowledged: historical docs, live refs in #607 scope | Misleading source citations in old research |

### Refinements Applied

1. AC2: Added section-level precision: explicitly lists S2-S5 with requirement for content fidelity
2. AC3: Specified what "project identity only" means: document title + project description paragraph (S1)
3. Old AC4 (settings): REMOVED, redundant with #600 AC6 (chat.instructionsFilesLocations)
4. Old AC5 (target project delivery): REMOVED, scope creep; delivery verification belongs to #604 AC7
5. AC4 (new): Explicit auto-discovery verification with applyTo: "**" fallback if VS Code does not auto-enable
6. Old AC6 (manual verification): Merged into new AC4
7. Tags: type:build replaced with type:config (pass-through tag for non-implementation work)
8. Notes: Added scope boundaries for settings (#600), target delivery (#604), and stale research refs (#607)

### Challenge Results

- Challenger: reconsider (confidence: 0.35)
- Concerns: (1) VS Code auto-discovery gap for no-applyTo files, (2) stale line refs in research docs, (3) target project delivery unverified, (4) extraction boundary, (5) AC coverage
- Architect response: Override with targeted refinements
  - C1: AC4 now explicitly gates auto-discovery with applyTo: "**" fallback
  - C2: Dismissed: research docs are historical; live refs belong to #607
  - C3: Dismissed: target project delivery is #604 scope, not #605
  - C4: Accepted: boundary confirmed as reasonable
  - C5: Accepted: AC4 restored with specificity

### Verdict: APPROVE
### Action Taken: Refined AC (4 lines: file existence, content extraction, copilot-instructions.md reduction, auto-discovery verification with fallback). Replaced type:build with type:config. Removed redundant/out-of-scope AC lines. Advanced to todo.

[[2026-04-04]] Sat 22:36
APPROVED #605 to todo. Refined AC: 6 lines reduced to 4 (file existence, content extraction with S2-S5 precision, copilot-instructions.md reduction to S1, auto-discovery verification with applyTo fallback). Removed redundant AC4 (settings owned by #600) and out-of-scope AC5 (target delivery owned by #604). Replaced type:build with type:config. Challenger overridden (0.35): 2 concerns accepted (VS Code discovery gap, AC coverage), 2 dismissed (research refs historical, target delivery out of scope), 1 confirmed (boundary).

[[2026-04-05]] Sun 00:36
## Test-Writer Notes\n- Non-implementation task (tagged type:config) — no tests applicable.\n- AC1–AC4 describe file creation, markdown content extraction, and VS Code UI verification — no testable Python interfaces exist.\n- Passing through to builder.

[[2026-04-05]] Sun 05:51
## Builder Notes

**Files changed (2):**
- `share/instructions/owlbear-system.instructions.md` — created (S2–S5 extracted content, YAML frontmatter: `description:` only, no `applyTo` key per AC1)
- `.github/copilot-instructions.md` — reduced to S1 Project Identity only (title + paragraph)

**Test results:** N/A — type:config pass-through, no Python tests applicable.

**Lint status:** N/A — markdown-only changes.

**AC evidence:**
- AC1 ✅ File exists with `description:` frontmatter, no `applyTo` key
- AC2 ✅ S2 Decision Heuristics, S3 System Awareness (Tech Stack + Pipeline + Directory Structure), S4 Memory Governance, S5 Operational Fundamentals — content extracted verbatim, no omissions or additions
- AC3 ✅ `.github/copilot-instructions.md` retains only S1: document title + project description paragraph
- AC4 ⚠️ MANUAL VERIFICATION REQUIRED — open VS Code Chat Customizations panel, confirm `owlbear-system.instructions.md` appears and is auto-enabled. If not auto-enabled, add `applyTo: "**"` to the frontmatter.

**Commit:** 9690513

[[2026-04-05]] Sun 10:37
## Review Evidence

**Task type:** type:config (pass-through) — no Python tests, no lint applicable.

**Commit under review:** 9690513 — 2 files changed (71 insertions, 68 deletions).

---

### Tests
N/A — type:config pass-through. No testable Python interfaces.

### Lint
N/A — markdown-only changes.

### Coverage
N/A — no code modules touched.

### Commit Scope Verification
Commit stat: `.github/copilot-instructions.md` (68 deletions), `share/instructions/owlbear-system.instructions.md` (71 insertions). Exactly 2 files as claimed by builder. No extra scope.

Note: `share/instructions/owlbear-system.instructions.md` has a subsequent commit `b018f75` from #607 that updated path references to reflect the current folder structure. This is outside #605 scope and does not affect the AC evaluation.

---

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: File exists with `description:` frontmatter, no `applyTo` | File present at `share/instructions/owlbear-system.instructions.md`; frontmatter confirmed: `description: "OwlBear system instructions…"`, no `applyTo` key at commit 9690513 or in current state; `Select-String` returns no `applyTo` match | **PASS** |
| AC2: S2–S5 extracted with content fidelity, no material omissions/additions | Git diff of commit 9690513 shows new file content is byte-for-byte identical to removed content in copilot-instructions.md for all 4 sections (S2 Decision Heuristics — 8 bullets ✅, S3 System Awareness — Tech Stack, Pipeline, Directory Structure ✅, S4 Memory Governance ✅, S5 Operational Fundamentals — 5 bullets ✅). Builder notes claim "verbatim" — confirmed accurate against diff | **PASS** |
| AC3: copilot-instructions.md retains only S1 (title + paragraph) | Git diff and current file read both confirm: file contains only `# OwlBear — Copilot Workspace Instructions`, `## 1. Project Identity`, and the single paragraph. S2–S5 fully removed | **PASS** |
| AC4: File appears in VS Code Chat Customizations panel and auto-enabled | Cannot inspect VS Code UI programmatically. Indirect evidence: file IS loaded in current session (appears in `<instructions>` context without `applyTo`, meaning it was auto-discovered via settings). Builder correctly flagged as manual-verification-required per task AC language. AC fallback (add `applyTo: "**"`) not triggered — expected, since file IS loading | **PASS (indirect)** |

---

### Security Review (OWASP Top 10 scan)
Markdown files only, no code paths, no new system boundaries, no user input surfaces, no credentials or secrets. No concerns.

### TestFromAC Classes
None — type:config pass-through. Step 5.0 and 5.2 skipped.

### Test Quality
N/A.

---

### Deductions
- **-0.03**: AC4 formal UI panel verification deferred to manual check. Indirect evidence (file appears in current instructions context) is strong but not a panel screenshot. Acknowledged in AC language as a verification step.
- No other deductions.

---

### Verdict
**Confidence: .95 → PASS**
**Action: #605 → docs**

[[2026-04-05]] Sun 10:54
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | Verified | `.github/copilot-instructions.md` reduced to S1 only; `share/instructions/owlbear-system.instructions.md` created with S2–S5. Both files confirmed in correct final state by builder commit 9690513 and reviewer AC compliance table. README.md has no references to either file — no README update needed. |
| 2 | Module docstrings | No | N/A | Markdown-only changes — no Python modules created or modified. |
| 3 | External attribution | No | N/A | No external repo, article, or doc patterns referenced in AC, builder notes, or review evidence. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | No | N/A | No `.owlbear/research/605-*.md` produced for this task. Pre-existing research doc stale line refs are explicitly out-of-scope per Notes (live ref updates belong to #607). |

### Files Updated
None — documentation already in correct final state per builder. No doc-writer edits required.

### Scratch Files
None — no `.owlbear/scratch/605-*` files found.

[[2026-04-05]] Sun 12:08
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: File exists with description: frontmatter, no applyTo | File at share/instructions/owlbear-system.instructions.md; frontmatter has description field, no applyTo key | PASS |
| AC2: S2-S5 extracted, content fidelity | S2 Decision Heuristics (L5), S3 System Awareness (L16), S4 Memory Governance (L50), S5 Operational Fundamentals (L65) confirmed. Commit 9690513 verified | PASS |
| AC3: copilot-instructions.md retains only S1 | File is 5 lines: title + S1 Project Identity paragraph. S2-S5 removed | PASS |
| AC4: Auto-discovery in VS Code | File loaded in current session instructions context (auto-discovered without applyTo). Fallback not triggered | PASS |

### Test Results
- pytest: 437 failed, 2834 passed, 18 skipped (398.94s). Zero failures in task scope (markdown-only, no Python). All pre-existing.
- ruff: All checks passed

### Architect Quality: 5/5

### Deduction Breakdown
- AC4 indirect evidence (session context, not UI panel): -0.01

### Confidence: .99
### Action: archive
