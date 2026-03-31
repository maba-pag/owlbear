---
id: 176
title: Build KB data loader script and sources manifest
status: todo
priority: needed
created: 2026-03-29T19:50:47.4770555+02:00
updated: 2026-03-30T21:33:30.3560413+02:00
tags:
    - phase-2
    - scope:knowledge
    - type:build
depends_on:
    - 32
    - 308
    - 431
class: standard
---

## Objective
Create data/knowledge/general/sources.yaml manifest and a loader script (packages/knowledge/src/owlbear_knowledge/loader.py) that reads the manifest and ingests documents via IngestPipeline.

## Acceptance Criteria
- [ ] sources.yaml schema: sequence of {name: str, type: file_glob|url_list, config: {glob: str} or {urls: [str]}, scope: str (default global), enabled: bool (default true)}
- [ ] Manifest parsed and validated using strictyaml with typed schema; malformed YAML raises immediately with a clear error message
- [ ] Loader resolves file globs via pathlib.Path.glob() relative to workspace root
- [ ] Each resolved path passed through intake.read_file(path, workspace_root=root) for sandbox validation
- [ ] Registers each manifest entry as a KnowledgeSource via KnowledgeSourceStore.create() with ISO timestamps for created_at/updated_at
- [ ] Ingests each resolved file via IngestPipeline.ingest(IntakeResult, scope=source.scope) with delta detection handled internally by the pipeline
- [ ] Empty glob matches logged as WARNING, processing continues to next source
- [ ] Per-file ingest failures logged, processing continues; final summary reports ok/skipped/failed counts per source
- [ ] CLI entry point: uv run python -m owlbear_knowledge.loader --manifest <path> [--root <workspace_root>]; argparse, no extra deps
- [ ] Non-zero exit code when any source has all files failed
- [ ] Initial sources.yaml includes: all docs/research/*.md, all skills/*/SKILL.md, all instructions/*.md

## Context
Split from #24. See docs/research/general-kb-initial-data-load.md.
Research: docs/research/kb-data-loader-manifest.md

## Architecture Notes
- Use IngestPipeline.ingest(IntakeResult) not ingest_text() per research finding (.90 confidence). ingest() handles delta detection via check_content_changed() and content hash updates internally.
- Follow intake.read_file() for sandbox-safe file reading. sandbox_path() in _paths.py prevents path traversal.
- KnowledgeSource model has required created_at/updated_at: str fields. Loader sets these to datetime.now(tz=UTC).isoformat().
- argparse CLI, no click/typer dependency. Knowledge package stays lean.
- strictyaml schema provides fail-fast validation at parse time. Requires #308 (add strictyaml to knowledge deps).

[[2026-03-30]] Mon 21:33
## Architecture Review
**Verdict:** REFINE

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| sources.yaml manifest format | Good; maps to existing SourceType enum and KnowledgeSource model | Tightened schema spec with field defaults |
| Loader reads manifest, resolves globs | Good; pathlib.Path.glob() is correct approach | Added sandbox_path reference |
| Registers via KnowledgeSourceStore.create() | Good; verified method signature: create(source: KnowledgeSource) | Added created_at/updated_at requirement |
| Checks content delta via StatusStore | Redundant; IngestPipeline.ingest() handles delta internally | Removed from AC |
| Calls IngestPipeline.ingest_text() | Wrong API; ingest(IntakeResult) is superior (.90 confidence) | Replaced with ingest(IntakeResult) |
| CLI entry point | Good; argparse, no extra deps | Added --root flag |
| Unit tests with mock EmbeddingProvider | Belongs in test task | Moved to #431 |
| Initial sources.yaml ~50 docs | Vague quantity | Tightened to explicit glob patterns |

### Architecture Notes
Verified all interfaces in packages/knowledge/src/owlbear_knowledge/: IngestPipeline.ingest(IntakeResult) at ingest.py:127, intake.read_file() at intake.py:32, KnowledgeSourceStore.create(KnowledgeSource) at source_store.py:67, sandbox_path() at _paths.py:11. All align with proposed design. Single domain (scope:knowledge).

### Changes Made
- Rewrote AC: ingest_text() replaced with ingest(IntakeResult), removed redundant StatusStore check, tightened manifest schema, moved tests to #431
- Created #431 (Test: KB data loader) at todo with depends_on #308
- Added depends_on: #308 (strictyaml dep), #431 (test task)

### Dependencies
- #32 (vector store + embedding pipeline): archived (done)
- #308 (strictyaml dep): backlog, must complete before test-writer/builder
- #431 (test task): todo, TDD RED phase precedes implementation
