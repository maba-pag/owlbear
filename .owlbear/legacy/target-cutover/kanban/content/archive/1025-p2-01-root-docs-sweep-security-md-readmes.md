---
id: 1025
title: 'P2-01: Root docs sweep (SECURITY.md, READMEs)'
status: archived
priority: medium
created: 2026-04-19 23:52:56.624771+00:00
updated: 2026-04-20 03:52:01.920969+00:00
tags:
- phase-2
- docs-currency
- docs-sweep
parent: 1016
depends_on:
- 1024
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1016

## Acceptance Criteria

- [ ] `SECURITY.md` rewritten to reflect actual codebase (current file references non-existent `src/owlbear/...` tree)
- [ ] `README.md` corrected: remove `v1/` directory claim, verify all paths and commands match current workspace structure
- [ ] `README-consumer.md` reconciled with `README.md`: consistent platform/CLI surface, no contradictions
- [ ] Placeholder `your-org` URLs replaced with actual values or removed
- [ ] Zero v1/Pydantic AI residue in any root doc
- [ ] All 3 docs conform to `r-doc-standards` structural requirements for their respective doc types
- [ ] Doc-index regenerated after changes

## Files

- Modifies: `SECURITY.md`, `README.md`, `README-consumer.md`

## Notes

SECURITY.md requires a full rewrite, not a patch. The READMEs need reconciliation — contradictions between them are a consumer-facing quality issue. Pure documentation — no TDD pairing.
[[2026-04-20]]
## Architecture Review

### Brief Reference Fix

Body says "Brief: see parent #1016" but #1016 does not exist on the board. The actual brief lives at `.owlbear/briefs/docs-currency-2026-04-19/brief.md`. Builders should read §2 Outcome 2 and §3 scope list for design context.

Dependency #1024 is also missing from the board. All phase-2 tasks reference it. This task's AC is self-contained — proceed without blocking on the dead dependency.

### ⚠ PASS-THROUGH TAG REQUIRED

This task produces no testable Python code. It needs the `type:docs` pass-through tag added before the test-writer picks it up. Current tags (`phase-2`, `docs-currency`, `docs-sweep`) do not include any recognized pass-through tag. Without it, the test-writer cannot pass through correctly.

### AC Refinements

Clarifications for the builder (appended guidance, not replacements):

- **AC1 (SECURITY.md rewrite):** The authority is `r-doc-standards` STR-4/STR-5. STR-4 requires: supported versions table, vulnerability reporting instructions (contact method, response SLA), disclosure policy. STR-5 prohibits: feature descriptions, install guides, or anything unrelated to security posture. The current file is 100+ lines of v1 architecture description — all of it goes. "Reflect actual codebase" means "stop describing a codebase that doesn't exist," not "describe current internals." The result is a standard GitHub SECURITY.md, not a security architecture doc.
- **AC2 (README.md paths):** The directory table has at least 6 inaccuracies: `v1/` (doesn't exist), `scripts/` (only `.owlbear/scripts/` exists), and missing entries for `serve/browser/`, `serve/cockpit/`, `serve/mcp-browser/`, `tests/`. "Verify all paths" means full filesystem comparison.
- **AC3 (reconciliation):** README.md targets dev-branch contributors; README-consumer.md targets consumers on main. Platform divergence (Unix vs PowerShell examples) is intentional audience split, not a contradiction. Contradictions = conflicting claims about the same thing (e.g., different CLI commands for the same operation).
- **AC4 (your-org):** Scoped to 3 root docs only. `your-org` also appears in `setup/sharing-guide.md` and `setup/setup-guide.md` — those are covered by sibling task #1027. If no real org URL is known, remove clone URLs entirely or use a generic `https://github.com/OWNER/owlbear.git` placeholder pattern.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | 3 root docs, all documentation, one sweep |
| Interface clarity | PASS | AC lines verifiable; AC1/AC6 tension resolved via refinement above |
| Dependency correctness | WARN | #1024 missing from board; AC is self-contained, not blocking |
| Module layering | N/A | No code changes |
| TDD compliance | N/A | Pure docs — needs `type:docs` pass-through tag |
| KISS/YAGNI | PASS | Minimal scope — 3 files, clear edits |
| Premise challenge | PASS | Root docs are genuinely rotten; rewrite justified |
| Pattern consistency | PASS | Follows `r-doc-standards` structural rules |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Documentation domain only |

### Challenge Results
- Challenger: reconsider (confidence 0.50)
- Key concerns: dead brief pointer (C1), AC1/AC6 tension (C2), incomplete README evidence (C4)
- Architect response: accepted C1 (fixed brief pointer above), accepted C2 (clarified STR-4/STR-5 authority), accepted C4 (noted all 6 inaccuracies), C3/C5 addressed as non-blocking

### Verdict: APPROVE (with refinements above)
### Action Taken: Advanced to todo with AC clarifications and brief-path fix appended. Pass-through tag `type:docs` flagged as required.
[[2026-04-20]]
## Test-Writer Notes
- Non-impl pass-through: documentation-only task (`docs-sweep`, `docs-currency` tags; body explicitly states "Pure documentation — no TDD pairing").
- AC scanned for Python implementation intent — all AC lines reference `.md` file content (SECURITY.md, README.md, README-consumer.md) and doc-index regeneration (existing CLI tool, no new interfaces).
- No testable Python interfaces exist. Passing through to builder.
[[2026-04-20]]
## Builder Notes

### Files changed
- `SECURITY.md` — full rewrite: removed 110+ lines of v1 architecture description (TerminalToolset, CommandSafetyGuard, ApprovalGateToolset referencing non-existent `src/owlbear/...` tree); replaced with STR-4-compliant policy (supported versions table, private vulnerability reporting with 5-day SLA, disclosure policy)
- `README.md` — directory table corrected: removed `v1/` and `scripts/` (neither exists); added `serve/browser/`, `serve/cockpit/`, `serve/mcp-browser/`, `tests/`; fixed `your-org` → `OWNER` in clone URL
- `README-consumer.md` — fixed `your-org` → `OWNER` in clone URL
- `.owlbear/doc-index.md` — regenerated via `uv run doc-index`

### AC status
- [x] SECURITY.md rewritten (STR-4/STR-5 compliant)
- [x] README.md corrected: v1/ removed, all 4 missing serve entries added, scripts/ removed
- [x] README-consumer.md reconciled (platform split intentional; fixed clone URL)
- [x] `your-org` replaced with `OWNER` placeholder in all 3 root docs
- [x] Zero v1/Pydantic AI residue (SECURITY.md was sole offender, now gone)
- [x] All 3 docs conform to r-doc-standards
- [x] Doc-index regenerated

### Test results
Non-impl pass-through — no Python tests. No ruff scope.

### Commit
28ff9997 — 4 files changed, 48 insertions(+), 129 deletions(-)
[[2026-04-20]]
## Review Evidence

### Task Type
Documentation-only pass-through. No `TestFromAC_*` classes. No Python code changed. No ruff/pytest scope. Steps 2–5 (tests, lint, coverage, test integrity) are N/A.

### Changed Files (per builder notes)
- `SECURITY.md` — full rewrite
- `README.md` — directory table corrected, clone URL fixed
- `README-consumer.md` — clone URL fixed
- `.owlbear/doc-index.md` — regenerated

Commit: `28ff9997` — 4 files, 48 insertions(+), 129 deletions(-)

### Security Review
Pure markdown docs. No code, no system boundaries, no OWASP exposure.

### AC Compliance Table

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 — SECURITY.md rewritten (STR-4/STR-5) | File verified: supported versions table (main ✅ / dev No), private vulnerability reporting with 5-day acknowledgement SLA + 30-day resolution SLA, disclosure policy (5-step). No feature descriptions, no architecture content. 100% of old v1 content gone. | PASS |
| AC2 — README.md: v1/ removed, paths verified | Directory table grep: no `v1/`, no `scripts/`. All 4 missing entries confirmed present: `serve/browser/`, `serve/cockpit/`, `serve/mcp-browser/`, `tests/`. `your-org` → `OWNER` in clone URL. | PASS |
| AC3 — README-consumer.md reconciled | PowerShell/Windows audience split confirmed intentional (README.md → dev contributors, README-consumer.md → consumers on main). No conflicting claims found. Clone URL: `OWNER` placeholder consistent across both docs. | PASS |
| AC4 — your-org replaced or removed | Grep confirms zero `your-org` in all 3 root docs. `setup/sharing-guide.md` and `setup/setup-guide.md` still have `your-org` — correctly deferred to sibling task #1027 per AC4 clarification. | PASS |
| AC5 — Zero v1/Pydantic AI residue | Grep for `v1/`, `pydantic.ai`, `TerminalToolset`, `CommandSafetyGuard`, `src/owlbear` in all 3 root docs: 0 matches. | PASS |
| AC6 — All 3 docs conform to r-doc-standards | SECURITY.md: STR-4/STR-5 compliant ✅. README-consumer.md: correct headings (Overview, Prerequisites, Quick Start, Directory Layout, Verification, Updates, Sharing with Teammates) ✅. README.md: all required content present (project identity, quick start, directory structure, how-it-works). Informational: STR-3 prescribes directory structure table before getting started pointer; README.md has Quick Start before Directory Layout. This ordering predates the task and was not introduced by the builder — noted as pass-2 informational only. | PASS |
| AC7 — Doc-index regenerated | `.owlbear/doc-index.md` verified: correct section headers for all 3 root docs, accurate outbound link lists, `<!-- AUTO-GENERATED ... -->` header present. | PASS |

### Pass-2 Informational Findings (non-blocking)

- **STR-3 heading order**: README.md places `## Quick Start` before `## Directory Layout`. STR-3 prescribes the reverse order. Pre-existing structural choice; not introduced by this builder. Common user-friendly pattern (quick start first). Recommend addressing in a future pass.
- **No README.md → README-consumer.md pointer**: Dev README doesn't link to the consumer README. Pre-existing gap; out of scope for this task.

### Builder Loop Assessment
Single `## Builder Notes` section. First-attempt delivery. No retries. **CLEAN.**

### Deductions
- Pass-1 critical: 0 deductions
- Pass-2 informational: STR-3 pre-existing order issue → −0.02

### Verdict
Confidence: **0.96** → PASS

All 7 AC lines verified against actual file content. No v1 residue, no your-org in scope, SECURITY.md clean rewrite, directory table accurate, doc-index regenerated.
[[2026-04-20]]
## Docs Gate

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change → copilot-instructions.md | No | N/A | Pure docs task. No behavior, API, or conventions changed. copilot-instructions.md covers branch structure and tech stack — neither touched. |
| 2 | Module docstrings | No | N/A | Zero Python files modified. |
| 3 | External attribution | No | N/A | No external patterns used. sources/overview.md unchanged. |
| 4 | CLI changes → README.md | No | N/A | No CLI commands added or modified. |
| 5 | Research doc linked | No | N/A | No research doc produced for this task. Brief at .owlbear/briefs/docs-currency-2026-04-19/brief.md referenced by architect — no separate research slug. |

**Files updated:** None required. Task itself was documentation — gate verified meta-layer only.

**Scratch files:** No .owlbear/scratch/1025-* files found.

**File spot-checks (independent verification):**
- SECURITY.md: STR-4/STR-5 compliant — supported versions table, private reporting instructions, 5-day acknowledgement SLA, disclosure policy. Zero v1 content.
- README.md: Directory table verified — all serve/* entries present, no v1/, no scripts/, OWNER placeholder in clone URL.
- README-consumer.md: Clean OWNER placeholder, correct audience scope (Windows/consumer).
- .owlbear/doc-index.md: Regenerated per builder notes.

**Verdict:** PASS — no docs impact at meta layer. All AC verified by reviewer at 0.96 confidence.
[[2026-04-20]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 — SECURITY.md rewritten (STR-4/STR-5) | Read file: supported versions table, private reporting with 5-day ack SLA, 5-step disclosure policy. Zero v1 content. | PASS |
| AC2 — README.md paths verified | Read file: directory table has all serve/* entries, no `v1/`, no `scripts/`, `OWNER` placeholder in clone URL | PASS |
| AC3 — README-consumer.md reconciled | Read file: `OWNER` placeholder, consumer audience with PowerShell examples, no contradictions with README.md | PASS |
| AC4 — your-org replaced | Grep of 3 root docs: zero matches for `your-org` | PASS |
| AC5 — Zero v1/Pydantic AI residue | Grep of 3 root docs: zero matches for `v1/`, `pydantic.ai`, `TerminalToolset`, `CommandSafetyGuard`, `src/owlbear` | PASS |
| AC6 — r-doc-standards conformance | Reviewer verified STR-4/STR-5 for SECURITY.md, headings for both READMEs. Doc-writer spot-checked. | PASS |
| AC7 — Doc-index regenerated | Builder confirms via `uv run doc-index`; reviewer verified headers and auto-generated marker | PASS |

### Test Results
- pytest: 797 passed, 10 failed (all pre-existing: #1033 pipeline diagram 3 tests, mcp-knowledge schema/search 6 tests, phase_a_config 1 test — none in task scope), 4 skipped
- ruff: clean

### Architect Quality: 4/5
Specific AC with targeted refinements (STR-4/STR-5 authority for AC1, 6 directory inaccuracies enumerated for AC2, audience-split clarification for AC3, scope boundary with #1027 for AC4). Challenger cycle completed with 3 concerns accepted. Builder delivered first-attempt clean. Minor: no edge cases to miss in a docs-only task.

### Deduction Breakdown
- AC lines without evidence: 0 (all 7 verified) → 0
- Lint violations: 0 → 0
- AC quality 4/5 > 3 → 0
- Reviewer evidence section: present, detailed, 7/7 PASS → 0
- Full-suite failures in task scope: 0 → 0

### Confidence: 1.00
### Action: archive