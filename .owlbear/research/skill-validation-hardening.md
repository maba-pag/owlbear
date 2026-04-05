# Skill Validation Hardening with Agent Skills Spec + deer-flow Patterns

> **Owning task:** #511 — Harden skill validation with deer-flow patterns
> **Date:** 2026-04-01 **Status:** Complete

## 1. Context and Question

OwlBear's `scripts/validate_skills.py` delegates to `scripts/skills_ref/validator.py`, which only checks: (1) required `description` field, (2) `name` matches directory name. No naming convention enforcement, no max length, no description safety. The task asks whether deer-flow's validation patterns align with the official spec and should be adopted.

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| Agent Skills Specification (agentskills.io) | agentskills.io/specification | Authoritative — defines name rules (hyphen-case, 1-64 chars, no leading/trailing/consecutive hyphens), description max 1024 chars (.95) |
| VS Code Agent Skills docs | code.visualstudio.com/docs/copilot/customization/agent-skills | Confirms spec: "Must be lowercase, using hyphens for spaces. Maximum 64 characters. Must match parent directory name." (.90) |
| deer-flow `validation.py` (MIT) | github.com/bytedance/deer-flow → `backend/packages/harness/deerflow/skills/validation.py` | Implementation reference — regex `^[a-z0-9-]+$`, angle-bracket rejection, max 1024 desc (.85) |
| OwlBear broad survey S2D | docs/research/deer-flow-broad-survey.md | Prior analysis recommending adoption (.75) |

## 3. Analysis

### Naming convention rules

| Rule | Official Spec (agentskills.io) | deer-flow impl | OwlBear current | Gap? |
|------|-------------------------------|-----------------|-----------------|------|
| Lowercase + digits + hyphens only | Yes (`a-z`, digits, hyphens) | `^[a-z0-9-]+$` | Not checked | **Yes** |
| No leading/trailing hyphen | Yes | Explicit check | Not checked | **Yes** |
| No consecutive hyphens | Yes | `"--" in name` | Not checked | **Yes** |
| Max 64 characters | Yes | `len(name) > 64` | Not checked | **Yes** |
| Name matches directory | Yes | Checked | Checked ✓ | No |

### Description safety

| Rule | Official Spec | deer-flow impl | OwlBear current | Gap? |
|------|--------------|-----------------|-----------------|------|
| Max 1024 characters | Yes | Checked | Not checked | **Yes** |
| No HTML/angle brackets | Not in spec | `"<" in desc or ">" in desc` | Not checked | **Yes** (defense-in-depth) |

### Current OwlBear compliance audit

All 22 existing skills pass the proposed rules:
- All directory names match `^[a-z0-9-]+$`
- None start/end with hyphens or contain consecutive hyphens
- All names ≤ 64 characters (longest: `architecture-standards` at 23 chars)
- No descriptions contain angle brackets
- No descriptions exceed 1024 characters

### Where to add the rules

The validation lives in two layers:
- `scripts/skills_ref/validator.py` — spec-level validation (shared reference library)
- `scripts/validate_skills.py` — OwlBear wrapper (vendor field filtering)

Naming convention and max length are **spec rules** → add to `skills_ref/validator.py`.
Description safety (angle brackets) is **OwlBear-specific hardening** → add to `validate_skills.py` or `validator.py` (builder's choice — both are reasonable).

## 4. Recommendation (.85 confidence)

**Adopt all proposed rules.** The naming convention and max length are mandatory per the official Agent Skills Spec — OwlBear's validator is currently non-compliant with the spec it claims to implement. The angle-bracket check is a low-cost defense-in-depth addition from deer-flow (MIT).

**Tier: T1 (Autonomous).** This enhances an existing validation script with rules already defined by the spec. No new capabilities, no architecture changes, no pipeline modifications.

**Implementation notes:**
- Regex pattern: `^[a-z0-9]+(-[a-z0-9]+)*$` (stricter than deer-flow's — inherently rejects leading/trailing/consecutive hyphens)
- Or use deer-flow's approach: `^[a-z0-9-]+$` + explicit edge-case checks (more readable error messages)
- Description check: simple `"<" in desc or ">" in desc` — no regex needed
- All existing skills already comply — zero migration effort

## 5. Follow-up Tasks

Task #511 AC is well-specified and directly actionable. No additional tasks needed — the existing AC covers all identified gaps. The architect can approve as-is.
