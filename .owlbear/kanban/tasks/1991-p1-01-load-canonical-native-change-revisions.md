---
id: 1991
title: 'P1-01: Load canonical native change revisions'
status: collect
priority: medium
created: 2026-07-22T01:58:43.460559+02:00
updated: 2026-07-22T02:36:39.541139+02:00
tags:
  - phase-1
  - scope:core
  - authority
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-001
  - packet:DN-001-PK-001
parent: 1977
depends_on: []
ac:
  - 'AC-1: Given a contained `.owlbear/changes/<change_id>` package whose two Markdown
    files decode as UTF-8 and whose schema-version-1 decision and graph documents
    name the requested change, the public `ChangeRevision` loader returns one immutable
    revision with accepted decisions and the ten authored delivery sections addressable
    through stable IDs; verify through the public loader in a temporary workspace.'
  - 'AC-2: Given two packages that differ only by CRLF versus LF, trailing line breaks,
    YAML mapping order, or accepted-decision source order, `delivery-v1` returns the
    same SHA-256 digest; changing a Markdown character, accepted decision record,
    delivery sequence item, or delivery mapping value changes that digest; verify
    through the public digest boundary against canonical JSON vectors.'
  - 'AC-3: Given an absolute, traversing, null-containing, or symlinked change path;
    a missing authority file; BOM or non-UTF-8 Markdown; malformed YAML; a duplicate
    stable ID; or an unresolved graph reference, the public loader returns a structured
    diagnostic and no `ChangeRevision`; verify with table-driven temporary-workspace
    cases.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Bootstrap Projection Identity
- `change_id`: `replace-delivery-pipeline`
- `delivery_digest`: `9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8`
- `delivery_node_id`: `DN-001`
- `packet_id`: `DN-001-PK-001`

## Outcome
A public immutable `ChangeRevision` boundary joins the four authority files, resolves stable graph identities and references, computes `delivery-v1`, and rejects unsafe, malformed, or partial packages without returning partial authority.

## Scope
In scope: strict boundary models for the four authority files; strict UTF-8 Markdown reads; YAML-to-JSON-mode values; stable ID/reference indexing; the canonical delivery envelope and SHA-256 digest; contained non-symlink package/file reads; structured loader diagnostics; public package exports; durable loader, digest, and path-safety tests.

Out of scope: delivery completeness and admission rules; Kanban jobs; receipt persistence; receipt-chain validity; MCP, HTTP, and UI contracts.

## Authority
Resolve normative behavior from `DN-001`, `IF-001`, `RISK-004`, and `PROOF-001` in `.owlbear/changes/replace-delivery-pipeline/graph.yaml`. This bootstrap task cannot add, weaken, or supersede those obligations.

Proof guidance: exercise the public loader and digest boundary with a temporary filesystem replacement only; run focused package pytest plus package-export and downstream-import scans. Durable tests are justified by the shared identity and path-security boundary.

[[2026-07-22T02:16:40+02:00]]
## Builder Notes

### Change Envelope
- Added the public native `ChangeRevision` model, contained four-file loader, stable identity/reference index, `delivery-v1` digest, and structured load diagnostics inside `owlbear_kanban`.
- Added package-root exports and public-boundary proof for canonicalization, semantic changes, immutability, JSON projection, traversal, symlinks, encoding, schema, duplicate IDs, and unresolved references.
- Excluded admission completeness, job creation, receipt persistence/validity, MCP, HTTP, and UI behavior as shaped.

### Files Changed
- `serve/kanban/src/owlbear_kanban/change.py` (new): strict frozen authority models, loader, identity resolution, canonical digest, diagnostics, and deep-frozen execution projection.
- `serve/kanban/src/owlbear_kanban/__init__.py`: additive public exports.
- `serve/kanban/tests/test_change_revision.py` (new): durable public-boundary and security/identity regression cases.
- `tests/test_init_exports.py`: replaced an obsolete historical exact-cardinality assertion with cumulative established-export preservation; the retired `pick_dispatchable` exclusion remains.

### Module Map And Test Justification
- No production-module deviation from the shaped map. Existing `_naming.validate_path_containment` and `yaml_rt.make_yaml` are reused without modification; no dependency was added.
- The root export-test repair is a justified downstream proof update, not compatibility work: its prior assertion forbade any future public API growth.
- Durable tests pass the Rent Test because semantic identity, immutable authority, and path traversal are shared security/data-integrity boundaries whose regressions are hard to detect manually. Tests exercise the public loader/digest rather than private helpers.

### Evidence
- Real admitted package: zero diagnostics; `IF-001` and `DN-001` resolve; JSON projection succeeds; digest equals `9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8`.
- Focused loader suite: 18 passed.
- Mapped kanban regression: 920 passed (`serve/kanban/tests`, root `test_engine_*`, `test_kanban_*`, and touched export contract).
- `uv run lint` on the four source/test paths passed all applicable hooks; four unrelated pre-existing TODO warnings were informational.
- Editor diagnostics and `git diff --check`: clean.
- `builder-challenger`: `decision: pass`; reran 920 tests and real-package digest smoke, applied no fixes, and authorized advancement to verify.

### Residual Boundary
- Receipt persistence and read-only change health remain intentionally owned by dependency-gated packet #1992.

[[2026-07-22T02:36:39+02:00]]
## Verify Notes

### Boundary And Authority
- Verified builder commit `85ca0918447b4cb5a3437ef11a4f6328a7f98ee5` against task AC-1 through AC-3 and admitted `DN-001`, `IF-001`, `RISK-004`, `PROOF-001`, plus design sections 3 and 4.
- The changed production modules match the shaped map: native authority remains in `owlbear_kanban.change`, package-root exports are additive, and existing naming/YAML owners are reused. No interface or scope deviation found.
- Exercised the normal public `load_change` and digest boundary with only temporary filesystem replacement below it.

### Findings And Patches
- Patched `DecisionOption.confidence` to reject non-finite YAML numbers before canonical JSON hashing; the public loader now returns `ERR_CHANGE_SCHEMA_INVALID` and no revision instead of raising `ValueError`.
- Patched diagnostic projection to expose bounded path basenames rather than absolute paths.
- Removed unrestricted unsafe change IDs from diagnostic targets. Serialized probes confirmed temporary/workspace roots and absolute caller inputs are absent.
- Files patched by verifier: `serve/kanban/src/owlbear_kanban/change.py`. No durable test, helper, abstraction, or unrelated cleanup added.

### Evidence
- Focused public loader/export suite: 47 passed.
- Mapped kanban regression: 920 passed.
- Real admitted package: zero diagnostics, 20 accepted decisions, `IF-001` and `DN-001` resolve, JSON projection succeeds, and digest equals `9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8`.
- Adversarial probes covered non-finite confidence, symlinked changes root, missing-file path redaction, and unsafe-ID target redaction.
- Repository lint passed all applicable hooks on the four reviewed source/test paths; four unrelated TODO notices were informational. Editor diagnostics and `git diff --check` were clean.
- Initial challenger rejected absolute diagnostic paths. Rechallenge rejected raw unsafe-ID targets. Both findings were repaired and revalidated.
- Final `verifier-challenger`: `decision: pass`; all prior findings closed and PASS to collect explicitly authorized.

### Route
PASS. Advance #1991 to collect for mechanical archival.
