---
id: 916
title: Publish EntityExtractor gleaning results and rollout recommendation
status: archived
priority: nice-to-have
created: 2026-03-21T15:56:10.2656872+01:00
updated: 2026-03-21T15:56:10.2656872+01:00
tags:
    - scope:core
    - knowledge
    - benchmark
    - docs
    - type:docs
    - phase-research
parent: 908
depends_on:
    - 915
class: standard
---

**Source:** #908 and docs/research/entity-extractor-gleaning-evaluation-plan.md §5

Run the baseline-vs-gleaning benchmark runner on the curated OwlBear corpus, publish a results document, and decide whether gleaning deserves rollout work or remains experimental.

**Files:** docs/research/

**AC:**

1. Publish a results document with side-by-side tables for micro recall, per-type recall, token or cost totals, and runtime deltas.
2. Link the results document from the owning task body and record the exact benchmark command or entry point used.
3. If micro recall gain is greater than 10 percent, create an integration follow-up that keeps gleaning default-off initially and documents rollout guidance.
4. If micro recall gain is 10 percent or less, document why single-pass remains the default.
