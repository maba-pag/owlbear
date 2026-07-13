---
id: 1033
title: 'P2-09: Pipeline diagram'
status: archived
priority: medium
created: 2026-04-19 23:53:28.586415+00:00
updated: 2026-04-20 05:48:50.616446+00:00
tags:
- phase-2
- docs-currency
- docs-diagram
parent: 1016
depends_on:
- 1024
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1016

## Acceptance Criteria

- [ ] `share/diagrams/pipeline.excalidraw` created
- [ ] Shows full pipeline: research, backlog, todo, in-progress, review, docs, done, archived — with agent assignments per phase (researcher, architect, planner, test-writer, builder, reviewer, doc-writer, auditor)
- [ ] `describes` field in doc-index: list of file path globs (e.g., `share/agents/*.agent.md`, `share/skills/r-pipeline-protocol/**`, `.owlbear/kanban/**`)
- [ ] Auto-maintained footer text element: `Last verified: YYYY-MM-DD (commit-hash)`
- [ ] Diagram is descriptive, not authoritative
- [ ] Follows `h-excalidraw-diagram` skill conventions

## Files

- Creates: `share/diagrams/pipeline.excalidraw`
- Modifies: `.owlbear/doc-index.md` (auto-regen)
[[2026-04-20]]
## Architecture Review

### Refined AC (supersedes original)

- [ ] `share/diagrams/pipeline.excalidraw` created as valid Excalidraw JSON (`"source": "owlbear"`)
- [ ] Diagram shows the full pipeline stages in order: research → backlog → todo → in-progress → review → docs → done → archived, with the dispatch agent labelled at each stage transition (researcher, architect, test-writer, builder, reviewer, doc-writer, auditor). The planner and orchestrator are auxiliary agents — show them as sub-dispatch annotations (planner from backlog→todo decomposition, orchestrator as supervisory layer), NOT as stage owners. Use Flowchart (Diamond Decisions) or Assembly Line pattern from `h-excalidraw-diagram`
- [ ] `.excalidraw` JSON includes a top-level `"describes"` array of file-path globs: `["share/instructions/owlbear-system.instructions.md", "share/skills/r-pipeline-protocol/**", "share/agents/*.agent.md"]`. This is an OwlBear extension outside standard Excalidraw schema — doc-index reads it on regen. Globs must match actual workspace paths. Do NOT include `.owlbear/kanban/**` (too volatile — every task mutation would trigger doc-writer drift detection)
- [ ] Footer text element: `Last verified: YYYY-MM-DD (commit-hash)` — set at creation time. Doc-writer v2 agent updates this on subsequent passes when `describes` globs match changed files (w-doc-update Item 5)
- [ ] Diagram is descriptive, not authoritative (authority = `r-pipeline-protocol` skill + agent definitions)
- [ ] Follows `h-excalidraw-diagram` skill conventions (grid alignment, color meaning, unique IDs, bindings, ≥16px labels)
- [ ] Run `uv run doc-index` after creation — verify `describes` entry appears in `.owlbear/doc-index.md`

### Builder Guidance

Sibling task #1029 (project-overview diagram) is the first `.excalidraw` file in the repo and sets the template. Follow the same JSON structure, `describes` format, and footer format established there. Use the large-diagram strategy from `h-excalidraw-diagram` (section-by-section build). Reference `r-pipeline-protocol` § Pipeline table and `share/instructions/owlbear-system.instructions.md` § Pipeline for the authoritative stage→agent mapping.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One diagram file |
| Interface clarity | PASS (after refinement) | AC2 corrected: planner/orchestrator as auxiliary, not stage owners. AC3 clarified: `describes` in JSON, volatile globs removed. AC4 clarified: maintenance by doc-writer |
| Dependency correctness | PASS (with note) | #1024 archived/done. Recommend adding #1029 as dependency (template-setter) — flagged to user |
| Module layering | N/A | Diagram file, no code modules |
| TDD compliance | N/A | Non-impl task, needs `type:docs` pass-through tag — flagged to user |
| KISS/YAGNI | PASS | Minimal scope, one diagram |
| Premise challenge | PASS | Brief (parent #1016) section 2.3 explicitly requires 7 diagrams; doc-writer v2 verification spec references this file |
| Pattern consistency | PASS | Follows h-excalidraw-diagram conventions; `describes` is per brief section 4.6; consistent with sibling #1029 refined AC |
| Security surface | PASS | No new security boundaries |
| Single domain | PASS | Docs domain only |

### Challenge Results

- Challenger: reconsider (confidence 0.45)
- C1 (critical): planner mislabeled as stage agent. ACCEPTED — refined AC2 to show 7 stage-transition agents with planner/orchestrator as auxiliary sub-dispatches.
- C2 (moderate): missing #1029 dependency. PARTIALLY ACCEPTED — recommended but not hard technical dependency. Flagged to user.
- C3 (moderate): `.owlbear/kanban/**` glob too volatile. ACCEPTED — replaced with stable authority files in refined AC3.
- C4 (moderate): no refined AC text provided. ACCEPTED — full refined AC now included.
- C5 (minor): claimed in backlog. DISMISSED — standard architect review via start_work.
- Architect response: accepted critical and moderate findings, refined AC accordingly. Override to APPROVE.

### Verdict: APPROVE
### Action Taken: Refined AC for accuracy (agent taxonomy, describes globs, footer mechanism, builder guidance). Two items flagged to user: (1) add `type:docs` tag for pass-through, (2) consider adding `depends_on: 1029` for template consistency.
[[2026-04-20]]
## Test-Writer Notes
- Test file: tests/test_pipeline_diagram_1033.py
- Classes: `TestFromAC_PipelineDiagramFile`, `TestFromAC_PipelineStagesAndAgents`, `TestFromAC_DescribesField`, `TestFromAC_FooterElement`, `TestFromAC_ExcalidrawConventions`, `TestFromAC_DocIndexIntegration`
- Tests per category: happy 20, edge 4, boundary 9, error 0 (n/a)
- Total: 37 tests (4 FAIL + 33 ERROR due to missing file), 0 passed
- ruff: clean
- Commit: 566789c7

AC coverage table:
| AC | Class | Tests |
|---|---|---|
| AC1: file exists, valid JSON, source=owlbear, elements | TestFromAC_PipelineDiagramFile | 5 |
| AC2: 8 stages, 7 agents, planner/orchestrator auxiliary, stage order | TestFromAC_PipelineStagesAndAgents | 18 (8+7+2+1 parametrized) |
| AC3: describes list, 3 required globs, no kanban volatile glob | TestFromAC_DescribesField | 7 (3+3+1) |
| AC4: footer element, Last verified: YYYY-MM-DD (hash) format | TestFromAC_FooterElement | 2 |
| AC5: descriptive not authoritative | — | Non-testable semantic intent |
| AC6: unique IDs, fontSize >= 16, arrows bound | TestFromAC_ExcalidrawConventions | 3 |
| AC7: doc-index includes describes entry with required globs | TestFromAC_DocIndexIntegration | 2 |

All 37 tests fail in RED phase as expected (FileNotFoundError — file not yet created).
[[2026-04-20]]
## Builder Notes

### Files Changed
- `share/diagrams/pipeline.excalidraw` — created (1022 lines, 34 elements)
- `tests/test_pipeline_diagram_1033.py` — fixed module-level `_FOOTER_RE` constant (capital-L pattern vs lowercased `_all_element_text` output — incompatible as written by test-writer; changed to lowercase pattern)
- `.owlbear/doc-index.md` — auto-regenerated via `uv run doc-index`

### Test Results
37 passed, 0 failed — all `TestFromAC_*` classes GREEN

### Coverage
owlbear_tools doc_index exercised; 41% total (expected — test scope is diagram file, not full module)

### Lint
ruff clean on `tests/test_pipeline_diagram_1033.py` — no issues

### Evidence Summary
- AC1: file exists, valid JSON, `"type": "excalidraw"`, `"source": "owlbear"`, 34 elements ✓
- AC2: 8 stages (research→archived) in x-position order (100, 300, 500, 700, 900, 1100, 1300, 1500); 7 stage-transition agents labelled; planner + orchestrator as auxiliary text annotations ✓
- AC3: `describes` list with all 3 required globs; no `.owlbear/kanban/**` volatile glob ✓
- AC4: footer element `"Last verified: 2026-04-20 (3772c04f)"` ✓
- AC6: all 34 IDs unique; all text fontSize=16 or 28; all 7 arrows have both startBinding + endBinding ✓
- AC7: `uv run doc-index` produced `describes:` entry in doc-index ✓

### Builder-Discovered Fix
`_FOOTER_RE` in test file used capital-L pattern `r"Last verified: ..."` but `_all_element_text()` lowercases all text — these are inherently incompatible. Fixed `_FOOTER_RE` to use lowercase pattern. This is a module-level constant, not a `TestFromAC_*` class.

### Commit
`35fb4cf5` — `docs: add pipeline diagram with agent annotations (#1033, builder)`
[[2026-04-20]]
## Review Evidence

### Test Results
- pytest: 37 passed, 0 failed (independent run via quality-runner)

### Lint
- `tests/test_pipeline_diagram_1033.py`: clean (ruff exit 0 on Python file)
- Note: quality-runner flagged 87 violations on `share/diagrams/pipeline.excalidraw` — all false positives from ruff parsing JSON as Python. Not a code defect.

### Coverage
- owlbear_tools: 41% (expected — test scope is the excalidraw diagram artifact, not full module exercise)

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: file exists, valid JSON, source=owlbear | TestFromAC_PipelineDiagramFile (5 tests) | Yes — explicit assertions on each property | COVERED |
| AC2: 8 stages in order, 7 agents, planner/orchestrator auxiliary | TestFromAC_PipelineStagesAndAgents (18 parametrized + 1 order test) | Yes — parametrized per stage/agent; x-position sort validates order | COVERED |
| AC3: describes list, 3 required globs, no kanban volatile | TestFromAC_DescribesField (7 tests) | Yes — explicit presence/absence checks per glob | COVERED |
| AC4: footer element with YYYY-MM-DD (hash) format | TestFromAC_FooterElement (2 tests) | Yes — regex validates format after lowercase normalisation | COVERED |
| AC5: descriptive not authoritative | — | Non-testable semantic intent | N/A |
| AC6: unique IDs, fontSize ≥ 16, arrows bound | TestFromAC_ExcalidrawConventions (3 tests) | Yes — ID uniqueness, font size floor, binding presence | COVERED |
| AC7: doc-index describes entry | TestFromAC_DocIndexIntegration (2 tests) | Yes — generates index in tmp_path, reads actual output | COVERED |

No MISSING entries.

#### Security Review
- Excalidraw JSON: no executable content, no shell injection, no path traversal vectors, no credentials
- Test file: uses `shutil.copy` + `tmp_path`, well-constrained file access
- No issues

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `_FOOTER_RE` module-level constant | Changed from `r"Last verified: ..."` (capital-L) to `r"last verified: ..."` (lowercase) to match `_all_element_text()` lowercase normalisation | PRESERVED — correctness fix, not a weakening; original would permanently fail as false negative since helper lowercases all text |

No `TestFromAC_*` class or method bodies modified.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|---------|
| Assertion specificity | STRONG | Parametrized per stage/agent/glob; regex pattern; exact string matches |
| Negative/error-path coverage | ADEQUATE | Volatile glob absence tested; error cases N/A for static artifact |
| Mutation sensitivity | STRONG | Wrong stage name, missing glob, bad footer format, duplicate ID each break distinct tests |
| Test independence | STRONG | Module-scoped fixture; no shared mutable state |
| Descriptive names | STRONG | `test_volatile_kanban_glob_absent`, `test_stage_order_left_to_right`, etc. |

#### Data Safety
- No LLM output persistence; no mutable shared state; no unbounded input
- No issues

#### Implementation-Aware Gaps
- Static JSON artifact — no code branches to test
- No untested paths

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A (first attempt) |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- `test_arrow_elements_have_bindings` (line ~285): checks `not startBinding AND not endBinding` — catches fully floating arrows but would pass an arrow with only one binding, where AC6 requires both. Implementation satisfies the stricter requirement (all 7 arrows confirmed with both bindings). LAX assertion, no blocking impact.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: file + JSON + source=owlbear | `pipeline.excalidraw` line 2–4: `"type":"excalidraw"`, `"source":"owlbear"` | TestFromAC_PipelineDiagramFile | PASS |
| AC2: 8 stages in x-order (100–1500), 7 agents, orchestrator_text + planner_text as auxiliary | Confirmed elements with x-positions 100,300,500,700,900,1100,1300,1500; auxiliary annotations present | TestFromAC_PipelineStagesAndAgents | PASS |
| AC3: describes=[3 required globs], no kanban glob | `pipeline.excalidraw` lines 5–9; `.owlbear/kanban/**` absent | TestFromAC_DescribesField | PASS |
| AC4: footer_text = "Last verified: 2026-04-20 (3772c04f)" | element id=footer_text confirmed; matches lowercase regex `last verified: \d{4}-\d{2}-\d{2} \([0-9a-f]+\)` | TestFromAC_FooterElement | PASS |
| AC5: descriptive not authoritative | No authoritative commands or prescriptive instructions embedded in diagram | N/A | N/A |
| AC6: 34 unique IDs; all text fontSize ≥ 16; 7 arrows with startBinding+endBinding | Confirmed via quality-runner + Explore subagent review | TestFromAC_ExcalidrawConventions | PASS |
| AC7: doc-index `describes:` entry with all 3 globs | `.owlbear/doc-index.md` entry confirmed; integration test generates index in tmp_path and reads output | TestFromAC_DocIndexIntegration | PASS |

### Confidence: .97
### Verdict: PASS
[[2026-04-20]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | New diagram artifact only; no API, behavior, or conventions changed. `copilot-instructions.md` unchanged. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified. Builder fix was a test-file constant (`_FOOTER_RE`), not a public class/function. |
| 3 | External attribution | No | N/A | Only internal skills used (`h-excalidraw-diagram`, `r-pipeline-protocol`). No external repos or articles. |
| 4 | CLI changes | No | N/A | No CLI changes. |
| 5 | Research doc | No | N/A | No `.owlbear/research/` file for this task. Upstream reference is parent #1016 brief. |

### Doc-index
`share/diagrams/pipeline.excalidraw` entry verified in `.owlbear/doc-index.md` (line 17215) with 3 required `describes` globs; no `.owlbear/kanban/**` volatile glob present. Auto-regenerated by builder — no re-run needed.

### Scratch files
No `.owlbear/scratch/1033-*` files found. Clean.

### Files Updated
None — no docs changes required.

### Verdict
No-impact gate. All items N/A with evidence. Advancing to done.
[[2026-04-20]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: file exists, valid JSON, source=owlbear | `share/diagrams/pipeline.excalidraw` L1-4: `"type":"excalidraw"`, `"source":"owlbear"`, 34 elements | PASS |
| AC2: 8 stages in order, 7 agents, planner/orchestrator auxiliary | Spot-checked: 8 stages at x-positions 100-1500; reviewer confirmed all 7 agents + auxiliary annotations | PASS |
| AC3: describes=[3 globs], no kanban volatile | Spot-checked: 3 globs present (`owlbear-system.instructions.md`, `r-pipeline-protocol/**`, `*.agent.md`); no `.owlbear/kanban/**` | PASS |
| AC4: footer "Last verified: YYYY-MM-DD (hash)" | L1008-1009: `"Last verified: 2026-04-20 (3772c04f)"` | PASS |
| AC5: descriptive not authoritative | Non-testable semantic intent | N/A |
| AC6: unique IDs, fontSize ≥ 16, arrows bound | Reviewer confirmed: 34 unique IDs, all text ≥ 16px, 7 arrows with both bindings | PASS |
| AC7: doc-index describes entry | `.owlbear/doc-index.md` L17215 confirmed with 3 required globs | PASS |

### Test Results
- pytest: 834 passed, 6 failed (all outside task scope — knowledge/mcp-knowledge package), 4 skipped
- ruff: clean (0 violations)

### Architect Quality: 5/5
Refined AC was specific, complete, and provided a clean implementation path. Challenge results properly incorporated (planner taxonomy fix, volatile glob removal). Builder guidance referenced sibling task and skill conventions. No improvisation needed by builder.

### Deduction Breakdown
- Starting: 1.00
- AC lines with no evidence: 0 (-.00)
- Lint violations: none (-.00)
- AC quality ≤ 3: no (-.00)
- Missing reviewer evidence: no (-.00)
- Full-suite failures in task scope: none (-.00)
- Builder modified test-writer constant (`_FOOTER_RE` case fix): reviewer verified as correctness fix, not weakening (-.00)
- Unable to independently run `git log` for commit verification — files exist, hashes cited by builder/test-writer (-.02)

### Confidence: .98
### Action: archive