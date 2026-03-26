---
id: 572
title: Add module docstring and exports to planning/__init__.py
status: archived
priority: someday
created: 2026-03-04T07:39:14.2711673+01:00
updated: 2026-03-22T19:17:47.5397487+01:00
started: 2026-03-07T04:37:17.6830918+01:00
completed: 2026-03-22T19:17:47.5397487+01:00
tags:
    - audit
    - docs
    - planning
    - type:build
depends_on:
    - 889
blocked: true
block_reason: 'Stale duplicate: planning package-root API already implemented in commit fc17a4c and fully verified under archived task #889; #572 should be board-cleanup and traceability only, not routed into builder flow again.'
class: standard
---

## Context
DOC-F-04 in docs/documentation-audit.md flagged src/owlbear/planning/__init__.py as the only empty package init in the repo. The package already exposes its usable surface across models.py, extractor.py, and markdown.py; this task is only to define the package-root API explicitly.

## Acceptance Criteria

- [ ] Update src/owlbear/planning/__init__.py so the file contains a non-empty module docstring, from __future__ import annotations, direct re-export imports, and an explicit __all__.
- [ ] Re-export ProjectDefinition and Requirement from owlbear.planning.models.
- [ ] Re-export ProjectDefinitionExtractor from owlbear.planning.extractor.
- [ ] Re-export project_definition_to_markdown from owlbear.planning.markdown.
- [ ] __all__ equals [ProjectDefinition, ProjectDefinitionExtractor, Requirement, project_definition_to_markdown].
- [ ] Do not export helper or prompt symbols such as EXTRACTION_PROMPT, _default_definition, _format_requirement, _bullet_list, or _optional_section.
- [ ] import owlbear.planning succeeds, and from owlbear.planning import ProjectDefinition, ProjectDefinitionExtractor, Requirement, project_definition_to_markdown succeeds.
- [ ] All tests added by task #889 pass.
- [ ] ruff check is clean for the touched files.

## Architecture Notes

- Follow the simple eager re-export pattern already used by src/owlbear/memory/__init__.py and src/owlbear/channels/__init__.py.
- Do not add lazy import machinery or new modules for this task.
- No behavior change beyond defining the package-root public API.

## Out of Scope

- Exporting EXTRACTION_PROMPT or any private helpers.
- Refactoring models.py, extractor.py, or markdown.py.
- Introducing lazy __getattr__ or _LAZY_IMPORTS scaffolding.

[[2026-03-21]] Sat 06:36
## Architecture Review
**Verdict:** Refine

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| docstring and public exports added | Too vague for implementation: missing the exact symbol set, package pattern, exclusion list, and TDD guard for the new package-root API | Rewrote AC, added dependency on #889, and created RED task #889 |

### Architecture Notes
- Existing small-package pattern is eager re-export plus explicit __all__, as used by src/owlbear/memory/__init__.py and src/owlbear/channels/__init__.py.
- Exact public surface for owlbear.planning is ProjectDefinition, ProjectDefinitionExtractor, Requirement, and project_definition_to_markdown only.
- Helpers and prompts stay internal; do not export EXTRACTION_PROMPT or private functions.
- No lazy-import scaffold is needed here; keep the change limited to the package init.

### Changes Made
- Claimed #572 for architecture review.
- Created RED task #889: Test planning package root exports and docstring (RED).
- Added dependency #889 to #572.
- Added planning and type:build tags to #572.
- Rewrote #572 body with precise, verifiable AC.

### Dependencies
- Added: #889, RED coverage for the package-root API.
- Verified: src/owlbear/planning/models.py, src/owlbear/planning/extractor.py, and src/owlbear/planning/markdown.py already exist and define the intended symbols.

[[2026-03-21]] Sat 15:11
## Architecture Review
**Verdict:** Block

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Update src/owlbear/planning/__init__.py so the file contains a non-empty module docstring, from __future__ import annotations, direct re-export imports, and an explicit __all__. | Already satisfied in the current tree and shipped in commit fc17a4c under task #889. | Do not route duplicate GREEN work; treat as stale tracker. |
| Re-export ProjectDefinition and Requirement from owlbear.planning.models. | Already satisfied in src/owlbear/planning/__init__.py. | Covered by archived #889 tests; no new work. |
| Re-export ProjectDefinitionExtractor from owlbear.planning.extractor. | Already satisfied in src/owlbear/planning/__init__.py. | Covered by archived #889 tests; no new work. |
| Re-export project_definition_to_markdown from owlbear.planning.markdown. | Already satisfied in src/owlbear/planning/__init__.py. | Covered by archived #889 tests; no new work. |
| __all__ equals [ProjectDefinition, ProjectDefinitionExtractor, Requirement, project_definition_to_markdown]. | Stale and ambiguous: Python package __all__ is a string-name contract, and #889 already locked the correct ordered string list. | Do not approve this outdated wording. |
| Do not export helper or prompt symbols such as EXTRACTION_PROMPT, _default_definition, _format_requirement, _bullet_list, or _optional_section. | Already enforced by #889 negative export coverage and the exact __all__ assertion. | Source of truth is the archived RED contract. |
| import owlbear.planning succeeds, and from owlbear.planning import ProjectDefinition, ProjectDefinitionExtractor, Requirement, project_definition_to_markdown succeeds. | Already satisfied and audited in #889. | No new builder work. |
| All tests added by task #889 pass. | Dependency #889 is archived with passing scoped pytest, review, docs, and audit evidence. | Dependency complete. |
| ruff check is clean for the touched files. | Archived #889 review and audit recorded scoped ruff clean on the touched files. | Dependency complete. |

### Architecture Notes
- Existing package-root pattern is eager re-export plus explicit string-based __all__, matching src/owlbear/memory/__init__.py and src/owlbear/channels/__init__.py.
- The executable contract for this public API now lives in archived RED task #889 and its audited test file tests/test_planning_package_exports.py.
- Commit fc17a4c already implemented src/owlbear/planning/__init__.py under #889, so routing #572 forward would duplicate shipped work and risk divergent requirements.
- Because this backlog card is stale and one AC line still uses outdated object-based __all__ wording, it should be cleaned up as traceability only rather than sent into builder flow again.

### Changes Made
- Claimed #572 for architecture review with task-scoped label architect-572.
- Verified src/owlbear/planning/__init__.py already matches the intended public API.
- Verified dependency #889 is archived and contains RED, GREEN, review, docs, and audit evidence for this exact scope.
- Marked #572 as a stale duplicate and returned it to ideation blocked for board cleanup instead of approving duplicate GREEN work.

### Dependencies
- Verified: #889 archived.
- Verified: commit fc17a4c implemented the planning package-root exports under #889.
- Verified: tests/test_planning_package_exports.py is the executable contract for this API surface.
