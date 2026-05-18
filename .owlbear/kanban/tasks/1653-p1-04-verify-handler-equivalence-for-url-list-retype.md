---
id: 1653
title: 'P1-04: Verify handler equivalence for URL_LIST retype'
status: research
priority: important
created: 2026-05-18T03:11:06.930657+02:00
updated: 2026-05-18T03:15:32.331209+02:00
tags:
  - scope:knowledge
  - research
parent: 1650
depends_on: []
ac:
  - "AC-1: Research document in `.owlbear/research/` compares `_handle_url_list` and
    `_handle_authenticated_web` codepaths in `refresh.py` for sources with `fetch_method='http'`,
    documenting input handling, URL fetching, chunking, and result aggregation differences"
  - 'AC-2: Document concludes with pass/fail on handler equivalence; if pass, creates
    a follow-up backlog task for the `_direct_source_config` retype from `AUTHENTICATED_WEB`
    to `URL_LIST` (new sources only, no migration); if fail, documents incompatibilities
    and appends O3-dropped note to parent #1650 body'
proof_bundle: skip
blocked: false
block_reason:
claimed_at: 2026-05-18T03:15:32.331209+02:00
archival_reason:
archival_refs: []
---
Brief: see parent #1650

## Scope

**In-scope:** Static analysis of `_handle_url_list` vs `_handle_authenticated_web` for `fetch_method="http"` sources. Determine whether `URL_LIST` handler produces equivalent refresh results.

**Out-of-scope:** Implementation of the retype (follow-up task if equivalence holds). Migration of existing `AUTHENTICATED_WEB` records.

## Context

O3 is gated on handler equivalence. `_direct_source_config` currently returns `(SourceType.AUTHENTICATED_WEB, "http", {"url": source_url, "urls": [source_url]})` for HTTP URLs. The proposed change would return `(SourceType.URL_LIST, "http", ...)` instead.

Key question: does `_handle_url_list` with `fetch_method="http"` produce the same documents, chunks, and refresh counters as `_handle_authenticated_web` for a single-URL source?

`_handle_url_list` is at line 199 in refresh.py. `_handle_authenticated_web` is at line 317.