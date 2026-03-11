---
id: 705
title: Audit global vs scoped instruction file ratio
status: archived
priority: nice-to-have
created: 2026-03-09T05:12:29.139761+01:00
updated: 2026-03-11T22:22:08.8274838+01:00
started: 2026-03-10T00:53:14.5059268+01:00
completed: 2026-03-11T22:22:08.8274838+01:00
tags:
    - phase-research
    - scope:core
    - docs
claimed_by: auditor
claimed_at: 2026-03-11T22:22:03.7411865+01:00
class: standard
---

Stripe avoids global agent rules to save context window space. Audit OwlBear's .instructions.md files to check if any global rules (applyTo: '**') could be scoped more narrowly.

AC:
- [ ] List all .instructions.md files with their applyTo patterns and a one-line rationale for each scope
- [ ] For each file with applyTo: '**', assess whether it could be narrowed without breaking agent loading (check Loading Note in agent-common.instructions.md)
- [ ] Propose scoping changes with rationale, OR document 'no changes needed' with evidence (e.g. only N files are global, each has a documented reason)
- [ ] Output: brief summary in task body (no separate research doc needed for this size)

See docs/research/stripe-minions-research.md S3c for rationale.

[[2026-03-11]] Wed 20:45
## Architecture Review
Verdict: APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| List all .instructions.md files with applyTo + rationale | Clear, verifiable enumeration | Kept |
| For each applyTo: '**', assess narrowing feasibility | Clear, references Loading Note evidence | Refined (added Loading Note pointer) |
| Propose changes OR document 'no changes needed' | Clear, explicit dual-path outcome | Refined (added no-changes-needed path) |
| Output: brief summary in task body | Appropriate for small audit scope | Added (no separate doc needed) |

### Architecture Notes
- Only 4 instruction files exist; only 1 (agent-common.instructions.md) is global
- agent-common has a documented Loading Note explaining why applyTo: '**' is required
- Audit will likely confirm no changes needed, but formalizing the assessment has value
- No code changes, no TDD needed (pure research/audit task)
- Priority nice-to-have is appropriate

### Changes Made
- Refined AC3 to include explicit 'no changes needed' outcome path
- Added AC4: output format (brief summary in task body, no separate doc)
- Moved to todo

### Dependencies
- None required; research doc (stripe-minions-research.md S3c) exists and is complete

[[2026-03-11]] Wed 21:11
## Test-Writer Notes
Non-implementation task (tagged phase-research, scope:core, docs). AC involves listing, assessing, and documenting instruction file scoping  no testable code will be produced. Architecture Review confirms: 'No code changes, no TDD needed (pure research/audit task).' Passing through to builder.

-t

[[2026-03-11]] Wed 21:40
## Builder Notes (Audit Results)

### Instruction File Inventory

| # | File | applyTo | Scope Type | Rationale |
|---|------|---------|------------|-----------|
| 1 | agent-common.instructions.md | `**` | Global | Cross-agent coordination (task claiming, handoff, inter-agent protocol). Must load regardless of file context. |
| 2 | python.instructions.md | `**/*.py` | Scoped | Python conventions (uv, type hints, ruff). Only relevant for .py files. |
| 3 | frontend.instructions.md | `src/**/ui/**,...,**/*.scss` | Scoped | Frontend/UI standards. Only relevant for UI files. |
| 4 | research-docs.instructions.md | `docs/research/*.md` | Scoped | Research document guardrails. Only relevant when writing research docs. |

### Global Scope Assessment (applyTo: '**')

Only 1 of 4 files (25%) uses global scope: agent-common.instructions.md.

Can it be narrowed? NO.

Evidence:
- Loading Note (lines 10-12) documents a previous attempt to scope to `.github/agents/**` which broke agent loading when agents worked exclusively on source files
- Content covers cross-agent coordination (task discipline, claiming, handoff, inter-agent protocol) that applies regardless of which files an agent touches
- All 3 other files are already properly scoped to their domain

### Verdict: No changes needed

The current ratio (1 global : 3 scoped) is appropriate. The single global file has a documented reason for its scope and a prior failed attempt at narrowing.

[[2026-03-11]] Wed 21:50
## Review Evidence (reviewer, 2026-03-11)

### Task Type
Pure audit/documentation  no code changes, no tests, no pytest/ruff/coverage applicable.

### Independent Verification
- Confirmed 4 instruction files exist via file_search (exact match)
- Confirmed applyTo patterns via Select-String:
  - agent-common.instructions.md: `**` (global)
  - python.instructions.md: `**/*.py` (scoped)
  - frontend.instructions.md: `src/**/ui/**,...,**/*.scss` (scoped)
  - research-docs.instructions.md: `docs/research/*.md` (scoped)
- Confirmed Loading Note at agent-common.instructions.md lines 10-12
- Confirmed no file changes: `git diff HEAD -- .github/instructions/` = empty
- Confirmed no separate research doc created (audit in task body only)

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: List all .instructions.md with applyTo + rationale | Builder table lists 4 files with correct patterns (verified via Select-String) | PASS |
| AC2: Assess global applyTo narrowing feasibility | 1/4 global identified; Loading Note (L10-12) documents prior failed narrowing attempt | PASS |
| AC3: Propose changes OR document no changes needed | `No changes needed` with evidence (1:3 ratio, documented reason, prior failed attempt) | PASS |
| AC4: Brief summary in task body | Audit written in task body under Builder Notes, no separate doc | PASS |

### Confidence: .93
### Verdict: PASS

[[2026-03-11]] Wed 21:51
## Review Evidence (reviewer, 2026-03-11)

### Task Type
Pure audit/documentation - no code changes, no tests, no pytest/ruff/coverage applicable.

### Independent Verification
- Confirmed 4 instruction files exist via file_search (exact match)
- Confirmed applyTo patterns via Select-String
- Confirmed Loading Note at agent-common.instructions.md lines 10-12
- Confirmed no file changes: git diff empty
- No separate research doc created

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: List files with applyTo + rationale | Builder table has 4 files with correct patterns (verified) | PASS |
| AC2: Assess global narrowing | 1/4 global; Loading Note L10-12 documents prior failed narrowing | PASS |
| AC3: Propose or document no changes | No changes needed with evidence (1:3 ratio, documented reason) | PASS |
| AC4: Brief summary in task body | Audit in task body under Builder Notes | PASS |

### Confidence: .93
### Verdict: PASS

[[2026-03-11]] Wed 22:00
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Pure audit confirmed status quo; no behavior/API/convention change |
| 2 | Docstrings | No | N/A | No Python modules created or modified |
| 3 | sources/overview.md | No | N/A | Stripe Minions already attributed (rows exist in overview.md) |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/stripe-minions-research.md exists and is referenced in task body |
| 6 | No impact | N/A | N/A | Items 1-4 don't apply; item 5 passes |

### Files Updated
- None

### Scratch Files Cleaned
- None found (no docs/scratch/705-* files)

[[2026-03-11]] Wed 22:22
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: List all .instructions.md with applyTo + rationale | Builder table lists 4 files with correct applyTo patterns (verified via Select-String) | PASS |
| AC2: Assess global applyTo narrowing | 1/4 global; Loading Note L10-12 documents prior failed narrowing | PASS |
| AC3: Propose changes OR document no-changes-needed | No changes needed with evidence (1:3 ratio, Loading Note, prior failed attempt) | PASS |
| AC4: Brief summary in task body | Audit in Builder Notes section, no separate doc | PASS |

### Test Results
- N/A (pure audit/documentation task, no code changes)

### Confidence: .97
### Action: archive
