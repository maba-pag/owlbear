# SAST Coverage

> Owning task: #1419
> Date: 2026-05-08

## Tool Coverage Matrix

| Tool | Category | Scan Scope | Determinism |
|------|----------|------------|-------------|
| Ruff S-rules | Python SAST | Python source under `serve/*/src/` (plus tests/scripts in CI runs) | Yes |
| Gitleaks | Secret detection | Full repository content and commit history as scanned by MegaLinter | Yes |
| DevSkim | Pattern-based SAST | Source files across the repository | Yes |
| Trivy | Dependency and configuration security scan | Repository filesystem and dependency manifests | Mostly (depends on vuln DB version) |

## Production noqa S-rule Suppressions

The table below documents all production `# noqa: S...` suppressions and the global S-rule suppression in Ruff config.

| Rule code | Affected file(s) | Count | Justification |
|-----------|------------------|-------|---------------|
| S101 | `serve/*/src/*` (global in `pyproject.toml`) | 1 (global) | Production asserts are used as explicit contract and invariant checks. |
| S105 | `serve/knowledge/src/owlbear_knowledge/copilot_auth.py` | 2 | `*_TOKEN_URL` constants are endpoint URLs, not embedded credentials. |
| S311 | `serve/kanban/src/owlbear_kanban/engine.py` | 1 | Randomness is used only for human-readable slug generation, not security. |
| S506 | `serve/kanban/src/owlbear_kanban/storage.py` | 1 | Loader usage is constrained to a safe custom loader path. |
| S603 | `serve/kanban/src/owlbear_kanban/engine.py`; `serve/mcp-memory/src/owlbear_mcp_memory/git.py` | 3 | Subprocess invocations are fixed, trusted commands (`git`/`code`) with validated path inputs. |
| S607 | `serve/kanban/src/owlbear_kanban/engine.py`; `serve/mcp-memory/src/owlbear_mcp_memory/git.py`; `serve/knowledge/src/owlbear_knowledge/copilot_auth.py` | 4 | Partial executable paths intentionally call standard system binaries in controlled environments. |
| S608 | `serve/knowledge/src/...` (multiple modules); `serve/mcp-knowledge/src/...` | 15 | SQL string composition uses trusted table/column identifiers and parameterized values for user data. |

Total inline production suppressions: 26.

## MegaLinter Baseline Evidence

### CI trigger configuration

MegaLinter is configured in `.github/workflows/megalinter.yml` to run on:
- Push to `dev`
- Pull requests targeting `dev`
- Manual `workflow_dispatch`

The workflow keeps `continue-on-error: true` for report capture, then applies a final explicit failure step to preserve quality-gate behavior.

### Baseline execution confirmation

Baseline runs have executed after trigger enablement:
- Multiple (5+) pushes to `origin/dev` occurred after trigger addition.
- Merged automated fix PRs `megalinter-fixes-*` (including #66 and #71) confirm workflow execution and artifact generation.

This confirms the baseline CI scan is active and recurring.
