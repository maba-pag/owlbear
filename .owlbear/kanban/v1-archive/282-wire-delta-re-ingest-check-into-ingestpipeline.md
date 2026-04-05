---
id: 282
title: Wire delta re-ingest check into IngestPipeline
status: archived
priority: needed
created: 2026-02-28T22:57:07.7443634+01:00
updated: 2026-03-01T17:07:36.0311633+01:00
started: 2026-02-28T23:12:17.0437641+01:00
completed: 2026-03-01T17:07:36.0311633+01:00
tags:
    - phase-9
    - knowledge-graph
depends_on:
    - 278
    - 279
    - 280
    - 281
class: standard
---

Wire content hashing and delta detection into the main ingest entry points.

AC:
- [ ] ingest(): before intake, call check_content_changed(source, ...) — if unchanged, return early with skipped=True
- [ ] ingest(): if changed and existing_document_id is not None, call delete_document_data() before re-ingesting
- [ ] ingest_text(): same logic using metadata['url'] or source label as key
- [ ] After successful ingest, update document_status.content_hash with computed hash
- [ ] IngestResult gains skipped: bool = False field
- [ ] Logging: INFO 'Skipping unchanged source %s' / INFO 'Re-ingesting changed source %s (old doc %s)'
- [ ] Tests: re-ingest same content -> skip, re-ingest changed -> delete+new doc, first ingest -> normal path

Depends on #278 (schema), #279 (find_status_by_source), #280 (hash check), #281 (delete cascade).
See docs/research/content-hashing.md
