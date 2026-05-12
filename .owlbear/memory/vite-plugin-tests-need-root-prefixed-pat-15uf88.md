---
id: 96fe1fba-9d17-4501-b81d-5e0b9e0da41e
title: Vite plugin tests need root-prefixed path assertions
categories:
- pitfall
- domain-knowledge
- process
confidence: 0.89
state: curated
scope_agents:
- reviewer
- test-writer
- architect
source_agent: reviewer
created_at: '2026-05-12T22:01:08.610840Z'
updated_at: '2026-05-12T22:17:53.301511Z'
approved_at: null
---

In Cockpit Vite plugin review, tests that call configResolved() but assert only path suffixes do not prove the resolved root is stored/used. Require assertions on FAKE_ROOT-prefixed package/assets paths, and for files.find(regex) behavior add a mixed fixture with a leading non-match plus later match so first-entry regressions cannot pass.
