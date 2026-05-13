# Security Stance — Structured Task Specification Fields

## Security Stance

This design is fundamentally sound for a laptop-resident, single-user system. No confidentiality or availability risks. All concerns are **integrity-class**: ensuring that the values agents rely on for verification routing are correct, consistent, and validated.

The primary risk is not YAML injection, not DoS, and not filesystem bypass in isolation. It is **split-brain consistency during the transition period** — a window where body-reading and frontmatter-reading consumers see different values for the same field.

## Risk Assessment

### 1. Split-Brain Authority (HIGH)

**The finding:** Current agents (w-tdd-red, w-tdd-green, w-code-review, w-arch-review, w-task-decomposition) read proof_bundle and AC from the task body via string matching. The dispatch clarity gate (dispatch.py) checks body AC. Adding frontmatter fields creates a second source of truth. During the transition period:

- An architect sets `proof_bundle: behavioral` in frontmatter
- The body still says `Proof bundle: skip` (or says nothing)
- A body-reading agent sees "skip" and reduces verification depth
- A frontmatter-reading consumer sees "behavioral" and expects full tests

This is the highest-integrity risk in the design. It is not theoretical — it is the guaranteed state of every existing task until either migrated or agent skills are updated.

**Mitigation requirements:**
- The Brief must specify which source is authoritative and when consumers switch. Forward-only with "agent improvisation" is insufficient — it leaves the authority question unanswered.
- Agent skill updates (body → frontmatter reading) should ship in the same release as the schema change, not as a follow-up sweep.
- Migration script should be promoted from "optional" to "first-run recommended." A clear-cut switchover beats a prolonged dual-authority window.

### 2. proof_bundle Integrity (HIGH)

**The finding:** proof_bundle is integrity-relevant routing metadata. It determines:
- Test scope and count (w-tdd-red)
- Challenger involvement (r-pipeline-protocol)
- Review depth (w-code-review)

A wrong value directly reduces verification rigor. There is no role-based enforcement — any agent or the Cockpit UI can change it. The source label on edit events is free-form text, not a verified identity.

**What this is not:** It is not an authorization boundary in the RBAC sense. The system has no actor model. But it functions as a verification-depth selector, and getting it wrong has real downstream impact.

**Mitigation requirements:**
- Strict `Literal` validation on base values (`skip | existing | smoke | behavioral | critical`). Not regex — closed enum.
- Modifiers (`+challenge`, `+reader`) should also validate against a closed set. The current `r-pipeline-protocol` taxonomy defines exactly two modifiers.
- Write-time validation in `edit_task` — reject invalid values at the engine API, not just at model construction. This prevents silent task exclusion (see Risk 3).

### 3. Silent Task Exclusion on Invalid Fields (HIGH)

**The finding:** The engine's corruption handling catches `CorruptionError` and silently excludes malformed tasks from views and dispatch (engine.py:670, 692, 706, 715). If a direct file write (or a bug) produces an invalid `proof_bundle` value, the task does not "fail loudly" — it disappears from `list_tasks`, `pick_tasks`, and board views.

This is worse than a validation error. A missing task is harder to notice than an error message.

**Mitigation requirements:**
- Validate `proof_bundle` and `ac` at write time in `edit_task` and `create_task`, not just at deserialization. Write-time validation catches bad values before they reach storage.
- Consider distinguishing field-validation errors from structural corruption in the engine's error handling — a typed field with an invalid value is a fixable edit, not a corrupt file.

### 4. AC Manipulation After Test-Writing (MEDIUM)

**The finding:** AC drives what gets tested (w-tdd-red creates tests from AC) and what gets verified (w-code-review maps evidence to AC lines). If AC is modified after tests are written — items removed, weakened, or reworded — the verification pipeline may pass on criteria that were never actually tested.

**Practical severity:** Medium because this requires either intentional manipulation or a workflow error. Agents follow pipeline conventions, and the user reviews results. But the gap between "tests written from AC v1" and "review verifies against AC v2" is a real integrity concern.

**Mitigation requirements:**
- Include changed-field names in the `edit_task` activity event detail string (e.g., `"edited: ac, proof_bundle"`). This is achievable within the current activity schema without structural changes.
- Document that AC should be stable after task enters in-progress. Enforcement is procedural (skill instructions), not mechanical.

### 5. YAML Injection via AC Strings (LOW)

**The finding:** The serialization path (Pydantic `model_dump()` → ruamel.yaml `dump()`) and deserialization path (ruamel.yaml `load()` → Pydantic `model_validate()`) both handle YAML special characters correctly. ruamel.yaml quotes strings containing `:`, `{`, `[`, `#`, etc. Pydantic validates types on ingress. There is no string concatenation or template injection path.

**Mitigation requirements:**
- None beyond existing mechanisms. The Pydantic + ruamel.yaml pipeline is safe.
- Max-length on individual AC strings (500 chars) and max-items on the list (20 items) are reasonable defense-in-depth but not security-critical.

### 6. Shadow Keys via extra='allow' (LOW)

**The finding:** The Task model's `extra='allow'` preserves unknown YAML keys through round-trips. A typo like `proof_bundel` or `acceptance_criteria` would be stored as an extra field while the canonical typed field uses its default. This creates ambiguous state — the file appears to have a value, but the model doesn't see it.

**Mitigation requirements:**
- Awareness-level concern only. Document canonical field names clearly. The engine already handles extras correctly for serialization.

### 7. Migration Data Loss (MEDIUM)

**The finding:** Forward-only migration means old tasks retain AC in the body. If a body edit removes the `## Acceptance Criteria` section (intentionally or accidentally), that AC is lost. With frontmatter AC, this cannot happen (frontmatter is structurally separate from body).

**Mitigation requirements:**
- Promote migration script from "optional" to "recommended, run once on deployment."
- The migration script should be idempotent — safe to run multiple times.
- Consider a pre-migration backup (copy task files before modifying them).

## Compliance Implications

None. OwlBear is a laptop-resident, single-user development tool. No regulatory frameworks apply. No PII is stored in AC or proof_bundle fields. No data crosses trust boundaries.

## Least-Privilege Recommendations

1. **Write-time validation over read-time detection.** Validate proof_bundle and ac in `edit_task`/`create_task` before writing to disk. Don't rely on deserialization to catch bad values.
2. **Atomic authority switchover.** Ship agent skill updates (body → frontmatter reading) with the schema change, not after. No dual-authority window.
3. **Strict enum, not regex.** proof_bundle base values and modifiers should both use closed-set validation. Open regex permits values the taxonomy doesn't define.
4. **Audit trail within existing capabilities.** Include changed-field names in edit event detail text. Don't over-engineer field-level audit logs.

## Warnings

1. **Do not ship schema without skill updates.** If frontmatter fields land but agents still read body text, split-brain is not a risk — it's a certainty.
2. **"Optional migration" is a split-brain factory.** Every unmigrated task is a dual-authority task. Promote to recommended.
3. **Silent exclusion is the failure mode, not loud errors.** An invalid proof_bundle value makes a task invisible, not invalid. The Brief should address this in the engine validation design.

## Confidence

**0.78** — Revised upward from initial 0.82 draft after Critic exposed the split-brain and silent-exclusion blind spots, which were incorporated. Downward pressure from the Critic's evidence on current engine corruption handling and the gap between recommended mitigations and current activity-log capabilities. The core positions are now grounded in verified system behavior, not assumptions.
