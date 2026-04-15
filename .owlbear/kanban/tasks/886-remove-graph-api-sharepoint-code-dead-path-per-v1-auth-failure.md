---
id: 886
title: Remove Graph API SharePoint code — dead path per v1 auth failure
status: backlog
priority: nice-to-have
created: '2026-04-15T12:41:52.520931+00:00'
updated: '2026-04-15T12:41:52.520931+00:00'
tags:
- scope:knowledge
- type:config
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
Graph API SharePoint extraction was fully implemented (task 879) but the authentication prerequisite (Azure AD app registration from corporate IT, task 878) is not viable — v1 exploration confirmed auth cannot be obtained in the corporate environment.

## Acceptance Criteria
- Delete `serve/knowledge/src/owlbear_knowledge/graph_fetcher.py`
- Remove `SourceType.SHAREPOINT_API` from `models.py`
- Remove `_handle_sharepoint_api()` and `graph_content_fetcher` parameter from `refresh.py` and `RefreshOrchestrator`
- Remove or update associated tests (tasks 880-885 test coverage)
- Archive task 878 as won't-do
- Update any docs referencing SharePoint API extraction

## Context
- Parent research: task 773 (Phase 4, optional)
- Implementation: task 879 (28 tests, all passing)
- Blocker: task 878 (IT approval, non-viable)
- Playwright browser path is the deployed solution and works
