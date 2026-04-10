---
id: 778
title: Add hash stability validation protocol to CDP spike execution (#753)
status: research
priority: needed
created: '2026-04-10T12:16:54.010932+00:00'
updated: '2026-04-10T12:16:54.010932+00:00'
tags:
- phase-0
- scope:browser
parent: 751
depends_on:
- 776
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
Add content hash stability testing to the CDP spike execution checklist (#753).

The spike execution should include this validation protocol:
1. For at least 2 target pages: extract the same page 3 times, 60s apart
2. For each extraction, record: (a) raw HTML hash, (b) trafilatura output hash, (c) trafilatura output text
3. Compare across extractions:
   - Raw HTML hashes likely differ (dynamic boilerplate) — document the delta
   - Cleaned (trafilatura) hashes MUST match for go/no-go
   - If cleaned hashes differ, inspect the diff to identify leaking dynamic elements
4. If trafilatura output differs between extractions of the same page:
   - Test with `prune_xpath` to remove dynamic elements
   - Document specific XPath patterns needed for corporate pages
   - If still unstable, this is a NO-GO signal for the hashing approach

AC:
1. Hash stability protocol added to #753 execution checklist
2. Protocol tests at least 2 pages × 3 extractions × 60s intervals
3. Results compared at raw HTML and cleaned-content levels
4. Go/no-go determination includes hash stability verdict

Context: From #774 research — AC 7 was not covered by original spike design.
Data voice Gap 2 identified hash-on-raw-content as critical issue.
Research: .owlbear/research/774-edge-cdp-spike.md §3.3
