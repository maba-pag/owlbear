# CI Sync — Build SPA Bundle into Main Branch

> **Owning task:** #938 — P3-02: CI sync — build SPA bundle into main branch
> **Date:** 2026-04-19 **Status:** Complete

## 1. Context and Question

The sync-to-main workflow copies product files from `dev` to `main`. Since `serve/cockpit/dist/` is gitignored on dev (never committed), consumer clones of main lack the SPA bundle. Users must have Node/npm to build it themselves — violating D15 (no Node toolchain required for consumers).

**Question:** How to extend the workflow so `dist/` is built in CI and included on main?

## 2. Sources Studied

| Source | Relevance | What was taken |
|--------|-----------|----------------|
| `.github/workflows/sync-to-main.yml` (codebase) | 1.0 | Current workflow structure, SHA-pinned actions pattern |
| `serve/cockpit/web/vite.config.ts` (codebase) | 1.0 | `outDir: '../dist'` → output lands at `serve/cockpit/dist/` |
| `serve/cockpit/src/owlbear_cockpit/main.py` (codebase) | 0.9 | Backend expects `dist/` at `serve/cockpit/dist/` |
| `.gitignore` + `serve/cockpit/web/.gitignore` (codebase) | 0.9 | Both ignore `dist/` — tracked files unaffected |
| `serve/cockpit/web/package.json` (codebase) | 0.8 | Build script: `tsc -b && vite build`; Node ≥20.19 |
| `serve/cockpit/web/.nvmrc` (codebase) | 0.7 | Pins Node 20.19.0 |
| GitHub `actions/setup-node` docs | 0.8 | `node-version-file` reads `.nvmrc`; `cache: 'npm'` optional |

## 3. Analysis

### Implementation Approach (single viable option)

Insert build step between "Build consumer tree" and "Detect changes":

```yaml
- name: Setup Node.js
  uses: actions/setup-node@<SHA>  # v4
  with:
    node-version-file: serve/cockpit/web/.nvmrc

- name: Build cockpit SPA
  working-directory: serve/cockpit/web
  run: npm ci && npm run build

- name: Stage built SPA bundle
  run: git add -f serve/cockpit/dist/
```

### Key Design Points

| Concern | Resolution |
|---------|------------|
| `dist/` in `.gitignore` | `git add -f` overrides ignore rules; tracked files stay visible to cloners |
| `node_modules/` exclusion | Never staged — only `git add -f serve/cockpit/dist/` is explicit |
| Build failure blocks sync | Default GHA behavior: non-zero exit fails the step → job fails |
| Node version | Read from `.nvmrc` (20.19.0) — single source of truth |
| Output path | `serve/cockpit/dist/` (not `web/dist/`) — confirmed by vite `outDir: '../dist'` |
| SHA pinning | Must pin `actions/setup-node` SHA matching existing `actions/checkout` pattern |
| npm caching | Optional (`cache: 'npm'`, `cache-dependency-path`) — workflow runs rarely |

### Alternatives Considered

| Option | Verdict | Reason |
|--------|---------|--------|
| Commit dist/ to dev | Rejected | Pollutes dev history, merge conflicts, violates clean-source principle |
| Separate build workflow + artifact | Rejected | Over-engineering for a manual-dispatch sync |
| Modify .gitignore on main only | Unnecessary | Tracked files are not affected by .gitignore |

## 4. Recommendation

**Single clear approach** — add 3 steps to the existing workflow (confidence: 0.92).

No alternatives merit a comparison matrix. The pattern is well-established (build-then-deploy in CI), the workflow structure accommodates it cleanly, and all edge cases resolve naturally.

Challenge: SKIPPED — trivial implementation with single viable approach, no trade-off between options.

## 5. Follow-up Tasks

Task #938 itself is the implementation task — no additional research-status tasks needed. The task already has concrete AC and a single file to modify. Ready to advance to backlog.
