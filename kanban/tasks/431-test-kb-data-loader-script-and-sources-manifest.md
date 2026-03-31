---
id: 431
title: 'Test: KB data loader script and sources manifest'
status: todo
priority: needed
created: 2026-03-30T21:31:51.1166724+02:00
updated: 2026-03-30T21:32:05.2789979+02:00
started: 2026-03-30T21:32:05.2789979+02:00
tags:
    - phase-2
    - scope:knowledge
    - type:test
    - test
depends_on:
    - 308
class: standard
---

## Objective
Write failing tests for #176 (KB data loader script and sources manifest) targeting packages/knowledge/src/owlbear_knowledge/loader.py.

## Acceptance Criteria
- [ ] Test manifest parsing: valid YAML accepted; malformed YAML raises strictyaml.YAMLValidationError
- [ ] Test manifest schema enforces required fields (name, type, config) and rejects unknown type values
- [ ] Test file glob resolution: glob expands to expected files using tmp_path fixture
- [ ] Test empty glob: returns 0 files, logged at WARNING level
- [ ] Test source registration: KnowledgeSourceStore.create() called once per manifest entry with correct KnowledgeSource fields (including created_at/updated_at as ISO strings)
- [ ] Test ingest flow: IngestPipeline.ingest() called for each resolved file with IntakeResult from intake.read_file()
- [ ] Test delta skipping: when IngestPipeline.ingest() returns status="skipped", file counted as skipped
- [ ] Test per-file failure isolation: one file ingest fails, remaining files still ingested
- [ ] Test CLI entry point: --manifest flag parsed, --root defaults to cwd; missing --manifest exits non-zero
- [ ] Test exit codes: 0 on all-ok/some-skipped, non-zero when all files in any source fail
- [ ] All tests use mock EmbeddingProvider — no FlagEmbedding dependency
- [ ] Test file: tests/test_kb_loader.py

## Context
TDD RED phase for #176. See docs/research/kb-data-loader-manifest.md for design.
