# Context — Agent & Skill Signal-to-Noise Ratio

## Problem Statement

Agent and skill files in `share/` have grown organically over months — paragraphs added, rarely reorganized or restructured. The result is context window bloat without proportional behavioral improvement. Many sections contain verbose phrasing, trivial/common knowledge the model already has, cross-file repetition, or over-specification that constrains where latitude would be appropriate.

The existing agent-audit prompt (format compliance + obvious problems) does not evaluate signal density at the paragraph/sentence level. Its D6 (SNR) dimension is surface-level — it flags "rationale the agent won't act on" but doesn't ask "is this sentence actually steering behavior the model wouldn't produce alone?"

The constraint is methodological: 80 files can't be audited at quality in a single context window. Two complementary tools are needed — one for big-picture coherence, one for attention-dense per-file compression.

## Outcomes

Two complementary prompts:

| Tool | Strength | Role |
|------|----------|------|
| **Broad audit** (improved agent-audit) | Ecosystem coherence | Cross-agent consistency, coverage gaps, duplication patterns, structural comparison, SNR scoring relative to peers |
| **Deep-dive prompt** (new) | Attention density | One agent + linked skills. Per-sentence signal evaluation, terse rewriting, creative-vs-mechanical calibration. Edits in-session |

**Best outcome:** Both tools operational, demonstrated, reducing total share/ token footprint by ~30% with no pipeline regression.
**MVP:** Deep-dive prompt demonstrated on the reviewer agent with measurable token reduction.

## Project Type

existing-feature/refactor

## Verification Signal

Outcome-based monitoring: reviewer-rejects, auditor-rejects, hangs, death-loops. If a change causes more pipeline failures, it was over-cut.

## Volume Estimate

User estimates ~1/3 noise: ~5% trivial (model already knows), ~20% low signal, remainder too verbose for the signal it carries.

## Origin

Task 1293, spawned from the neutral-shared-layer ideation (draft-neutral-shared). The first-principles stance challenged: of the 60 files marked "clean" in the path-audit, how many carry universal opinion the model doesn't already have? The rest are either noise (token cost with no behavioral steering) or OwlBear-workflow-specific local artifacts wearing a shared costume.
