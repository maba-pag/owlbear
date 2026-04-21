# Synthesis — Documentation Currency Brief

**Synthesiser:** Pragmatist
**Brief:** draft-docs-currency-2026-04-19
**Stances evaluated:** Architect (0.88), Data (0.88), End-User (0.85), Security (0.88)

---

## Convergences

### 1. Root cause is scope definition, not execution quality

All four panelists agree: doc-writer does its declared job correctly; its declared job excludes ~70 of 76 product docs. The fix is structural expansion of scope, not behavioral correction.

- **Architect:** "scope-definition failure, not an execution failure"
- **Data:** centers the index as the mechanism to close the scope gap
- **End-User:** accepts the broadened scope but demands gating to prevent cry-wolf
- **Security:** "right operational direction" — the current 5-path scope IS the root cause of rot

### 2. Auto-generated doc-index as central artifact

All four panelists support a deterministic, regeneratable doc-index that enumerates the product-doc surface. No dissent on the concept. The index is consumed by doc-writer v2 and doc-audit. It is never hand-edited. It regenerates on demand. Divergences on format, enumeration strategy, and metadata are flagged below, but the artifact itself is unanimous.

### 3. Two-layer safety net (per-task + periodic)

All four agree on the architecture: Layer 1 is doc-writer v2 running per-task at the docs pipeline phase. Layer 2 is doc-audit.prompt.md running on user invocation as a repo-wide backstop.

- **Architect, Data, End-User:** describe this explicitly
- **Security:** presupposes both layers and focuses on bounding their risk

### 4. doc-audit mirrors agent-audit structurally

Architect, Data, and End-User converge on agent-audit's process architecture as the template: standards-loading preamble → scan → severity queue → one-finding-at-a-time loop with askQuestions → pause/bail. Security adds loop-bound constraints (max 3 re-scan cycles) but does not contest the mirror structure.

### 5. YAML index format (3 of 4)

Architect, Data, and Security converge on YAML (or JSON) and explicitly reject markdown:

- **Architect:** YAML — machine-parseable, human-readable, supports structured metadata
- **Data:** YAML — "markdown is not [acceptable]… this is a data integrity constraint, not an implementation preference"
- **Security:** JSON/YAML — markdown headings interpolated into shell commands are an injection vector

End-User dissents (see Disagreement §2).

### 6. r-doc-standards skill is required

Architect calls it "non-negotiable" — without citable rules, doc-audit findings are subjective opinions. Data's index schema and cross-reference constraints presuppose codified rules. End-User and Security do not contest the need — End-User's audit-dimension model and Security's compliance requirements both depend on standards existing. The skill should be `r-` prefixed (SHALL/MUST constraints), not `h-` (handbook).

### 7. User-gated deletion — doc-writer never deletes autonomously

All four panelists agree deletion requires human approval. doc-writer proposes; user decides. Mechanism and granularity diverge (see Disagreement §5).

### 8. Diagrams in share/diagrams/, git-tracked

Architect proposes `share/diagrams/` as the location — synced to main, single discovery point, accommodates cross-cutting diagrams. End-User requires diagrams in synced paths (consistent). Security and Data do not contest the location. All agree diagrams are git-tracked (Excalidraw JSON is text, diffs are readable).

### 9. Decomposed sweep via normal pipeline tasks

Architect and End-User both reject a single mega-task or custom sweep mechanism. Standard kanban tasks with proper TDD, review, and docs gates. They differ on granularity (see Disagreement §6) but agree on the decomposition principle.

### 10. doc-writer v2 scope gating preserves the 90/80 no-op rate

Architect and End-User agree that broadened scope must NOT mean doc-writer checks all 76 docs for every task. The relevance-to-current-task heuristic must remain, mediated by the index. doc-audit is the backstop for whatever per-task assessment misses. Data and Security do not contest this.

---

## Disagreements

### 1. Index enumeration strategy: exclusion-list vs allowlist

**Architect vs Data.**

- **Architect:** Filesystem walk with hardcoded directory exclusions in the script (`.owlbear/research/`, `.owlbear/kanban/`, `tests/`, etc.). Allowlist is rejected as "brittle — new doc types require agent-file edits."
- **Data:** Allowlist of glob patterns in a separate config file (`.owlbear/doc-index.config.yaml`). Exclusion lists are rejected as "fail open — new working directories auto-include as docs." Allowlist fails closed; `doc-audit` catches unrecognized files as a safety net.

**Nature of tension:** Failure-mode preference. Architect accepts false-includes (caught by human review); Data accepts false-excludes (caught by doc-audit). Data's allowlist + config-file separation is more defensive; Architect's exclusion approach is simpler but less safe by default.

### 2. Index format: YAML vs markdown

**Architect + Data + Security vs End-User.**

- **Architect, Data, Security:** YAML (or JSON). Markdown requires fragile regex parsing, creates implicit schema assumptions, and introduces shell-injection risk when headings are interpolated.
- **End-User:** Markdown — "agents parse markdown reliably; humans scan it trivially; git diffs are meaningful." JSON/YAML "add a parser dependency for human reading."

**Nature of tension:** Audience priority. End-User optimizes for the solo dev debugging doc-writer decisions in VS Code. The other three optimize for programmatic consumers and data integrity. Security adds a concrete attack scenario (markdown heading `# $(rm -rf /)` interpolated into shell).

### 3. Diagram metadata strategy — three competing answers

**Architect vs Data vs End-User.** (Security defers to git-mtime comparison, closest to End-User.)

- **Architect:** "Filename IS the metadata, no per-diagram config." The doc-index includes diagrams as category `diagram`; doc-writer matches filenames to code areas. No additional metadata needed.
- **Data:** Per-diagram `describes` field required in the index — a hand-authored list of paths/concepts the diagram covers, authored at creation time. Without it, drift detection is impossible mechanically. Acknowledges this violates "no hand-maintained fields" but defends it as a controlled exception (authored once, immutable, validated by doc-audit).
- **End-User:** In-diagram `Last verified YYYY-MM-DD (abc1234)` footer text element. Machine-checkable (doc-audit compares date/hash against recent commits). Reader-facing freshness signal.

**Nature of tension:** These are not mutually exclusive in principle but represent different philosophies. Architect: zero metadata overhead. Data: mechanical drift detection requires explicit linkage. End-User: reader trust requires visible freshness signal. The Data and End-User approaches could coexist (describes field in index + footer in diagram), but Architect's "no metadata" position conflicts with both.

### 4. Index script location: .owlbear/ vs synced path

**Architect vs End-User + Security.**

- **Architect:** `.owlbear/scripts/doc-index.py` — project-ops tooling, serves the pipeline, belongs alongside hooks. Test in `tests/test_doc_index.py`.
- **End-User:** Must live in a synced path (`setup/` or `serve/`) so consumers can regenerate the index for their own tree. If it lives in `.owlbear/`, consumers can't use it.
- **Security:** "The index script ships to consumers as executable code" — implies synced path. Adds: must be minimal, auditable, stdlib-only.

**Nature of tension:** Whether consumers need the index generator. Architect treats the index as dev-only pipeline tooling. End-User and Security treat it as a product artifact that consumers must be able to run. This depends on whether consumer projects use doc-writer v2 with their own doc surface (they do, per M2 outcome 1's "OwlBear-shipped paths are marked" — which implies consumers have their own index).

### 5. Deletion granularity and mechanism

**Architect vs Data + End-User + Security.**

- **Architect:** Route through existing DR (decision-request) mechanism via scribe. During the sweep, aggregate multiple deletions into a single DR with a table of files + reasoning. Per-task, each deletion creates a separate DR.
- **Data:** Per-proposal with full blast-radius (inbound links listed). Deletion + inbound-link repair in a single logical commit. Broken inbound links are "data corruption." No batch.
- **End-User:** One task per deletion file. Must not be buried inside fix tasks.
- **Security:** One file per deletion task. Must include first 10 lines of actual content (not just agent summary). Agent-executable files (`share/skills/`, `share/instructions/`, `share/prompts/`, `SECURITY.md`) require architect-authored AC, not just user approval.

**Nature of tension:** Two axes. (a) **Granularity:** Architect allows aggregation during sweep; Data/End-User/Security want per-file. (b) **Mechanism:** Architect reuses DRs (existing pipeline concept); others use kanban tasks (more visible, more structured). (c) **Data's unique add:** inbound-link repair must be transactional with deletion. (d) **Security's unique add:** agent-executable file deletion needs higher authority (architect AC).

### 6. Hook redesign as blocking prerequisite

**Security vs Architect + Data + End-User.**

- **Security:** The `deny-code-writes.py` refactor to extension-based allowlist is a **blocking prerequisite** for doc-writer v2. "Do not ship doc-writer v2 with the current deny-list hook." The current hook permits writes to consumer source code in arbitrary directory structures. Additionally: seeded consumer hook must be the most restrictive variant (`.md` only); owlbear-dev can be broader. Two separate hook files.
- **Architect, Data, End-User:** Do not mention the hook as a prerequisite or address the consumer-safety gap.

**Nature of tension:** Security raises a genuine safety gap that the other three panelists did not consider. The gap is concrete: consumer projects with source in `src/`, `lib/`, or `app/` get zero protection from the current directory-based deny-list. Whether this is a blocker for the Brief's implementation or a parallel workstream is the decision.

---

## Recommendation

**Proceed with the two-body design (sweep + process redesign) as architected.** The four panelists are broadly aligned on the structural approach — the disagreements are on implementation details, not direction. The following path resolves the clear convergences and surfaces the open decisions:

### Immediate (Phase 0 — prerequisite tooling)

1. **Create `r-doc-standards` skill** — non-negotiable per Architect; presupposed by all.
2. **Create doc-index script + YAML output** — convergence on the artifact; format is YAML (3-of-4 convergence, with Security's injection concern reinforcing). Enumeration strategy (allowlist vs exclusion) is an open question (§1 above).
3. **Create `doc-audit.prompt.md`** — mirror agent-audit with End-User's pre-scan summary addition (uncontested enhancement).
4. **Refactor `deny-code-writes.py` to extension-based allowlist** — Security's finding is a genuine safety gap. Even if not formally a "blocker," it should be addressed in Phase 0 alongside other tooling, before doc-writer v2 ships. The cost is low (hook refactor is a small task); the risk of deferral is high (consumer source code exposure).

### Phase 1 — Agent redesign

5. **Redesign doc-writer v2** with index-derived scope + End-User's scope-gating (per-task relevance filtering). Ship gating and broadened scope together (End-User's warning: without gating, broadened scope is a net UX negative).

### Phase 2–3 — Remediation + diagrams

6. **Sweep tasks decomposed by area** (~8-10 tasks per End-User's grouping — pragmatic for board usability). Deletion tasks are per-file, not aggregated (3-of-4 convergence).
7. **7 diagram tasks** with diagram metadata strategy decided (open question §3 below).

### Flagged tensions in this recommendation

- **Enumeration strategy** (Disagreement §1) affects the index script's design. Must be resolved before implementation.
- **Diagram metadata** (Disagreement §3) affects what doc-audit can mechanically check. Must be resolved before diagram tasks begin.
- **Index script location** (Disagreement §4) affects whether consumers can regenerate. Must be resolved before the script is created.
- **Hook refactor timing** (Disagreement §6) — recommended as Phase 0, but the user may choose to parallelize or defer.

### Confidence: 0.78

Strong convergence on direction and structure. The 0.78 (not higher) reflects four genuine open questions that affect implementation details, plus the End-User's markdown-format dissent which, if overridden, should be acknowledged with a debugging-UX mitigation (e.g., a human-readable `--pretty` flag on the index script).

---

## Open Questions

### OQ1 — Index enumeration: allowlist or exclusion-list?

**Architect** (exclusion-list, hardcoded in script) vs **Data** (allowlist, config-file driven).

Data's allowlist-with-config is more defensive (fails closed), but adds a maintained config file. Architect's exclusion-list is simpler but fails open. The user must decide the acceptable failure mode. Data's `doc-audit` unrecognized-file check partially mitigates the allowlist's false-exclude risk.

### OQ2 — Index format: override End-User's markdown preference?

**Architect + Data + Security** (YAML) vs **End-User** (markdown).

If YAML wins (3-of-4 + a concrete security argument), consider End-User's debugging concern: add a `--pretty` or `--human` output mode to the index script that renders a readable summary, so the solo dev can inspect doc-writer's scope without parsing YAML manually.

### OQ3 — Diagram metadata: none, describes field, or verification footer?

**Architect** (none — filename is enough) vs **Data** (`describes` field in index for mechanical drift detection) vs **End-User** (in-diagram `Last verified` footer for reader trust + machine checking).

These are partially composable: the `describes` field and the verification footer serve different purposes (drift detection vs reader signal) and could coexist. But Architect's "no metadata" position must be explicitly overridden if either is adopted. The user must decide: (a) no metadata (accept LLM-only drift detection), (b) `describes` field only (mechanical drift, no reader signal), (c) footer only (reader signal, weaker drift detection), or (d) both (strongest guarantees, highest maintenance).

### OQ4 — Index script location: .owlbear/scripts/ or synced path?

**Architect** (`.owlbear/scripts/`) vs **End-User + Security** (synced path like `setup/` or `serve/`).

Depends on whether consumer projects regenerate their own doc-index. M2 outcome 1 says "In consuming projects, OwlBear-shipped paths are marked" — this implies consumers DO have their own index, which implies they need the generator script. If so, it must ship in a synced path.

### OQ5 — Deletion mechanism: DR or kanban task?

**Architect** (DR via scribe, allows sweep-phase aggregation) vs **Data + End-User + Security** (per-file kanban task, no aggregation).

Secondary question: **Data** requires inbound-link repair to be transactional with deletion (single commit). **Security** requires agent-executable file deletions to route through architect review. These add-ons are compatible with either mechanism but affect task/DR template design.

### OQ6 — Hook refactor: blocking prerequisite or parallel workstream?

**Security** says blocking. Others are silent.

Security's consumer-safety argument is concrete: the current hook permits writes to consumer source directories. The refactor is small. Recommendation is Phase 0 (see above), but the user may judge the probability too low to block on. If deferred, the user accepts the residual risk for consumer projects until the refactor ships.
