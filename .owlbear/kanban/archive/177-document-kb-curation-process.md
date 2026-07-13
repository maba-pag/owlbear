---
id: 177
title: Document KB curation process
status: archived
priority: medium
created: 2026-03-29 19:50:54.093837+02:00
updated: 2026-03-30 05:06:44.238957+02:00
started: 2026-03-30 05:06:09.693558+02:00
completed: 2026-03-30 05:06:09.693558+02:00
tags:
- phase-2
- scope:knowledge
- type:docs
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Write curation process documentation for adding, updating, and removing knowledge sources.

## Acceptance Criteria
- [ ] docs/research/ or skills/ doc covering: how to add a new source, how to refresh existing sources, how to remove stale content
- [ ] Describes sources.yaml manifest format
- [ ] Describes the delta detection workflow (StatusStore content hashing)
- [ ] Covers scope assignment conventions (global vs project vs agent)
- [ ] Includes examples for adding internal docs and external URLs

## Context
Split from #24 AC item 'Document the curation process for adding new sources'. See docs/research/general-kb-initial-data-load.md.

[[2026-03-29]] Sun 20:22
## Research
Research doc: docs/research/kb-curation-process.md
Covers all 5 AC items: add/refresh/remove workflow, sources.yaml format, delta detection (StatusStore), scope conventions (global/project/agent), worked examples.
Follow-up task created: #183 (cross-reference in knowledge-ops skill).
All infrastructure primitives already exist in packages/knowledge/. Loader script is tracked by #176.

[[2026-03-29]] Sun 20:36
## Architecture Review
**Verdict:** Approve

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| docs/research/ or skills/ doc covering add/refresh/remove | Clear, verifiable â€” check doc exists with sections | None |
| Describes sources.yaml manifest format | Clear â€” check manifest format section present | None |
| Describes delta detection workflow (StatusStore) | Clear â€” check StatusStore section present | None |
| Covers scope assignment conventions | Clear â€” check scope conventions section present | None |
| Includes examples for internal docs and external URLs | Clear â€” check worked YAML examples present | None |

### Architecture Notes
Pure documentation task â€” no code changes, no module layering concerns, no security surface. The research doc (docs/research/kb-curation-process.md) already covers all 5 AC items comprehensively. The writer gate verifies doc quality and completeness.

All referenced infrastructure exists: StatusStore (status_store.py), KnowledgeSourceStore (source_store.py), KnowledgeSource model (models.py). The manifest format documented aligns with the SourceType enum and KnowledgeSource model fields.

No TDD needed â€” type:docs task. Follow-up #183 (cross-reference in knowledge-ops skill) already created at ideation.

Risk: #176 (loader script) may evolve the manifest format â€” acceptable, docs can be updated.

### Changes Made
- Approved to todo

### Dependencies
- No formal depends_on â€” correct for a docs task
- Related: #176 (loader script, ideation), #183 (cross-reference, ideation)

[[2026-03-29]] Sun 21:01
## Test-Writer Notes
- Non-implementation task (tagged type:docs) -- no tests applicable.
- Passing through to builder.

[[2026-03-29]] Sun 22:03
## Builder Notes
- Non-implementation task (type:docs) - no code changes needed.
- docs/research/kb-curation-process.md verified: exists, covers all 5 AC items (add/refresh/remove, sources.yaml format, StatusStore delta detection, scope conventions, worked examples).
- Passing through to review.

[[2026-03-29]] Sun 23:31
## Review Evidence

**Reviewer:** reviewer | **Date:** 2026-03-29

### Deliverable
docs/research/kb-curation-process.md -- exists, read in full.
No code changes (type:docs task). No pytest or ruff applicable.

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| doc covering add/refresh/remove | Doc exists. Add: Step 1 (register source). Refresh: Steps 2-5 (delta check, ingest, track). Remove: Step 6 claims delete + cascade -- see finding below. | PARTIAL |
| Describes sources.yaml manifest format | Section 3.3 has complete YAML example. Fields verified against KnowledgeSource model (models.py). | PASS |
| Describes delta detection (StatusStore) | Section 3.5 accurately describes check_content_changed(source, content, scope), SHA-256 of stripped content, 3-branch logic. Verified against status_store.py lines 115-131. | PASS |
| Covers scope assignment conventions | Section 3.4 covers global/project:{name}/agent:{name} -- consistent with models.py scope field default. | PASS |
| Includes examples for internal docs and external URLs | Section 3.3 YAML: file_glob for docs/research/*.md (internal), url_list for PydanticAI URLs (external). | PASS |

### Critical Finding -- Documentation Inaccuracy

Section 3.2 Step 6 states removal is 'KnowledgeSourceStore.delete() + cascade'. This is factually incorrect.

1. source_store.py delete() (lines 143-150): bare DELETE FROM knowledge_sources. No cleanup of related tables.
2. schema.py knowledge_sources (lines 100-114): no FOREIGN KEY, no ON DELETE CASCADE.
3. grep CASCADE in packages/knowledge/src/: 1 match in graph_store.py (entity edges only -- unrelated).
4. document_status tracks by source URI -- no FK to knowledge_sources.id.

Result: Deleting a source orphans document_status records. Documentation misleads users into believing full cleanup occurs.

AC Item 1 (remove stale content) is not accurately documented.

### Verdict: FAIL (confidence .93)

Builder must correct Step 6 to accurately describe actual removal behavior: source record deleted only, document_status and related records are orphaned (no cascade exists at application or schema level).

[[2026-03-29]] Sun 23:57
## Test-Writer Notes (retry)
- Retry reason: reviewer FAIL was about documentation inaccuracy (Step 6 incorrectly states cascade deletion), not missing tests.
- Existing pass-through preserved. Builder will correct inaccurate removal docs.

[[2026-03-30]] Mon 03:19
## Builder Notes (retry)
- Files changed: docs/research/kb-curation-process.md
- Fix: Corrected Step 6 in Section 3.2 curation workflow table.
- Old text: 'KnowledgeSourceStore.delete() + cascade -- Clean up decommissioned sources'
- Verified against source_store.py delete() (lines 143-150): bare DELETE FROM knowledge_sources, no cascade.
- Verified against schema.py: no FOREIGN KEY / ON DELETE CASCADE on knowledge_sources.
- New text: documents bare delete only, explains orphaning of document_status rows, advises manual cleanup steps.
- No pytest/ruff applicable (type:docs task). No code changes.

-t

[[2026-03-30]] Mon 03:19
## Builder Notes (retry)
- Files changed: docs/research/kb-curation-process.md
- Fix: Corrected Step 6 in Section 3.2 curation workflow table
- Old: 'KnowledgeSourceStore.delete() + cascade -- Clean up decommissioned sources'
- Verified source_store.py delete() (lines 143-150): bare DELETE FROM knowledge_sources, no cascade
- Verified schema.py: no FOREIGN KEY or ON DELETE CASCADE on knowledge_sources
- New text: documents bare delete, explains document_status orphaning, advises manual cleanup
- No code changes; type:docs task, no pytest/ruff applicable

## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | type:docs task, no behavior/API change |
| 2 | Docstrings | No | N/A | No Python modules changed |
| 3 | docs/sources/overview.md | Yes | Pass | LlamaIndex entry at line 317 (already logged by researcher). LangChain RecordManager already logged at line 1877 under content-hashing task. |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/kb-curation-process.md verified: exists, covers all 5 AC items. Follow-up task #183 created. |

### AC Verification
All 5 AC items verified against docs/research/kb-curation-process.md:
- Add/refresh/remove workflow: Section 3.2 (6-step process, Step 6 corrected per builder retry)
- sources.yaml manifest format: Section 3.3 (complete YAML examples)
- Delta detection (StatusStore): Section 3.5 (SHA-256, 3-branch logic)
- Scope assignment conventions: Section 3.4 (global/project/agent table)
- Examples for internal docs and external URLs: Section 3.3 (file_glob + url_list examples)

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/177-* files found)

[[2026-03-30]] Mon 05:06
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| doc covering add/refresh/remove | docs/research/kb-curation-process.md S3.2: 6-step process table, Step 6 corrected per reviewer finding | PASS |
| Describes sources.yaml manifest format | S3.3: complete YAML example with file_glob + url_list types, field mapping to KnowledgeSource model | PASS |
| Describes delta detection (StatusStore) | S3.5: SHA-256 of stripped content, 3-branch logic, verified against status_store.py | PASS |
| Covers scope assignment conventions | S3.4: global/project/agent table with defaults and query resolution | PASS |
| Includes examples for internal docs and external URLs | S3.3: file_glob pattern for docs/research/*.md (internal), url_list for PydanticAI URLs (external) | PASS |

### Test Results
- pytest (full suite): 0 passed, 4 collection errors (all ModuleNotFoundError for unimplemented modules: owlbear.planner, owlbear.voice.process, owlbear_mcp_project.tree -- none related to #177)
- ruff: 2 violations in tests/test_necessity_check_196.py (PT018, unrelated to #177)

### Quality Gaps
- Deliverable not committed by upstream agents (builder/writer). Auditor commits as leftover.

### Deduction breakdown: none -- all 5 AC lines verified with specific evidence, no in-scope lint/test issues
### AC Quality Score: 4/5 -- specific, verifiable AC items; each mapped directly to a doc section
### Confidence: 1.0
### Action: archive

[[2026-03-30]] Mon 05:06
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| efed904 | docs | kb-curation-process.md, 177-*.md | #177 |
