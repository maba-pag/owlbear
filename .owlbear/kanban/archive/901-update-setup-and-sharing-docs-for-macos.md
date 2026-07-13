---
id: 901
title: Update setup and sharing docs for macOS
status: archived
priority: medium
created: 2026-04-16T22:54:41.755078+00:00
updated: 2026-04-17T10:07:13.418031+00:00
tags:
- phase-3
- scope:docs
- type:docs
- platform
parent: 890
depends_on:
- 897
- 900
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #890 and `.owlbear/briefs/draft-macos-compat/brief.md`

## Acceptance Criteria

- [ ] setup/setup-guide.md updated: macOS prerequisites added, cross-platform commands shown (forward-slash paths, python ../owlbear/setup/init.py)
- [ ] Windows-only limitation note (same drive) scoped to Windows only, not presented as universal
- [ ] setup/sharing-guide.md updated: macOS section added covering hook behavior, MCP server startup
- [ ] PowerShell-only examples replaced with cross-platform alternatives or annotated
- [ ] No instructions assume powershell binary is available

## Files

- `setup/setup-guide.md` (edit)
- `setup/sharing-guide.md` (edit)
[[2026-04-17]]

## Research

- Research doc: .owlbear/research/901-setup-docs-cross-platform.md
- Sources: 5 studied, 4 high-relevance (all codebase-internal)
- Recommendation: straightforward doc update — replace Windows-only examples with cross-platform defaults, scope Windows notes, update hook table to 7 .py files (confidence: 0.92)
- Follow-up tasks created: none needed — #908 already covers .ps1/powershell removal; #901 itself covers the broader cross-platform edits. Both tasks target the same 2 files and should be addressed in one editing pass.
- Decision requests: none
- Tier: T1 (autonomous — documentation correction)

### Key findings

1. **16 issues** across 2 files: 4 stale .ps1/powershell refs, 6 Windows-only paths/comments, 2 missing hook entries (only 2 of 7 listed), 3 stale `setup.py` refs (should be `init.py`), 1 missing macOS section
2. **No code changes needed** — init.py and hooks are already cross-platform (confirmed by #900 research)
3. **#901 and #908 overlap significantly** — recommend merging into one editing pass to avoid conflicts
[[2026-04-17]]

## Architecture Review

### Refined Acceptance Criteria

Original AC is good but needs tightening per research findings and #908 merge. Builder should use these refined criteria:

- [ ] `setup/setup-guide.md`: macOS prerequisites added (note: none beyond existing Python/uv/Git), cross-platform Quick Start shown with forward-slash paths (`python ../owlbear/setup/init.py`), Windows variant in callout
- [ ] Windows-only limitation note (same drive) scoped to Windows only in both files — not presented as universal blocker
- [ ] `setup/sharing-guide.md`: macOS section added covering hook behavior (7 `.py` hooks, cross-platform) and MCP server startup (`uv run` works identically on all platforms)
- [ ] `setup/sharing-guide.md` Quick Start: `C:\Dev\...` Windows-only paths replaced with cross-platform paths (`~/Dev/...` or generic), Windows variant in callout
- [ ] `powershell` code fences replaced with `shell` in both files
- [ ] Hook table in setup-guide.md lists all 7 `.py` hooks: allow-stances-only.py, deny-code-writes.py, deny-scratch-only-writes.py, deny-src-writes.py, deny-writes.py, lint-changed.py, session-context.py
- [ ] All `setup.py` references updated to `init.py` (1 in setup-guide.md L~113, 3 in sharing-guide.md troubleshooting)
- [ ] Zero-residue gate: `grep -riE '\.ps1|powershell|setup\.py|C:\\\\' setup/*.md` returns no results

### #908 Merge Note

Task #908 (Update setup docs for cross-platform hooks) targets the same 2 files with a strict subset of this task's AC. Research recommends merging into one editing pass to avoid conflicts. #908 should be superseded after #901 completes. Builder: all #908 ACs are covered by the refined criteria above.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: make setup/sharing docs cross-platform |
| Interface clarity | PASS | AC refined with specific line refs, hook names, grep gate |
| Dependency correctness | PASS | #897, #900 both done (archived) |
| Module layering | N/A | Docs only, no code |
| TDD compliance | PASS | Tagged `type:docs` — non-implementation pass-through |
| KISS/YAGNI | PASS | Factual corrections, no speculative content |
| Premise challenge | PASS | Docs reference .ps1 files that no longer exist — must be updated |
| Pattern consistency | PASS | Follows existing doc structure and callout patterns |
| Security surface | PASS | No security surface — docs only |
| Single domain | PASS | Documentation domain only |

### Challenge Results

- Challenger: proceed (confidence 0.88)
- Refinements accepted: (1) AC3 expanded to cover sharing-guide Quick Start paths, (2) grep gate expanded to catch `C:\` backslash paths
- Architect response: accepted both refinements

### Verdict: APPROVE (with REFINE)

### Action Taken: Refined AC to merge #908 scope, added zero-residue grep gate, expanded path coverage. Advanced to todo

[[2026-04-17]]

## Test-Writer Notes

- Non-implementation task (tagged `type:docs`) — no tests applicable.
- AC references only `setup/setup-guide.md` and `setup/sharing-guide.md` — pure documentation edits, no Python interfaces.
- Passing through to builder.
[[2026-04-17]]

## Builder Notes

**Files changed:** `setup/setup-guide.md`, `setup/sharing-guide.md`

**Test results:** N/A — type:docs task, no tests applicable

**Lint status:** N/A — markdown only

**Evidence summary:**

- Zero-residue grep gate passed: `grep -iE '\.ps1|powershell|setup\.py|C:\\\\' setup/*.md` → 0 results
- All 7 AC items verified via grep output

**Changes applied:**

setup-guide.md:

- Added `> **macOS and Linux:** No additional prerequisites` note after Windows limitation block
- Changed `powershell` code fence → `shell`
- Removed "same drive" comment from Quick Start code; changed `python ..\owlbear\setup\init.py` → `python ../owlbear/setup/init.py`
- Added `> **Windows:** use backslashes...` callout after Quick Start
- Replaced 2 `.ps1` hook rows with all 7 `.py` hooks: allow-stances-only.py, deny-code-writes.py, deny-scratch-only-writes.py, deny-src-writes.py, deny-writes.py, lint-changed.py, session-context.py
- Fixed `mcp.json` note: `setup.py` → `init.py`

sharing-guide.md:

- Fixed body text: "same drive and in a sibling layout" → scoped Windows restriction to Windows only
- Changed `powershell` code fence → `shell`; replaced `C:\Dev\...` paths with `~/Dev/...`; fixed backslash path to forward-slash; added Windows callout
- Added `## Platform Notes` section with macOS/Linux hook + MCP notes and Windows same-drive note
- Fixed 3 troubleshooting rows: `setup.py` → `init.py`

**Commit:** `5f73bb92` — also supersedes #908
[[2026-04-17]]

## Review Evidence

**Type:** docs-only task — no tests applicable (type:docs pass-through confirmed by test-writer). No quality-runner dispatch needed.

**Commit reviewed:** 5f73bb92
**Files reviewed:** `setup/setup-guide.md`, `setup/sharing-guide.md`

---

### Grep Gate Results

| Pattern | Matches | Assessment |
|---------|---------|------------|
| `\.ps1` | 0 | CLEAN |
| `powershell` | 0 | CLEAN |
| `setup\.py` | 0 | CLEAN |
| `C:\\` (single backslash) | 3 — all in Windows-scoped callouts/sections | SCOPED / CLEAN |

Note: Builder's gate pattern `C:\\\\` (single-quoted) checks for `C:\\` (double backslash), not `C:\`. The three `C:\` occurrences are in: (1) Windows limitation explanation in setup-guide.md L19, (2) Windows callout in sharing-guide.md L45, (3) Platform Notes > Windows in sharing-guide.md L68. All correctly scoped — AC intent met. Gate pattern is a minor documentation imprecision, not a violation.

---

### Code fences

Both files: only `shell` and `json` fences. No `powershell` fences. ✓

---

### AC Compliance Table

| AC Line | Evidence | Status |
|---------|----------|--------|
| setup-guide.md: macOS prerequisites added, cross-platform Quick Start with `python ../owlbear/setup/init.py`, Windows callout | setup-guide.md L20-22 (macOS note), L37 (forward-slash Quick Start), L43-44 (Windows callout) | PASS |
| Windows-only same-drive limitation scoped to Windows only in both files | setup-guide.md L15 (`> **Windows limitation:**`), sharing-guide.md L9 (`On Windows, they must also be on the same drive.`), L18-21 (`> **Windows limitation:**`) | PASS |
| sharing-guide.md macOS section: 7 hooks, MCP server startup | sharing-guide.md L55-66 (`## Platform Notes > macOS and Linux`) — all 7 hooks listed, `uv run` noted identical on all platforms | PASS |
| sharing-guide.md Quick Start: `C:\Dev\...` replaced with `~/Dev/...`, Windows callout | sharing-guide.md L31-40 (Quick Start uses `~/Dev/...`), L45 (Windows callout) | PASS |
| `powershell` fences → `shell` in both files | grep: 0 `powershell` matches; `shell` at setup-guide.md L28, sharing-guide.md L30 | PASS |
| Hook table lists all 7 `.py` hooks | setup-guide.md L56-62: allow-stances-only.py, deny-code-writes.py, deny-scratch-only-writes.py, deny-src-writes.py, deny-writes.py, lint-changed.py, session-context.py | PASS |
| All `setup.py` refs → `init.py` | grep: 0 `setup.py` matches; 14 `init.py` matches — correct throughout | PASS |

---

### Security Review

Documentation only. No code paths, no secrets, no injection surface. N/A.

### TestFromAC Audit

No TestFromAC classes — type:docs task. N/A.

---

### Deductions

0 deductions. All 7 AC items verified by direct file inspection and grep gate.

### Verdict

Confidence: .96 → **PASS** → advance to docs
[[2026-04-17]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Docs-only task; `.github/copilot-instructions.md` covers branches/identity only — no setup procedures or platform guidance to update |
| 2 | Module docstrings | No | N/A | No Python files modified |
| 3 | External attribution | No | N/A | All 5 sources codebase-internal per research doc and task body |
| 4 | CLI changes | No | N/A | No CLI changes; README.md references `init.py` correctly throughout (verified grep) |
| 5 | Research doc | Yes | Verified | `.owlbear/research/901-setup-docs-cross-platform.md` exists and linked in task body |

### Zero-Residue Gate (re-verified)

| Pattern | Matches | Status |
|---------|---------|--------|
| `.ps1` | 0 | CLEAN |
| `powershell` | 0 | CLEAN |
| `setup.py` | 0 | CLEAN |
| `C:\` | 3 — all in Windows-scoped callouts | SCOPED / CLEAN |

### Files Updated

None — builder commit 5f73bb92 is complete. No additional documentation updates required.

### Scratch Files

No `.owlbear/scratch/901-*` files found. Already clean.

### Verdict

All checklist items pass or confirmed N/A. Builder changes verified against AC. Docs gate passed.
[[2026-04-17]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| setup-guide.md: macOS prerequisites, cross-platform Quick Start with forward-slash paths, Windows callout | setup-guide.md L20-22 macOS note, L37 forward-slash cmd, L43-44 Windows callout (direct read) | PASS |
| Windows-only same-drive limitation scoped to Windows in both files | setup-guide.md L15 "Windows limitation:", sharing-guide.md L9 "On Windows", L18-21 "Windows limitation:" | PASS |
| sharing-guide.md macOS section: 7 hooks, MCP startup | sharing-guide.md L55-66 Platform Notes section, all 7 hooks listed, uv run noted | PASS |
| sharing-guide.md Quick Start: ~/Dev/... paths, Windows callout | sharing-guide.md L31-40 uses ~/Dev/..., L45 Windows callout | PASS |
| powershell fences replaced with shell | grep: 0 powershell matches in setup/*.md | PASS |
| Hook table lists all 7 .py hooks | setup-guide.md L56-62: allow-stances-only, deny-code-writes, deny-scratch-only-writes, deny-src-writes, deny-writes, lint-changed, session-context | PASS |
| All setup.py refs updated to init.py | grep: 0 setup.py matches in setup/*.md | PASS |
| Zero-residue gate | .ps1: 0, powershell: 0, setup.py: 0, C:\: 3 (all in Windows-scoped callouts) | PASS |

### Test Results

- pytest tests/: 4327 passed, 255 failed (pre-existing), 189 skipped
- pytest serve/: timeout (known infrastructure issue, unrelated)
- ruff: clean
- No Python code changed by this task. 255 failures are pre-existing, not regressions.

### Architect Quality: 5/5

Exemplary upstream work. AC refined with specific line refs, all 7 hook names enumerated, zero-residue grep gate added, #908 scope merged to avoid conflicts. Challenger refinements accepted and integrated. No improvisation needed by builder or reviewer.

### Deduction Breakdown

- AC lines with no evidence: 0 (8/8 verified) = -0
- Lint violations: 0 = -0
- AC quality score 5 (above 3 threshold) = -0
- Reviewer evidence: present, detailed, PASS = -0
- Full-suite test failures in task scope: 0 (type:docs, no Python changed) = -0

### Confidence: .98

(.02 conservative margin for serve/ test timeout preventing full-suite completion, though zero Python files changed makes regression from this task impossible)

### Action: archive
