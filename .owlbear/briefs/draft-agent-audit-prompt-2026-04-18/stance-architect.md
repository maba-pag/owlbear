# Architectural Stance — Agent-Audit Prompt Rewrite

**Panelist:** Architect
**Confidence:** 0.88
**Critic rounds:** 3 (all critical challenges resolved; 2 moderate issues acknowledged as limitations)

---

## 1. Approach: Rewrite-with-Current-as-Inspiration

The current prompt has well-proven content that must carry forward: six audit dimensions with concrete operational checks (especially Pipeline Integrity's rejection-routing tables), the finding presentation protocol (facts → options → recommendation → approval), dynamic file discovery, and the standards-first loading approach.

However, three structural gaps — memory governance, continuous loop mechanic, and negative-space methodology — require changes that touch every section. A rewrite-with-inspiration is preferred over in-place patching because the "start clean, lift deliberately" mindset avoids accidentally preserving patterns obsoleted by the new loop mechanic (batch REMEDIATION PLAN, batch FINDINGS with IDs, rigid output template). Whether you call the approach "heavy patch" or "rewrite" matters less than the target structure — but starting clean reduces accidental preservation.

**What carries forward (specific, not vague):**

- All 6 current dimension check-lists — especially Pipeline Integrity's concrete routing rules: reviewer severity-based targeting, builder cause-based routing, architect REJECT-to-ideation, auditor always-backlog, BLOCK/BLOCKED prohibition, agent rename consistency
- Finding presentation protocol: facts → options → recommendation → approval
- "Read ALL files first" instruction
- Dynamic file discovery via file_search (no hardcoded file lists)
- Verification traces: implementation task, non-implementation task, rejection routing, SNR spot-check

**What is discarded:**

- Batch FINDINGS section with IDs (replaced by per-finding on-the-fly presentation)
- Batch REMEDIATION PLAN (replaced by continuous loop)
- Rigid output format template (findings are presented individually, not batched)
- "Save plan to session memory" as a standalone step (replaced by lightweight running bookkeeping)

## 2. Section Architecture (5 Sections)

| Section | Purpose | Why this exists |
|---------|---------|-----------------|
| **Preamble** | Role, stakes, askQuestions mandate, behavioral contract | Sets the auditor's identity and non-negotiable interaction rules |
| **Audit Surface & Standards** | Three-surface discovery model + standards loading order with per-dimension citation | Ensures complete coverage and correct authority for findings |
| **Audit Dimensions** | 7 dimensions with dual-direction probes | The actual quality checks — what to look for and what's missing |
| **Process** | Complete control loop in one place | Scan → remediate → re-scan cycle with bookkeeping |
| **Verification** | End-of-cycle integrity checks | Confirms the audit's own completeness |

The control loop (scan/remediate/re-scan, finding presentation, queue triage, bookkeeping) lives in ONE section — Process — not scattered across multiple. This was a Critic challenge that exposed the coherence risk of splitting execution mechanics.

## 3. Audit Dimensions: 7, with Authority Citations

### Existing 6 (carried forward, enhanced with negative-space probes)

| # | Dimension | Authority | Negative-space probe |
|---|-----------|-----------|---------------------|
| 1 | Structural violations | h-agent-structure | "List all pipeline statuses. For each, verify a handler agent exists." Two instruction-file classes: stubs (4 defined in h-agent-structure) checked for format; authority files (`owlbear-system.instructions.md`, `agent-common.instructions.md`) checked for content quality. |
| 2 | Duplication / Rule of Two | h-agent-structure | "For each agent's critical_rules references, verify the referenced skills exist." |
| 3 | Content placement / 80% rule | h-agent-structure (Loading Model) | "For each item in copilot-instructions.md, verify ≥80% of agents need it." |
| 4 | Quality signals | h-agent-structure (Required Sections, Implicit Encoding) | "For each agent persona, list behaviors it encodes. Cross-check against that agent's critical_rules — are critical behaviors missing from the persona?" |
| 5 | Pipeline integrity | r-pipeline-protocol + r-project-standards + agent-common.instructions.md | "Walk the full pipeline path end-to-end. At each transition, verify both forward agent AND rejection routing are defined." All specific routing tables carry forward. |
| 6 | Signal-to-noise | General (no single authority) | Not applicable — SNR is about removing noise, not finding missing signal. |

### New: Dimension 7 — Memory Governance

| Authority | owlbear-system.instructions.md (§4 Memory Governance) + r-pipeline-protocol (§4 Post-task Reflection) |
|-----------|---|
| What to check | Governance boundary compliance, content quality, reflection compliance, dual-write state |
| Negative-space probe | "For each tier in the governance boundary table, verify actual content matches declared scope. For each pipeline agent, verify post-task reflection artifacts exist." |

Memory has unique rules (governance boundary table, dual-write migration, cross-store referencing) that don't map to any existing dimension. Folding it into Content Placement would bury its distinct concerns.

### Instruction File Distinction

h-agent-structure defines "instruction stubs" and their 3-line format for 4 specific files. It does NOT define a broader "authority instruction file" class. Two instruction files (`owlbear-system.instructions.md`, `agent-common.instructions.md`) are demonstrably not stubs. The audit acknowledges this taxonomy gap:

- **Stubs** (python, frontend, research-docs, agents-and-skills): check 3-line format compliance per h-agent-structure.
- **Authority files** (owlbear-system, agent-common): check content quality, inter-file consistency, and accuracy of references to skills/standards. Do NOT apply stub format rule.
- **Unclassified instruction files** (neither defined stub nor known authority): flag as a structural finding.

## 4. Three-Surface Discovery Model

The audit covers three distinct surfaces with different access semantics:

| Surface | Contents | Discovery | Read | When |
|---------|----------|-----------|------|------|
| **File** | Agents, skills, instructions, copilot-instructions | `file_search` | `read_file` | Always |
| **Memory** | `/memories/`, `/memories/repo/inbox/`, `/memories/session/` | `memory view /memories/` | `memory view <path>` | Always |
| **MCP** | owlbearMemory store | `list_entries()` | `get_knowledge()`, `list_entries(agent_id=...)` | When available |

The file surface and memory surface are always available. The MCP surface requires owlbearMemory tools in the tool allowlist.

### MCP Availability Logic

MCP is documented as canonical (owlbear-system.instructions.md §4), with file inbox as fallback (r-pipeline-protocol §4). The audit respects this hierarchy:

| MCP state | Audit behavior |
|-----------|---------------|
| **Unavailable** (tools not in allowlist, or call fails) | Audit file-based stores only. Note MCP unavailability as informational context, not a finding. |
| **Available, empty** | During dual-write migration, empty is expected. Note as informational. Check file-based stores for content that should have been dual-written (but don't flag — migration is in progress). |
| **Available, has data** | MCP is the canonical surface. Audit MCP content quality. Cross-reference with file inbox for dual-write compliance. |

This respects the documented hierarchy (MCP canonical, files fallback) without creating false positives during migration. The audit prompt is forward-compatible: as MCP becomes the primary store, the audit naturally shifts its weight to the MCP surface.

## 5. Process: Scan-Remediate-Rescan

```
SCAN PHASE
├── Discover all three surfaces (file, memory, MCP)
├── Load standards per loading order
├── Read all discovered files/entries
├── Build prioritized findings queue (each finding gets ID: F1, F2, ...)
├── Present summary: "Found N findings across M dimensions"
└── askQuestions: "Proceed with remediation? / Bail?"

REMEDIATE PHASE (loop)
├── Present finding: facts → options → recommendation
├── askQuestions: approve / modify / skip / bail
├── If approved: implement → verify fix
├── Triage remaining queue: invalidate findings whose root cause was addressed
├── Update running summary in session memory
└── Next finding (or exhausted)

RE-SCAN PHASE
├── askQuestions: "Findings exhausted. Run from the top?"
├── If yes: re-discover, re-read, build new queue
│   (Convergence signal: fewer findings than previous cycle = positive)
│   (Zero new findings = audit complete)
└── If no: produce final summary with all finding dispositions
```

The scan phase is essential — not optional — because it enables priority ordering and root-cause deduplication. Without scanning first, findings arrive in arbitrary file-reading order and cross-file patterns are missed.

After each fix, queue triage is lightweight: check remaining findings for invalidation by the fix. The full re-scan at cycle end catches anything the triage missed.

**Bookkeeping:** Each finding gets a sequential ID. Session memory tracks a running disposition table: `F{n} | dimension | file | disposition (fixed/skipped/invalidated)`. End-of-cycle summary consolidates.

**askQuestions protocol:** ALL user-facing turns use askQuestions. No exceptions. Finding presentations, cycle transitions, bail offers — all via askQuestions. This is a non-negotiable behavioral rule stated in the Preamble and enforced throughout Process.

## 6. Negative Space: Dual-Direction per Dimension

Each dimension checks both directions:

- **Bottom-up (what's wrong):** Scan existing files/entries for violations of the dimension's authority.
- **Top-down (what's missing):** Check that expected elements exist, using the authority as the expectation source.

This is embedded in each dimension's specification, not a separate phase. This avoids two-pass architecture and means negative-space analysis naturally informs priority ordering.

Calibration by objectivity:

| Dimension type | Negative-space technique |
|----------------|------------------------|
| **Objectively enumerable** (pipeline transitions, agent roster, memory tiers, stub list) | Set-based probes: enumerate the expected set from the authority, verify each element exists |
| **Subjectively assessable** (quality signals, SNR) | Comparative probes: ground assessment in the file's own declared rules (e.g., "does this persona encode all behaviors listed in its critical_rules?") |

### Memory Content Quality Heuristics

No authority defines thresholds for "stale," "contradictory," or "duplicated" memory entries. The audit uses practical heuristics:

- **Stale:** references files, agents, skills, or conventions that no longer exist in the workspace
- **Contradictory:** entries scoped to the same agent that give opposing advice for the same situation
- **Duplicated:** entries that express substantially the same learning (same root insight, different wording)

These are common-sense quality criteria that don't require an authority citation.

## Key Trade-offs

| Decision | Trade-off | Why this side |
|----------|-----------|---------------|
| Rewrite vs. patch | Regression risk vs. coherence risk | Rewrite — gaps touch every section; "lift deliberately" is safer than "hope nothing breaks" |
| 7 dimensions vs. fold memory into existing | Cognitive load vs. audit thoroughness | 7 — memory has unique rules orthogonal to content placement |
| Scan-first vs. stream | Upfront cost vs. priority quality | Scan-first — can't prioritize without the full picture |
| Three surfaces vs. two | Complexity vs. correctness | Three — memory file system and MCP have distinct access semantics |
| Explicit negative-space probes vs. general instruction | Prompt size vs. audit reliability | Explicit — "find what's missing" is too vague without per-dimension probes |

## Warnings

1. **Instruction file taxonomy gap.** h-agent-structure does not define an "authority instruction file" class. The audit works around this pragmatically but the gap should eventually be closed in h-agent-structure itself.

2. **Memory quality heuristics are uncited.** The staleness/contradiction/duplication checks are common-sense, not authority-backed. If the memory store grows, these may need codified thresholds.

3. **MCP migration creates a moving target.** The audit's forward-compatibility relies on probe-based adaptation. If the MCP API changes (new tools, different semantics), the memory dimension's MCP sub-section will need updating.

4. **Queue invalidation is a heuristic, not a proof.** After a fix, the auditor decides which remaining findings are invalidated. Misjudgment can drop findings. The end-of-cycle re-scan is the safety net.
