---
id: 683
title: 'Research: diagram rendering tool for agents'
status: archived
priority: medium
created: 2026-04-08T19:18:21.6102963+02:00
updated: 2026-04-09T01:26:37.2871535+02:00
started: 2026-04-09T01:26:37.2871535+02:00
completed: 2026-04-09T01:26:37.2871535+02:00
tags:
    - scope:tools
    - ' type:research'
    - ' source:analysis'
class: standard
---

## Context

v1 had a Kroki API-based diagram tool — agents could render Mermaid, PlantUML, or other diagram source to PNG and deliver/persist images. v2 has the `h-excalidraw-diagram` skill (agents can write Excalidraw JSON) and Mermaid knowledge in prompts, but no tool that renders diagram source to an image file.

Currently agents can *write* diagram source but can't *render* it — the user must manually render or paste into a viewer.

## Research Questions

1. **What rendering options exist?**
   - Kroki API (v1 approach — external service, supports many formats)
   - Mermaid CLI (`@mermaid-js/mermaid-cli` — local, Mermaid only)
   - Excalidraw export (headless Puppeteer-based, Excalidraw JSON → PNG/SVG)
   - VS Code extension integration (Mermaid Preview, Excalidraw editor — already installed?)
   - `renderMermaidDiagram` tool already exists in deferred tools list — is this sufficient?

2. **What's the integration surface?**
   - MCP tool on a new/existing server?
   - Standalone script agents call via run_in_terminal?
   - Leverage existing VS Code deferred tool (`renderMermaidDiagram`)?

3. **What formats matter?** Mermaid covers most use cases (architecture, sequence, flowcharts). Is PlantUML/Excalidraw rendering needed?

## Acceptance Criteria

- [ ] AC1: Evaluate rendering options (local vs API, format coverage, complexity)
- [ ] AC2: Check if `renderMermaidDiagram` deferred tool already solves this
- [ ] AC3: Recommendation on approach with trade-offs
- [ ] AC4: Follow-up implementation task if warranted

[[2026-04-08]] Wed 21:12
## Research
- Research doc: .owlbear/research/diagram-rendering-tool-v2.md
- Sources: 9 studied, 4 high-relevance
- Recommendation: Do nothing — VS Code already provides diagram rendering via mermaid-chat.enabled (chat UI), h-visual-output (HTML+Mermaid CDN), and h-excalidraw-diagram (JSON). No new tool needed. (confidence: .85)
- Follow-up tasks created: #691 (verify mermaid-chat.enabled, document rendering paths)
- Decision requests: none (T1 autonomous — no new capability)

## Key Findings
1. `renderMermaidDiagram` does NOT exist as a VS Code built-in or deferred tool
2. VS Code's `mermaid-chat.enabled` renders Mermaid in chat responses automatically — covers primary use case
3. `bierner.markdown-mermaid` extension (installed) renders Mermaid in Markdown Preview
4. v2's VS Code-native model eliminates v1's need for image file generation — the IDE handles rendering
5. Only gap: standalone image file output (PNG/SVG) — no current use case requires this

## Challenge Results
- Challenger: FALLBACK — T1 autonomous finding, no architectural change proposed
- Confidence in original: .85
- Key challenges: N/A
- Researcher response: N/A

[[2026-04-08]] Wed 21:54
## Architecture Review
### AC Assessment
| AC | Assessment | Action |
|----|-----------|--------|
| AC1: Evaluate rendering options | PASS — research doc §3.2 compares 6 rendering paths with effort/coverage/KISS matrix | None |
| AC2: Check `renderMermaidDiagram` deferred tool | PASS — §3.1 confirmed tool does not exist; documented what does exist (4 alternatives) | None |
| AC3: Recommendation with trade-offs | PASS — "do nothing" recommendation backed by gap analysis showing VS Code handles rendering natively | None |
| AC4: Follow-up task if warranted | PASS — #691 created (verify mermaid-chat.enabled, document rendering paths) | None |

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One scope: evaluate diagram rendering needs for v2 |
| Interface clarity | PASS | AC defines 4 clear research deliverables |
| Dependency correctness | PASS | No dependencies needed or listed |
| Module layering | N/A | Research task, no code |
| TDD compliance | PASS | `type:research` pass-through tag present |
| KISS/YAGNI | PASS | Recommendation itself follows KISS — don't build what the IDE already provides |
| Premise challenge | PASS | Research correctly challenged the premise that a new tool was needed |
| Pattern consistency | N/A | Research task |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | scope:tools |

### Architecture Notes
- Research is well-sourced (9 sources, 4 high-relevance) with clear gap analysis
- The "do nothing" recommendation is architecturally sound — v2's VS Code-native model eliminates v1's need for server-side image generation
- Follow-up #691 appropriately scoped to verify the setting and document paths for agents
- If image file rendering is ever needed, the research pre-identifies Kroki MCP tool as the minimal path (~100 LOC)

### Challenge Results
- Challenger: FALLBACK — challenger subagent not available in current agent set
- Architect response: accepted — T1 autonomous finding with no architectural change, thorough evidence

### Verdict: APPROVE
### Action Taken: Advanced to todo. Research complete with all AC satisfied.

[[2026-04-08]] Wed 22:38
## Test-Writer Notes
- Non-implementation task (tagged type:research) — no tests applicable.
- Passing through to builder.

[[2026-04-08]] Wed 23:05
## Builder Notes
- Non-implementation task — no code changes needed.
- Passing through to review.

[[2026-04-08]] Wed 23:25
## Review Evidence

### Task Type
`type:research` pass-through — no code changes, no tests, no lint/coverage to execute.

### Tests
N/A — non-implementation task. Test-writer and builder both correctly passed through.

### Lint / Coverage
N/A — no changed files.

### Changed Files
None (deliverable: `.owlbear/research/diagram-rendering-tool-v2.md` — verified present and complete).

### AC Compliance

| AC | Evidence | Status |
|----|----------|--------|
| AC1: Evaluate rendering options (local vs API, format coverage, complexity) | §3.2 comparison table covers 6 paths (A–F) with Coverage, Effort, Image file?, KISS columns; §3.4 adds architecture-fit assessment for the 3 build options | PASS |
| AC2: Check if `renderMermaidDiagram` deferred tool exists | §3.1 explicitly confirms tool does not appear in VS Code built-in tools list (source #1 — authoritative VS Code docs); 4 existing alternatives documented | PASS |
| AC3: Recommendation on approach with trade-offs | §4 delivers "do nothing now" recommendation backed by §3.3 gap analysis (5 use cases with solved/unsolved mapping) and §3.4 trade-off table; Kroki path pre-identified if image files ever needed | PASS |
| AC4: Follow-up implementation task if warranted | #691 created and confirmed active (status: archived) — appropriate scope for verifying the setting and documenting paths | PASS |

### Research Integrity Check
- 9 sources studied, 4 high-relevance — sourcing proportionate to a T1 autonomous decision
- Primary finding (tool nonexistence) sourced from official VS Code docs (source #1) — not from inference
- "Do nothing" recommendation conservative and architecturally sound per v2's VS Code-native model
- Gap analysis (§3.3) identifies the lone unmet use case (standalone image files) honestly with no YAGNI suppression
- Confidence .85 is appropriate for a "yes we've covered the primary cases, but one gap acknowledged" conclusion

### Deductions
None.

### Verdict
Confidence: .95 → PASS

[[2026-04-09]] Thu 00:06
## Docs Gate

| # | Item | Applies? | Status | Evidence |
|---|------|----------|--------|----------|
| 1 | Behavior/API change → copilot-instructions.md | No | N/A | type:research — no code, no behavior change |
| 2 | Module docstrings | No | N/A | No Python modules created or modified |
| 3 | External attribution → sources/overview.md | Yes | PASS | 3 external sources used; VS Code built-in tools + Mermaid-in-chat documented under #683 section; bierner/markdown-mermaid documented under #680 section with Where Used pointing to diagram-rendering-tool-v2.md — all external sources covered |
| 4 | CLI changes → README.md | No | N/A | No CLI changes |
| 5 | Research doc | Yes | PASS | .owlbear/research/diagram-rendering-tool-v2.md present and complete (9 sources, §3.1–3.4 gap analysis, §4 recommendation); follow-up #691 created and active; linked in task body |

**Files updated:** None  
**Scratch files:** None found (683-* search returned no matches)

[[2026-04-09]] Thu 01:26
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: Evaluate rendering options (local vs API, format coverage, complexity) | Research doc §3.2: 6-path comparison table (A–F) with Coverage, Effort, Image file?, KISS columns | PASS |
| AC2: Check if `renderMermaidDiagram` deferred tool exists | Research doc §3.1: confirmed tool does not exist in VS Code built-in tools list; 4 existing alternatives documented | PASS |
| AC3: Recommendation on approach with trade-offs | Research doc §4: "do nothing" recommendation backed by §3.3 gap analysis (5 use cases mapped) and §3.4 trade-off table; Kroki path pre-identified | PASS |
| AC4: Follow-up implementation task if warranted | #691 created (verify mermaid-chat.enabled, document paths) — confirmed active at status:done | PASS |

### Research Task Verification (Step 1a)
1. Research doc exists: `.owlbear/research/diagram-rendering-tool-v2.md` ✓
2. Follow-up task #691 created and references the research doc ✓
3. Doc is thorough: 9 sources, 4 high-relevance, structured gap analysis ✓

### Test Results
- pytest: 3663 passed, 383 failed, 18 skipped, 1 error — all pre-existing (type:research, no Python changes)
- ruff: 5 pre-existing errors unrelated to this task (no Python files changed)

### Architect Quality: 4/5
AC is specific for a research task: 4 clear deliverables covering evaluation, tool verification, recommendation, and follow-up. Minor gap: AC4 is open-ended ("if warranted") but appropriate for research.

### Deduction Breakdown
- AC lines without evidence: 0 (all 4 PASS) → 0
- Lint violations in scope: 0 (no Python files changed) → 0
- AC quality ≤ 3: no (4/5) → 0
- Missing reviewer evidence: no (present, detailed, PASS verdict at .95) → 0
- Full-suite test failures in scope: 0 → 0

### Process Note
Research doc was never committed by upstream agents — committed by auditor as orphaned deliverable (c22f2b1).

### Confidence: 1.00
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| c22f2b1 | docs | .owlbear/research/diagram-rendering-tool-v2.md | #683 |
