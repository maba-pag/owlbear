# Architect Debate Log — Body Newline Normalization

## Cycle 1

### Draft Position

1. Standalone `_normalize_body_newlines(text: str) -> tuple[str, bool]` helper in `server.py`
2. Pre-process before engine call, inject flag into guidance after
3. Do NOT extend `collect_guidance()` — keep normalization guidance inline
4. False-positive risk is negligible (simplifier agreed)
5. `create_task` needs guidance wiring added (pre-existing gap)
6. `create_dr`: normalize silently without guidance
7. No coupling with `body_parser.py`
8. First-principles "wrong layer" rebutted

Confidence: 0.88

### Critic Challenges (Cycle 1)

1. **Tuple helper not justified (moderate).** No tuple-return precedent in the codebase. Existing helpers (`_coerce_to_str`, `_record_to_task`) are single-value transforms. The flag can be obtained by a simple `"\\n" in text` check at the call site.

2. **Inline guidance creates a second assembly path (critical).** AgentView already returns guidance (body size warnings, skip-transition hints). `collect_guidance()` runs conditionally (`if not result.guidance`). A third inline source creates unacknowledged maintenance divergence. The "wrong category" argument is weaker than stated because `guidance.py` already mixes operation names, kwargs, and state.

3. **Silent `create_dr` undercuts the notification contract (critical).** `create_dr` writes human-facing DR files. Silent mutation with no retry path contradicts the locked D4 decision (normalize-and-notify). The DR body is persisted directly after frontmatter — visible to humans.

4. **False-positive risk understated (critical).** The Critic found actual instances of intentional literal `\n` in archive task bodies outside code fences. "No semantic purpose in markdown" is too strong — repo evidence contradicts it.

5. **Test surface blindspot.** Existing MCP tests pin exact forwarded body strings. This is a contract change requiring explicit test updates.

6. **Locked decisions contradicted.** Dismissing the escape convention and false-positive concern conflicts with locked D4 without naming the conflict.

### Revisions After Cycle 1

- Dropped tuple helper → simple `_normalize_escaped_newlines(text: str) -> str` + `"\\n" in text` flag
- Changed from "second assembly path" to append-to-existing-list approach
- Reversed `create_dr` position → add `guidance` key to dict return
- Retracted "negligible" false-positive claim → real but mitigated by notify pattern
- Added test surface impact to scope
- Added tool description documentation requirement
- Respected locked D4 decision on escape convention

### Position After Cycle 1

Confidence: 0.82

---

## Cycle 2

### Critic Challenges (Cycle 2)

1. **Escape convention is internally inconsistent (critical).** Code fences change rendering after write, not at ingress. MCP tools take plain strings. The claim that false positives are "recoverable" via code fence is not proven at the ingress level — the escape convention circularity identified in research-notes.md is real.

2. **Underspecified normalization surface (critical).** Position text used `body` in examples and concrete patterns. The locked surface is 5 parameters: `body` (create_task, edit_task, create_dr), `append_body` (edit_task), `note` (end_work). Adapter tests pin all of these. Easy for an implementer to ship body-only.

3. **Guidance ordering matters (moderate).** The `if not result.guidance` guard means normalization append must come AFTER the existing guidance wiring block, not before. If before, it populates the list, preventing `collect_guidance()` from running → suppresses DR/commit reminders.

4. **`create_dr` guidance is a special case, not contract reuse (moderate).** `create_dr` has no output schema patching, no parameter description patching, and tests assert exact dict equality. Adding `guidance` is a new field, not an existing contract.

5. **Per-parameter description patching (blindspot).** The server already has a per-parameter description patch surface for tool parameters. The normalization contract should also be documented there, not just in top-level docstrings.

### Revisions After Cycle 2

- Acknowledged escape convention circularity honestly — no clean escape path exists at the string level; guidance message is for transparency, not a functional retry mechanism
- Explicitly enumerated all 5 parameters in the position
- Specified guidance append ordering: AFTER existing `if not result.guidance` block
- Acknowledged `create_dr` guidance as a special-case addition
- Added per-parameter description patching to documentation scope

### Final Position

Confidence: 0.80
