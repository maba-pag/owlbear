---
id: 1869
title: 'Cockpit: delegate decision resolution to kanban resolve_decision()'
status: research
priority: important
created: 2026-05-25T00:20:42.926678+02:00
updated: 2026-05-25T00:20:42.926678+02:00
tags:
  - scope:cockpit-backend
  - boundary-audit
parent: 1865
depends_on:
  - 1868
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Replace inline file-lifecycle code in `routes/decisions.py` resolve endpoint (lines 195–222) with a single call to `owlbear_kanban.decisions.resolve_decision(pending_path, req.response, engine, notes=req.notes, resolved_by="cockpit-api")`. Remove now-unused helpers `_rewrite_response` and `_append_response_section` from the route module. Keep HTTP-layer concerns (id validation, 404 checking, error→HTTPException mapping) in Cockpit. Depends on the kanban resolve_decision task above.