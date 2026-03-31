# Reviewer Parallel Fan-Out — Design Validation

> **Owning task:** #265 — Enable parallel fan-out in reviewer agent
> **Date:** 2026-03-30 **Status:** Complete

## 1. Context and Question

The reviewer agent currently runs a 9-step sequential workflow (code-review skill). Steps 3–5 execute tests/lint/coverage; steps 6–7 perform read-only code analysis. These two groups are **fully independent** — code analysis doesn't need test execution results, and test execution doesn't need code analysis. The proposal: split the reviewer into a coordinator that dispatches Quality-Runner and Code-Reader as parallel subagents, then synthesizes their reports into a final verdict.

**Key questions:** (1) Is the step-to-subagent split clean? (2) What should the Code-Reader interface look like? (3) How does synthesis work? (4) What risks exist?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| S1 | VS Code Agents Concepts | https://code.visualstudio.com/docs/copilot/concepts/agents | .95 — "VS Code can spawn multiple subagents in parallel" |
| S2 | VS Code Subagents Guide | https://code.visualstudio.com/docs/copilot/agents/subagents | .95 — Multi-perspective review pattern ("Thorough Reviewer"), coordinator/worker |
| S3 | OwlBear subagent-nesting research | docs/research/subagent-nesting-architecture.md | .90 — §3d ranks reviewer benefit as "highest" (40-50% context savings) |
| S4 | OwlBear code-review skill | skills/code-review/SKILL.md | .90 — current 9-step sequential workflow, step dependencies |
| S5 | VS Code Custom Agents docs | https://code.visualstudio.com/docs/copilot/customization/custom-agents | .85 — agents array overrides disable-model-invocation; assign vs inherit |

## 3. Analysis

### 3a. Step-to-Subagent Mapping

| Review Step | Current Owner | Proposed Owner | Dependency |
|-------------|---------------|----------------|------------|
| 1. Read/claim task | Reviewer | Reviewer (coordinator) | None |
| 2. Check source control | Reviewer | Reviewer (coordinator) | None |
| 3. Run tests | Reviewer | Quality-Runner | None |
| 4. Run lint | Reviewer | Quality-Runner | None |
| 5. Run coverage | Reviewer | Quality-Runner | None |
| 6.0 Test-writer audit | Reviewer | Code-Reader | None — reads test files only |
| 6.1 Security review | Reviewer | Code-Reader | None — reads source only |
| 6.2 Test integrity | Reviewer | Code-Reader | None — reads test files only |
| 6.3 Test quality | Reviewer | Code-Reader | None — reads test code only |
| 6.4 Data safety | Reviewer | Code-Reader | None — reads source only |
| 6.5 Test gap analysis | Reviewer | Code-Reader | None — reads source+tests |
| 6.6 Necessity check | Reviewer | Code-Reader (conditional) | None |
| 7.1–7.4 Informational | Reviewer | Code-Reader | None |
| 8. AC compliance | Reviewer | Reviewer (synthesis) | Needs BOTH reports |
| 9. Verdict | Reviewer | Reviewer (synthesis) | Needs step 8 |

**Conclusion (.90 confidence):** The split is clean. Steps 3–5 and 6–7 have zero data dependencies on each other. Step 8 is the natural merge point. This matches the "Thorough Reviewer" multi-perspective pattern from VS Code docs (S2), where independent perspectives run in parallel and the coordinator synthesizes.

### 3b. Code-Reader Interface Design

**Mode:** Assign (.85 confidence). Needs only read tools — no terminal execution. Assign prevents scope creep and keeps the tool surface minimal.

**Tools (assign):** `read/readFile`, `read/viewImage`, `read/problems`, `search`, `vscode/memory`

**Why not inherit:** Inherit gives ~43 tools including terminal execution, file editing, and MCP. Code-Reader should never execute commands or modify files. Assign enforces this architecturally, not just by instruction (S5).

**Input contract:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| task_id | string | yes | Kanban task being reviewed |
| ac_lines | string[] | yes | Acceptance criteria lines |
| changed_files | string[] | yes | Files modified by builder |
| test_files | string[] | yes | Test files for this task |

**Output contract** (structured text sections):

| Section | Content |
|---------|---------|
| test_writer_audit | AC-to-test coverage table (COVERED/MISSING/LAX per AC line) |
| security_review | Findings or "No issues" |
| test_integrity | TestFromAC comparison table (PRESERVED/WEAKENED/REMOVED/STRENGTHENED) |
| test_quality | 5-dimension rating table (STRONG/ADEQUATE/WEAK) |
| data_safety | Findings or "No issues" |
| test_gaps | Untested implementation paths |
| necessity_check | Overlap findings (conditional) |
| informational | Code style, doc, structure notes |

**Error contract:** Code-Reader is read-only and deterministic — no retries needed. If a file can't be read, note it in the output. Max runtime: 3 min.

### 3c. Synthesis Workflow

After both subagents return, the reviewer coordinator:

1. **Parse reports** — extract Quality-Runner's test/lint/coverage results and Code-Reader's analysis
2. **Cross-walk** — merge test results with Code-Reader's AC coverage map. For each AC line: does the mapped test exist (Code-Reader) AND pass (Quality-Runner)?
3. **Build AC compliance table** — combined evidence from both reports
4. **Apply confidence threshold** — ≥.90 per agent-common
5. **Produce verdict** — PASS/FAIL with Channel B evidence and Channel A signal

**Critical synthesis rules:**
- Any MISSING or WEAK from Code-Reader = automatic FAIL (regardless of test pass rate)
- Any test failure from Quality-Runner = automatic FAIL (regardless of code quality)
- Security finding from Code-Reader = automatic FAIL
- Both reports clean + all AC lines mapped and passing = eligible for PASS

### 3d. Fallback Design

If either parallel subagent fails (crash, timeout, rate limit):

1. Reviewer detects the failure from the `runSubagent` error return
2. Falls back to the current sequential workflow (run all steps itself)
3. Notes the fallback in Channel B: "Parallel fan-out failed: {reason}. Fell back to sequential."

This is KISS-aligned (S3 §3a): the orchestrator's existing sequential-fallback pattern provides the model. The reviewer already knows how to do all 9 steps — the parallel dispatch is an optimization, not a capability change.

### 3e. Reviewer Agent Changes Required

| Change | Detail |
|--------|--------|
| `agents:` frontmatter | Change from `[]` to `['quality-runner', 'code-reader']` |
| Instructions | Add parallel dispatch section: dispatch both, await results, synthesize |
| Fallback clause | If either subagent fails, run full sequential workflow |
| `tools:` | Keep existing (still needed for fallback) |

### 3f. Code-Review Skill Changes

The skill needs a new "Parallel Fan-Out" section between Steps 2 and 3:

- **Step 2.5 (new):** Dispatch Quality-Runner (steps 3-5) and Code-Reader (steps 6-7) as parallel subagents. Pass changed_files, test_files, AC lines.
- **Step 8 (modified):** Synthesize from two structured reports instead of inline analysis.

## 4. Recommendations

| Item | Recommendation | Confidence |
|------|---------------|------------|
| Split viability | Clean split confirmed — zero data deps between groups | .90 |
| Code-Reader mode | Assign — minimal read-only tool surface | .85 |
| Code-Reader model | Same as reviewer (Sonnet 4.6 / GPT-5.4) — needs strong reasoning for security and test quality | .80 |
| Synthesis approach | Coordinator merge at step 8 — simple report combination | .90 |
| Fallback | Sequential fallback using existing skill steps | .90 |
| Task scope | #265 covers 4 AC items — consider splitting Code-Reader creation into a separate task for focus | .75 |

**Context savings estimate:** 40-50% (S3 §3d). Quality-Runner's terminal output (test results, lint output, coverage tables) stays in its subagent context. Code-Reader's file reads stay in its subagent context. The reviewer coordinator only sees summaries.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Create Code-Reader subagent (agent.md)" --priority needed --status ideation --tags "scope:agents,phase-2" --body "Design and implement the Code-Reader read-only analysis subagent per docs/research/reviewer-parallel-fan-out.md §3b. Assign-mode agent with read+search tools only.\n\nAC:\n- [ ] code-reader.agent.md exists with assign-mode tools, user-invocable: false\n- [ ] Covers steps 6.0-6.6 and 7.1-7.4 of code-review skill\n- [ ] Returns structured text report per §3b output contract\n- [ ] Read-only — no terminal execution or file editing tools\n\nDepends on: decision 228-parallel-fan-out approval"
```

Task #265 itself covers the reviewer wiring (dispatch, synthesis, fallback). The Code-Reader creation is a prerequisite that should be a separate task for cleaner delivery, similar to how #263 (Quality-Runner) was split out.

## 6. Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Subagent startup latency (2x) | Medium | Medium | Net positive: 40-50% context savings outweigh 2-5s startup per subagent |
| Code-Reader misses cross-cutting issue | Medium | Low | Synthesis step cross-walks both reports; reviewer retains domain knowledge |
| Both subagents need the same files | Low | High | VS Code handles concurrent file reads; no contention |
| Decision 228-parallel-fan-out not yet approved | High | Medium | #265 explicitly blocked pending this decision |
| Quality-Runner (#263) not yet built | High | Medium | #265 depends on #263; can't wire parallel until both subagents exist |
