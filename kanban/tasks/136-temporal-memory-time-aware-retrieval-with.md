---
id: 136
title: Temporal memory — time-aware retrieval with relevance decay
status: archived
priority: nice-to-have
created: 2026-02-27T14:57:37.6652855+01:00
updated: 2026-02-28T23:53:00.3423026+01:00
started: 2026-02-28T00:52:48.4750205+01:00
completed: 2026-02-28T23:53:00.3423026+01:00
tags:
    - phase-9
    - memory
class: standard
---

More recent knowledge should rank higher in retrieval. Research approaches: timestamp weighting in vector search, explicit decay functions, sliding window. The knowledge graph already stores created_at — this adds time-awareness to queries. May also include 'importance' scoring to prevent critical long-term knowledge from decaying.
