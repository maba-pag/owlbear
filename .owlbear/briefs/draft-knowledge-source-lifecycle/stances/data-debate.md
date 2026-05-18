# Data Quality Debate Log — Knowledge Source Lifecycle

## Cycle 1

### Draft Position Summary

- O1: TypedDict expansion is backwards-compatible, low risk
- O2: Three-state conditional update model (success, all-failed, empty no-op)
- O3: Retyping from AUTHENTICATED_WEB to URL_LIST is low migration risk since `fetch_method` drives dispatch
- O4: `source_store.delete_cascade()` skips Qdrant vectors — critical orphan risk
- Dual cascade is a DRY violation; recommend removing `source_store.delete_cascade`
- `SourceInfo` TypedDict not derived from model — drift risk

### Critic Challenges (Confidence: 0.44, Pressure: high)

1. **O3 — "fetch_method drives dispatch" is wrong.** Refresh branches on `source_type` first. `URL_LIST` → `_handle_url_list` (direct `read_url`), `AUTHENTICATED_WEB` → `_handle_authenticated_web` (injected content fetcher). Retyping changes the handler path, not just a label. **Severity: critical.** *Accepted — this invalidates the "low risk" claim.*

2. **O2 — Skipped-only state is missing.** Unchanged-content refresh produces `skipped > 0, refreshed == 0, failed == 0`. This is a real, tested outcome (`test_direct_ingest_delta.py`). Three-state model omits it entirely. **Severity: critical.** *Accepted — expanded to four-state model.*

3. **O2 — Cancelled/blocked status aliasing.** `_record_ingest_outcome` aliases any status not in `{ok, partial, skipped, failed}` to `"ok"`. Cancelled ingest outcomes get counted as successes, inflating `refreshed` counter before `_update_source_record` runs. **Severity: critical.** *Accepted — flagged as pre-existing upstream contamination.*

4. **O4 — `document_store.delete_source_cascade` doesn't delete the source row.** It handles docs + pages + vectors but NOT the `knowledge_sources` row. Neither cascade is a complete replacement for the other. **Severity: critical.** *Accepted — revised from "pick one" to "compose both".*

5. **O4 — Fragmented transaction boundary.** `delete_document_data` commits per document; `delete_source_cascade` commits again for source_pages. N+1 commits vs single commit. **Severity: moderate.** *Accepted — noted as design weakness.*

6. **O1 — MCP schema tests may enforce TypedDict shape.** Adding fields changes the declared output schema. **Severity: moderate.** *Partially accepted — investigated further, tests check presence not exclusivity.*

7. **O2 — `last_error` carries warnings too.** Current implementation persists `errors + warnings` into `last_error`. The field is semantically overloaded. **Severity: moderate.** *Accepted — acknowledged in revised stance.*

8. **O3 — Existing tests expect AUTHENTICATED_WEB.** `test_direct_ingest_delta.py` explicitly asserts source type. **Severity: moderate.** *Accepted — added to evidence.*

9. **O3 — `resolve_by_url` and duplicate source risk.** If old sources are AUTHENTICATED_WEB and new ones URL_LIST, could duplicates be created? **Severity: moderate.** *Noted for investigation in Cycle 2.*

### Revisions Made

- O2: Expanded from three-state to four-state model (added skipped-only)
- O2: Flagged cancelled/blocked status aliasing as pre-existing contamination
- O2: Acknowledged `last_error` carries warnings
- O3: Revised from "low risk" to "medium risk — behavioral change"
- O3: Added duplicate-record concern via `resolve_by_url`
- O4: Revised from "pick one cascade" to "compose both" or "extend source_store cascade"
- O4: Added transaction fragmentation analysis

---

## Cycle 2

### Revised Position Summary

- O1: Low risk, known test impact (may need schema test updates)
- O2: Four-state model (success, skipped-only, all-failed, empty no-op) with upstream contamination caveat
- O3: Behavioral change, not label fix — recommend keeping AUTHENTICATED_WEB
- O4: Neither cascade is complete — compose or extend
- Dual cascade is complementary, not redundant

### Critic Challenges (Confidence: 0.54, Pressure: high)

1. **O2 — Cancelled refresh masquerades as other states.** Refresh handlers break loops on cancel, but early-exit produces partial counts that map to skipped-only or partial success. Four-state model still collapses materially different situations. **Severity: critical.** *Acknowledged but held firm — cancellation is a pre-existing bug in status aliasing, not in the O2 fix's domain. The four-state model is correct for the data `_update_source_record` receives; the contamination happens upstream.*

2. **O2 — "Empty no-op" conflates three different situations.** URL_LIST with no URLs (silent zero iteration), FILE_GLOB with no matches (returns zeros), and cancelled refresh (broken loop). All produce all-zero counters. **Severity: critical.** *Accepted — acknowledged the ambiguity but held firm that "preserve previous state" is the least-harmful default for all three. Added recommendation to log a warning on all-zero.*

3. **O2 — Aliasing evidence is asymmetric.** `cancelled` is definitely emitted by ingest; `blocked` may not have a current producer. Overstating evidence on `blocked`. **Severity: moderate.** *Accepted — softened language to focus on `cancelled` as the evidenced aliasing case.*

4. **O3 — Duplicate-record concern is not real.** `resolve_by_url` keys off `config.url`, and `name+scope` is unique. Identity rules prevent duplicates regardless of type. **Severity: moderate.** *Accepted — dropped duplicate-record concern from O3.*

5. **O4 — Both cascade methods are dead code.** Neither is called from the MCP layer. Discussion is about future wiring, not current callers. **Severity: moderate.** *Accepted — clarified that O4 is about wiring new code, not fixing existing callers.*

6. **O4 — SQLite-only path gets too much credit.** Single `commit()` is not the same as an explicit rollback-scoped transaction. **Severity: moderate.** *Partially accepted — noted but SQLite autocommit behavior makes the single-commit path still stronger than N+1 commits.*

7. **O1 — Test impact may be zero.** Schema tests check field presence, not exclusive key sets. Adding fields may not break tests. **Severity: minor.** *Accepted — softened from "known test impact" to "may not require test updates at all".*

8. **Blind spot — Integrity audit doesn't cover vectors.** `integrity.py` only audits SQLite-level orphans. No detection for Qdrant vector orphans. **Accepted — added to stance as a follow-up recommendation.**

9. **Blind spot — Metadata stamping differs.** AUTHENTICATED_WEB stamps `authenticated_web` origin; URL_LIST stamps `url` origin. Retyping changes metadata, not just handler. **Accepted — strengthened O3 argument against retyping.**

### Revisions Made

- O2: Acknowledged "empty no-op" ambiguity explicitly, added warning recommendation
- O2: Softened blocked evidence claim, focused on cancelled
- O3: Dropped duplicate-record concern (identity rules prevent it)
- O3: Added metadata stamping difference as additional evidence against retyping
- O4: Clarified both methods are dead code; O4 wires new code
- O4: Added integrity audit blind spot (no vector orphan detection)
- O1: Softened test impact claim

### Final Assessment

Position hardened across two cycles. The Critic's challenges improved the four-state model specification and corrected the O3 analysis substantially. The core findings — Qdrant orphan risk in O4, handler dispatch in O3, and state model completeness in O2 — survived adversarial pressure with refinements. Confidence stabilized at 0.80.
