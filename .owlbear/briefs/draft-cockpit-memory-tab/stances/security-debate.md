# Security Stance — Critic Debate Log

## Cycle 1

### Draft Position Summary

1. Path Traversal — HIGH: slug-based filename manipulation could escape memory dir.
2. XSS via Markdown — MEDIUM: agent-generated content could contain script.
3. YAML Deserialization — LOW: safe mode + content bound.
4. State Machine Integrity — MEDIUM: backend must enforce transitions.
5. CSRF / Cross-Origin — LOW-MEDIUM: no auth means no CSRF token.
6. Race Conditions — LOW: mtime-based optimistic concurrency.
7. Input Validation — MEDIUM: enforce bounds beyond Pydantic types.

### Critic Challenges (Cycle 1)

**XSS underrated:** Draft labeled MEDIUM. Critic argued: if script executes in cockpit origin, attacker has full read/write over ALL cockpit APIs. This is whole-origin compromise, not a localized display bug. Severity should be HIGH/CRITICAL. **Accepted — elevated to HIGH.**

**Path traversal aimed at wrong primitive:** Draft focused on slug character injection. Critic noted the actual engine uses id→path maps, not slug-addressed mutations. The real concern is trust in the id→path association, symlinks, and TOCTOU — not classical client-supplied path input. **Accepted — reframed around id-addressing and containment checks.**

**Cross-origin model wrong:** Draft treated as CSRF (session riding). Critic noted: no session exists. The real gate is whether mutations force CORS preflight via JSON content-type requirement. Local processes are outside CORS entirely. **Accepted — reframed as loopback reachability.**

**YAML parser assumption wrong:** Draft assumed ruamel.yaml and cited 1024-char content cap. Critic noted: engine may use PyYAML safe_load, and the 1024 cap is on content only — frontmatter is unbounded on disk. **Accepted — parser-agnostic stance, file size bound added.**

**State machine underscoped:** Draft treated as workflow correctness. Critic argued: state changes alter trust, visibility, and dissemination to other agents. Blast radius of unauthorized approve is broader than workflow. **Accepted — elevated to MEDIUM-HIGH.**

**Race condition mis-focused:** Draft emphasized file corruption. Critic noted temp-file-plus-replace already handles that. Real risk is stale semantic overwrite. **Accepted — reframed around optimistic concurrency.**

**Blind spots identified:**
- Immutable field integrity absent (id, source_agent, timestamps must be server-owned) — **Added to stance.**
- Non-script markdown hazards (remote images, external links) — **Added as separate lower-severity item.**
- Storage root authority unclear — **Addressed via containment check requirement.**
- Logic drift as first-order security concern — **Added as its own section.**

**Critic confidence:** 0.61 | **Pressure:** high

---

## Cycle 2

### Revised Position Summary

Restructured to 8 risks, elevated XSS to #1 HIGH, reframed file I/O around id-addressing, added logic drift and immutable fields.

### Critic Challenges (Cycle 2)

**Transition table still wrong:** Stance listed legal transitions but omitted `pending→curated` (auto-promote when scope_agents provided). This is in the existing engine contract. **Accepted — added to canonical transition table.**

**Path traversal overranked given id-addressed routes:** Since mutations use UUID path params (per feature brief), classical traversal is not the primary vector. The live concern is trust in id→path map integrity. Severity framing adjusted but containment checks retained. **Partially accepted — kept HIGH because hard-delete is irreversible, but reframed the threat description.**

**id→path map has no duplicate/stale behavior defined:** Stance said "scan once" while acknowledging concurrent writers. Duplicate ids and stale maps are the real integrity gap. **Accepted — noted that map must be refreshed, not long-lived cache without invalidation.**

**scope_agents validation breaks existing contract:** Stance proposed alphanumeric-only rule, but existing engine supports `*` wildcard. This creates compatibility failure, not security improvement. **Accepted — removed strict grammar, defer to existing model contract.**

**Localhost CORS overclaims what preflight buys:** Preflight only gates browser-based attacks. Local processes and extensions bypass CORS entirely. The mitigation is useful but the threat-model framing was overstated. **Accepted — added explicit statement that local processes are trusted peers.**

**XSS bundles distinct threat classes:** Script execution (whole-origin compromise) lumped with remote image beacons (privacy/exfiltration). Different severity, should be separated. **Accepted — separated in final stance.**

**Logic drift smuggles architecture refactoring:** Elevating shared package extraction as preferred answer is a scope change, not a security requirement. The security requirement is identical test coverage. **Accepted — reframed as maintenance cost with testing mitigation.**

**Additional blind spots:**
- Upstream contradiction on approve-from-pending ("skip curate" vs curated-only approval in engine) — **Named explicitly in final stance.**
- New validation rules beyond existing model contract risk compatibility failures — **Added warning.**
- Duplicate-id and non-object-frontmatter handling — **Noted in YAML section.**

**Critic confidence:** 0.74 | **Pressure:** high

---

## Resolution

Position hardened across both cycles. Key shifts from initial draft:
- XSS elevated from MEDIUM to HIGH (whole-origin blast radius)
- Path traversal reframed from slug injection to id→path trust + containment
- State machine elevated from MEDIUM to MEDIUM-HIGH (trust-bearing transitions)
- Cross-origin reframed from CSRF to loopback reachability
- Logic drift added as independent concern
- Immutable fields added as server-owned constraint
- Validation rules aligned to existing engine contract (no over-tightening)

Final confidence: 0.85
