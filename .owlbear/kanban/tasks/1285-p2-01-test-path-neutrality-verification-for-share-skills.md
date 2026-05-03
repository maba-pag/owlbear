---
id: 1285
title: 'P2-01: Test — path neutrality verification for share/skills/'
status: todo
priority: critical
created: 2026-05-02T16:01:17.041733+00:00
updated: 2026-05-03T11:18:27.204594+00:00
tags:
- phase-2
- scope:test
- shared-layer
parent: 1280
depends_on:
- 1282
blocked: false
block_reason:
claimed_at: 2026-05-03T11:18:27.204594+00:00
archival_reason:
archival_refs: []
---

Brief: see parent #1280 and `.owlbear/briefs/draft-neutral-shared/brief.md`

## Acceptance Criteria

- [ ] Pytest test file `tests/test_path_neutrality_1285.py` exists (td:0)
- [ ] Test asserts zero hits from `pathlib.rglob` + regex `r'\bserve/'` across `share/skills/**/*.md`, excluding lines matching `mcp-` or `Example (` — equivalent to `grep -r 'serve/' share/skills/ | grep -v 'mcp-\|Example ('` (td:2)
- [ ] Test asserts `share/skills/h-quality-runner/SKILL.md` contains directive referencing `copilot-instructions.md` for frontend root and test path routing (td:1)
- [ ] Test asserts `share/skills/r-architecture-standards/SKILL.md` has no `## v2 Architecture Overview`, no `## Package Dependency Rules`, no `## Domain Taxonomy` section headers (td:1)
- [ ] Test asserts r-doc-standards chain has no dangling cross-references: r-doc-standards skill references doc-standards.instructions.md which references doc-audit.prompt.md — each target must exist at its expected path under `share/` (td:2)
- [ ] Test asserts `doc-audit.prompt.md`, `agent-audit.prompt.md`, `arch-audit.prompt.md` exist in `.owlbear/prompts/` and do NOT exist in `share/prompts/` (td:1)
- [ ] All tests fail initially (RED phase) (td:0)

## Scope

- IN: Write pytest verification tests for P2 AC
- OUT: Implementing the actual genericization (that is #1286–#1291)

## Implementation Notes

- Pattern: follow `tests/test_dead_code_sweep_1296.py` — `_REPO_ROOT = Path(__file__).parent.parent`, one function per AC
- AC2 exclusion regex must match shell `grep -v` semantics: skip any line containing `mcp-` OR `Example (`
- AC4 + AC2 together cover both structural section removal AND path-level neutrality — AC4 checks section headers, AC2 catches any surviving `serve/` references
- AC5 scope: the three-member chain only (r-doc-standards → doc-standards.instructions → doc-audit.prompt). Agent-audit and arch-audit prompt moves are #1291's scope but tested structurally via AC6
- AC6: the 3 prompts are doc-audit.prompt.md, agent-audit.prompt.md, arch-audit.prompt.md

[[2026-05-03]]
## Research
- Research doc: .owlbear/research/path-neutrality-tests-1285.md
- Sources: 7 studied, 5 high-relevance
- Recommendation: Proceed with implementation — all 6 AC lines map to straightforward filesystem content assertions using pathlib + regex. Established pattern in test_dead_code_sweep_1296.py. (confidence: 0.90)
- Follow-up tasks created: none (task itself is the test-writer deliverable; sibling tasks #1286–#1291 cover GREEN)
- Decision requests: none

### Key findings
- All 6 AC lines confirmed testable; all will fail against current state (RED verified)
- AC2: 51 serve/ references in share/skills/ after exclusions — regex must match shell grep semantics
- AC3: h-quality-runner has NO project-config routing prose currently
- AC4: r-architecture-standards has v2 overview + domain taxonomy + package dependency rules to remove
- AC5: Cross-ref check scoped to r-doc-standards ↔ doc-standards.instructions ↔ doc-audit.prompt chain
- AC6: All 3 audit prompts in share/prompts/; .owlbear/prompts/ doesn't exist yet
- Challenge: skipped — trivial test-mapping with no architectural trade-offs

## Architecture Review

**Verdict:** APPROVED → todo

### AC Assessment

| AC | Assessment | Action |
|----|-----------|--------|
| AC1 (file exists) | td:0, meta-AC satisfied by other tests existing | No change |
| AC2 (no serve/ paths) | td:2, well-specified shell-equivalent regex with exclusions. 51 current matches confirm RED. | Refined: added `pathlib.rglob` + regex specification |
| AC3 (quality-runner routing) | td:1, was vague ("project config"). Brief specifies `copilot-instructions.md` explicitly. | Refined: narrowed to `copilot-instructions.md` reference |
| AC4 (arch-standards generic) | td:1, parenthetical was incomplete. Three specific section headers identified. | Refined: listed all 3 H2 headers to check for absence |
| AC5 (doc-standards chain) | td:2, scope ambiguity between narrow 3-file chain and broad share/-wide scan. | Refined: scoped to the specific 3-member chain |
| AC6 (prompt relocation) | td:1, 3 prompts named in brief. | Refined: named all 3 prompt files explicitly |
| AC7 (RED phase) | td:0, workflow constraint, not separately tested | No change |

### Architecture Notes

- **Pattern:** Follows established `test_dead_code_sweep_1296.py` pattern for RED-phase filesystem assertions
- **Coverage design:** AC2 (path-level) + AC4 (section-level) provide overlapping coverage for r-architecture-standards neutrality — no false-green gap
- **AC5 boundary:** Scoped to doc-standards chain only. Agent-audit/arch-audit prompt moves verified structurally by AC6, not by cross-ref tracing
- **Behavioral preservation:** Out of scope for this structural test. Each GREEN task (#1286–#1291) owns behavioral regression for its scope

### Dependency Analysis

- **#1282** (P1-02: Split owlbear-system.instructions.md): archived/done ✓
- **#1280** (parent: Neutral shared layer): archived/done ✓
- **Downstream:** #1286, #1287, #1288, #1289, #1290, #1291 all depend on this task

### Challenger Results

- Confidence: 0.44, recommended `block`
- 3 AC-refinement concerns accepted and addressed (AC3 vagueness, AC4 under-specification, AC5 scope ambiguity)
- 2 concerns overridden: "behavior unchanged" criterion is GREEN-task responsibility, not RED-test scope; prompt wiring is #1291's concern
- 1 minor overridden: phase-level integration gate design is intentional per brief
[[2026-05-03]]
Architecture review complete. Refined 4 AC lines (AC2 regex specification, AC3 narrowed to copilot-instructions.md, AC4 explicit section headers, AC5 scoped to 3-member chain, AC6 named all 3 prompts). Challenger at 0.44 recommended block — 3 concerns addressed via refinement, 3 overridden with rationale. Test-depth annotated: 2×td:0, 2×td:1 (skip not applicable — task has td:2 lines), 3×td:1, 2×td:2.