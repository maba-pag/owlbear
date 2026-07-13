---
id: 527
title: Build memory migration CLI tool
status: archived
priority: medium
created: 2026-04-01 16:11:40.972773+02:00
updated: 2026-04-02 22:09:23.861275+02:00
started: 2026-04-02 22:09:23.347461+02:00
completed: 2026-04-02 22:09:23.347461+02:00
tags:
- scope:agents
- phase-2
depends_on:
- 524
class: standard
archival_reason: completed
archival_refs: []
---

CLI tool to bulk-import existing /memories/repo/ files into memory.db. Per docs/research/memory-mcp-server-design.md sec 3L (Phase 3). Depends on #524.

AC:
- [ ] Module at `packages/mcp-memory/src/owlbear_mcp_memory/migrate.py`, invocable via `uv run --project packages/mcp-memory python -m owlbear_mcp_memory.migrate --source-dir PATH [--dry-run] [--db-path PATH]`
- [ ] `--source-dir` (required): filesystem path to the Copilot repo memory directory (VS Code workspace storage path ending in `GitHub.copilot-chat/memory-tool/memories/repo/`). No default (installation-dependent path)
- [ ] `--db-path` (optional): SQLite DB path. Default resolved from OWLBEAR_MEMORY_DB_PATH env var, fallback `data/memory/memory.db` (same logic as server.py)
- [ ] `--dry-run` (flag): prints each would-be entry (source, category, content preview <=80 chars) plus summary counts by category. No DB writes
- [ ] Inbox parsing: reads `{source_dir}/inbox/*.md`. Heading format `# Lessons: #{id} ({agent}, {date})` extracts agent name for scope_agent and date string for created_at. Each `- {label}: {content}` bullet produces one entry. Label-to-category map: problems_faced to knowledge, workarounds_applied to knowledge, patterns_discovered to behavior, time_sinks to context, quality_gaps to context. Unrecognized labels to knowledge (with warning to stderr)
- [ ] Inbox entries: confidence=0.7, approval_state=pending, scope_project=NULL, source=`migration:inbox/{filename}`
- [ ] Established-file parsing: reads `{source_dir}/*.md` (top-level only, excludes inbox/ subdirectory). Splits on `##`-delimited sections. Content before the first `##` heading is captured as a separate entry (not silently dropped). Files with no `##` headings produce a single entry using full file content (excluding the `#` title line). category=knowledge, scope_agent=NULL
- [ ] Established entries: confidence=0.7, approval_state=approved (curated knowledge), scope_project=NULL, source=`migration:{filename}[#section-slug]` where section-slug is the lowercased `##` heading for section entries or omitted for whole-file entries. created_at from date in `#` heading (parse parenthesized date) or file mtime if no parseable date; updated_at = migration run timestamp (ISO 8601 UTC)
- [ ] All entries: id generated via uuid.uuid4(). Validates each entry via MemoryEntry model from owlbear_mcp_memory.models before SQL INSERT; invalid entries logged to stderr and skipped
- [ ] Idempotent: before each INSERT, SELECT by source field; skips entries whose source value already exists in DB
- [ ] Opens SQLite directly (same path resolution as server.py DEFAULT_DB_PATH); imports only MemoryEntry from models.py (no server.py runtime dependency). Runs CREATE TABLE IF NOT EXISTS DDL before inserting
- [ ] File encoding: reads all markdown files as utf-8-sig (handles Windows BOM transparently)
- [ ] Unparseable files: logs warning to stderr, continues processing remaining files

[[2026-04-02]] Thu 07:44
## Architecture Review
**Verdict:** APPROVE
**DR Verification:** docs/decisions/resolved/387-memory-mcp-architecture.md approved: true (Option A)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Script reads /memories/repo/inbox/*.md and established repo memory files | Vague: no module location, no CLI interface, no parsing spec for established files | Rewritten: module path, CLI args, parsing rules for both formats |
| Category mapping: problems_faced/workarounds_applied to knowledge, etc. | Correct per design doc sec 3L. Missing: unrecognized label handling | Kept + added fallback to knowledge with warning |
| Entries created with approval_state=pending, confidence=0.7 | Wrong for established files: curated knowledge should be approved, not pending | Split: inbox=pending, established=approved |
| Source field set to migration:filename | Underspecified: no section-level granularity for established files | Rewritten: migration:filename[#section-slug] |
| Dry-run mode shows what would be imported | Missing: output format spec | Rewritten: source, category, content preview <=80 chars + summary counts |
| (missing) created_at/updated_at | Unspecified: timestamps for migrated entries | Added: extract date from heading or mtime; updated_at=migration timestamp |
| (missing) id generation | Unspecified | Added: uuid.uuid4() |
| (missing) file encoding | Unspecified (Windows BOM risk) | Added: utf-8-sig |
| (missing) pre-## content handling | Would silently drop content before first ## heading | Added: captured as separate entry; no-## files become single entry |

### Architecture Notes
Module placement: co-located in mcp-memory package (packages/mcp-memory/src/owlbear_mcp_memory/migrate.py) since it imports MemoryEntry model and reuses path resolution. Direct SQLite writes (not MCP tools) for bulk performance. No dependency on server.py runtime, only models.py.

Key pattern: repo memory files live in VS Code workspace storage (GitHub.copilot-chat/memory-tool/memories/repo/), NOT in project workspace. source-dir must be a required CLI arg with no default.

Established vs inbox quality gradient: established files are curated multi-session knowledge (approval_state=approved); inbox files are raw per-task observations (approval_state=pending). This preserves the quality signal in get_knowledge result ordering.

### Changes Made
- Rewrote full AC body with 14 testable criteria (was 5 vague lines)
- Added module location, CLI interface spec, parsing rules for both file types
- Split approval_state handling by file type (inbox=pending, established=approved)
- Added pre-## content handling and no-## file fallback to prevent silent data loss
- Added timestamp, id, encoding specs

### Dependencies
- Verified: #524 (scaffold mcp-memory) is done. DDL and MemoryEntry model available
- #525 (implement MCP tools) at ideation. No dependency needed: migration writes directly to SQLite
- DR #387 approved (Option A): architecture validated

### Challenge Results
- Challenger: reconsider (confidence 0.62)
- Key challenges: (C1) silent content loss for files without ## sections, (C2) approval_state=pending wrong for established files, (C3) no DB-level idempotency guarantee, (C4) timestamps unspecified, (C5) id generation unspecified, (C6) scope_project=NULL discards project context
- Architect response: accepted C1 (added pre-## handling and no-## fallback), accepted C2 (split approval_state by file type), rebutted C3 (application-layer idempotency sufficient for single-run migration), accepted C4 (added timestamp spec), accepted C5 (added uuid4), rebutted C6 (repo memories are OwlBear-wide, not project-specific). Revised confidence: .85

[[2026-04-02]] Thu 12:30
## Test-Writer Notes
- Test file: tests/test_memory_migration_cli_527.py
- Classes: TestFromAC_ModuleExistence, TestFromAC_CLIInterface, TestFromAC_InboxParsing, TestFromAC_EstablishedFileParsing, TestFromAC_EntryMetadata, TestFromAC_Idempotency, TestFromAC_DryRun, TestFromAC_FileEncoding, TestFromAC_ErrorHandling
- Tests per category: happy 20, edge 10, error 10, boundary 7
- Total: 47 tests, all FAIL ok
- ruff: clean
- AC coverage:
  AC1 (module exists/importable): test_module_file_exists, test_module_importable, test_module_invocable_as_main
  AC2 (source-dir required): test_source_dir_required_exit_nonzero, test_source_dir_required_stderr_mentions_source_dir
  AC3 (db-path default): test_db_path_uses_env_var, test_db_path_fallback_to_data_memory_db; test_unknown_argument_rejected_with_specific_error
  AC4 (dry-run): test_dry_run_does_not_create_db_file, test_dry_run_prints_source_field, test_dry_run_prints_category, test_dry_run_content_preview_truncated_at_80_chars, test_dry_run_prints_summary_counts_by_category
  AC5/AC6 (inbox parsing): test_each_bullet_produces_one_entry, test_heading_extracts_agent_name_, test_heading_extracts_date_for_created_at, test_problems/workarounds/patterns/time/quality_*_maps_to_*, test_unrecognized_label_maps_to_knowledge, test_unrecognized_label_warns_to_stderr, test_inbox_entry_confidence_is_0_7, test_inbox_entry_approval_state_is_pending, test_inbox_entry_source_format_is_migration_inbox_filename, test_inbox_entry_scope_project_is_null
  AC7/AC8 (established parsing): test_sections_split_on_double_hash, test_pre_heading_content_captured, test_file_with_no_hash_headings_produces_single_entry, test_no_heading_entry_excludes_title_line, test_inbox_subdir_not_parsed_as_established, test_established_entry_approval_state_is_approved, test_established_entry_source_has_lowercased_section_slug, test_established_entry_source_slug_uses_lowercase, test_established_entry_confidence_is_0_7, test_established_entry_scope_project_is_null
  AC9 (entry metadata): test_entry_id_is_valid_uuid4, test_create_table_ddl_creates_memory_entries_table, test_no_server_py_import_in_migrate, test_entry_updated_at_is_migration_timestamp
  AC10 (idempotency): test_existing_source_not_duplicated_on_second_run, test_second_run_inserts_new_files
  AC11 (SQLite/DDL): covered by test_create_table_ddl_creates_memory_entries_table + test_no_server_py_import_in_migrate
  AC12 (encoding): test_reads_utf8_bom_file_without_bom_artifact_in_content
  AC13 (error handling): test_unparseable_file_does_not_crash_migration, test_unparseable_file_logs_to_stderr, test_unparseable_file_does_not_prevent_valid_files

[[2026-04-02]] Thu 17:19
## Builder Notes
- Files changed: packages/mcp-memory/src/owlbear_mcp_memory/migrate.py (new), tests/test_memory_migration_cli_527.py (TestBuilderDiscovered added)
- Tests: 74 passed (47 TestFromAC + 27 TestBuilderDiscovered), coverage 97% on migrate.py
- Lint: ruff clean on changed files
- Fixes applied: UP017 (timezone.utc to datetime.UTC); pre-loaded existing-sources set before insert loop for idempotency on multi-bullet inbox files

[[2026-04-02]] Thu 22:09
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: Module at migrate.py, invocable via CLI | File exists at packages/mcp-memory/src/owlbear_mcp_memory/migrate.py; `uv run --project packages/mcp-memory python -m owlbear_mcp_memory.migrate --help` returns usage | PASS |
| AC2: --source-dir required | --help shows required arg; tests test_source_dir_required_* confirm | PASS |
| AC3: --db-path optional, env fallback | _resolve_db_path at L52-57 checks arg then env then default; tests test_db_path_* confirm | PASS |
| AC4: --dry-run flag, preview output | _dry_run at L245-256 prints source/category/preview + summary; tests test_dry_run_* confirm | PASS |
| AC5: Inbox parsing headings/bullets | _INBOX_HEADING_RE extracts agent+date; bullet regex at L85; tests confirm | PASS |
| AC6: Inbox metadata (confidence=0.7, pending, source format) | Entry dict at L91-103; tests test_inbox_entry_* confirm all fields | PASS |
| AC7: Established parsing (## sections, pre-## content, no-## fallback) | _split_into_sections + _parse_established_file handle all three cases; tests confirm | PASS |
| AC8: Established metadata (approved, section-slug source) | _make_established_entry at L127-139 with approval_state=approved; _slugify for source; tests confirm | PASS |
| AC9: All entries uuid4 + MemoryEntry validation | uuid.uuid4() in entry dicts; _insert_entry validates via MemoryEntry(**entry); tests confirm | PASS |
| AC10: Idempotent by source field | Pre-loaded existing set at L307-309; skip if source in existing; tests test_existing_source_not_duplicated confirm | PASS |
| AC11: Direct SQLite, MemoryEntry import only, CREATE TABLE DDL | No server.py import (grep verified); _DDL at L20-32; tests confirm | PASS |
| AC12: utf-8-sig encoding | read_text(encoding=utf-8-sig) at L68 and L201; test_reads_utf8_bom confirms | PASS |
| AC13: Unparseable files logged, continue | Exception handling in _parse_inbox_file and _parse_established_file; tests confirm | PASS |

### Test Results
- pytest: 74 passed (47 TestFromAC + 27 TestBuilderDiscovered), 97% coverage on migrate.py
- ruff: clean on migrate.py and test file

### Upstream Commits
- 80f960b test: add failing tests for memory migration CLI (#527, test-writer)
- 5ba9f90 feat: implement memory migration CLI tool (#527, builder)

### Architect Quality
Score: 5/5 - Rewrote AC from 5 vague lines to 14 testable criteria with parsing specs, encoding, timestamps, and edge cases

### Deduction breakdown
- -.02 missing Review Evidence section in task body
- -.02 missing Docs Gate section in task body
### Confidence: .96
### Action: archive
