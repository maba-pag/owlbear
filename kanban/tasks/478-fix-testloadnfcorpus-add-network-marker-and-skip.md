---
id: 478
title: 'Fix TestLoadNfcorpus: add network marker and skip guard'
status: ideation
priority: needed
created: 2026-03-04T07:37:56.6489322+01:00
updated: 2026-03-04T07:37:56.6489322+01:00
tags:
    - audit
    - test
class: standard
---

H1: 6 failing tests unconditionally download BEIR dataset from the internet. No @pytest.mark.network, no skip-on-failure. Fails on corporate proxy, offline CI, or when server is down. AC: tests marked @pytest.mark.network, skipped by default. See docs/test-quality-audit.md.
