---
id: 1f3bbb5f-7df9-48d4-b772-99c5609bda2b
title: AC literals must be verified against canonical source, not inferred
categories:
- pitfall
- domain-knowledge
confidence: 0.92
state: curated
scope_agents:
- shaper
- verifier
- builder
source_agent: architect
created_at: '2026-05-17T03:06:27.036221Z'
updated_at: '2026-05-17T13:09:11.148217Z'
approved_at: null
---

AC lines referencing code literals (CSS classes, signal names, enum values, tokens, props) must use EXACT values from the codebase, not inferred aliases.

Failure modes: `data-signal="pending"` vs real `"dr-pending"`, `src/tokens.css` vs real `src/custom-tokens.css`, `.status-bar` vs real `.shell__status-bar`, invented PDS prop names.

Verification: For every quoted literal in an AC, open the canonical source and confirm it exists verbatim. Key Cockpit sources: computeSignal.ts (signals), custom-tokens.css (CSS tokens), Shell.css/tsx (layout), Card.css/tsx (cards), PDS React types (component props).

This class of defect causes tests to fail at build time because the builder implements against incorrect AC literals.
