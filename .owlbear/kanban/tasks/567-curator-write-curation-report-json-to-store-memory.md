---
id: 567
title: 'Curator: write curation-report.json to store/memory/'
status: todo
priority: important
created: 2026-04-03T10:25:09.2481537+02:00
updated: 2026-04-05T10:22:35.982191+02:00
tags:
    - scope:agents
    - phase-2
    - agent
depends_on:
    - 530
class: standard
---

When curator completes a curation cycle, write a structured JSON report to store/memory/curation-report.json containing entry IDs with recommendations. Per .owlbear/research/approve-memory-cli-wrapper.md 3C.

AC:
- [ ] w-mem-curation SKILL.md Step 5 updated: curator writes store/memory/curation-report.json before appending task body
- [ ] Format: top-level JSON array of {entry_id, content_preview, recommendation, reason} per approve.py _load_curation_report preferred format
- [ ] File is overwritten each cycle (latest report only)
- [ ] Verify: approve.py _load_curation_report() in serve/mcp-memory/src/owlbear_mcp_memory/approve.py already reads this path and format correctly (no code changes needed)

Target file: share/skills/w-mem-curation/SKILL.md (Step 5 Deliverables)

## Research
Validation pass on existing research: .owlbear/research/approve-memory-cli-wrapper.md section 3C, .owlbear/research/curator-curation-report-json.md.

Key findings:
- Consumer exists: approve.py _load_curation_report() reads db_path.parent / curation-report.json, resolves to store/memory/curation-report.json
- Supports two formats: top-level JSON array with entry_id key (preferred) and legacy dict with id key
- Curator skill w-mem-curation Step 5 writes report to task body but NOT to JSON file
- store/memory/ is the canonical memory data location (migrated from data/memory/)
- Implementation: curator skill needs Step 5 addition to write JSON file after curation

Classification: T1 autonomous (add JSON output to existing curation workflow)
Confidence: .90
Follow-up tasks: none needed (this task IS the implementation)

[[2026-04-04]] Sat 23:12
Research complete (.90). T1 autonomous. Consumer exists in approve.py, curator skill needs JSON output step. See .owlbear/research/approve-memory-cli-wrapper.md 3C.

[[2026-04-05]] Sun 10:22
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One change: add JSON report writing to curator skill Step 5 |
| Interface clarity | PASS (after refinement) | Stale data/memory/ paths corrected to store/memory/; JSON schema aligned with approve.py consumer |
| Dependency correctness | PASS | #530 archived. #531 (approve_memory CLI) also archived; consumer _load_curation_report handles array format with entry_id key (approve.py L101) |
| Module layering | PASS | Skill file update only; no code dependencies |
| TDD compliance | N/A | Non-impl task (skill markdown change, tagged agent) |
| KISS/YAGNI | PASS | Minimal Step 5 addition; convention-based JSON file is simpler than cross-MCP coupling |
| Premise challenge | PASS | No existing mechanism writes machine-readable curation output; task body (Channel B) is human-readable only |
| Pattern consistency | PASS | Follows existing w-mem-curation step structure; JSON schema matches approve.py expectations |
| Security surface | PASS | File write scoped to store/memory/; no untrusted input; curator writes own assessment data |
| Single domain | PASS | agents domain only (scope:agents tag) |

### Refinements Applied

1. Title: data/memory/ corrected to store/memory/ (directory reorg already landed)
2. AC1: Specifies target file (w-mem-curation SKILL.md Step 5) and correct path
3. AC2: Explicitly names preferred format matching approve.py array branch
4. AC4: Rephrased as verification criterion (consumer already exists, no code changes needed)
5. Body: All data/memory/ references updated to store/memory/
6. Added agent pass-through tag (non-impl: skill markdown change only)

### Challenge Results

- Challenger: reconsider (confidence 0.88)
- Key challenges: (C1) #531 format bug as hard blocker; (C2) stale data/memory/ paths
- Architect response:
  - C1 REBUTTED: #531 is archived (completed). approve.py L101 handles array format with entry_id key. Challenger used stale info from research doc written before #531 landed.
  - C2 ACCEPTED: All paths corrected from data/memory/ to store/memory/ in title, AC, and body.

### Verdict: APPROVE (REFINE then approve)
### Action Taken: Corrected stale paths, refined AC for verifiability, added agent tag, moved to todo

[[2026-04-05]] Sun 10:22
APPROVED #567: Corrected stale data/memory/ paths to store/memory/, refined AC for verifiability, added agent pass-through tag. Challenger rebutted on #531 blocker (already archived). Skill-only change to w-mem-curation Step 5.
