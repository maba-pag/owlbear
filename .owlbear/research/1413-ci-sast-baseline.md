# CI/SAST Baseline — Deterministic Security Scanning Infrastructure

> **Owning task:** #1413 — D2: CI/SAST baseline — deterministic security scanning infrastructure
> **Date:** 2026-05-08 **Status:** Complete

## 1. Context and Question

Task #1403 (pipeline review rethink) identifies CI/SAST as a prerequisite for B1 (reviewer rewrite). The reviewer currently performs cognitive security scanning; before that can be removed, deterministic automated scanning must be in place. This research evaluates whether the existing tooling meets the AC, identifies gaps, and proposes follow-up tasks.

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `.mega-linter.yml` (local) | Config | 0.95 — current SAST tool inventory |
| `.github/workflows/megalinter.yml` (local) | CI workflow | 0.95 — trigger, failure semantics, reporting |
| `pyproject.toml` ruff config (local) | Config | 0.90 — S-rule coverage and suppressions |
| [Ruff S-rules / flake8-bandit](https://pydevtools.com/handbook/how-to/how-to-enable-ruff-security-rules/) | Docs | 0.80 — rule coverage |
| [Best SAST Tools for Python 2026](https://appsecsanta.com/sast-tools/sast-tools-for-python) | Article | 0.75 — tool comparison |
| [Semgrep vs Bandit comparison](https://dev.to/rahulxsingh/semgrep-vs-bandit-python-security-scanning-compared-2026-5e5j) | Article | 0.70 — alternative evaluation |

## 3. Analysis

### Current Tool Inventory

| Tool | Category | Scope | Deterministic? | Status |
|------|----------|-------|----------------|--------|
| Ruff S-rules | Python SAST (bandit) | `serve/*/src/` | Yes | ✅ Active locally + CI |
| Gitleaks | Secret detection | Full repo history | Yes | ✅ Configured in MegaLinter |
| DevSkim | Regex SAST | All source files | Yes | ✅ Configured in MegaLinter |
| Trivy | Dep vuln + secrets + IaC | Repo filesystem | Mostly¹ | ⚠️ Partially broken |

¹ Trivy results depend on vulnerability DB version. Same DB = same results.

### Ruff S-Rule Baseline

Ran `ruff check --select S` across all `serve/*/src/`. Production code: **clean** — 0 unresolved findings. 14 inline `noqa` suppressions, all documented with rationale:

- S603/S607 (subprocess): git commands with trusted, validated paths (3 locations)
- S608 (SQL formatting): parameterized values, trusted table names (3 locations)
- S311 (random): slug generation, not crypto (1 location)
- S110/S112 (exception pass): intentional error suppression (3 locations)
- S506 (yaml.load): custom SafeLoader subclass (1 location)
- S101: globally suppressed in ruff config — intentional, production asserts serve as caller-contract guards

### Gap Analysis

| Gap | Severity | AC Impact |
|-----|----------|-----------|
| **G1: Manual-only trigger** — `workflow_dispatch` only, no push/PR trigger | Critical | Violates P1 "configured as CI step" — must run automatically |
| **G2: No SARIF upload** — SARIF generated but not pushed to GitHub Code Scanning | Moderate | Findings not in Security tab; no baseline tracking |
| **G3: uv.lock excluded** — `FILTER_REGEX_EXCLUDE` blocks `uv\.lock$` from all linters, breaking Trivy dep scanning | Moderate | Trivy can't read lockfile → incomplete dependency vulnerability coverage |
| **G4: Missing ruff src entry** — `serve/mcp-browser/src` not in `[tool.ruff] src` list | Low | Import classification only; linting still covers the files |
| **G5: No documentation** — tool choices, coverage matrix, and suppression rationale not documented | Moderate | Violates P2 "documented" |

### Alternative Tools Evaluated

| Tool | Fit | Verdict |
|------|-----|---------|
| Semgrep | Taint analysis, dataflow tracking | **Defer** — adds value for FastAPI/subprocess boundaries but overkill for baseline (conf. 0.55) |
| Bandit (standalone) | Python SAST | **Skip** — fully covered by Ruff S-rules |
| CodeQL | Deep semantic analysis | **Skip** — heavy, GitHub-hosted, redundant with existing stack |

### Failure Semantics (Corrected after challenge)

The workflow's `continue-on-error: true` on the MegaLinter step is properly resolved by a final `Fail if lint failed` step (`exit 1` when outcome ≠ success). **The workflow IS a proper quality gate** — `continue-on-error` just allows artifact upload and job summary before failing.

## 4. Recommendation

**Proceed: fix configuration gaps in the existing MegaLinter setup.** No new tools needed for baseline. Confidence: **0.78**.

Follow-up tasks address G1-G5. Once complete, the CI/SAST baseline will satisfy the AC and unblock B1 (reviewer rewrite).

Challenge: proceed — confidence in original: 0.36 → revised to 0.78 after correcting `continue-on-error` misconception, acknowledging Trivy lockfile gap, and reframing from "adequate" to "partially configured — needs gap fixes."

Semgrep is deferred as a separate enhancement — valuable for dataflow-oriented surfaces (FastAPI endpoints, subprocess boundaries, SSRF-aware browser navigation) but not required for the baseline gate.

## 5. Follow-up Tasks

1. **Add push/PR triggers to MegaLinter workflow** — add `push: branches: [dev]` and/or `pull_request` triggers
2. **Add SARIF upload step** — `github/codeql-action/upload-sarif` after MegaLinter step
3. **Fix uv.lock exclusion** — remove `uv\.lock$` from `FILTER_REGEX_EXCLUDE` or add separate Trivy config
4. **Add `serve/mcp-browser/src` to ruff src list** — minor config fix
5. **Document SAST coverage** — tool matrix, suppression rationale, scan scope in repo docs
6. **Run baseline CI scan** — execute workflow on dev, save report as baseline artifact (satisfies P3)
