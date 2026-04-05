---
id: 813
title: Add re-exports to auth, planning, projects, providers, safety __init__.py
status: archived
priority: nice-to-have
created: 2026-03-15T05:11:26.8550756+01:00
updated: 2026-03-16T14:34:19.1769091+01:00
started: 2026-03-15T11:24:09.5007049+01:00
completed: 2026-03-16T14:34:14.5493297+01:00
tags:
    - architecture
    - scope:core
class: standard
---

Add eager re-exports with __all__ to 5 core packages. See docs/research/init-re-exports.md section 3.2 for per-package export list. Pattern: match core/__init__.py (from .mod import X + __all__).

## AC
- [ ] auth/__init__.py re-exports 7 public functions from copilot.py
- [ ] planning/__init__.py re-exports ProjectDefinition, Requirement, ProjectDefinitionExtractor, project_definition_to_markdown
- [ ] projects/__init__.py re-exports Project, ProjectStore, ProjectToolset, ProjectWorkspace
- [ ] providers/__init__.py re-exports create_copilot_client, create_copilot_model, get_premium_requests
- [ ] safety/__init__.py re-exports ApprovalGateToolset, ApprovalPolicy, ApprovalRule, ApprovalSession
- [ ] Each file has __all__ tuple
- [ ] Ruff clean, all tests pass
- [ ] No circular import issues (test with python -c 'import owlbear.{pkg}')

[[2026-03-15]] Sun 05:44
## Research
Validation of parent research (docs/research/init-re-exports.md).
All 22 exports confirmed in source. Zero circular import risk.
Import order: safety: policy before gate; planning: models before extractor before markdown.
See docs/research/core-pkg-re-exports.md for full validation.

[[2026-03-15]] Sun 06:00
## Architecture Review
**Verdict:** BLOCK

### Contradictory Research
Two research docs for parent #549 give opposite recommendations:
1. init-reexports.md (2026-03-07, .85): DO NOT add. 0/66 consumers use existing re-exports.
2. init-re-exports.md (2026-03-15, .90): ADD. Does not address first doc evidence.

### Empirical Evidence (architect-verified)
- from owlbear.core import in src/: 0 matches
- from owlbear.{auth..safety} import: 0 matches
- All 20+ consumers use deep imports

### Board Contradiction
- #812 (ideation): Remove unused re-exports from core
- #813 (backlog): Add re-exports to 5 more packages

### YAGNI/KISS/DRY
- Zero demand for short-path imports
- 22 exports + __all__ adds maintenance cost with no benefit
- Second import path complicates refactoring

### Resolution
Decision request needed: should OwlBear add re-exports despite zero demand?

[[2026-03-15]] Sun 09:43
## Research (2026-03-15, researcher)
Doc: docs/research/re-export-contradiction.md

Findings:
- 3 independent checks confirm 0/26+ consumers use package-level imports
- init-re-exports.md (.90 ADD) assumed demand without checking; init-reexports.md (.85 REMOVE) verified empirically
- KISS/YAGNI/DRY all favor deep imports for an application codebase
- Recommendation: .90 confidence do NOT add (Option A in decision request)

Decision request: docs/decisions/pending/813-re-export-feature-gate.md
Related tasks: #812 (remove existing), #822 (implement removal), #823 (close #813)

[[2026-03-15]] Sun 11:23
## Research (2026-03-15, researcher  PydanticAI compat validation)
Doc: docs/research/pydanticai-re-export-compat.md

User decision note: validate PydanticAI compatibility before proceeding.

Findings (.95 confidence):
- PydanticAI tool discovery is 100% explicit (toolsets=[], @agent.tool, add_function)
- AbstractToolset has no __init_subclass__ registry, no pkgutil scanning
- PydanticAI never imports from owlbear.*  relationship is one-directional
- Standalone daemon already works with deep imports
- Decision A (no re-exports) is fully PydanticAI-compatible

No new tasks needed. #822 and #823 can proceed unblocked.

[[2026-03-15]] Sun 13:59
## Research Summary (final, 2026-03-15, researcher)
All research rounds complete. 7 docs produced. Decision resolved (Option A: don't add, remove existing). PydanticAI compat validated (.95). Follow-up tasks #822 (implement removal) and #823 (close #813) at ideation. No further research needed  task is ready for #823 to close formally.

[[2026-03-16]] Mon 12:32
## Research (2026-03-16, researcher -- final closure)
Decision resolved: Option A (don't add re-exports). All research complete. 5 independent research rounds, 7 docs produced, empirical evidence confirmed 0 consumers use package-level imports. Moving to done as won't-do.

[[2026-03-16]] Mon 14:34
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| auth/__init__.py re-exports | Won't-do: intentionally not implemented per approved decision A | PASS (won't-do) |
| planning/__init__.py re-exports | Won't-do: intentionally not implemented | PASS (won't-do) |
| projects/__init__.py re-exports | Won't-do: intentionally not implemented | PASS (won't-do) |
| providers/__init__.py re-exports | Won't-do: intentionally not implemented | PASS (won't-do) |
| safety/__init__.py re-exports | Won't-do: intentionally not implemented | PASS (won't-do) |
| Each file has __all__ | Won't-do: not needed | PASS (won't-do) |
| Ruff clean, tests pass | No code changes; not applicable | PASS |
| No circular imports | No imports added; not applicable | PASS |

### Won't-Do Verification
| Check | Evidence | Status |
|-------|----------|--------|
| Decision request exists | docs/decisions/resolved/813-re-export-feature-gate.md | PASS |
| Decision approved | approved: true, Option A -- do not add re-exports | PASS |
| 5 __init__.py files unchanged | auth/planning/projects/providers/safety: no re-exports added, read-verified | PASS |
| Follow-up tasks created | #822 (remove existing core re-exports, ideation) and #823 (close #813, todo) | PASS |

### Test Results
- pytest: not run -- no code changes made
- ruff: not applicable -- no source files modified

### Quality Gaps
- Researcher did not commit research deliverables; fixed by auditor (commit c5f8026)

### Confidence: .95
### Action: archive

## Commits
| Commit | Type | Files | Task |
|--------|------|-------|------|
| c5f8026 | docs | 4 research/decision docs | #813 |
