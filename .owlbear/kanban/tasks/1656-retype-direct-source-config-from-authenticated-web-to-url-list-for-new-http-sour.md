---
id: 1656
title: Retype _direct_source_config from AUTHENTICATED_WEB to URL_LIST for new 
  HTTP sources
status: backlog
priority: important
created: 2026-05-18T03:27:04.998459+02:00
updated: 2026-05-18T04:15:19.397429+02:00
tags:
  - scope:knowledge
  - implementation
parent: 1650
depends_on:
  - 1653
ac:
  - 'AC-1: `_direct_source_config(source_url)` in `serve/knowledge/src/owlbear_knowledge/ingest.py`
    returns `(SourceType.URL_LIST, "http", {"url": source_url, "urls": [source_url]})`
    when `source_url` is a non-local HTTP/HTTPS URL'
  - 'AC-2: `_direct_source_config(source_url)` continues to return `(SourceType.FILE_GLOB,
    "file", ...)` for local file paths (local-path branch unchanged)'
  - 'AC-3: Change applies only to newly created sources — no migration of existing
    AUTHENTICATED_WEB source records'
  - 'AC-4: Implementation change is limited to `serve/knowledge/src/owlbear_knowledge/ingest.py`
    (single return-value edit)'
  - 'AC-5: Regression-safe verification — existing tests covering `_direct_source_config`
    and `_handle_url_list` pass without modification; if no such tests exist, add
    a focused unit test asserting the new return type for HTTP URLs'
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1650

## Scope

**In-scope:** Change the non-local URL branch of `_direct_source_config` in `ingest.py` to return `SourceType.URL_LIST` instead of `SourceType.AUTHENTICATED_WEB`. The config dict shape (`{"url": source_url, "urls": [source_url]}`) and `fetch_method="http"` remain identical.

**Out-of-scope:** Migration of existing `AUTHENTICATED_WEB` source records. Changes to `_handle_url_list` or `_handle_authenticated_web` in `refresh.py`. Changes to the local-path (`FILE_GLOB`) branch.

## Context

Research task #1653 confirmed handler equivalence between `_handle_url_list` and `_handle_authenticated_web` for `fetch_method="http"` single-URL sources. This task implements the one-line retype that research validated.