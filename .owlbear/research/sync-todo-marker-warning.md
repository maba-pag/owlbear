# Sync-to-Main TODO Marker Warning Step

> **Owning task:** #1426 — P1-05: Add sync-to-main TODO marker warning step
> **Date:** 2026-05-09 **Status:** Complete

## 1. Context and Question

The doc-writer quality redesign (parent #1421) introduced `> **TODO:**` markers for pre-existing doc issues. Before syncing dev→main, the CI workflow should warn (not block) when unresolved markers remain. Question: how to implement this as a GitHub Actions workflow step?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | [GitHub Actions Workflow Commands — docs.github.com](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands) | 1.0 — authoritative reference for `::warning::` annotation syntax |
| 2 | [freckle/grep-action](https://github.com/freckle/grep-action) | 0.3 — third-party action, overkill for this use case |
| 3 | Existing `sync-to-main.yml` in `.github/workflows/` (471 lines) | 1.0 — target file, reviewed in full |
| 4 | Brief `draft-doc-writer-quality/brief.md` §TODO Marker Format | 1.0 — defines the grep pattern |

## 3. Analysis

### Approach Comparison

| Criterion | Inline bash step | freckle/grep-action | Custom composite action |
|-----------|-----------------|---------------------|------------------------|
| Complexity | ~15 lines bash | External action dep | ~30 lines + action.yml |
| KISS | ✅ Best | ❌ Adds dependency | ❌ Over-engineered |
| Maintenance | Self-contained | Version pinning needed | Separate file |
| Flexibility | Full control | PR-only events | Full control |

### Implementation Details

**Warning syntax** (GitHub docs, Source 1):
```
echo "::warning title=TITLE::message"
```

**Grep pattern** (Brief, Source 4):
```
> \*\*TODO:\*\*
```

**Target files** (AC item 1):
- `serve/*/README.md`
- `README.md`
- `README-consumer.md`

**Placement**: After "Checkout dev branch" (line ~120, needs files on disk) and before "Validate selected paths exist on dev" (line ~148). The step runs unconditionally — markers in any README matter regardless of which sync scopes are selected.

**Behavior**: grep returns exit 1 when no matches → use `|| true` or `grep ... || true` to avoid step failure. Count files + total markers from grep output. Emit `::warning::` annotation only when count > 0.

### Current State

No `> **TODO:**` markers exist in target files today (verified via local grep). The step will be a no-op until doc-writer starts inserting markers per the redesigned `w-doc-update` skill.

## 4. Recommendation (confidence: 0.95)

Use a single inline bash step. ~15 lines, no external dependencies, aligns with KISS principle and existing workflow style.

Challenge: SKIP — trivial CI config change, no architecture decision.

### Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| `serve/*/README.md` glob fails (no matching files) | Low | Use `2>/dev/null` on grep |
| Annotation message too long (many markers) | Low | Truncate file list if > 5 files |

## 5. Follow-up Tasks

No new tasks needed — #1426 itself is the implementation task. Advancing to backlog for architect/builder pickup.
