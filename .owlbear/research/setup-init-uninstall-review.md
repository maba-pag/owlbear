# Setup Init Uninstall Review

> **Owning task:** User-requested review follow-up
> **Date:** 2026-08-19
> **Question:** How should `setup/init.py --uninstall` remove only OwlBear-owned project surfaces without deleting user data, following the initial and independent reviews?

## 1. Context and Question

The first draft used the current seed tree as an uninstall authority. That approach could not distinguish what setup actually created from content that merely matched the current seed. It also performed filesystem operations through unresolved destination paths.

The review decision was to use an install receipt as the ownership boundary. The receipt records paths created or merged by a successful setup run, post-install digests, claimed settings and MCP values, managed ignore-line additions, and directories created during setup.

Global Copilot reasoning settings remain preserved on uninstall by explicit user decision. They are written outside the project and shared across projects, so this workflow does not attempt to infer ownership or revert them.

## 2. Sources Studied

| Source | Fact used | Evidence limit |
| --- | --- | --- |
| Initial review in the user request | Identified parent-symlink escape, equality-as-ownership, nested-checkout deletion, JSONC loss, and report gaps | Review evidence was reproduced in temporary projects rather than treated as authority alone |
| Independent review in the user request | Identified install-created config leftovers, empty ignore files, partial-failure reporting, directory cleanup, CLI flag scope, API naming, and seed drift | Recommendations were reconciled against the current implementation and tests |
| `setup/init.py` | Owns seed copying, merge behavior, profile configuration, receipt creation, and uninstall traversal | Local source is authoritative for current behavior |
| `tests/test_setup_init_uninstall.py` | Exercises public init/uninstall and CLI behavior in temporary projects | Test coverage does not prove filesystem race resistance |
| `setup/setup-guide.md` | Defines the operator-facing uninstall contract and preserved global profile behavior | Documentation is updated as part of this change |

## 3. Analysis

### Confirmed pre-fix findings

1. A symlinked child directory could route a regular-looking leaf file outside the target and allow deletion or rewriting there.
2. The exact seed value was used as a proxy for ownership, deleting pre-existing identical settings and ignore rules.
3. A target nested under the OwlBear checkout was accepted, allowing destination paths to overlap the seed tree.
4. JSONC comments and formatting were lost when a merged file was rewritten.
5. Fresh setup-created skip-if-existing configuration files were always preserved, while empty directories were removed without recording whether setup created them.
6. A mid-operation failure could leave partial changes while discarding the accumulated action report.
7. `--yes`, the `interactive` API parameter, and the default report behavior did not express their actual contracts clearly.

### Implemented controls

- Added `.owlbear/install-manifest.json`, written atomically after successful setup.
- Recorded created-file ownership, post-install SHA-256 digests, settings/MCP claims, managed ignore-line additions, and setup-created directories.
- Made uninstall operate only on receipt-owned, unchanged content. Missing receipts take a conservative preserve path.
- Resolved every uninstall destination and preserve paths that resolve outside the target, including parent-directory symlinks.
- Refused the OwlBear checkout and all descendants.
- Preserved later JSONC or formatting edits by requiring the complete post-install digest before merged-file cleanup.
- Removed only recorded ignore-line additions and removed fresh empty files instead of leaving zero-byte artifacts.
- Restricted empty-directory cleanup to directories recorded as created by setup.
- Returned `UninstallResult` actions by default and retained actions in `UninstallError`; the CLI prints completed actions on failure.
- Renamed the public confirmation control to `confirm`, moved non-interactive refusal into `uninstall`, and gated uninstall-only CLI flags.
- Added the workspace-surface guard, shared merge-key predicate, and simpler ignore cleanup path.

### Recommendation, confidence, and limits

The receipt is the correct ownership authority for future installations because it records what setup actually did rather than reconstructing intent from a moving seed tree. Confidence is high for ordinary filesystem operations and the covered round-trip cases.

The receipt is created only after a successful setup run. Projects installed by older drafts without a receipt are handled conservatively and are not aggressively cleaned. A user who explicitly refreshes a pre-existing config receives no automatic restoration of the overwritten prior bytes; uninstall preserves that pre-existing file instead of deleting it. Global Copilot profile settings remain untouched by design.

## 4. Verification

The focused uninstall regression suite passes with 18 tests, including fresh-install cleanup, exact pre-existing values, JSONC preservation, parent symlinks, nested checkout refusal, seed drift, created-directory retention, partial-failure action retention, refresh-config preservation, and CLI flag gating.
