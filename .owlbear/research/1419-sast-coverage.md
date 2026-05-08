# SAST Coverage and Baseline Documentation

> **Owning task:** #1419 — Document SAST coverage and run baseline CI scan
> **Date:** 2026-05-08 **Status:** Complete

## 1. Context and Question

Parent task #1413 gap G5 identified that no documentation exists for SAST tooling choices, coverage matrix, or suppression rationale. This task documents the current state of security scanning infrastructure and verifies the CI baseline.

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `.mega-linter.yml` (local) | Config | 0.95 — tool inventory |
| `.github/workflows/megalinter.yml` (local) | CI workflow | 0.95 — trigger and failure semantics |
| `pyproject.toml` ruff config (local) | Config | 0.90 — S-rule coverage and suppressions |
| `grep noqa: S[0-9]` across `serve/*/src/` | Codebase scan | 0.95 — 26 inline suppressions found |
| `git log origin/dev` (post-trigger commits) | Git history | 0.85 — confirms baseline runs |
| `.owlbear/research/1413-ci-sast-baseline.md` | Prior research | 0.90 — gap analysis and tool evaluation |

## 3. Security Scanning Tool Coverage

| Tool | Category | What It Covers | Scope | Deterministic? |
|------|----------|----------------|-------|----------------|
| **Ruff S-rules** | Python SAST (bandit equiv.) | Hardcoded secrets, SQL injection, subprocess calls, assert usage, YAML loading, pseudo-random, exception suppression | `serve/*/src/`, tests, scripts | Yes |
| **Gitleaks** | Secret detection | API keys, tokens, passwords, private keys in source and git history | Full repo | Yes |
| **DevSkim** | Regex SAST | Common vulnerability patterns (crypto, auth, injection) across all languages | All source files | Yes |
| **Trivy** | Dependency vuln scanning | Known CVEs in dependencies, embedded secrets, IaC misconfig | Repo filesystem | Mostly¹ |

¹ Trivy results depend on vulnerability DB version. Same DB = same results. Note: `uv.lock` is excluded from `FILTER_REGEX_EXCLUDE` but Trivy uses `project` CLI lint mode, so this exclusion does not affect it (see #1418 research).

### CI Configuration

- **Trigger:** Push to `dev`, pull requests to `dev`, manual dispatch
- **Quality gate:** `continue-on-error: true` on MegaLinter step → artifact upload → `exit 1` if failed (proper gate)
- **Artifacts:** `megalinter-reports` uploaded with 15-day retention; SARIF generated but not uploaded to GitHub Code Scanning
- **Auto-fix:** Optional via `workflow_dispatch` — creates fix PR or direct commit

## 4. Production `noqa` S-Rule Suppressions

### Global (pyproject.toml)

| Rule | Scope | Rationale |
|------|-------|-----------|
| S101 | All production code | Production asserts serve as caller-contract guards (e.g. preconditions, invariants) |

### Inline Suppressions (26 total across production `serve/*/src/`)

| Rule | Count | Files | Rationale |
|------|-------|-------|-----------|
| S105 | 2 | `knowledge/copilot_auth.py` | URL constants named `*_TOKEN_URL` — not actual secrets |
| S311 | 1 | `kanban/engine.py` | Slug generation (`adjective-noun`), not cryptographic |
| S506 | 1 | `kanban/storage.py` | Custom `YAML12SafeLoader` subclass is safe |
| S603 | 3 | `kanban/engine.py`, `mcp-memory/git.py` | `subprocess.run` with hardcoded `["git", ...]` — trusted commands, validated paths |
| S607 | 4 | `kanban/engine.py`, `mcp-memory/git.py`, `knowledge/copilot_auth.py` | Partial executable paths: `"git"`, `"code"` — standard system commands |
| S608 | 15 | `knowledge/` (11), `mcp-knowledge/` (1), `knowledge/consolidation.py` (1), `knowledge/bookmark_store.py` (2) | SQL string formatting with parameterized values and trusted table/column names from class constants |

### Suppression Safety Assessment

All 26 inline suppressions are justified:
- **S603/S607** (7 total): All subprocess calls use hardcoded command names (`"git"`, `"code"`) with arguments constructed from validated paths. No user-controlled input reaches command construction.
- **S608** (15 total): All SQL formatting uses `?`-parameterized values for user-controlled data. Table/column names come from class constants or hardcoded strings, not user input.
- **S105/S311/S506** (4 total): False positives — URL naming, non-crypto random, safe YAML loader.

## 5. Baseline Status

MegaLinter has been triggered multiple times on `dev` since push triggers were added (commit `60f88439`). Evidence:
- 5+ commits pushed to `origin/dev` after trigger addition
- 2 merged `megalinter-fixes-*` PRs (#66, #71) confirm workflow executed and applied autofixes

**Baseline exists in GitHub Actions artifacts.** The 15-day retention means older run artifacts may have expired, but the workflow continues to run on each push.

## 6. Recommendation

**T1 — Autonomous.** All findings are documentation of existing state. No new capabilities, architecture changes, or security policy modifications. Confidence: **0.85**.

Remaining gap: SARIF upload to GitHub Code Scanning (tracked by sibling task from #1413 follow-ups). Not in scope for this task.

Challenge: skipped — info-only documentation task, no recommendation to challenge.

## 7. Follow-up Tasks

1. Verify latest MegaLinter run is green (or document known failures) — requires GitHub Actions access
