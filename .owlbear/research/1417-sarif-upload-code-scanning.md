# SARIF Upload to GitHub Code Scanning

> **Owning task:** #1417 — Add SARIF upload to GitHub Code Scanning in MegaLinter workflow
> **Date:** 2026-05-08 **Status:** Complete

## 1. Context and Question

The MegaLinter workflow already generates a SARIF report (`SARIF_REPORTER: true` in `.mega-linter.yml`) but does not upload it to GitHub Code Scanning. This means findings are only visible in the artifact download — not in the repository's Security tab. Parent research (#1413, gap G2) identified this as a moderate-severity gap.

**Question:** What workflow changes are needed to publish MegaLinter SARIF findings to GitHub Code Scanning?

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| [MegaLinter SARIF Reporter docs](https://megalinter.io/latest/reporters/SarifReporter/) | Official docs | 0.95 — canonical step template, file path |
| [GitHub docs — Uploading a SARIF file](https://docs.github.com/en/code-security/code-scanning/integrating-with-code-scanning/uploading-a-sarif-file-to-github) | Official docs | 0.95 — permissions, category, examples |
| [github/codeql-action/upload-sarif/action.yml](https://github.com/github/codeql-action/blob/main/upload-sarif/action.yml) | Action definition | 0.90 — input params, defaults |
| [oxsecurity/megalinter SarifReporter.md](https://github.com/oxsecurity/megalinter/blob/main/docs/reporters/SarifReporter.md) | Source code | 0.85 — confirms file path |
| `.github/workflows/megalinter.yml` (local) | Workflow | 0.95 — current structure, permissions, step order |
| `.mega-linter.yml` (local) | Config | 0.90 — confirms `SARIF_REPORTER: true` already set |

## 3. Analysis

### What Exists

- `SARIF_REPORTER: true` is configured — MegaLinter generates `megalinter-reports/megalinter-report.sarif`
- The SARIF file is already captured by the artifact upload step (`megalinter-reports` directory, retention 15 days)
- No upload to GitHub Code Scanning exists

### Required Changes

| Change | Detail |
|--------|--------|
| **Permission** | Add `security-events: write` to job permissions (required for all repos) |
| **Step** | Add `github/codeql-action/upload-sarif@v4` step (SHA-pinned per workflow convention) |
| **SARIF path** | `megalinter-reports/megalinter-report.sarif` (MegaLinter default) |
| **Condition** | `if: always()` per AC; ensures upload on lint failure |
| **Category** | `category: megalinter` — differentiates from future CodeQL or other SARIF sources |
| **Placement** | After "Upload MegaLinter reports" artifact step, before "Fail if lint failed" |

### `if: always()` vs `success() || failure()`

| Condition | On success | On failure | On cancel |
|-----------|-----------|-----------|-----------|
| `always()` | ✅ | ✅ | ✅ |
| `success() \|\| failure()` | ✅ | ✅ | ❌ |

The AC specifies `if: always()`. MegaLinter docs recommend `success() || failure()` (skips cancelled runs). Both achieve the AC intent. Recommend following AC literally — `if: always()` — for consistency with the existing artifact upload step which also uses `if: always()`.

### Permission Requirements

| Permission | Required? | Currently present? |
|------------|-----------|-------------------|
| `security-events: write` | Yes (all repos) | ❌ — must add |
| `contents: read` | Yes (private repos) | ✅ — covered by `contents: write` |
| `actions: read` | Yes (private repos) | ❌ — should add |

For private repos, GitHub docs explicitly require both `security-events: write` and `actions: read`.

### Prerequisite: GitHub Code Security

For private/internal repos, Code Scanning requires GitHub Code Security (formerly GHAS) to be enabled on the repository. If not enabled, the upload-sarif action will fail with: _"GitHub Code Security or GitHub Advanced Security must be enabled for this repository to use code scanning."_

**Risk mitigation:** The upload step should use `continue-on-error: true` so that SARIF upload failure (due to missing GHAS or missing SARIF file) doesn't break the lint workflow. The "Fail if lint failed" step already gates on MegaLinter's outcome, not on SARIF upload.

### SHA Pinning

The workflow pins all actions to commit SHAs. The builder must resolve `github/codeql-action/upload-sarif@v4` to its current SHA at implementation time.

## 4. Recommendation

**Proceed: add a single workflow step plus permission updates.** Confidence: **0.90**.

The change is minimal (one step + two permission lines), well-documented by both MegaLinter and GitHub, and follows established patterns in the existing workflow. The only risk is the GHAS prerequisite for private repos, mitigated by `continue-on-error: true`.

Challenge: skipped — trivial config change, no competing options.

## 5. Follow-up Tasks

No additional follow-up tasks needed. Task #1417 itself is the implementation task; this research provides the implementation specification.
