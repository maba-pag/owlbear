# Reviewer Rewrite — Batch Findings, Trust Model, Protocol Update

> **Owning task:** #1407 — B1: Reviewer rewrite — batch findings, finding vs opinion, trust builder evidence, protocol update
> **Date:** 2026-05-08 **Status:** Complete

## 1. Context and Question

The current `w-code-review` skill (386 lines) has three structural problems identified in the pipeline review rethink (#1403):

1. **First-failure gating** — Steps 5.0–5.7 each declare "Any X = automatic FAIL," letting the reviewer stop after one finding. This turns 2 legitimate findings into 8+ pipeline runs.
2. **Redundant test execution** — The reviewer re-executes the same tests the builder already ran via quality-runner, doubling compute for no incremental value (auditor runs the full suite as the final gate).
3. **Heavyweight checklist** — 8 critical + 4 informational checks (~280 lines) diffuse attention across security review, necessity check, data safety, etc. — concerns now covered by CI/SAST (#1413 archived).

This research validates the rewrite approach from Brief B1 and identifies specific change boundaries.

## 2. Sources Studied

| Source | Type | Relevance | What |
|--------|------|-----------|------|
| Google Eng Practices — Review Standard | [Web](https://google.github.io/eng-practices/review/reviewer/standard.html) | .85 | "Nit:" prefix for non-blocking comments; approve when code health improves; don't seek perfection |
| Conventional Comments | [Web](https://conventionalcomments.org/) | .75 | Formal label taxonomy: issue vs suggestion vs nitpick; blocking vs non-blocking decorations |
| `.owlbear/research/two-pass-review-checklist.md` | Prior research | .90 | Established the two-pass (Critical/Informational) pattern; this research replaces it with finding/opinion |
| `w-code-review` SKILL.md (current) | Codebase | .95 | 386-line heavyweight skill with 8 critical + 4 informational checks |
| `r-pipeline-protocol` SKILL.md (current) | Codebase | .95 | Trust model: "Never trust self-reports"; evidence principles |
| `.owlbear/research/1413-ci-sast-baseline.md` | Prior research | .90 | CI/SAST now covers: Ruff S-rules, Gitleaks, DevSkim, Trivy — reviewer security scanning is redundant |
| `reviewer.agent.md` + `code-reader.agent.md` | Codebase | .85 | Current agent configs and subagent contracts |
| Pipeline rethink brief | `.owlbear/briefs/draft-pipeline-review-rethink/brief.md` | .95 | B1 deliverable spec + D2/D3 decisions |

## 3. Analysis

### 3.1 Current → New Structure Map

| Current | Lines | New | Rationale |
|---------|-------|----|-----------|
| Step 0 (Setup) | 6 | Keep (unchanged) | Standard claiming, AC noting |
| Step 1 (Source control) | 30 | Keep (simplified) | Commit hash, changed-file list; dirty-tree check retained |
| Step 2 (Evidence gathering — run tests) | 55 | **Replace**: Read builder evidence | D2 trust model; read quality-runner output from task body |
| Step 5.0 (TestFromAC audit) | 15 | **Merge**: → Test→AC alignment checklist item | Finding-vs-opinion replaces automatic FAIL |
| Step 5.1 (Security review) | 15 | **Remove** | CI/SAST (#1413) handles deterministically |
| Step 5.2 (TestFromAC immutability) | 20 | **Remove** | AC explicitly removes this rule |
| Step 5.3 (Test quality) | 15 | **Merge**: → Proof sufficiency checklist item | Assertion specificity becomes proof-quality check |
| Step 5.4 (Data safety) | 8 | **Remove** | CI/SAST + proof sufficiency covers |
| Step 5.5 (Test gap analysis) | 10 | **Merge**: → Test→AC alignment checklist item | Same concern, different framing |
| Step 5.6 (Necessity check) | 10 | **Demote**: → Observation | Non-AC-rooted concern → opinion |
| Step 5.7 (Builder process quality) | 15 | **Keep** (simplified) | Loop detection is still useful, but informational |
| Steps 6.1–6.4 (Informational) | 15 | **Merge**: → Observations | Already non-blocking |
| Step 7 (AC compliance) | 15 | **Merge**: → AC→Code mapping checklist item | Core of the new model |
| Step 8 (Verdict) | 35 | Keep (simplified) | Binary verdict, batch findings |
| Output template | 45 | **Replace** | Two-section template (Review Evidence + Observations) |

**Projected new size:** ~120–150 lines (vs 386 current). Net deletion: ~240 lines.

### 3.2 Three-Item Checklist Design

| # | Item | What reviewer checks | Finding trigger |
|---|------|---------------------|-----------------|
| 1 | AC→Code mapping | For each AC line: does the implementation satisfy it? Cite file:line evidence. | AC line not implemented, or implementation contradicts AC |
| 2 | Test→AC alignment | For each AC line: does a test exist that would fail if the AC were violated? | Missing test, or test would pass even if AC were violated (false green) |
| 3 | Proof sufficiency | Are assertions specific enough? Do boundary examples exist? | Lazy assertions (`assert result`), missing edge cases in AC-natural branches |

Each finding must cite an AC line or factual code/test deficiency. No citation → goes to Observations.

### 3.3 Trust Model Change

| Dimension | Current | New |
|-----------|---------|-----|
| Test execution | Reviewer runs quality-runner | Reviewer reads builder's quality-runner output |
| Security scanning | Reviewer cognitive scan (5.1) | CI/SAST deterministic scan |
| Test immutability | Reviewer enforces TestFromAC immutability | Removed; test-curator handles post-archive |
| Evidence trust | "Never trust self-reports" | "Upstream evidence is valid input. Verify through independent checks only when cost-justified." |
| Final safety net | Reviewer | Auditor (full suite run, cross-task integration) |

### 3.4 Code-Reader Impact

The code-reader agent contract is defined within `w-code-review` (Consumer Contract section). Current 8-section output maps to Steps 5.0–5.7 + 6.1–6.4. Under the new model:

- Sections `test_writer-audit`, `test_integrity`, `test_quality`, `test_gaps` → collapse into the 3-item checklist
- `security_review`, `data_safety` → removed (CI/SAST)
- `necessity_check` → becomes Observation-level
- `informational` → becomes Observations

The code-reader interface needs updating in the w-code-review rewrite (it's defined there). The code-reader agent file itself will need a follow-up update to match.

### 3.5 Reviewer Agent File Impact

`reviewer.agent.md` needs updates:
- Remove `quality-runner` from `agents:` list (no longer dispatched by default; read from task body)
- Update `<persona>` — remove "run tests yourself" language
- Update `<critical_rules>` — remove "Never trust builder self-reports"
- Update boundaries — remove TestFromAC enforcement
- Update examples — align with new output format

### 3.6 Repo Memory Impact

Six `reviewer-*.md` files in `/memories/repo/` contain operational patterns. After the rewrite:
- **Still valid:** `reviewer-routing.md`, `reviewer-proof-quality.md` (most entries), `reviewer-false-green-catalog.md`
- **Needs update:** `reviewer-coverage.md` (references to quality-runner dispatch model), `reviewer-proof-quality.md` (immutability-related entries become obsolete)
- **Consider consolidation:** memory curator should clean up post-rewrite

## 4. Recommendation

**Proceed with B1 as specified.** Confidence: .90.

The brief's design is well-grounded: batch findings reduces iteration spirals, finding-vs-opinion enforces objectivity, and CI/SAST provides the deterministic safety net that makes cognitive security scanning redundant. The three-item checklist is a strict subset of the current 12-check system, covering the same value with ~60% less skill text.

**Key risk:** Builder fabricating quality-runner results. Mitigation: auditor runs the full suite independently. If a fabrication slips through reviewer, auditor catches it. Confidence in this mitigation: .85 (auditor already runs full suite).

**Secondary risk:** Code-reader contract drift. The code-reader's 8-section contract is defined in w-code-review and must be updated during the rewrite. The code-reader agent file needs a follow-up task.

Challenge: FALLBACK — no challenger dispatched for T1 skill rewrite with explicit brief backing.

## 5. Follow-up Tasks

| # | Title | Status | Rationale |
|---|-------|--------|-----------|
| 1 | B1 implementation: w-code-review rewrite + r-pipeline-protocol trust model update | backlog | The implementation task itself — rewrite skill, update protocol |
| 2 | Code-reader agent update — align with new w-code-review contract | backlog | code-reader.agent.md references obsolete 8-section contract |
| 3 | Reviewer agent file update — align with new w-code-review model | backlog | reviewer.agent.md persona, rules, examples need alignment |
